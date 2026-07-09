"""Surge XT VST renderer — runs fully on the Modal/Linux build.

Render tests SKIP on hosts without the Surge VST3 (local Windows); the
availability/fallback contract is always tested.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.audio import SR, seconds_per_beat  # noqa: E402
from kidseq_engine.render.vst_render import (  # noqa: E402
    INSTRUMENT_PATCH,
    PATCHES,
    SURGE_VST3,
    _env,
    render_patch,
    render_riff_vst,
    vst_available,
)
from kidseq_engine.sequence import Note  # noqa: E402

_NOTES = [
    Note(pitch=48, velocity=100, start_beats=0.0, dur_beats=1.0),
    Note(pitch=55, velocity=100, start_beats=1.0, dur_beats=1.0),
    Note(pitch=60, velocity=100, start_beats=2.0, dur_beats=2.0),
]


def test_patches_cover_grid_instruments_and_pad():
    assert set(INSTRUMENT_PATCH) == {"synth", "bass"}
    assert set(PATCHES) >= {"synth", "bass", "pad"}
    for name in INSTRUMENT_PATCH.values():
        assert name in PATCHES


def test_env_mapping_is_monotonic_and_bounded():
    times = [0.004, 0.05, 0.25, 1.0, 4.0, 30.0]
    vals = [_env(t) for t in times]
    assert vals == sorted(vals)
    assert all(0.0 <= v <= 1.0 for v in vals)


def test_unmapped_instruments_report_unavailable():
    assert not vst_available("piano")
    assert not vst_available("trumpet")


def test_vst_render_is_non_silent_and_exact_length():
    if not SURGE_VST3.exists():
        print("SKIP (Surge VST3 not present) render tests")
        return
    tempo, bars = 120.0, 2
    expected = int((bars * 4.0 * seconds_per_beat(tempo) + 0.8) * SR)
    for instr in INSTRUMENT_PATCH:
        audio = render_riff_vst(_NOTES, tempo, instr, bars)
        assert len(audio) == expected, (instr, len(audio), expected)
        assert audio.dtype == np.float32
        assert float(np.max(np.abs(audio))) > 0.01, f"{instr} rendered silence"
    pad = render_patch(_NOTES, tempo, "pad", bars)
    assert float(np.max(np.abs(pad))) > 0.01, "pad rendered silence"


def test_vst_render_rejects_unmapped_instrument():
    try:
        render_riff_vst(_NOTES, 120.0, "piano", 1)
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
    print(f"all vst tests passed (Surge VST3: {'present' if SURGE_VST3.exists() else 'absent'})")
