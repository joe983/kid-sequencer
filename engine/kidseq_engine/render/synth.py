"""Numpy synth fallback renderer for the riff stem.

Quality is intentionally a placeholder — the plan's pro sound comes from swapping
this for sfizz/FluidSynth + sample libraries. The point of this module is to make
the riff-anchored pipeline produce real, exact audio end-to-end TODAY. The notes
rendered here are the precise MIDI from sequence.py, so the riff is exact.
"""

from __future__ import annotations

import numpy as np

from ..audio import SR, add_at, adsr, midi_to_hz, seconds_per_beat
from ..sequence import Note

# Per-instrument timbre: harmonic amplitudes + ADSR + a small detune for width.
# (a, d, s, r) in seconds / sustain level.
_VOICES = {
    "piano":   {"harmonics": [1.0, 0.5, 0.25, 0.12, 0.06], "adsr": (0.005, 0.25, 0.4, 0.3), "detune": 0.0},
    "synth":   {"harmonics": [1.0, 0.7, 0.5, 0.35, 0.2, 0.1], "adsr": (0.01, 0.1, 0.7, 0.2), "detune": 0.04},
    "bass":    {"harmonics": [1.0, 0.6, 0.3, 0.15], "adsr": (0.005, 0.08, 0.8, 0.12), "detune": 0.0},
    "strings": {"harmonics": [1.0, 0.6, 0.4, 0.3, 0.2, 0.12], "adsr": (0.12, 0.2, 0.85, 0.4), "detune": 0.06},
    "trumpet": {"harmonics": [1.0, 0.8, 0.6, 0.45, 0.3, 0.18], "adsr": (0.03, 0.1, 0.8, 0.15), "detune": 0.0},
    "bells":   {"harmonics": [1.0, 0.0, 0.4, 0.0, 0.25, 0.0, 0.15], "adsr": (0.002, 0.6, 0.15, 0.6), "detune": 0.0},
}


def _render_one(freq: float, dur_s: float, voice: dict, sr: int) -> np.ndarray:
    rel = voice["adsr"][3]
    n = int((dur_s + rel) * sr)
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    t = np.arange(n, dtype=np.float32) / sr
    sig = np.zeros(n, dtype=np.float32)
    for k, amp in enumerate(voice["harmonics"], start=1):
        if amp <= 0:
            continue
        sig += amp * np.sin(2 * np.pi * freq * k * t)
        if voice["detune"]:
            sig += amp * 0.5 * np.sin(2 * np.pi * freq * k * (1 + voice["detune"]) * t)
    sig /= max(1.0, sum(voice["harmonics"]))
    a, d, s, r = voice["adsr"]
    env = adsr(n, sr, a, d, s, r)
    return (sig * env).astype(np.float32)


def render_riff_stem(
    notes: list[Note],
    tempo: float,
    instrument: str,
    total_beats: float,
    sr: int = SR,
    tail_s: float = 1.0,
) -> np.ndarray:
    """Render the exact riff notes to a mono float buffer of `total_beats` length."""
    voice = _VOICES.get(instrument, _VOICES["piano"])
    spb = seconds_per_beat(tempo)
    n = int((total_beats * spb + tail_s) * sr)
    buf = np.zeros(n, dtype=np.float32)
    for note in notes:
        freq = midi_to_hz(note.pitch)
        sig = _render_one(freq, note.dur_beats * spb, voice, sr)
        sig = sig * (note.velocity / 127.0)
        add_at(buf, sig, int(note.start_beats * spb * sr))
    return buf


def render_riff_looped(
    notes: list[Note],
    tempo: float,
    instrument: str,
    bars: int,
    bar_beats: float = 4.0,
    sr: int = SR,
) -> np.ndarray:
    """Loop the 1-bar riff across `bars` bars (verbatim each bar)."""
    spb = seconds_per_beat(tempo)
    bar_samples = int(bar_beats * spb * sr)
    total = bars * bar_samples
    buf = np.zeros(total + sr, dtype=np.float32)  # +1s tail headroom
    one_bar = render_riff_stem(notes, tempo, instrument, bar_beats, sr=sr, tail_s=0.4)
    for b in range(bars):
        add_at(buf, one_bar, b * bar_samples)
    return buf[: total + int(0.4 * sr)]
