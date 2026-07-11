"""Arrangement FX — generator contracts, throw heuristic, flag null tests.

The null tests use a COMPACT plan override + the numpy-synth fallback so they
run anywhere (no assets needed) in seconds.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

# Null tests compare bit-identical renders — Surge XT's unison uses internal
# RNG a VST reset doesn't reseed (audibly identical, sample-different), so
# these tests pin the deterministic SF2/synth fallback renderers instead.
# Must be set BEFORE any kidseq_engine import (vst_render reads it at import).
os.environ["KIDSEQ_SURGE_VST3"] = str(Path("nonexistent-surge-for-null-tests"))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.arrange import Section  # noqa: E402
from kidseq_engine.arrange.render import FxFlags, build_song  # noqa: E402
from kidseq_engine.audio import SR  # noqa: E402
from kidseq_engine.render import fx  # noqa: E402
from kidseq_engine.sequence import Note, Riff  # noqa: E402

_PLAN = [
    Section("intro", 1, "sparse", "lite", bass=False, pads=False),
    Section("build", 2, "verbatim", "lite", bass=True, pads=True),
    Section("drop", 2, "verbatim", "full", bass=True, pads=True),
    Section("break", 1, "sparse_low", None, bass=False, pads=True),
    Section("build2", 2, "verbatim", "lite", bass=True, pads=True),
    Section("drop2", 2, "verbatim", "full", bass=True, pads=True),
    Section("outro", 1, "sparse", "lite", bass=False, pads=True),
]
_OFF = FxFlags(fx=False, fills=False, automation=False, gap=False, throw=False)


def _riff() -> Riff:
    notes = [
        Note(pitch=60, start_beats=0.0, dur_beats=1.0),
        Note(pitch=64, start_beats=1.0, dur_beats=1.0),
        Note(pitch=67, start_beats=2.0, dur_beats=1.0),
        Note(pitch=64, start_beats=3.0, dur_beats=1.0),  # sounds past beat 3 -> throw fits
    ]
    return Riff(notes=notes, tempo=120.0, key="C", instrument="piano", drum_style="techhouse")


def _peak_db(x) -> float:
    return 20.0 * np.log10(float(np.max(np.abs(x))) + 1e-12)


def test_generators_shapes_levels_determinism():
    r1 = fx.riser(2.0, SR, seed=7, gate_hz=8.0)
    r2 = fx.riser(2.0, SR, seed=7, gate_hz=8.0)
    assert r1.shape == (2 * SR, 2) and np.array_equal(r1, r2)
    assert abs(_peak_db(r1) - (-12.0)) < 1.5
    imp = fx.impact(SR)
    assert imp.shape[1] == 2 and abs(_peak_db(imp) - (-6.0)) < 0.8
    cr = fx.crash(SR, seed=3)
    assert abs(_peak_db(cr) - (-14.0)) < 0.8
    rc = fx.reverse_crash(cr, SR)
    assert abs(_peak_db(rc) - (-16.0)) < 0.8
    dl = fx.downlifter(2.0, SR)
    assert abs(_peak_db(dl) - (-16.0)) < 0.8
    # riser ends silent (the drop must start clean)
    assert float(np.max(np.abs(r1[-8:]))) < 1e-3
    # parameterised impact: defaults unchanged; genre-tuned booms hold level
    deep = fx.impact(SR, f0=60.0, f1=28.0)
    assert deep.shape == imp.shape and abs(_peak_db(deep) - (-6.0)) < 0.8
    assert not np.array_equal(deep, imp)
    # parameterised riser band: default level holds; dark band differs
    dark = fx.riser(2.0, SR, seed=7, gate_hz=8.0, f0=200.0, f1=2500.0)
    assert dark.shape == r1.shape and abs(_peak_db(dark) - (-12.0)) < 1.5
    assert not np.array_equal(dark, r1)
    # spinback: level pin, determinism, clean end into the drop
    sb = fx.spinback(1.5, SR, seed=5)
    assert sb.shape == (int(1.5 * SR), 2)
    assert np.array_equal(sb, fx.spinback(1.5, SR, seed=5))
    assert abs(_peak_db(sb) - (-14.0)) < 0.8
    assert float(np.max(np.abs(sb[-8:]))) < 1e-3
    # shepard riser: level pin, determinism, differs from classic, clean end
    sh = fx.shepard_riser(2.0, SR, seed=7)
    assert sh.shape == (2 * SR, 2)
    assert np.array_equal(sh, fx.shepard_riser(2.0, SR, seed=7))
    assert abs(_peak_db(sh) - (-12.0)) < 1.5
    assert float(np.max(np.abs(sh[-8:]))) < 1e-3
    assert not np.array_equal(sh, fx.riser(2.0, SR, seed=7))


def test_texture_generators_shapes_levels_determinism():
    for gen, kwargs, want_db in (
        (fx.vinyl_crackle, {"seed": 5}, -24.0),
        (fx.noise_wash, {"seed": 5}, -26.0),
        (fx.dark_drone, {"seed": 5, "root_hz": 65.41}, -26.0),
    ):
        a = gen(3.0, SR, **kwargs)
        b = gen(3.0, SR, **kwargs)
        assert a.shape == (3 * SR, 2) and np.array_equal(a, b), gen.__name__
        assert abs(_peak_db(a) - want_db) < 1.5, (gen.__name__, _peak_db(a))
        assert np.all(np.isfinite(a)), gen.__name__
        # edge fades: section boundaries must not click
        assert float(np.max(np.abs(a[:4]))) < 0.02, gen.__name__
        assert float(np.max(np.abs(a[-4:]))) < 0.02, gen.__name__
    # crackle rate knob (garage runs lighter than hiphop)
    dusty = fx.vinyl_crackle(3.0, SR, seed=5, ticks_per_s=4.0)
    assert not np.array_equal(dusty, fx.vinyl_crackle(3.0, SR, seed=5))


def test_throw_fits_heuristic():
    r = _riff()
    assert fx.throw_fits(r)
    from dataclasses import replace
    assert not fx.throw_fits(replace(r, tempo=170.0))                 # too fast
    dense = replace(r, notes=r.notes * 3)                             # 12 notes
    assert not fx.throw_fits(dense)
    early = replace(r, notes=[Note(pitch=60, start_beats=0.0, dur_beats=1.0)])
    assert not fx.throw_fits(early)                                   # nothing to echo


def test_flags_off_is_deterministic_baseline():
    r = _riff()
    l1, k1, _, _ = build_song(r, SR, plan=_PLAN, flags=_OFF)
    l2, k2, _, _ = build_song(r, SR, plan=_PLAN, flags=_OFF)
    assert k1 == k2 and sorted(l1) == sorted(l2)
    assert "fx" not in l1  # empty fx layer is dropped
    for name in l1:
        assert np.array_equal(l1[name], l2[name]), name


def test_drops_stay_verbatim_under_automation():
    """Filter automation may touch intro/builds/breaks — NEVER a drop. The
    riff layer inside every drop must be bit-identical to the no-FX baseline."""
    r = _riff()
    base, _, plan, _ = build_song(r, SR, plan=_PLAN, flags=_OFF)
    auto, _, _, _ = build_song(r, SR, plan=_PLAN,
                               flags=FxFlags(fx=False, fills=False, automation=True,
                                             gap=False, throw=False))
    bar_s = 4.0 * 60.0 / r.tempo
    bar = 0
    for sec in plan:
        a, e = int(bar * bar_s * SR), int((bar + sec.bars) * bar_s * SR)
        if sec.name.startswith("drop"):
            assert np.array_equal(base["riff"][a:e], auto["riff"][a:e]), sec.name
        bar += sec.bars


def test_gap_silences_and_does_not_click():
    """The gap length is a palette decision now (R10) — derive the expected
    silence span from choose_style, and skip the palette's exempt layer."""
    from kidseq_engine.arrange.style import choose_style

    r = _riff()
    pal = choose_style(r, 0).fx_palette
    layers, _, plan, _ = build_song(r, SR, plan=_PLAN,
                                    flags=FxFlags(fx=False, fills=False, automation=False,
                                                  gap=True, throw=False))
    bar_s = 4.0 * 60.0 / r.tempo
    spb = 60.0 / r.tempo
    gap_n = int(min(pal.gap_beats * spb, 1.1) * SR)
    bar = 0
    for sec in plan:
        a = int(bar * bar_s * SR)
        if sec.name.startswith("drop"):
            g0 = a - gap_n
            for name, buf in layers.items():
                if name == pal.gap_carry:
                    continue  # KSHMR carry layer keeps running through the gap
                assert float(np.max(np.abs(buf[g0:a]))) < 1e-6, (sec.name, name)
                # no click: sample-to-sample jump around the fade stays bounded
                seg = buf[g0 - int(0.004 * SR):a + 4]
                assert float(np.max(np.abs(np.diff(seg, axis=0)))) < 0.5, (sec.name, name)
        bar += sec.bars


