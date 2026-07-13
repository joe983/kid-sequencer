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
        from kidseq_engine.arrange.style import (LEAD_STACKS, LEAD_VOICES,
                                                 PAD_VOICINGS, RIFF_ORNAMENTS)
        for o in menu["riff_ornament"]:
            assert o in RIFF_ORNAMENTS, (genre, o)
        for v in menu["pad_voicing"]:
            assert v in PAD_VOICINGS, (genre, v)
        # every genre has 1+ lead stacks; every stack layer is renderable,
        # sits at least 8 dB under the main voice, and shifts by octaves only
        stacks = LEAD_STACKS[genre]
        assert stacks, genre
        for stack in stacks:
            for voice, semi, gain_db in stack:
                assert voice in LEAD_VOICES, (genre, voice)
                assert semi in (-12, 0, 12), (genre, voice, semi)
                assert gain_db <= -8.0, (genre, voice, gain_db)


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
                  "bass_feel", "pad_rhythm", "drum_variant", "pad_voicing",
                  "riff_ornament"):
        seen = set(picks(field))
        want = set(menu[field])
        assert seen == want, (field, seen, want)
    from kidseq_engine.arrange.style import LEAD_STACKS
    assert set(picks("lead_stack")) == set(range(len(LEAD_STACKS["techhouse"])))

    # structure: build_frac must not determine prog_pick (or vice versa) once
    # both have >1 option. Guarded so it activates as menus widen.
    fracs = sorted({s.structure.build_frac for s in styles})
    progs = sorted({s.prog_pick for s in styles})
    if len(fracs) > 1 and len(progs) > 1:
        combos = {(s.structure.build_frac, s.prog_pick) for s in styles}
        assert len(combos) > max(len(fracs), len(progs)), (
            "build_frac and prog_pick look locked together", sorted(combos))


def test_fx_palette_r10_menu_coverage():
    """R10 transition-core palette fields: every menu option occurs across 200
    variations, and genre vocabularies hold (drill keeps rolls + shepard out)."""
    r = _riff()  # techhouse
    pals = [choose_style(r, v).fx_palette for v in range(200)]
    assert {p.gap_beats for p in pals} == {2.0, 1.0, 0.15}
    assert {p.gap_carry for p in pals} == {None, "texture"}
    assert {p.bass_starve_bars for p in pals} == {0, 1, 2}
    assert {p.riser_restraint for p in pals} == {True, False}
    assert {p.riser_style for p in pals} == {"classic", "shepard"}
    assert {p.fill_shape for p in pals} == {0, 2, 3, 4}
    d = [choose_style(_riff(drum_style="drill"), v).fx_palette
         for v in range(200)]
    assert {p.riser_style for p in d} == {"classic"}
    assert {p.fill_shape for p in d} == {1}
    assert {p.gap_beats for p in d} == {1.0, 0.15}


def test_fx_palette_r15_riser_and_gap_discipline():
    """R15 (owner ear feedback): riser level/colour vary per press; hiphop
    NEVER gets more than the micro-gap; the big gap never stacks on bass
    starvation; dnb leads with the proper reese."""
    per_genre = {g: [choose_style(_riff(drum_style=g), v).fx_palette
                     for v in range(300)]
                 for g in DRUM_PATTERNS}
    th = per_genre["techhouse"]
    assert {p.riser_db for p in th} == {-17.0, -14.0, -20.0}
    assert {p.riser_color for p in th} == {"smooth", "textured", "airy"}
    assert {p.riser_bars for p in th} == {8, 4, 2}
    assert {p.riser_color for p in per_genre["drill"]} == {"textured", "smooth"}
    # hiphop: the micro-breath only — never a real gap (owner: never needs it)
    assert {p.gap_beats for p in per_genre["hiphop"]} == {0.15}
    # gap/starve exclusion: a 2-beat cut never also starves; 1-beat caps at 1
    for g, pals in per_genre.items():
        for p in pals:
            if p.gap_beats >= 2.0:
                assert p.bass_starve_bars == 0, g
            elif p.gap_beats >= 1.0:
                assert p.bass_starve_bars <= 1, g
    # the big gap is the exception now, not the norm (<= ~1/3 of takes)
    big = sum(1 for p in th if p.gap_beats >= 2.0)
    assert big / len(th) < 0.35
    # dnb bass menu leads with the reese
    dnb_bass = {choose_style(_riff(drum_style="dnb"), v).bass_patch
                for v in range(200)}
    assert dnb_bass == {"bass_reese", "bass", "bass_acid"}
    # mini_downlifter is out of dnb's candy vocabulary (read cheap)
    for p in per_genre["dnb"]:
        assert "mini_downlifter" not in p.earcandy_menu


