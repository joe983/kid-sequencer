"""Rendering: MIDI/notes -> audio.

Dispatchers prefer the real-sample soundfont renderer (sf_render) when a soundfont
is available, and fall back to the numpy synth so the pipeline always runs.
"""

from __future__ import annotations

import numpy as np

from ..audio import SR
from ..sequence import Note
from . import sample_kit
from .drums import DRUM_PATTERNS, render_drums
from .sf_render import default_soundfont, render_drums_sf, render_riff_sf
from .synth import render_riff_looped


def riff_audio(notes: list[Note], tempo: float, instrument: str, bars: int,
               bar_beats: float = 4.0, sr: int = SR) -> np.ndarray:
    if default_soundfont():
        return render_riff_sf(notes, tempo, instrument, bars, bar_beats, sr)
    return render_riff_looped(notes, tempo, instrument, bars, bar_beats, sr)


def drums_audio(style: str, tempo: float, bars: int, sr: int = SR) -> np.ndarray:
    pat = DRUM_PATTERNS.get(style)
    # Priority: real CC0 one-shot kit > GM soundfont > numpy synth fallback.
    if pat and sample_kit.kit_available(style):
        return sample_kit.render_drums_samples(style, tempo, bars, sr)
    if default_soundfont() and pat:
        return render_drums_sf(pat, tempo, bars, sr)
    return render_drums(style, tempo, bars, sr)


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