def test_gap_clamp_and_exempt_layer():
    """Unit pins for _apply_gap: 1.1 s clamp at slow tempo, exempt layer
    untouched, hard back in exactly at the drop sample."""
    from kidseq_engine.arrange.render import _apply_gap, _gap_samples

    spb = 60.0 / 50.0                      # tempo 50: 2 beats = 2.4 s
    assert _gap_samples(2.0, spb, SR) == int(1.1 * SR)   # clamped
    assert _gap_samples(0.15, 0.5, SR) == int(0.075 * SR)  # legacy micro-gap

    n = 5 * SR
    layers = {"a": np.ones((n, 2), dtype=np.float32),
              "keep": np.ones((n, 2), dtype=np.float32)}
    d = 4 * SR
    _apply_gap(layers, [d], SR, spb, 2.0, exempt=("keep",))
    gap_n = int(1.1 * SR)
    assert float(np.max(np.abs(layers["a"][d - gap_n + 8:d]))) < 1e-6
    assert float(np.min(layers["keep"])) == 1.0            # exempt untouched
    assert layers["a"][d, 0] == 1.0                        # back in at the drop


def test_fill_shapes_valid():
    """All fill shapes are 16-step rows ending EMPTY (they butt into the gap);
    shape 3 is 2 bars when the build allows, degrading to 1; shape 4 stops
    dead at beat 3 (the rug-pull)."""
    from kidseq_engine.arrange.render import _fill_bars, _fill_pattern

    for style in ("techhouse", "dnb", "garage", "reggaeton", "drill", "hiphop"):
        for shape in (0, 1, 2, 4):
            pat = _fill_pattern(style, shape)
            assert all(len(v) == 16 for v in pat.values()), (style, shape)
            assert all(v[-1] == 0.0 for v in pat.values()), (style, shape)
        bars = _fill_bars(style, 3, 2)
        assert len(bars) == 2 and all(
            len(v) == 16 for p in bars for v in p.values()), style
        assert len(_fill_bars(style, 3, 1)) == 1, style    # degrades
    p4 = _fill_pattern("dnb", 4)
    assert p4["snare"][12:] == [0.0, 0.0, 0.0, 0.0]        # a beat of silence


def test_fx_layer_present_with_flags_on():
    r = _riff()
    layers, _, _, _ = build_song(r, SR, plan=_PLAN, flags=FxFlags())
    assert "fx" in layers
    assert float(np.max(np.abs(layers["fx"]))) > 0.05


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
    print("all fx tests passed")
