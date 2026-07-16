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
_OFF = FxFlags(fx=False, fills=False, automation=False, gap=False, throw=False,
               earcandy=False, beds=False)


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
    # downlifter (R15 textured rework): noise-led composite, quieter, seeded
    dl = fx.downlifter(2.0, SR, seed=5)
    assert abs(_peak_db(dl) - (-18.0)) < 0.8
    assert np.array_equal(dl, fx.downlifter(2.0, SR, seed=5))
    assert not np.array_equal(dl, fx.downlifter(2.0, SR, seed=6))
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
    # the cycle must be AUDIBLE early: the first half already carries energy
    # (the old crossfade version was near-silent-then-swell like the classic)
    first_half_db = 20.0 * np.log10(float(np.max(np.abs(sh[: SR]))) + 1e-12)
    assert first_half_db > -30.0
    # riser colours (R15): each colour differs, all hold the level pin
    for color in ("textured", "airy"):
        rc2 = fx.riser(2.0, SR, seed=7, gate_hz=8.0, color=color)
        assert rc2.shape == r1.shape and abs(_peak_db(rc2) - (-12.0)) < 1.5, color
        assert not np.array_equal(rc2, r1), color
    # riser level knob (R15: prominence varies per press)
    quiet = fx.riser(2.0, SR, seed=7, gate_hz=8.0, peak_db=-17.0)
    assert abs(_peak_db(quiet) - (-17.0)) < 1.5