def test_fx_palette_r11_menu_coverage():
    """R11 ear-candy/vocabulary fields: coverage + genre gating (scratch is
    hiphop-only, drop_open garage-only, hiphop runs no candy cadence)."""
    from kidseq_engine.arrange.style import _CANDY_MENU
    from kidseq_engine.render.fx import CANDY_LEVELS

    per_genre = {g: [choose_style(_riff(drum_style=g), v).fx_palette
                     for v in range(200)]
                 for g in DRUM_PATTERNS}
    assert {p.earcandy_every for p in per_genre["techhouse"]} == {8, 4, 0}
    assert {p.earcandy_every for p in per_genre["hiphop"]} == {0}
    assert {p.earcandy_every for p in per_genre["reggaeton"]} == {8, 4}
    assert {p.swell_kind for p in per_genre["dnb"]} == {"delay", "reverb", None}
    assert {p.swell_kind for p in per_genre["techhouse"]} == {None}
    assert {p.scratch_on for p in per_genre["hiphop"]} == {True, False}
    assert {p.scratch_on for p in per_genre["techhouse"]} == {False}
    assert {p.drop_open for p in per_genre["garage"]} == {"no_pads", None}
    assert {p.drop_open for p in per_genre["dnb"]} == {None}
    assert {p.bomb_on for p in per_genre["dnb"]} == {True, False}
    # every candy-menu kind is either a fx.candy_blip kind or a placement kind
    placement_kinds = {"kick_fill", "drum_stop", "rev_swell_riff",
                       "rev_swell_delay"}
    for g, menu in _CANDY_MENU.items():
        for kind in menu:
            assert kind in CANDY_LEVELS or kind in placement_kinds, (g, kind)


def test_fx_palette_r12_menu_coverage():
    """R12 beds: rumble is techhouse-only, odd loop techhouse/garage; dnb and
    reggaeton finally have a texture menu."""
    per_genre = {g: [choose_style(_riff(drum_style=g), v).fx_palette
                     for v in range(200)]
                 for g in DRUM_PATTERNS}
    assert {p.rumble_on for p in per_genre["techhouse"]} == {True, False}
    assert {p.rumble_on for p in per_genre["dnb"]} == {False}
    assert {p.odd_loop_on for p in per_genre["techhouse"]} == {True, False}
    assert {p.odd_loop_on for p in per_genre["garage"]} == {True, False}
    assert {p.odd_loop_on for p in per_genre["drill"]} == {False}
    assert set(_GENRE_MENU["dnb"]["texture"]) == {"wash", None}
    assert set(_GENRE_MENU["reggaeton"]["texture"]) == {"wash", None}


def test_percussive_photek_variants_r16():
    """R16: percussive takes split between drone-bed and PAD-FREE (Photek);
    the industrial 'metal' texture is reachable; percussive takes lean off
    risers harder (owner: swooshes everywhere reads 90s-rave amateur)."""
    import json
    from pathlib import Path

    from kidseq_engine.sequence import parse_sequence

    payload = json.loads((Path(__file__).parents[1] / "examples" /
                          "cluster_riff.json").read_text(encoding="utf-8"))
    r = parse_sequence(payload)
    styles = [choose_style(r, v) for v in range(200)]
    assert all(s.production_mode == "percussive" for s in styles)
    assert {s.percussive_pads for s in styles} == {"drone", "none"}
    assert "metal" in {s.texture for s in styles}
    on = sum(1 for s in styles if s.fx_palette.riser_on)
    assert 0.30 < on / len(styles) < 0.70          # percussive: 50/50 riser
    # melodic tracks: risers now off on a real share of takes (~30%)
    mel = [choose_style(_riff(), v).fx_palette for v in range(300)]
    off = sum(1 for p in mel if not p.riser_on)
    assert 0.18 < off / len(mel) < 0.45
    # the new battery riffs all parse and land their designed mode
    for name, want in (("b_cluster", "percussive"), ("c_cluster", "percussive"),
                       ("d_cluster", "percussive"), ("b_major", "melodic"),
                       ("c_major", "melodic"), ("d_major", "melodic"),
                       ("b_minor", "melodic"), ("c_minor", "melodic"),
                       ("d_minor", "melodic")):
        p = json.loads((Path(__file__).parents[1] / "examples" /
                        f"{name}.json").read_text(encoding="utf-8"))
        rr = parse_sequence(p)
        modes = {choose_style(rr, v).production_mode for v in range(1, 30)}
        assert modes == {want}, (name, modes)


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
