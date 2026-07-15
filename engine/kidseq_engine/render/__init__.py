"""Rendering: MIDI/notes -> audio.

Dispatchers prefer the real-sample soundfont renderer (sf_render) when a soundfont
is available, and fall back to the numpy synth so the pipeline always runs.
"""

from __future__ import annotations

import numpy as np

from ..audio import SR, as_stereo
from ..sequence import Note
from . import sample_kit, sfz_render, vst_render
from .drums import DRUM_PATTERNS, render_drums
from .sf_render import default_soundfont, render_drums_sf, render_riff_sf
from .synth import render_riff_looped

# Every dispatcher below returns stereo (N, 2). Native-stereo renderers (sfizz,
# Surge, tinysoundfont, panned sample kits) pass through; the numpy-synth fallbacks
# stay mono and are upmixed by as_stereo. master() and arrange/render assume (N, 2).


def riff_audio(notes: list[Note], tempo: float, instrument: str, bars: int,
               bar_beats: float = 4.0, sr: int = SR) -> np.ndarray:
    # Priority (Linux/Modal renderers first, each covers disjoint instruments):
    # sfz/sfizz (trumpet/strings/bells) & Surge VST (synth/bass) > SF2 > numpy synth.
    if sfz_render.sfz_available(instrument):
        out = sfz_render.render_riff_sfz(notes, tempo, instrument, bars, bar_beats, sr)
    elif vst_render.vst_available(instrument):
        out = vst_render.render_riff_vst(notes, tempo, instrument, bars, bar_beats, sr)
    elif default_soundfont():
        out = render_riff_sf(notes, tempo, instrument, bars, bar_beats, sr)
    else:
        out = render_riff_looped(notes, tempo, instrument, bars, bar_beats, sr)
    return as_stereo(out)


def riff_source(instrument: str) -> str:
    """Which renderer riff_audio will use for `instrument` — for smoke-test logging."""
    if sfz_render.sfz_available(instrument):
        return "sfz(" + sfz_render.library_name(instrument) + ")"
    if vst_render.vst_available(instrument):
        return "vst(" + vst_render.library_name(instrument) + ")"
    if default_soundfont():
        return "soundfont"
    return "numpy-synth"


def drums_audio(style: str, tempo: float, bars: int, sr: int = SR) -> np.ndarray:
    pat = DRUM_PATTERNS.get(style)
    # Priority: real CC0 one-shot kit (stereo-panned) > GM soundfont > numpy synth.
    if pat and sample_kit.kit_available(style):
        out = sample_kit.render_drums_samples(style, tempo, bars, sr)
    elif default_soundfont() and pat:
        out = render_drums_sf(pat, tempo, bars, sr, style=style)
    else:
        out = render_drums(style, tempo, bars, sr)
    return as_stereo(out)


def drums_audio_pattern(style: str, pattern: dict, tempo: float, bars: int,
                        sr: int = SR,
                        takes: dict[str, int] | None = None,
                        swing: float | None = None) -> np.ndarray:
    """drums_audio with an explicit (possibly subset) pattern — the arranger's
    lite/full section renders. Same renderer priority as drums_audio. `takes`
    swaps sample-kit voices to their KIT_ALTS alternates (sample path only —
    the soundfont/synth fallbacks have one voice each). `swing` overrides the
    per-style SWING map on every renderer path (R31 producer groove)."""
    if sample_kit.kit_available(style):
        out = sample_kit.render_drums_samples(style, tempo, bars, sr,
                                              pattern=pattern, takes=takes,
                                              swing=swing)
    elif default_soundfont():
        out = render_drums_sf(pattern, tempo, bars, sr, style=style,
                              swing=swing)
    else:
        out = render_drums(style, tempo, bars, sr, pattern=pattern,
                           swing=swing)
    return as_stereo(out)


def drum_source(style: str) -> str:
    """Which renderer drums_audio will use for `style` — for smoke-test logging."""
    pat = DRUM_PATTERNS.get(style)
    if pat and sample_kit.kit_available(style):
        return "sample-kit"
    if default_soundfont() and pat:
        return "soundfont"
    return "numpy-synth"


def using_soundfont() -> bool:
    return default_soundfont() is not None
