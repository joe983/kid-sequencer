"""R32c — 'smp' repitch one-shot sampler (producer vocal chops / stabs / chants).

Plays a producer's REAL one-shot as a melodic lead layer under the kid's riff:
each note repitches the one-shot by playback rate (target/root), OCTAVE-FOLDED
into +-6 semitones — the vocal-chop idiom that keeps a chant sounding like a
chant instead of a chipmunk or a growl. Held for the note with a short cosine
release. Pure numpy => bit-deterministic (unlike Surge / tinysoundfont), so the
same (sequence, variation) still gives the same track.

Assets: scripts/fetch_producer_kits.py unpacks the pack's "melodic" section to
assets/melodic_oneshots/techhouse/<producer>/<name>.wav (+ meta.json carrying
root_hz). When an asset is absent, render returns empty and the caller uses the
declared fallback voice (SMP_VOICES[name][1]) — so local dev without the pack
still renders a lead.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..audio import SR, normalize, pan_stereo, read_wav, seconds_per_beat

SMP_DIR = Path(__file__).resolve().parents[2] / "assets" / "melodic_oneshots"

# smp voice name -> (relpath under SMP_DIR, fallback (kind, name) for the lead
# stack when the sample is missing). Fallbacks name REAL Surge patches / SF
# roles so a no-asset render still produces the producer's signature lead.
SMP_VOICES: dict[str, tuple[str, tuple[str, str]]] = {
    "chop_alien": ("techhouse/bassled/chop.wav", ("vst", "lead_talkbox")),
    "funk_stab":  ("techhouse/discofunk/funk_stab.wav", ("vst", "lead_italo")),
    "chant_v":    ("techhouse/latin/chant.wav", ("sf", "pad_accordion")),
    "chop_real":  ("techhouse/pianohouse/chop.wav", ("vst", "stab_vocal")),
    "chop_note":  ("techhouse/lofi/chop.wav", ("vst", "stab_vocal")),
    "rave_shot":  ("techhouse/bigroom/rave_shot.wav", ("vst", "supersaw_chord")),
}

_HALF_STEP_UP = 2.0 ** (0.5)    # +6 semitones
_HALF_STEP_DN = 2.0 ** (-0.5)   # -6 semitones
_REL_S = 0.060                  # cosine release

_cache: dict[str, np.ndarray] = {}
_root_cache: dict[str, float] = {}


def _rel(name: str) -> str:
    v = SMP_VOICES.get(name)
    return v[0] if v else name


def _root_hz(name: str) -> float | None:
    """root_hz for a voice, read once from the sibling meta.json."""
    rel = _rel(name)
    if rel in _root_cache:
        return _root_cache[rel] or None
    p = SMP_DIR / rel
    hz = 0.0
    meta = p.parent / "meta.json"
    if meta.exists():
        try:
            d = json.loads(meta.read_text(encoding="utf-8"))
            hz = float(d.get(p.stem, {}).get("root_hz") or 0.0)
        except Exception:  # noqa: BLE001 — a bad meta just disables smp for it
            hz = 0.0
    _root_cache[rel] = hz
    return hz or None


def smp_root_hz(name: str) -> float | None:
    return _root_hz(name)


def smp_available(name: str) -> bool:
    """True only if the one-shot AND a usable root_hz are present."""
    return (SMP_DIR / _rel(name)).exists() and _root_hz(name) is not None


def _load(name: str) -> np.ndarray:
    rel = _rel(name)
    if rel not in _cache:
        s = normalize(read_wav(SMP_DIR / rel, SR), 0.95)
        fi = min(int(0.002 * SR), s.size)
        fo = min(int(0.005 * SR), s.size)
        if fi:
            s[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)
        if fo:
            s[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)
        _cache[rel] = s
    return _cache[rel]


def fold_rate(target_hz: float, root_hz: float) -> float:
    """Playback rate target/root, octave-folded into +-6 semitones. Two pitches
    exactly one octave apart fold to the SAME rate (the vocal-chop idiom)."""
    rate = target_hz / root_hz
    while rate > _HALF_STEP_UP:
        rate *= 0.5
    while rate < _HALF_STEP_DN:
        rate *= 2.0
    return rate


def _repitch(one: np.ndarray, rate: float) -> np.ndarray:
    n_out = max(4, int(round(one.size / rate)))
    idx = np.linspace(0.0, one.size - 1.0, n_out)
    return np.interp(idx, np.arange(one.size), one).astype(np.float32)


def render_riff_smp(notes, tempo: float, name: str, bars: int,
                    bar_beats: float = 4.0, sr: int = SR) -> np.ndarray:
    """Repitch the smp one-shot per note (octave-folded), looped across `bars`
    bars, 0.8 s tail. Returns stereo (N, 2); EMPTY (0, 2) if the asset/root is
    missing so the caller can fall back."""
    root = _root_hz(name)
    if root is None or not (SMP_DIR / _rel(name)).exists():
        return np.zeros((0, 2), dtype=np.float32)
    one = _load(name)
    spb = seconds_per_beat(tempo)
    total = int((bars * bar_beats * spb + 0.8) * sr)
    buf = np.zeros(total, dtype=np.float32)
    rel_n = int(_REL_S * sr)
    for b in range(bars):
        bar_off = b * bar_beats * spb
        for nt in notes:
            target = 440.0 * 2.0 ** ((nt.pitch - 69) / 12.0)
            seg = _repitch(one, fold_rate(target, root))
            hold = int(nt.dur_beats * spb * sr)
            keep = min(seg.size, max(1, hold) + rel_n)
            seg = seg[:keep].copy()
            rn = min(rel_n, seg.size)
            if rn:
                env = ((1.0 + np.cos(np.linspace(0.0, np.pi, rn))) * 0.5)
                seg[-rn:] *= env.astype(np.float32)
            g = float(nt.velocity) / 96.0
            at = int((bar_off + nt.start_beats * spb) * sr)
            end = min(total, at + seg.size)
            if end > at:
                buf[at:end] += seg[: end - at] * np.float32(g)
    return pan_stereo(buf, 0.0)
