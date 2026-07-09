"""Rendering: MIDI/notes -> audio.

Dispatchers prefer the real-sample soundfont renderer (sf_render) when a soundfont
is available, and fall back to the numpy synth so the pipeline always runs.
"""

from __future__ import annotations

import numpy as np

from ..audio import SR
from ..sequence import Note
from . import sample_kit, sfz_render
from .drums import DRUM_PATTERNS, render_drums
from .sf_render import default_soundfont, render_drums_sf, render_riff_sf
from .synth import render_riff_looped


def riff_audio(notes: list[Note], tempo: float, instrument: str, bars: int,
               bar_beats: float = 4.0, sr: int = SR) -> np.ndarray:
    # Priority: SFZ via sfizz (VSCO orchestral, Linux/Modal) > SF2 > numpy synth.
    if sfz_render.sfz_available(instrument):
        return sfz_render.render_riff_sfz(notes, tempo, instrument, bars, bar_beats, sr)
    if default_soundfont():
        return render_riff_sf(notes, tempo, instrument, bars, bar_beats, sr)
    return render_riff_looped(notes, tempo, instrument, bars, bar_beats, sr)


def riff_source(instrument: str) -> str:
    """Which renderer riff_audio will use for `instrument` — for smoke-test logging."""
    if sfz_render.sfz_available(instrument):
        return "sfz(" + sfz_render.library_name(instrument) + ")"
    if default_soundfont():
        return "soundfont"
    return "numpy-synth"


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
