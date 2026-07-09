"""Render a SongPlan into full-length mono layers for master().

Each section is rendered separately (riff variant / drum subset / bass / pads) and
overlap-ADDED into the song buffers at its bar offset — renders carry an 0.8s
release tail that must bleed into the next section rather than be cut (clicks).

Layer renderers reuse the riff dispatchers, so every layer gets the same
premium-first fallback chain (sfz/vst > SF2 > numpy) with zero new audio code:
  riff  -> riff_audio(riff.instrument)      looped per bar (drops = verbatim notes)
  bass  -> riff_audio("bass")               one-shot span (bars=1, bar_beats=span)
  pads  -> vst 'pad' patch, else SF2 "pads" GM preset
"""

from __future__ import annotations

import numpy as np

from ..audio import SR, seconds_per_beat
from ..sequence import Riff
from . import Section, bass_notes, choose_progression, pad_notes, plan_song, riff_variant
from ..render import riff_audio
from ..render.drums import DRUM_PATTERNS
from ..render.sf_render import default_soundfont, render_riff_sf
from ..render import vst_render
from ..mixmaster import kick_onsets_from_pattern

# voices that keep playing in "lite" drum sections (no kick/snare/sub weight)
_LITE_VOICES = {"hatC", "hatO", "shaker", "rim", "cowbell"}


def _lite_pattern(pattern: dict) -> dict:
    return {k: v for k, v in pattern.items() if k in _LITE_VOICES}


def _render_pads(notes, tempo: float, span_beats: float, sr: int) -> np.ndarray:
    if vst_render.SURGE_VST3.exists():
        return vst_render.render_patch(notes, tempo, "pad", 1, span_beats, sr)
    if default_soundfont():
        return render_riff_sf(notes, tempo, "pads", 1, span_beats, sr)
    return np.zeros(0, dtype=np.float32)  # no pad fallback worth hearing


def _add_at(buf: np.ndarray, sig: np.ndarray, start: int) -> None:
    end = min(len(buf), start + len(sig))
    if end > start:
        buf[start:end] += sig[: end - start]


def build_song(riff: Riff, sr: int = SR):
    """Arrange + render the full song.

    Returns (layers, kick_onsets, plan, prog):
      layers = {"riff","drums","bass","pads"} full-length mono float32 (empty
      arrays dropped), kick_onsets = pump triggers only where a full kit plays.
    """
    plan: list[Section] = plan_song(riff.tempo)
    prog = choose_progression(riff)
    spb = seconds_per_beat(riff.tempo)
    bar_s = riff.bar_beats * spb

    total_bars = sum(s.bars for s in plan)
    n = int((total_bars * bar_s + 1.0) * sr)
    layers = {name: np.zeros(n, dtype=np.float32) for name in ("riff", "drums", "bass", "pads")}
    kick_onsets: list[int] = []

    pattern = DRUM_PATTERNS.get(riff.drum_style) if riff.drum_style else None

    bar = 0
    for sec in plan:
        at = int(bar * bar_s * sr)
        span_beats = sec.bars * riff.bar_beats

        if sec.riff_variant:
            notes = riff.notes if sec.riff_variant == "verbatim" else \
                riff_variant(riff.notes, sec.riff_variant)
            if notes:
                sig = riff_audio(notes, riff.tempo, riff.instrument, sec.bars, riff.bar_beats, sr)
                _add_at(layers["riff"], sig, at)

        if sec.drums and pattern:
            pat = pattern if sec.drums == "full" else _lite_pattern(pattern)
            if pat:
                from ..render import drums_audio_pattern
                sig = drums_audio_pattern(riff.drum_style, pat, riff.tempo, sec.bars, sr)
                _add_at(layers["drums"], sig, at)
            if sec.drums == "full":
                kick_onsets += [at + o for o in
                                kick_onsets_from_pattern(pattern, riff.tempo, sec.bars, sr)]

        if sec.bass:
            notes = bass_notes(riff, prog, sec.bars)
            sig = riff_audio(notes, riff.tempo, "bass", 1, span_beats, sr)
            _add_at(layers["bass"], sig, at)

        if sec.pads:
            notes = pad_notes(riff, prog, sec.bars)
            sig = _render_pads(notes, riff.tempo, span_beats, sr)
            _add_at(layers["pads"], sig, at)

        bar += sec.bars

    layers = {k: v for k, v in layers.items() if float(np.max(np.abs(v))) > 1e-6}
    return layers, kick_onsets, plan, prog
