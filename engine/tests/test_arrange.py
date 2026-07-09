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


def test_plan_totals_land_in_the_attention_window():
    for tempo in (60, 90, 120, 140, 170, 190):
        plan = plan_song(tempo)
        bars = sum(s.bars for s in plan)
        dur = bars * 4 * 60.0 / tempo
        assert 75.0 <= dur <= 240.0, (tempo, bars, dur)
        assert [s.name for s in plan][0] == "intro"
        # every drop keeps the verbatim riff — the fidelity guarantee
        for s in plan:
            if s.name.startswith("drop"):
                assert s.riff_variant == "verbatim" and s.drums == "full"


def test_riff_variants_are_deterministic_and_never_touch_verbatim():
    notes = _riff().notes
    assert riff_variant(notes, "verbatim") is notes  # same object, not a copy
    sparse = riff_variant(notes, "sparse")
    assert sparse and all(float(n.start_beats).is_integer() for n in sparse)
    low = riff_variant(notes, "sparse_low")
    assert [n.pitch + 12 for n in low] == [n.pitch for n in sparse]


def test_bass_notes_are_chord_roots_in_register():
    for key in _KEYS:
        for style in ("techhouse", "dnb", "drill"):
            riff = _riff(key, drum_style=style)
            prog = choose_progression(riff)
            semi, steps = _scale_steps(key)
            notes = bass_notes(riff, prog, bars=8)
            assert notes
            for n in notes:
                assert 36 <= n.pitch <= 47, (key, style, n)
                bar = int(n.start_beats // 4)
                root_pc = (semi + steps[prog[bar % 4]]) % 12
                assert n.pitch % 12 == root_pc, (key, style, bar, n)


def test_pad_notes_are_triads_one_per_bar():
    for key in _KEYS:
        riff = _riff(key)
        prog = choose_progression(riff)
        semi, steps = _scale_steps(key)
        notes = pad_notes(riff, prog, bars=4)
        assert len(notes) == 12  # 3 voices x 4 bars
        for b in range(4):
            bar_notes = [n for n in notes if n.start_beats == b * 4.0]
            assert len(bar_notes) == 3
            want = {(semi + pc) % 12 for pc in _triad_pcs(prog[b], steps)}
            assert {n.pitch % 12 for n in bar_notes} == want, (key, b)
            assert all(n.dur_beats == 4.0 and 60 <= n.pitch < 84 for n in bar_notes)


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
