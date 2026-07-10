"""Style layer — the seeded per-render decision system (pure, no assets)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.arrange.style import (  # noqa: E402
    _GENRE_MENU,
    PAD_ROLES,
    ArrangeStyle,
    choose_structure,
    choose_style,
)
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402
from kidseq_engine.render.vst_render import PATCHES  # noqa: E402
from kidseq_engine.sequence import _C4_MIDI, Note, Riff, _scale_steps  # noqa: E402


def _riff(key="C", tempo=120.0, drum_style="techhouse", instrument="piano") -> Riff:
    semi, steps = _scale_steps(key)
    tonic = _C4_MIDI + semi
    notes = [
        Note(pitch=tonic, start_beats=0.0, dur_beats=1.0),
        Note(pitch=tonic + steps[4], start_beats=2.0, dur_beats=1.5),
    ]
    return Riff(notes=notes, tempo=tempo, key=key,
                instrument=instrument, drum_style=drum_style)


def test_choose_style_is_deterministic():
    for genre in DRUM_PATTERNS:
        r = _riff(drum_style=genre)
        for v in (0, 1, 7, 999_999):
            assert choose_style(r, v) == choose_style(r, v), (genre, v)


def test_structure_depends_on_variation_only_never_the_riff():
    # two very different riffs, same nonce => identical skeleton decisions
    a = _riff("C", 120, "techhouse", "piano")
    b = _riff("Fm", 174, "dnb", "synth")
    for v in range(8):
        assert choose_style(a, v).structure == choose_style(b, v).structure, v
        assert choose_structure(v) == choose_style(a, v).structure, v


def test_every_genre_has_a_menu_and_options_are_renderable():
    for genre in DRUM_PATTERNS:
        menu = _GENRE_MENU[genre]
        # bass patches must exist as Surge patch dicts
        for patch in menu["bass_patch"]:
            assert patch in PATCHES, (genre, patch)
        # pad roles must be registered with a renderer route
        for role in menu["pad_role"]:
            assert role in PAD_ROLES, (genre, role)
        # variant indices are lists of ints starting at 0 (0 = base behaviour)
        for field in ("bass_feel", "pad_rhythm", "drum_variant"):
            opts = menu[field]
            assert opts and all(isinstance(i, int) and i >= 0 for i in opts), (genre, field)
        assert 0 in menu["drum_variant"], genre  # base pattern always available
        for t in menu["texture"]:
            assert t in (None, "crackle", "wash", "drone"), (genre, t)
        for rv in menu["riff_break_variant"]:
            assert rv in ("sparse_low", "octave_echo", "call_response"), (genre, rv)


def test_style_fields_are_decorrelated_across_nonces():
    """Marginals: every menu option must actually occur across nonces (once a
    menu has >1 option), and no field may be a pure function of another field's
    pick — the old `variation % 2` / `% 3` correlation bug, as a test."""
    r = _riff()
    styles = [choose_style(r, v) for v in range(200)]

    def picks(field):
        return [getattr(s, field) for s in styles]

    menu = _GENRE_MENU["techhouse"]
    for field in ("bass_patch", "pad_role", "texture", "riff_break_variant",
                  "bass_feel", "pad_rhythm", "drum_variant"):
        seen = set(picks(field))
        want = set(menu[field])
        assert seen == want, (field, seen, want)

    # structure: build_frac must not determine prog_pick (or vice versa) once
    # both have >1 option. Guarded so it activates as menus widen.
    fracs = sorted({s.structure.build_frac for s in styles})
    progs = sorted({s.prog_pick for s in styles})
    if len(fracs) > 1 and len(progs) > 1:
        combos = {(s.structure.build_frac, s.prog_pick) for s in styles}
        assert len(combos) > max(len(fracs), len(progs)), (
            "build_frac and prog_pick look locked together", sorted(combos))


def test_arrange_style_is_frozen_and_hashable():
    s = choose_style(_riff(), 0)
    assert isinstance(s, ArrangeStyle)
    try:
        object.__setattr__  # noqa: B018
        s_dict_ok = hash(s) == hash(choose_style(_riff(), 0))
    except TypeError:
        s_dict_ok = False
    assert s_dict_ok


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
    print("all style tests passed")