def test_texture_generators_shapes_levels_determinism():
    for gen, kwargs, want_db in (
        (fx.vinyl_crackle, {"seed": 5}, -24.0),
        (fx.noise_wash, {"seed": 5}, -26.0),
        (fx.dark_drone, {"seed": 5, "root_hz": 65.41}, -26.0),
        (fx.metal_drone, {"seed": 5, "root_hz": 65.41}, -26.0),
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


def test_percussive_pad_free_take_has_no_pads():
    """R16 (Photek): a percussive take whose style picks percussive_pads ==
    'none' renders NO pads layer at all — hits, bass pedal and texture only."""
    import json
    from pathlib import Path

    from kidseq_engine.arrange.style import choose_style
    from kidseq_engine.sequence import parse_sequence

    payload = json.loads((Path(__file__).parents[1] / "examples" /
                          "cluster_riff.json").read_text(encoding="utf-8"))
    r = parse_sequence(payload)
    v_none = next(v for v in range(200)
                  if choose_style(r, v).percussive_pads == "none")
    v_drone = next(v for v in range(200)
                   if choose_style(r, v).percussive_pads == "drone")
    l_none, _, _, _ = build_song(r, SR, plan=_PLAN, flags=_OFF, variation=v_none)
    l_drone, _, _, _ = build_song(r, SR, plan=_PLAN, flags=_OFF, variation=v_drone)
    assert "pads" not in l_none
    # the drone half needs a pad renderer — asset-free local runs render
    # empty pads for BOTH takes (the null tests' SF2/synth fallback has no
    # pad voice); on Modal (soundfonts present) this assert is live
    from kidseq_engine.render.sf_render import default_soundfont
    if default_soundfont():
        assert "pads" in l_drone


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


def test_r11_event_generators_levels_determinism():
    """R11 ear-candy + event FX: level pins (the breath-level law), shapes,
    determinism, and the silent-input guard on reverse_swell."""
    bm = fx.bomb(SR, seed=3)
    assert bm.shape[1] == 2 and bm.shape[0] <= int(6.0 * SR)
    assert abs(_peak_db(bm) - (-10.0)) < 1.0
    assert np.array_equal(bm, fx.bomb(SR, seed=3))
    assert float(np.max(np.abs(bm[-4:]))) < 0.02      # faded end

    ds = fx.dub_siren(4.0, SR, seed=5, bar_s=2.0)
    assert ds.shape == (4 * SR, 2)
    assert np.array_equal(ds, fx.dub_siren(4.0, SR, seed=5, bar_s=2.0))
    assert _peak_db(ds) < -22.0                        # breath level

    sc = fx.scratch(SR, seed=9)
    assert sc.shape == (int(0.6 * SR), 2)
    assert abs(_peak_db(sc) - (-18.0)) < 1.0
    assert np.array_equal(sc, fx.scratch(SR, seed=9))

    base = fx.crash(SR, seed=2)[: SR]                  # any non-silent slice
    for mode in ("reverb", "delay"):
        sw = fx.reverse_swell(base, SR, mode)
        assert sw.shape[1] == 2 and sw.shape[0] > base.shape[0]
        assert abs(_peak_db(sw) - (-18.0)) < 1.0
        assert np.array_equal(sw, fx.reverse_swell(base, SR, mode))
        assert float(np.max(np.abs(sw[-4:]))) < 0.02   # clean into the entry
    silent = np.zeros((SR, 2), dtype=np.float32)
    assert fx.reverse_swell(silent, SR).size == 0      # silent-input guard

    for kind, want in fx.CANDY_LEVELS.items():
        a = fx.candy_blip(kind, 2.0, SR, seed=4)
        b = fx.candy_blip(kind, 2.0, SR, seed=4)
        assert a.shape[1] == 2 and np.array_equal(a, b), kind
        assert _peak_db(a) <= want + 1.5, (kind, _peak_db(a))


def test_r12_beds_generators():
    """rumble_bed: determinism, level pin, strictly low-band; odd cell:
    determinism, length, quiet."""
    ons = [i * 0.5 for i in range(8)]
    rb = fx.rumble_bed(4.0, SR, seed=6, onsets_s=ons, decay_s=0.75)
    assert rb.shape == (4 * SR, 2)
    assert np.array_equal(rb, fx.rumble_bed(4.0, SR, seed=6, onsets_s=ons,
                                            decay_s=0.75))
    assert abs(_peak_db(rb) - (-14.0)) < 1.5
    # low-band character: energy above 300 Hz is far below the sub band
    m = rb.mean(axis=1).astype(np.float64)
    mag = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    fr = np.fft.rfftfreq(len(m), 1.0 / SR)
    lo = 10.0 * np.log10(mag[(fr >= 30) & (fr < 110)].mean() + 1e-20)
    hi = 10.0 * np.log10(mag[(fr >= 300) & (fr < 4000)].mean() + 1e-20)
    assert lo - hi > 20.0, (lo, hi)

    from kidseq_engine.render.drums import render_odd_cell
    c1 = render_odd_cell("techhouse", 120.0, 6.0, SR)
    c2 = render_odd_cell("techhouse", 120.0, 6.0, SR)
    assert np.array_equal(c1, c2) and c1.shape[0] == 6 * SR
    assert 0.0 < float(np.max(np.abs(c1))) < 0.5   # a quiet lane, not a kit


def test_candy_slots_hook_protection_and_spacing():
    from kidseq_engine.arrange import Section
    from kidseq_engine.arrange.render import _candy_slots

    bar_n = SR * 2  # 1 bar at 120 bpm
    bounds = [
        (Section("intro", 4, "sparse", "lite", False, False), 0, 4 * bar_n),
        (Section("drop", 16, "verbatim", "full", True, True), 4 * bar_n, 20 * bar_n),
        (Section("break", 4, "sparse_low", None, False, True), 20 * bar_n, 24 * bar_n),
        (Section("drop2", 16, "verbatim", "full", True, True), 24 * bar_n, 40 * bar_n),
    ]
    slots = _candy_slots(bounds, 4, 2.0, SR)
    assert slots == _candy_slots(bounds, 4, 2.0, SR)   # pure/deterministic
    assert _candy_slots(bounds, 0, 2.0, SR) == []      # off = no events
    d1 = [b for pos, name, b in slots if name == "drop"]
    d2 = [b for pos, name, b in slots if name == "drop2"]
    assert all(b >= 8 for b in d1), d1                 # drop 1 hook protected
    assert d1 == [8, 12] and d2 == [4, 8, 12]
    for pos, name, b in slots:                         # >=1 bar from boundaries
        sec_a = 4 * bar_n if name == "drop" else 24 * bar_n
        sec_e = sec_a + 16 * bar_n
        assert sec_a + bar_n <= pos <= sec_e - 2 * bar_n, (name, b)


def test_kick_onsets_never_point_at_silent_drums():
    """The pump must never duck the mix against silence — the drum_stop event
    removes its muted span's onsets, and the gap never zeroes an onset (drops
    start AT the drop sample). Invariant-checked across variations."""
    r = _riff()
    for v in (0, 3, 11):
        layers, onsets, _, _ = build_song(r, SR, plan=_PLAN, flags=FxFlags(),
                                          variation=v)
        drums = layers.get("drums")
        assert drums is not None
        for o in onsets:
            seg = drums[o:o + int(0.02 * SR)]
            assert float(np.max(np.abs(seg))) > 1e-5, (v, o)


def test_fx_samples_registry_and_fallbacks():
    # R32e: every sampled-fx kind has a valid synth fallback (a real candy_blip
    # kind or a placement kind, or None); sampled sweeps are registered; and
    # every smp_* kind used in a producer candy menu has a fallback entry.
    from kidseq_engine.arrange.style import _PRODUCER_CANDY
    from kidseq_engine.render import fx_samples
    from kidseq_engine.render.fx import CANDY_LEVELS
    placement = {"kick_fill", "drum_stop", "rev_swell_riff", "rev_swell_delay"}
    for kind, fb in fx_samples.FX_FALLBACK.items():
        assert kind.startswith("smp_"), kind
        if fb is not None:
            assert fb in CANDY_LEVELS or fb in placement, (kind, fb)
    assert fx_samples.SAMPLED_SWEEP_KINDS <= set(fx_samples.FX_FALLBACK)
    for prod, menu in _PRODUCER_CANDY.items():
        for kind in menu:
            if kind.startswith("smp_"):
                assert kind in fx_samples.FX_FALLBACK, (prod, kind)


def test_fx_shot_when_assets_present():
    # R32e: with the pack unpacked, each producer fx one-shot loads as stereo,
    # non-silent, capped to the bar, deterministic; a missing kind is empty.
    from kidseq_engine.render import fx_samples
    prods = [f"techhouse:{p}"
             for p in ("bassled", "latin", "lofi", "discofunk", "bigroom")]
    avail = [(k, kind) for k in prods for kind in fx_samples.FX_FALLBACK
             if fx_samples.fx_shot_available(k, kind)]
    if not avail:
        print("  (skipped: producer fx assets not fetched)")
        return
    bar_s = 60.0 / 124 * 4
    for k, kind in avail:
        sig = fx_samples.fx_shot(k, kind, bar_s, SR)
        assert sig.ndim == 2 and sig.shape[1] == 2, (k, kind)
        assert 0 < sig.shape[0] <= int(bar_s * SR) + 2, (k, kind)
        assert float(np.max(np.abs(sig))) > 0.001, (k, kind)
        assert np.array_equal(sig, fx_samples.fx_shot(k, kind, bar_s, SR)), (k, kind)
    assert fx_samples.fx_shot("techhouse:bassled", "no_such_kind",
                              bar_s, SR).shape == (0, 2)


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
