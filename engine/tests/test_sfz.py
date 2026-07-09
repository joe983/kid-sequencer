"""SFZ renderer (sfizz + VSCO 2 CE) — runs fully on the Modal/Linux build.

On hosts without sfizz_render or the VSCO assets (i.e. local Windows) the render
tests SKIP; the availability/fallback contract is always tested.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.audio import SR, seconds_per_beat  # noqa: E402
from kidseq_engine.render import riff_source  # noqa: E402
from kidseq_engine.render.sfz_render import (  # noqa: E402
    INSTRUMENT_SFZ,
    render_riff_sfz,
    sfz_available,
    sfizz_binary,
)
from kidseq_engine.sequence import Note  # noqa: E402

_NOTES = [
    Note(pitch=60, velocity=100, start_beats=0.0, dur_beats=1.0),
    Note(pitch=64, velocity=100, start_beats=1.0, dur_beats=1.0),
    Note(pitch=67, velocity=100, start_beats=2.0, dur_beats=2.0),
]


def test_registry_covers_the_gm_placeholder_instruments():
    assert set(INSTRUMENT_SFZ) == {"trumpet", "strings", "bells"}


def test_riff_source_never_crashes_and_names_a_renderer():
    for instr in ("piano", "trumpet", "strings", "bells", "synth", "bass"):
        src = riff_source(instr)
        assert src.startswith(("sfz(", "soundfont", "numpy-synth")), src


def test_unavailable_instruments_report_unavailable():
    # piano has no SFZ mapping — must never claim sfz availability
    assert not sfz_available("piano")


def _skip(name: str) -> bool:
    if not sfz_available(name):
        print(f"SKIP (sfizz/VSCO not present) render test for {name}")
        return True
    return False


def test_sfz_render_is_non_silent_and_exact_length():
    tempo, bars = 120.0, 2
    expected = int((bars * 4.0 * seconds_per_beat(tempo) + 0.8) * SR)
    for instr in INSTRUMENT_SFZ:
        if _skip(instr):
            continue
        audio = render_riff_sfz(_NOTES, tempo, instr, bars)
        assert len(audio) == expected, (instr, len(audio), expected)
        assert audio.dtype == np.float32
        assert float(np.max(np.abs(audio))) > 0.01, f"{instr} rendered silence"


def test_sfz_render_rejects_unmapped_instrument():
    try:
        render_riff_sfz(_NOTES, 120.0, "piano", 1)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError for unmapped instrument")


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:  # noqa: BLE001
                print(f"FAIL {name}: {e}")
                fails += 1
    if fails:
        sys.exit(1)
    print(f"all sfz tests passed (sfizz binary: {sfizz_binary() or 'absent'})")
