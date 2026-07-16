"""Tests for the mix/master chain — the numeric master gates (loudness, true peak,
pump behaviour). These need no soundfont: layers are synthetic buffers."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.audio import SR  # noqa: E402
from kidseq_engine.mixmaster import (  # noqa: E402
    GENRE_PRESETS,
    kick_onsets_from_pattern,
    master,
    pump_envelope,
)
from kidseq_engine.mixmaster.master import preset_for  # noqa: E402
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402


def _tone(freq, secs, amp=0.3):
    t = np.arange(int(secs * SR)) / SR
    return (np.sin(2 * np.pi * freq * t) * amp).astype(np.float32)


def test_pump_empty_onsets_is_unity():
    env = pump_envelope(SR, SR, [], depth=0.6, release_s=0.18)
    assert np.allclose(env, 1.0)


def test_pump_dips_to_one_minus_depth():
    env = pump_envelope(SR, SR, [SR // 2], depth=0.6, release_s=0.18)
    assert abs(env.min() - 0.4) < 1e-3      # dips to 1-depth at the onset
    assert env[0] == 1.0 and env[-1] > 0.95  # baseline before, recovered after


def test_pump_ignores_out_of_range_onsets():
    # onset past the buffer must not raise and must leave the envelope at unity
    env = pump_envelope(SR, SR, [SR * 5, -10], depth=0.6, release_s=0.18)
    assert np.allclose(env, 1.0)


def test_kick_onsets_count_matches_pattern():
    on = kick_onsets_from_pattern(DRUM_PATTERNS["techhouse"], 120, 4, SR)
    kicks_per_bar = sum(1 for v in DRUM_PATTERNS["techhouse"]["kick"] if v > 0)
    assert len(on) == kicks_per_bar * 4
    assert on == sorted(on)


def test_kick_onsets_fall_back_to_sub():
    # a pattern with only a 'sub' lane still yields a pump trigger
    on = kick_onsets_from_pattern({"sub": [1, 0, 0, 0]}, 120, 1, SR)
    assert len(on) == 1


def test_master_hits_loudness_target_and_peak_ceiling():
    np.random.seed(0)
    riff = _tone(440, 2.0)
    drums = (np.random.uniform(-1, 1, int(2.0 * SR)) * 0.3).astype(np.float32)
    on = kick_onsets_from_pattern(DRUM_PATTERNS["techhouse"], 120, 1, SR)
    res = master({"riff": riff, "drums": drums}, SR, genre="techhouse", kick_onsets=on)
    preset = preset_for("techhouse")
    assert abs(res.lufs - preset.lufs_target) < 0.6      # lands on target
    assert res.true_peak_db <= preset.peak_ceiling_db    # never over the ceiling
    assert res.audio.ndim == 2 and res.audio.shape[1] == 2  # stereo
    assert float(np.max(np.abs(res.audio))) > 0.1        # non-silent


def test_master_requires_riff():
    try:
        master({}, SR, genre=None, kick_onsets=[])
    except ValueError:
        return
    raise AssertionError("master() must reject a missing riff layer")


def test_master_works_without_drums():
    riff = _tone(330, 1.5)
    res = master({"riff": riff}, SR, genre=None, kick_onsets=[])
    assert abs(res.lufs - GENRE_PRESETS["default"].lufs_target) < 0.6
    assert res.layers == ("riff",)


def test_kit_key_null_contract():
    # R32b: master(kit_key=None) is byte-identical to omitting kit_key — the
    # null contract that keeps every non-producer genre unchanged. A producer
    # key threads to the slot lookups; with no pack on disk it falls back to the
    # base genre slot, so the master still matches the base.
    np.random.seed(2)
    riff = _tone(440, 1.2)
    drums = (np.random.uniform(-1, 1, int(1.2 * SR)) * 0.3).astype(np.float32)
    on = list(kick_onsets_from_pattern(DRUM_PATTERNS["techhouse"], 120, 1, SR))
    a = master({"riff": riff.copy(), "drums": drums.copy()}, SR,
               genre="techhouse", kick_onsets=list(on))
    b = master({"riff": riff.copy(), "drums": drums.copy()}, SR,
               genre="techhouse", kick_onsets=list(on), kit_key=None)
    assert np.array_equal(a.audio, b.audio), "kit_key=None must equal omitting it"
    from kidseq_engine.render.sample_kit import kit_available
    if not kit_available("techhouse:bassled"):
        c = master({"riff": riff.copy(), "drums": drums.copy()}, SR,
                   genre="techhouse", kick_onsets=list(on),
                   kit_key="techhouse:bassled")
        assert np.array_equal(a.audio, c.audio), \
            "a producer key with no pack must slot around the base genre kick"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all master tests passed")
