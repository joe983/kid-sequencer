"""Arrangement stage — theory + plan invariants (pure, no assets needed)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.arrange import (  # noqa: E402
    _MAJOR_BANK,
    _MINOR_BANK,
    _triad_pcs,
    bass_notes,
    choose_progression,
    pad_notes,
    plan_song,
    riff_variant,
)
from kidseq_engine.sequence import (  # noqa: E402
    _C4_MIDI,
    Note,
    Riff,
    _scale_steps,
)

_KEYS = ["A", "Am", "B", "Bm", "C", "Cm", "D", "Dm", "E", "Em", "F", "Fm", "G", "Gm"]


def _riff(key="C", tempo=120.0, drum_style="techhouse") -> Riff:
    semi, steps = _scale_steps(key)
    tonic = _C4_MIDI + semi
    notes = [
        Note(pitch=tonic, start_beats=0.0, dur_beats=1.0),
        Note(pitch=tonic + steps[2], start_beats=1.0, dur_beats=1.0),
        Note(pitch=tonic + steps[4], start_beats=2.0, dur_beats=1.5),
        Note(pitch=tonic + steps[1], start_beats=3.5, dur_beats=0.5),
    ]
    return Riff(notes=notes, tempo=tempo, key=key, instrument="piano", drum_style=drum_style)


def test_every_bank_progression_is_diatonic_in_every_key():
    for key in _KEYS:
        _, steps = _scale_steps(key)
        scale_pcs = {s % 12 for s in steps}
        bank = _MINOR_BANK if key.endswith("m") else _MAJOR_BANK
        for prog in bank:
            for degree in prog:
                assert set(_triad_pcs(degree, steps)) <= scale_pcs, (key, prog, degree)


def test_choose_progression_is_deterministic_and_covers_riff():
    for key in _KEYS:
        riff = _riff(key)
        prog = choose_progression(riff)
        assert prog == choose_progression(riff)
        assert len(prog) == 4
        # tonic-anchored riffs must land a progression containing the tonic chord
        assert 0 in prog, (key, prog)


def _plan_ok(plan, tempo, ctx):
    bars = sum(s.bars for s in plan)
    dur = bars * 4 * 60.0 / tempo
    assert 180.0 <= dur <= 240.0, (*ctx, bars, dur)
    # cold_open shapes start straight on a drop; everything else on an intro
    assert plan[0].name == "intro" or plan[0].name.startswith("drop"), ctx
    assert plan[-1].name == "outro", ctx
    # every drop keeps the verbatim riff + full kit — the fidelity guarantee
    for s in plan:
        if s.name.startswith("drop"):
            assert s.riff_variant == "verbatim" and s.drums == "full", (*ctx, s)


def test_plan_totals_land_in_the_attention_window():
    # every song must be >=3:00 (180 s) and <=4:00, across the app's 40-200 BPM
    # clamp AND every per-press variation nonce
    for tempo in (40, 60, 90, 120, 140, 170, 200):
        for variation in range(8):
            plan = plan_song(tempo, variation)
            _plan_ok(plan, tempo, (tempo, variation))


def test_every_shape_and_length_combo_fits_the_window():
    # exhaustive skeleton sweep: the corrective loop must hold the window for
    # EVERY shape x length combination the style layer can emit, at every tempo
    from kidseq_engine.arrange.style import SONG_SHAPES, StructureStyle

    for tempo in (40, 60, 90, 120, 140, 170, 200):
        for shape in SONG_SHAPES:
            for frac in (1 / 5.0, 1 / 4.0, 1 / 3.0, 2 / 5.0, 1 / 2.0):
                for bias in ("short", "normal", "long"):
                    for intro_b, break_b, outro_b in ((4, 8, 4), (8, 4, 8), (8, 8, 4)):
                        st = StructureStyle(
                            song_shape=shape, intro_bars=intro_b,
                            break_bars=break_b, outro_bars=outro_b,
                            build_frac=frac, drop_bias=bias,
                            intro_character="sparse", escalation="full")
                        plan = plan_song(tempo, 0, structure=st)
                        _plan_ok(plan, tempo, (tempo, shape, frac, bias))
                        if shape == "cold_open":
                            assert plan[0].name.startswith("drop"), (tempo, frac, bias)


def test_variation_changes_the_arrangement_not_the_riff():
    riff = _riff()
    # deterministic per nonce
    assert choose_progression(riff, 0) == choose_progression(riff, 0)
    assert choose_progression(riff, 1) == choose_progression(riff, 1)
    # nonces produce genuinely different skeletons at a typical tempo
    plans = [tuple((s.name, s.bars) for s in plan_song(120, v)) for v in range(8)]
    assert len(set(plans)) >= 3, sorted(set(plans))
    # progressions still contain the tonic chord (riff coverage holds)
    for v in range(4):
        assert 0 in choose_progression(riff, v), v


def test_riff_ornaments_are_octave_velocity_only_and_deterministic():
    from kidseq_engine.arrange import ornament_riff

    notes = _riff().notes
    base_pcs = {n.pitch % 12 for n in notes}
    for kind in ("echo", "octave_pop", "push", "cadence"):
        a = ornament_riff(notes, kind)
        assert a == ornament_riff(notes, kind), kind           # deterministic
        assert {n.pitch % 12 for n in a} <= base_pcs, kind     # octave-only
        # ornaments never remove or re-time the original melody
        for orig in notes:
            assert any(n.pitch % 12 == orig.pitch % 12
                       and n.start_beats == orig.start_beats for n in a), (kind, orig)
        # everything stays inside the bar
        assert all(n.start_beats + n.dur_beats <= 4.0 + 1e-6 for n in a), kind
    assert ornament_riff(notes, "none") is notes               # identity


def test_soften_clashes_is_velocity_only_and_targets_semitone_rubs():
    from kidseq_engine.arrange import chord_pcs_for_bar, soften_clashes

    riff = _riff()
    prog = choose_progression(riff)
    pcs = chord_pcs_for_bar(riff, prog, 0)
    assert len(pcs) == 3
    out = soften_clashes(riff.notes, pcs)
    assert len(out) == len(riff.notes)
    for orig, new in zip(riff.notes, out):
        # pitch + timing NEVER change; only clashing velocities ease
        assert new.pitch == orig.pitch and new.start_beats == orig.start_beats
        assert new.dur_beats == orig.dur_beats
        pc = orig.pitch % 12
        rub = pc not in pcs and any((pc - c) % 12 in (1, 11) for c in pcs)
        if rub:
            assert new.velocity < orig.velocity, orig
        else:
            assert new.velocity == orig.velocity, orig
    # chord tones themselves are never softened
    tone = [n for n in riff.notes if n.pitch % 12 in pcs]
    assert tone and all(a.velocity == b.velocity for a, b in
                        zip(tone, [n for n in out if n.pitch % 12 in pcs]))


def test_riff_variants_are_deterministic_and_never_touch_verbatim():
    notes = _riff().notes
    assert riff_variant(notes, "verbatim") is notes  # same object, not a copy
    sparse = riff_variant(notes, "sparse")
    assert sparse and all(float(n.start_beats).is_integer() for n in sparse)
    low = riff_variant(notes, "sparse_low")
    assert [n.pitch + 12 for n in low] == [n.pitch for n in sparse]

    # octave_echo: sparse statement + soft +12 echoes two beats later, in-bar
    echo = riff_variant(notes, "octave_echo")
    assert echo[:len(sparse)] == sparse
    for n in echo[len(sparse):]:
        src = next(s for s in sparse if s.start_beats + 2.0 == n.start_beats)
        assert n.pitch == src.pitch + 12 and n.velocity < src.velocity
        assert n.start_beats < 4.0
    # call_response: first-half notes verbatim + soft -12 answers, octave-only
    cr = riff_variant(notes, "call_response")
    call = [n for n in notes if n.start_beats < 2.0]
    assert cr[:len(call)] == call
    for n in cr[len(call):]:
        assert n.pitch % 12 in {c.pitch % 12 for c in call}  # octave transforms only
        assert n.start_beats < 4.0
    assert riff_variant(notes, "octave_echo") == riff_variant(notes, "octave_echo")


def test_bass_notes_are_chord_roots_in_register():
    from kidseq_engine.arrange import bass_feel_for
    from kidseq_engine.render.drums import DRUM_PATTERNS

    for key in _KEYS:
        for style in DRUM_PATTERNS:
            riff = _riff(key, drum_style=style)
            prog = choose_progression(riff)
            semi, steps = _scale_steps(key)
            for variant in (0, 1, 2, 3):  # indices wrap per-genre
                feel = bass_feel_for(style, variant)
                notes = bass_notes(riff, prog, bars=8, feel=feel)
                assert notes
                for n in notes:
                    # base register C2-B2; octave-pop hits may sit C3-B3
                    assert 36 <= n.pitch <= 59, (key, style, variant, n)
                    bar = int(n.start_beats // 4)
                    root_pc = (semi + steps[prog[bar % 4]]) % 12
                    assert n.pitch % 12 == root_pc, (key, style, variant, bar, n)
                    assert n.start_beats + n.dur_beats <= (bar + 1) * 4.0 + 0.5, (style, n)


def test_bass_feel_variant0_matches_legacy_default():
    # variant 0 must reproduce the pre-style behaviour for every genre bucket
    from kidseq_engine.arrange import bass_feel_for

    riff = _riff()
    prog = choose_progression(riff)
    for style in ("techhouse", "garage", "reggaeton", "dnb", "drill", "hiphop"):
        r = _riff(drum_style=style)
        legacy = bass_notes(r, prog, bars=2)          # default feel branch
        v0 = bass_notes(r, prog, bars=2, feel=bass_feel_for(style, 0))
        assert legacy == v0, style


def test_pad_notes_are_diatonic_triads_in_register_for_every_genre_rhythm():
    from kidseq_engine.arrange import pad_rhythm_for
    from kidseq_engine.render.drums import DRUM_PATTERNS

    for key in _KEYS:
        riff = _riff(key)
        prog = choose_progression(riff)
        semi, steps = _scale_steps(key)
        for genre in DRUM_PATTERNS:
            for variant in (0, 1):
                for voicing in ("close", "first_inv", "alt"):
                    rhythm = pad_rhythm_for(genre, variant)
                    notes = pad_notes(riff, prog, bars=4, rhythm=rhythm,
                                      voicing=voicing)
                    assert len(notes) == 3 * len(rhythm) * 4, (genre, variant)
                    for b in range(4):
                        bar_notes = [n for n in notes
                                     if b * 4.0 <= n.start_beats < (b + 1) * 4.0]
                        want = {(semi + pc) % 12 for pc in _triad_pcs(prog[b], steps)}
                        # every chord onset voices exactly the bar's triad
                        assert {n.pitch % 12 for n in bar_notes} == want, (key, genre, b, voicing)
                        for n in bar_notes:
                            assert 60 <= n.pitch < 84, (key, genre, voicing, n)
                            assert n.dur_beats > 0, (key, genre, n)
                            # onsets stay inside their bar
                            assert n.start_beats + n.dur_beats <= (b + 1) * 4.0 + 0.5, (genre, n)


def test_default_pad_notes_keep_the_whole_bar_wash():
    # no rhythm argument = the original whole-bar behaviour (fallback callers)
    riff = _riff()
    prog = choose_progression(riff)
    notes = pad_notes(riff, prog, bars=2)
    assert len(notes) == 6
    assert all(n.dur_beats == 4.0 for n in notes)


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
    print("all arrange tests passed")
