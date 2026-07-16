"""Tests for the smp repitch one-shot sampler (R32c).

Statics + the octave-fold property need no assets. The render tests are skipped
when the producer pack hasn't been unpacked (CI without assets/), so a clean
checkout never fails — they execute on Modal where the pack is present.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.audio import SR  # noqa: E402
from kidseq_engine.render import smp_render  # noqa: E402
from kidseq_engine.sequence import Note  # noqa: E402


def _notes():
    return [Note(pitch=60, start_beats=0.0, dur_beats=1.0, velocity=96),
            Note(pitch=64, start_beats=1.0, dur_beats=1.0, velocity=80),
            Note(pitch=67, start_beats=2.0, dur_beats=2.0, velocity=110)]


def _hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def test_smp_voices_registry_and_fallbacks():
    # every smp voice names a techhouse relpath + a fallback that is a REAL
    # Surge patch / SF role, and is wired into LEAD_VOICES as ("smp", name).
    from kidseq_engine.arrange.style import LEAD_VOICES
    from kidseq_engine.render import vst_render
    for name, (rel, (fkind, fname)) in smp_render.SMP_VOICES.items():
        assert rel.endswith(".wav") and rel.startswith("techhouse/"), (name, rel)
        assert fkind in ("vst", "sf"), (name, fkind)
        if fkind == "vst":
            assert fname in vst_render.PATCHES, (name, fname)
        assert LEAD_VOICES.get(name) == ("smp", name), name


def test_octave_fold_property():
    # pitches one octave apart fold to the SAME playback rate, and every folded
    # rate stays within +-6 semitones (the vocal-chop idiom).
    root = 220.0
    for m in (48, 55, 60, 62, 67, 72, 79):
        r_lo = smp_render.fold_rate(_hz(m), root)
        r_hi = smp_render.fold_rate(_hz(m + 12), root)
        assert abs(r_lo - r_hi) < 1e-9, (m, r_lo, r_hi)
        assert 2.0 ** -0.5 - 1e-9 <= r_lo <= 2.0 ** 0.5 + 1e-9, (m, r_lo)


def test_missing_asset_returns_empty():
    # a voice with no pack on disk renders empty so the caller can fall back
    sig = smp_render.render_riff_smp(_notes(), 124, "no_such_voice", 2, 4.0, SR)
    assert sig.shape == (0, 2)


def test_render_and_determinism_when_assets_present():
    avail = [n for n in smp_render.SMP_VOICES if smp_render.smp_available(n)]
    if not avail:
        print("  (skipped: smp assets not fetched)")
        return
    rendered = {}
    for name in avail:
        sig = smp_render.render_riff_smp(_notes(), 124, name, 2, 4.0, SR)
        assert sig.ndim == 2 and sig.shape[1] == 2, name
        assert sig.shape[0] > SR, name              # ~2 bars + 0.8 s tail
        assert float(np.max(np.abs(sig))) > 0.01, f"{name} silent"
        sig2 = smp_render.render_riff_smp(_notes(), 124, name, 2, 4.0, SR)
        assert np.array_equal(sig, sig2), f"{name} not deterministic"
        rendered[name] = sig
    # distinct producer chops sound different
    keys = list(rendered)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = rendered[keys[i]], rendered[keys[j]]
            m = min(a.shape[0], b.shape[0])
            assert not np.array_equal(a[:m], b[:m]), (keys[i], keys[j])


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all smp tests passed")
