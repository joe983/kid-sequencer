"""Tests for the CC0 sample-kit drum renderer.

read_wav is tested with a synthesised WAV (no assets needed). The render tests are
skipped when the kits haven't been fetched (CI without assets/), so they never fail
on a clean checkout — run scripts/fetch_drumkits.py first to exercise them.
"""

import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.audio import SR, read_wav, seconds_per_beat, write_wav  # noqa: E402
from kidseq_engine.render import sample_kit  # noqa: E402
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402


def test_read_wav_roundtrip_mono():
    t = np.arange(SR // 10) / SR
    sig = (np.sin(2 * np.pi * 220 * t) * 0.5).astype(np.float32)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "tone.wav"
        write_wav(p, sig, SR)            # writes 16-bit stereo
        got = read_wav(p, SR)            # downmixes back to mono
    assert got.ndim == 1
    assert abs(got.shape[0] - sig.shape[0]) <= 1
    n = min(got.shape[0], sig.shape[0])
    assert float(np.max(np.abs(got[:n] - sig[:n]))) < 0.01  # within 16-bit quantisation


def test_read_wav_resamples_to_target():
    # a 22050 Hz file read at SR=44100 should roughly double in length
    half = SR // 2
    t = np.arange(half // 5) / half
    sig = (np.sin(2 * np.pi * 100 * t) * 0.4).astype(np.float32)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "low.wav"
        write_wav(p, sig, half)
        got = read_wav(p, SR)
    assert abs(got.shape[0] - sig.shape[0] * 2) <= 2


def test_every_genre_kit_covers_its_pattern_voices():
    # the registry must define a sample for every voice each genre actually triggers,
    # else those hits render silent. This is a static check — no assets required.
    for style, pat in DRUM_PATTERNS.items():
        kit = sample_kit.KITS.get(style)
        assert kit is not None, f"no sample kit defined for genre {style!r}"
        missing = [v for v in pat if v not in kit]
        assert not missing, f"{style}: pattern voices with no sample mapping: {missing}"


def test_render_is_non_silent_and_right_length_when_assets_present():
    style = "drill"
    if not sample_kit.kit_available(style):
        print("  (skipped: drum assets not fetched)")
        return
    tempo, bars = 120, 4
    buf = sample_kit.render_drums_samples(style, tempo, bars, SR)
    expected = int(bars * 4 * seconds_per_beat(tempo) * SR)
    assert buf.ndim == 2 and buf.shape[1] == 2  # stereo, constant-power panned
    assert abs(buf.shape[0] - expected) < SR  # within the tail allowance
    assert float(np.max(np.abs(buf))) > 0.05  # real hits, not silence


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all sample-kit tests passed")
