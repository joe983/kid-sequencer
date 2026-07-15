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
    # 4 triad-anchored notes: firmly MELODIC under riff_tonality (R29 routes
    # 1-2 note patterns to the percussive/sparse treatment, so the melodic
    # fixture must be a real melody)
    semi, steps = _scale_steps(key)
    tonic = _C4_MIDI + semi
    notes = [
        Note(pitch=tonic, start_beats=0.0, dur_beats=1.0),
        Note(pitch=tonic + steps[2], start_beats=1.0, dur_beats=1.0),
        Note(pitch=tonic + steps[4], start_beats=2.0, dur_beats=1.5),
        Note(pitch=tonic + steps[2], start_beats=3.5, dur_beats=0.5),
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


def test_r19_bass_menus_weights_and_levers():
    # explicit weight lists must match their menus; feel indices must exist;
    # gate/pump levers pick from their menus and default sanely.
    from kidseq_engine.arrange import _BASS_FEELS
    from kidseq_engine.arrange.style import (_BASS_FEEL_W, _BASS_GATE,
                                             _BASS_PATCH_W, _PUMP_MENU)

    for genre, w in _BASS_PATCH_W.items():
        assert len(w) == len(_GENRE_MENU[genre]["bass_patch"]), genre
        assert abs(sum(w) - 1.0) < 1e-6, genre
    for genre, w in _BASS_FEEL_W.items():
        assert len(w) == len(_GENRE_MENU[genre]["bass_feel"]), genre
    for genre in DRUM_PATTERNS:
        feels = _BASS_FEELS.get(genre, [])
        for i in _GENRE_MENU[genre]["bass_feel"]:
            assert i < len(feels), (genre, i, len(feels))
    # owner asks encoded: reese no longer ~50% of dnb; drill untouched
    dnb = _GENRE_MENU["dnb"]["bass_patch"]
    assert _BASS_PATCH_W["dnb"][dnb.index("bass_reese")] <= 0.35
    assert "bass_pizz" in dnb and "bass_sub_roll" in dnb
    assert _GENRE_MENU["drill"]["bass_patch"] == ["bass_sub808", "bass_round"]
    assert _BASS_GATE["drill"] == ([1.0], None)
    # gate + pump land across variations (techhouse has both menus)
    r = _riff()
    styles = [choose_style(r, v) for v in range(200)]
    assert {s.bass_gate for s in styles} == {1.0, 0.6, 0.35}
    assert {s.pump_depth for s in styles} == {None, 0.35, 0.22}
    dnb_styles = [choose_style(_riff("C", 174, "dnb", "piano"), v)
                  for v in range(300)]
    assert {s.bass_patch for s in dnb_styles} == set(dnb)
    reese = sum(1 for s in dnb_styles if s.bass_patch == "bass_reese")
    assert reese / len(dnb_styles) < 0.5   # "stuck on reese" is gone
    assert _PUMP_MENU.get("dnb") is None   # pump lever is techhouse-only


def test_r26_r27_r28_ear_feedback_round_two():
    # R26: the dnb half-feel is OUT of the song-level skeleton menu and
    # lives on as the second-drop switch-up (melodic dnb only); no drummer
    # menu offers "static" (variety at least every 16 bars). R27: hiphop
    # NEVER rides a riser and its impact is soft. R28: the downlifter is
    # rarer on riser-led takes.
    from kidseq_engine.arrange.style import (_DRUMMER_MENU, _IMPACT,
                                             _SKELETON_MENU)
    from kidseq_engine.render.drums import DNB_HALF_SKELETON

    assert DNB_HALF_SKELETON not in _SKELETON_MENU["dnb"][0]
    for genre, (menu, _) in _DRUMMER_MENU.items():
        assert "static" not in menu, genre
        assert "sparse" in menu or "regular" in menu or "busy" in menu, genre

    dnb = [choose_style(_riff(drum_style="dnb"), v) for v in range(200)]
    mel = [s for s in dnb if s.production_mode == "melodic"]
    assert {s.half_switch for s in mel} == {True, False}
    for g in DRUM_PATTERNS:
        if g == "dnb":
            continue
        assert not any(choose_style(_riff(drum_style=g), v).half_switch
                       for v in range(50)), g

    hh = [choose_style(_riff(drum_style="hiphop"), v).fx_palette
          for v in range(200)]
    assert {p.riser_on for p in hh} == {False}
    assert _IMPACT["hiphop"][2] <= -12.0

    th = [choose_style(_riff(), v).fx_palette for v in range(400)]
    dl_with_riser = [p.downlifter_on for p in th if p.riser_on]
    dl_without = [p.downlifter_on for p in th if not p.riser_on]
    assert sum(dl_with_riser) / len(dl_with_riser) < \
        sum(dl_without) / len(dl_without)


def test_r24_percussive_doctrine():
    # R24: both low-end modes and both note treatments occur across takes;
    # pad-free leads (60/40); percussive textures follow the genre's
    # reference flavour menus.
    import json
    from pathlib import Path

    from kidseq_engine.arrange.style import _PERC_TEXTURE
    from kidseq_engine.sequence import parse_sequence

    payload = json.loads((Path(__file__).parents[1] / "examples" /
                          "cluster_riff.json").read_text(encoding="utf-8"))
    for genre, (tex_menu, _) in _PERC_TEXTURE.items():
        payload["drumStyle"] = genre
        r = parse_sequence(payload)
        styles = [choose_style(r, v) for v in range(200)]
        assert {s.perc_low for s in styles} == {"stabs", "accents"}, genre
        assert {s.perc_note_style for s in styles} == \
            {"dry_echo", "washed"}, genre
        for s in styles:
            assert s.texture in tex_menu, (genre, s.texture)
        none_share = sum(1 for s in styles
                         if s.percussive_pads == "none") / len(styles)
        assert none_share > 0.5, (genre, none_share)   # pad-free leads


def test_r23_percussive_mud_discipline():
    # R23: one sustained dark bed at a time (drone pads exclude drone/metal
    # textures), the moving pedals lead, and all three pedal shapes occur.
    import json
    from pathlib import Path

    from kidseq_engine.sequence import parse_sequence

    payload = json.loads((Path(__file__).parents[1] / "examples" /
                          "cluster_riff.json").read_text(encoding="utf-8"))
    r = parse_sequence(payload)
    styles = [choose_style(r, v) for v in range(300)]
    assert all(s.production_mode == "percussive" for s in styles)
    for s in styles:
        if s.percussive_pads == "drone":
            assert s.texture not in ("drone", "metal"), s.texture
    # metal stays reachable on the pad-free takes (the R16 signature)
    assert any(s.texture == "metal" and s.percussive_pads == "none"
               for s in styles)
    assert {s.percussive_pedal for s in styles} == {0, 1, 2}
    moving = sum(1 for s in styles if s.percussive_pedal in (1, 2))
    assert moving / len(styles) > 0.55   # the static root is the minority


def test_r22_reggaeton_polish():
    # R22: reggaeton has a tuned impact (no longer the generic default), the
    # conga rim overlay is reachable, and the dembow snare stays untouchable
    # across every skeleton and seasoning variant (Tainy rule).
    from kidseq_engine.arrange.style import _IMPACT
    from kidseq_engine.render.drums import (DRUM_SKELETONS, DRUM_VARIANTS,
                                            pattern_for)

    assert "reggaeton" in _IMPACT
    assert len(DRUM_VARIANTS["reggaeton"]) == 5
    assert max(_GENRE_MENU["reggaeton"]["drum_variant"]) == \
        len(DRUM_VARIANTS["reggaeton"])
    base_snare = pattern_for("reggaeton", 0)["snare"]
    for sk in range(len(DRUM_SKELETONS["reggaeton"]) + 1):
        for dv in range(len(DRUM_VARIANTS["reggaeton"]) + 1):
            assert pattern_for("reggaeton", dv, sk)["snare"] == base_snare


def test_r21_house_substyles():
    # R21: techhouse splits into classic/bigroom/minimal/detroit; every
    # sub-style's pads/stacks/rhythms are renderable; the rave flavours are
    # demoted in classic; other genres never carry a house_style.
    from kidseq_engine.arrange import _PAD_RHYTHMS
    from kidseq_engine.arrange.style import (_HOUSE_MENU, _HOUSE_PAD_MENU,
                                             _HOUSE_PUMP, _HOUSE_RHYTHM,
                                             _HOUSE_RUMBLE, _STACK_W,
                                             LEAD_STACKS, LEAD_VOICES,
                                             lead_stack_key)

    for house in _HOUSE_MENU[0]:
        for role in _HOUSE_PAD_MENU[house]:
            assert role in PAD_ROLES, (house, role)
        for i in _HOUSE_RHYTHM[house][0]:
            assert i < len(_PAD_RHYTHMS["techhouse"]), (house, i)
        assert house in _HOUSE_PUMP and house in _HOUSE_RUMBLE
        skey = lead_stack_key("techhouse", house)
        for stack in LEAD_STACKS[skey]:
            for voice, semi, gain_db in stack:
                assert voice in LEAD_VOICES, (house, voice)
                assert semi in (-12, 0, 12) and gain_db <= -8.0, (house, voice)
    assert lead_stack_key("techhouse", "classic") == "techhouse"
    assert lead_stack_key("dnb", None) == "dnb"
    assert len(_STACK_W["techhouse"]) == len(LEAD_STACKS["techhouse"])
    # classic demotion: rave_stab/acid recipes carry the LOW weights
    voices0 = [s[0][0] for s in LEAD_STACKS["techhouse"]]
    for i, v in enumerate(voices0):
        if v in ("rave_stab", "acid"):
            assert _STACK_W["techhouse"][i] <= 0.15, (v, i)

    styles = [choose_style(_riff(), v) for v in range(300)]
    assert {s.house_style for s in styles} == set(_HOUSE_MENU[0])
    for g in DRUM_PATTERNS:
        if g == "techhouse":
            continue
        assert choose_style(_riff(drum_style=g), 7).house_style is None, g
    # per-sub-style routing holds: bigroom never draws a classic-only role
    for s in styles:
        if s.production_mode == "melodic" and s.house_style:
            assert s.pad_role in _HOUSE_PAD_MENU[s.house_style], s.house_style


def test_r20_sparse_instrumentation_guarded():
    # lead_stack None and pads_on False both occur; the hollow-mid combo
    # (no stack + no pads + no texture) never survives choose_style.
    for genre in DRUM_PATTERNS:
        styles = [choose_style(_riff(drum_style=genre), v) for v in range(300)]
        assert any(s.lead_stack is None for s in styles), genre
        assert any(s.lead_stack is not None for s in styles), genre
        assert any(not s.pads_on for s in styles), genre
        for s in styles:
            if s.production_mode == "melodic":
                assert s.lead_stack is not None or s.pads_on \
                    or s.texture is not None, (genre, s)


def test_style_fields_are_decorrelated_across_nonces():
    """Marginals: every menu option must actually occur across nonces (once a
    menu has >1 option), and no field may be a pure function of another field's
    pick — the old `variation % 2` / `% 3` correlation bug, as a test."""
    r = _riff()
    styles = [choose_style(r, v) for v in range(200)]

    def picks(field):
        return [getattr(s, field) for s in styles]

    menu = _GENRE_MENU["techhouse"]
    from kidseq_engine.arrange.style import _HOUSE_PAD_MENU, _HOUSE_RHYTHM
    for field in ("bass_patch", "pad_role", "texture", "riff_break_variant",
                  "bass_feel", "pad_rhythm", "drum_variant", "pad_voicing",
                  "riff_ornament"):
        seen = set(picks(field))
        want = set(menu[field])
        if field == "pad_role":   # R21: sub-styles widen the role pool
            want = {r for m in _HOUSE_PAD_MENU.values() for r in m}
        if field == "pad_rhythm":
            want = {i for m, _ in _HOUSE_RHYTHM.values() for i in m}
        assert seen == want, (field, seen, want)
    from kidseq_engine.arrange.style import LEAD_STACKS
    # R20: None (no stack) joined the menu
    assert set(picks("lead_stack")) == \
        set(range(len(LEAD_STACKS["techhouse"]))) | {None}

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
    # dnb bass menu leads with the reese (R19 widened it — owner: "stuck on
    # reese every time"; the full menu/weight contract lives in the R19 test)
    dnb_bass = {choose_style(_riff(drum_style="dnb"), v).bass_patch
                for v in range(200)}
    assert dnb_bass == {"bass_reese", "bass_sub_roll", "bass", "bass_pizz",
                        "bass_acid"}
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
    # R22: reggaeton joined the odd-loop club (shaker undercurrent)
    assert {p.odd_loop_on for p in per_genre["reggaeton"]} == {True, False}
    assert {p.odd_loop_on for p in per_genre["drill"]} == {False}
    assert set(_GENRE_MENU["dnb"]["texture"]) == {"wash", None}
    # R22: reggaeton gained the warm-tape crackle bed
    assert set(_GENRE_MENU["reggaeton"]["texture"]) == {"wash", "crackle", None}


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
