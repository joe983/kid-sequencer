"""Per-render style decisions — the ONE place the variation nonce is spent.

`choose_style(riff, variation)` derives every nonce-driven choice once per
render into a frozen `ArrangeStyle`; nothing downstream touches `variation`
again. Before this module, `variation % 2` (progression) and `variation % 3`
(build:drop split) were moduloed independently, which correlates the picks —
every even nonce always paired progression 0 with one of the same splits.

Two seed domains, deliberately separate:
  * STRUCTURE fields derive from `variation` alone (no riff) so
    `plan_song(tempo, variation)` stays riff-free and its tempo-sweep tests
    need no riff fixture. Same nonce => same skeleton for any riff.
  * PALETTE fields derive from `fx.song_seed(riff, variation)` so the
    accompaniment choices also reshuffle when the riff changes.

Every field draws from its own named sub-stream (`_sub_rng`) — decorrelated by
construction, deterministic by construction.

`_GENRE_MENU` is the authenticity contract: per genre, a curated list of
allowed options per field, signature option first (weighted heaviest). The rng
only ever picks within the menu — "quintessentially the genre, not completely
so".
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

import numpy as np

from ..sequence import Riff
from ..render import fx


def _sub_rng(seed: int, name: str) -> np.random.Generator:
    """A named, decorrelated random stream — one per style field."""
    return np.random.default_rng([seed & 0xFFFFFFFF, zlib.crc32(name.encode())])


def _pick(seed: int, name: str, options: list, weights: list[float] | None = None):
    """Deterministic weighted pick from a menu via the field's own sub-stream."""
    if len(options) == 1:
        return options[0]
    rng = _sub_rng(seed, name)
    if weights is None:
        # signature-first default: first option ~50%, rest split the remainder
        rest = 0.5 / (len(options) - 1)
        weights = [0.5] + [rest] * (len(options) - 1)
    w = np.asarray(weights, dtype=np.float64)
    return options[int(rng.choice(len(options), p=w / w.sum()))]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StructureStyle:
    """Skeleton decisions — derived from `variation` only (never the riff)."""
    song_shape: str        # "classic" | "cold_open" | "double_drop" | "late_break"
    intro_bars: int        # 4 | 8
    break_bars: int        # 4 | 8
    outro_bars: int        # 4 | 8
    build_frac: float      # build share of a cycle
    drop_bias: str         # "short" | "normal" | "long" — biases drop clamps
    intro_character: str   # "sparse" | "pad_open" | "low"
    escalation: str        # "full" | "gain_only" | "off"


@dataclass(frozen=True)
class FxPalette:
    """Arrangement-FX dressing choices."""
    riser_on: bool = True
    riser_kind: str = "noise"      # "noise" sweep | "spinback" (tape brake)
    riser_bars: int = 8            # cap; still clamped to the build length
    riser_f0: float = 300.0        # noise-riser sweep band (genre character)
    riser_f1: float = 8000.0
    gate_depth: float = 0.5        # first-drop riser gate (later drops deepen)
    impact_f0: float = 80.0
    impact_f1: float = 35.0
    impact_db: float = -6.0
    downlifter_on: bool = True
    reverse_crash_on: bool = True
    fill_shape: int = 0            # index into the fill-shape menu
    throw: bool | None = None      # None = auto via fx.throw_fits
    intro_lpf: float = 2500.0      # intro riff filter (>=15k = wide open)
    # R10 transition core — the pro pre-drop moves (Noisia / KSHMR / Attack):
    gap_beats: float = 0.15        # pre-drop silence, in beats (clamped 1.1 s;
    #                                0.15 = the legacy 0.6-of-a-16th breath)
    gap_carry: str | None = None   # layer exempt from the gap (KSHMR: keep one
    #                                element running through the silence)
    bass_starve_bars: int = 0      # HP the bass for the build's final N bars —
    #                                the drop's low end lands as pure contrast
    riser_restraint: bool = True   # only drop 1 gets the full prominent riser;
    #                                later drops get half/reverse-only/none
    riser_style: str = "classic"   # "classic" | "shepard" (first riser only)
    # R15 riser feel (owner: samey, too prominent):
    riser_db: float = -12.0        # riser peak dBFS — varied per press
    riser_color: str = "smooth"    # noise character (fx._RISER_COLORS)
    # R17: sampled breakbeat fill take (0 = synthesized _fill_pattern; dnb
    # only for now — sample_kit.KIT_FILLS)
    fill_take: int = 0
    # R11 ear candy + genre FX vocabularies (all breath-level — Tumay):
    earcandy_every: int = 0        # 0 = off; 4|8 = phrase-boundary event cadence
    earcandy_menu: tuple = ()      # the genre's event kinds (fixed per genre)
    swell_kind: str | None = None  # "reverb"|"delay" reverse-riff swell, drops 2+
    scratch_on: bool = False       # hiphop: ONE turntable gesture per track
    drop_open: str | None = None   # garage: "no_pads" 2-bar drop opening
    bomb_on: bool = False          # breakdown-entry sub impact (fx_sub layer)
    # R12 beds (FxFlags.beds): the fullness layers under the kit
    rumble_on: bool = False        # techno rumble bed under drop kicks (Hades)
    odd_loop_on: bool = False      # 3-beat perc cell against the 4/4 (KiNK)


@dataclass(frozen=True)
class ArrangeStyle:
    """Everything the nonce decides for one render."""
    production_mode: str           # "melodic" | "percussive" (from riff_tonality)
    structure: StructureStyle
    prog_pick: int                 # index into choose_progression's candidates
    bass_patch: str                # Surge patch for the bass LAYER
    bass_feel: int                 # per-genre rhythm variant index
    pad_role: str                  # key into PAD_ROLES
    pad_rhythm: int                # per-genre rhythm variant index
    pad_voicing: str               # "close" | "first_inv" | "alt"
    texture: str | None            # "crackle" | "wash" | "drone" | None
    percussive_pedal: int          # 0 = static root pedal, 1 = root->fifth
    drum_variant: int              # seasoning overlay index (0 = base pattern)
    riff_break_variant: str        # riff transform used in breaks
    riff_ornament: str             # primary vary_end bar kind (vary_bar)
    riff_ornament_b: str           # secondary kind — alternates with primary
    lead_stack: int | None         # LEAD_STACKS recipe index; None = no stack
    fx_palette: FxPalette
    percussive_pads: str = "drone"  # "drone" | "none" — pad-free Photek takes
    # R17 drum variety (owner: "the drum beat is exactly the same in every
    # song"): base-beat skeleton variant + per-press sample-take swaps
    drum_skeleton: int = 0         # index into drums.DRUM_SKELETONS (0 = legacy)
    snare_take: int = 0            # index into sample_kit.KIT_ALTS snares
    hat_take: int = 0              # index into sample_kit.KIT_ALTS hats
    # R18: in-drop gesture cadence ("static" = never — today's behaviour)
    drummer: str = "static"        # "static" | "sparse" | "regular" | "busy"
    # R19: staccato articulation lever (multiplies bass-note durations) +
    # per-press sidechain pump depth (None = the genre preset)
    bass_gate: float = 1.0
    pump_depth: float | None = None
    # R20: pads render switch for melodic takes (percussive has its own
    # percussive_pads); guarded so lead+pads never BOTH drop without texture
    pads_on: bool = True
    # R31: per-genre producer style (techhouse: "bassled"|"discofunk"|
    # "latin"|"pianohouse"|"lofi"|"bigroom" — see _PRODUCER_MENU); None for
    # genres without a producer menu. Supersedes R21's house_style.
    producer_style: str | None = None
    # R31: per-press hat-lane swing override (None = the drums.SWING map —
    # every genre without a producer menu renders byte-identical)
    drum_swing: float | None = None
    # R24 percussive/sparse doctrine (owner: skeletal + spacious; low end
    # never sustained; the note treatment alternates per track)
    perc_low: str = "stabs"          # "stabs" | "accents"
    perc_note_style: str = "dry_echo"  # "dry_echo" | "washed"
    # R26: melodic dnb only — the second drop opens on the half-feel
    # skeleton for its first phrases, then snaps back (the switch-up)
    half_switch: bool = False

    @property
    def drum_takes(self) -> dict[str, int] | None:
        """Voice->alt-take dict for drums_audio_pattern (None = all default)."""
        t = {}
        if self.snare_take:
            t["snare"] = self.snare_take
        if self.hat_take:
            t["hatC"] = self.hat_take
        return t or None


# pad role -> (renderer, patch-or-preset name). The menu validity test walks
# this so a menu can never name an unrenderable role. Synth-family roles are
# Surge patches; keys-family roles are GM presets (real samples read truer for
# organs/e-pianos than a subtractive synth).
PAD_ROLES: dict[str, tuple[str, str]] = {
    "supersaw": ("vst", "pad"),
    "pluck": ("vst", "pad_pluck"),
    "dark": ("vst", "pad_dark"),
    "organ": ("sf", "pad_organ"),
    "epiano": ("sf", "pad_epiano"),
    "pizz": ("sf", "pad_pizz"),
    "warm": ("sf", "pad_warm"),
    "strings_pad": ("sf", "pad_strings"),
    "newage": ("sf", "pad_newage"),
    "glass": ("vst", "pad_glass"),
    "choir": ("sf", "pad_choir"),
    "brass_stab": ("sf", "pad_brass"),
    "clav": ("sf", "pad_clav"),
    "nylon": ("sf", "pad_nylon"),
    "fmep": ("sf", "pad_fmep"),
    # R21 techhouse sub-style roles
    "supersaw_chord": ("vst", "supersaw_chord"),   # big-room chords
    "dub_chord": ("vst", "dub_chord"),             # Berlin dub stab
    "string_machine": ("vst", "string_machine"),   # Detroit strings
    "piano": ("sf", "pad_piano"),                  # real grand (Salamander)
    # R31 producer-style roles
    "accordion": ("sf", "pad_accordion"),          # HUGEL cumbia hooks
    "felt_piano": ("sf", "pad_piano"),             # Fred lofi bed (PAD_POST LPF)
}

#: pad triad voicings pad_notes understands
PAD_VOICINGS = ("close", "first_inv", "alt")

# Lead-stack voices: texture layers rendered UNDER the kid's riff (never
# replacing their instrument) -> (renderer, patch-or-preset name).
LEAD_VOICES: dict[str, tuple[str, str]] = {
    "shimmer": ("vst", "pad_pluck"),   # glassy pluck (octave-up sparkle)
    "unison": ("vst", "synth"),        # the rave lead as unison body — EDM girth
    "body": ("vst", "pad_dark"),       # dark thickener (unison or -12)
    "glass": ("sf", "pad_newage"),     # GM bell-glass
    "keys": ("sf", "pad_epiano"),      # GM Rhodes doubling — boom-bap keys
    "strings": ("sf", "pad_strings"),  # GM string section whisper
    # twinkles
    "twinkle": ("sf", "pad_celesta"),
    "musicbox": ("sf", "pad_musicbox"),
    "vibes": ("sf", "pad_vibes"),
    "marimba": ("sf", "pad_marimba"),
    "kalimba": ("sf", "pad_kalimba"),
    "harp": ("sf", "pad_harp"),
    "bellglass": ("vst", "bell_glass"),
    # ravey synths
    "hoover": ("vst", "lead_hoover"),
    "acid": ("vst", "lead_acid"),
    "rave_stab": ("vst", "stab_rave"),
    "fifths": ("sf", "lead_fifths"),
    "square": ("sf", "lead_square"),
    # R21 techhouse sub-style voices
    "supersaw": ("vst", "supersaw_chord"),
    "dub": ("vst", "dub_chord"),
    "machine_strings": ("vst", "string_machine"),
    "piano": ("sf", "pad_piano"),
    # R31 producer-style voices
    "talkbox": ("vst", "lead_talkbox"),      # Dom Dolla vowel-wah hook
    "vocal_stab": ("vst", "stab_vocal"),     # MK/Fred chop-syllable stab
    "italo": ("vst", "lead_italo"),          # PDM sparkling lead
    "accordion": ("sf", "pad_accordion"),    # HUGEL cumbia riff
    "brass": ("sf", "pad_brass"),            # HUGEL mariachi stabs
    "organ_v": ("sf", "pad_organ"),          # MK M1-organ riff
    # R32c SMP voices: the producer's REAL one-shot repitched (smp_render).
    # kind "smp"; the name is an smp_render.SMP_VOICES key (which carries its
    # own Surge/SF fallback for no-asset renders).
    "chop_alien": ("smp", "chop_alien"),     # Dom Dolla talkbox-alien vocal
    "funk_stab": ("smp", "funk_stab"),       # PDM funk stab
    "chant_v": ("smp", "chant_v"),           # HUGEL cumbia chant
    "chop_real": ("smp", "chop_real"),       # MK dub vocal-sample syllable
    "chop_note": ("smp", "chop_note"),       # Fred voice-note fragment
    "rave_shot": ("smp", "rave_shot"),       # Guetta supersaw/rave stab
    "futurerave": ("vst", "lead_futurerave"),  # R32d Guetta saturated stab (VOICE_POST dist)
}

# Per-genre lead STACKS: always-on texture for the lead. Each stack is a list
# of (voice, semitone_shift, gain_db) layered under the main riff voice; the
# main voice renders untouched on top, and the riff layer's LUFS calibration
# holds the composite level — the lead gets RICHER, not louder. Signature
# stack first; style.lead_stack picks per press.
LEAD_STACKS: dict[str, list[list[tuple[str, int, float]]]] = {
    # R21: shimmer-led classic; the rave lead / stab / acid flavours are now
    # the occasional wink, not the default (_STACK_W demotes them — owner:
    # "still has this cheesy 90s feel")
    "techhouse": [
        [("shimmer", 12, -9.0), ("body", -12, -14.0)],
        [("unison", 0, -9.0), ("shimmer", 12, -13.0)],
        [("rave_stab", 0, -9.0), ("twinkle", 12, -13.0)],
        [("acid", 0, -10.0), ("shimmer", 12, -14.0)],
    ],
    # R31 techhouse PRODUCER-STYLE stacks (lead_stack_key routes here; the
    # plain "techhouse" bank above is the required per-genre fallback and is
    # never drawn while a producer is set)
    # R32c: each producer's SIGNATURE stack slot now leads with its REAL
    # repitched one-shot (smp voice); the Surge/SF flavours stay as alternates.
    "techhouse:bassled": [
        [("chop_alien", 0, -9.0), ("shimmer", 12, -14.0)],
        [("talkbox", 0, -10.0)],
        [("keys", 0, -10.0), ("shimmer", 12, -14.0)],
    ],
    "techhouse:discofunk": [
        [("funk_stab", 0, -9.0), ("machine_strings", 0, -13.0)],
        [("machine_strings", 0, -9.0), ("shimmer", 12, -14.0)],
        [("brass", 0, -10.0), ("italo", 12, -14.0)],
    ],
    "techhouse:latin": [
        [("chant_v", 0, -9.0), ("shimmer", 12, -14.0)],
        [("brass", 0, -9.0)],
        [("marimba", 0, -10.0), ("accordion", 0, -13.0)],
    ],
    "techhouse:pianohouse": [
        [("chop_real", 0, -9.0), ("piano", 0, -13.0)],
        [("piano", 0, -9.0), ("shimmer", 12, -14.0)],
        [("organ_v", 0, -10.0), ("vocal_stab", 12, -14.0)],
    ],
    "techhouse:lofi": [
        [("chop_note", 0, -10.0), ("keys", 0, -13.0)],
        [("keys", 0, -9.0), ("shimmer", 12, -15.0)],
        [("piano", 0, -10.0)],
    ],
    "techhouse:bigroom": [
        [("rave_shot", 0, -9.0), ("shimmer", 12, -14.0)],
        [("piano", 0, -9.0), ("supersaw", 0, -13.0)],
        [("futurerave", 0, -9.0), ("shimmer", 12, -14.0)],
    ],
    "dnb": [
        [("unison", 0, -10.0), ("shimmer", 12, -14.0)],
        [("strings", 12, -11.0), ("body", 0, -14.0)],
        [("hoover", 0, -10.0)],
        [("bellglass", 12, -11.0), ("body", -12, -14.0)],
    ],
    "garage": [
        [("shimmer", 12, -9.0), ("keys", 0, -13.0)],
        [("keys", 0, -9.0), ("shimmer", 12, -14.0)],
        [("vibes", 0, -10.0), ("twinkle", 12, -14.0)],
        [("bellglass", 12, -10.0), ("keys", 0, -13.0)],
    ],
    "drill": [
        [("body", -12, -10.0), ("strings", 12, -15.0)],
        [("body", 0, -9.0)],
        [("bellglass", 12, -13.0), ("body", -12, -10.0)],
        [("harp", 12, -11.0), ("body", -12, -13.0)],
    ],
    "hiphop": [
        [("keys", 0, -9.0)],
        [("body", -12, -11.0), ("keys", 0, -13.0)],
        [("vibes", 0, -10.0)],
        [("musicbox", 12, -12.0), ("body", -12, -12.0)],
    ],
    "reggaeton": [
        [("shimmer", 12, -10.0), ("keys", 0, -14.0)],
        [("keys", 0, -10.0)],
        [("marimba", 0, -10.0), ("twinkle", 12, -14.0)],
        [("kalimba", 0, -10.0), ("shimmer", 12, -14.0)],
    ],
}

#: riff variation-bar kinds (arrange.vary_bar) — bold pattern rewrites first,
#: light decorations after. "none" is no longer offered: every track varies
#: its riff on the cadence (the owner's spec — the hook still owns drop 1's
#: opening bars and every non-variation bar).
RIFF_ORNAMENTS = ("ending_fill", "answer", "retrigger", "rest_gap",
                  "cadence", "echo", "octave_pop", "push", "none")


# ---------------------------------------------------------------------------
# Genre menus (signature option FIRST — it carries ~50% of the weight)
# ---------------------------------------------------------------------------

# Menus widen per increment; fields not yet genre-differentiated share _BASE.
_BASE_MENU: dict[str, list] = {
    "bass_patch": ["bass"],
    "bass_feel": [0],
    "pad_role": ["supersaw"],
    "pad_rhythm": [0],
    "pad_voicing": ["close", "first_inv", "alt"],
    "texture": [None],
    "drum_variant": [0],
    "riff_break_variant": ["sparse_low"],
    "riff_ornament": ["ending_fill", "answer", "cadence", "retrigger",
                      "rest_gap", "echo"],
}


def _menu(**over) -> dict[str, list]:
    m = dict(_BASE_MENU)
    m.update(over)
    return m


_GENRE_MENU: dict[str, dict[str, list]] = {
    # pluck stabs are the tech-house signature; the supersaw wash is the alt.
    # Bass: plucky rolling line first, reese as the darker alt.
    "techhouse": _menu(pad_role=["pluck", "supersaw", "newage", "glass"],
                       pad_rhythm=[0, 1],
                       bass_patch=["bass_pluck", "bass_funk", "bass",
                                   "bass_acid", "bass_pizz"],
                       bass_feel=[0, 1, 2, 3, 4],
                       drum_variant=[0, 1, 2, 3], texture=[None, "crackle"],
                       riff_break_variant=["sparse_low", "octave_echo", "call_response"]),
    # dnb: supersaw wash (its pad identity) + cinematic strings/choir/glass;
    # reese leads but no longer dominates (R19 — owner: "stuck on reese every
    # time"): rolling clean sub + stab/pizz colours join the menu
    "dnb": _menu(pad_role=["supersaw", "strings_pad", "choir", "glass"],
                 pad_rhythm=[0, 1],
                 bass_patch=["bass_reese", "bass_sub_roll", "bass",
                             "bass_pizz", "bass_acid"],
                 bass_feel=[0, 1, 2, 3, 4, 5],
                 drum_variant=[0, 1, 2, 3], texture=[None, "crackle"],
                 riff_break_variant=["sparse_low", "octave_echo"]),
    # organ skank IS UK garage; pluck/clav/brass-stab alternates. Bouncy bass
    # with octave pops; FM knock as the alt colour.
    "garage": _menu(pad_role=["organ", "pluck", "clav", "brass_stab"],
                    pad_rhythm=[0, 1],
                    bass_patch=["bass_pluck", "bass_fm", "bass_funk", "bass"],
                    bass_feel=[0, 1, 2, 3],
                    drum_variant=[0, 1, 2, 3], texture=["crackle", None],
                    riff_break_variant=["sparse_low", "octave_echo", "call_response"]),
    # drill: dark closed-down sustain; cinematic strings + dark choir
    # (UK drill's string/choir-loop DNA). 808 sub + round alt. Breaks stay low.
    # (Owner: drill sounds great — menus deliberately untouched in R19.)
    "drill": _menu(pad_role=["dark", "strings_pad", "choir"], pad_rhythm=[0, 1],
                   bass_patch=["bass_sub808", "bass_round"], bass_feel=[0, 1],
                   drum_variant=[0, 1, 2], texture=["drone", None],
                   riff_break_variant=["sparse_low", "call_response"]),
    # hiphop: e-piano comping (boom-bap keys); warm pad / FM tines / clav.
    # 808 / round sub / FM knock / funk-pluck bass colours.
    "hiphop": _menu(pad_role=["epiano", "warm", "fmep", "clav"], pad_rhythm=[0, 1],
                    bass_patch=["bass_sub808", "bass_round", "bass_funk",
                                "bass_fm", "bass"],
                    bass_feel=[0, 1, 2],
                    drum_variant=[0, 1, 2, 3], texture=["crackle", None],
                    riff_break_variant=["sparse_low", "call_response"]),
    # reggaeton: pizzicato dembow-accent plucks; nylon guitar (the reggaeton
    # sound) / warm / strings alts. Tresillo bass with an octave answer;
    # short plucked colours lead (R19 — the real-world dembow bass is short).
    "reggaeton": _menu(pad_role=["pizz", "nylon", "warm", "strings_pad"],
                       pad_rhythm=[0, 1],
                       bass_patch=["bass_pluck", "bass_pizz", "bass_round",
                                   "bass"],
                       bass_feel=[0, 1, 2, 3],
                       drum_variant=[0, 1, 2, 3, 4, 5],
                       texture=["crackle", None],
                       riff_break_variant=["sparse_low", "octave_echo", "call_response"]),
}

# R19 explicit bass weights (owner: reese ~50% read as "every time"; bass
# variety per genre). None = the signature-first default. Lengths must match
# the menus above.
_BASS_PATCH_W: dict[str, list[float]] = {
    "techhouse": [0.35, 0.20, 0.15, 0.15, 0.15],
    "dnb": [0.35, 0.25, 0.15, 0.15, 0.10],
    "garage": [0.45, 0.20, 0.20, 0.15],
    "hiphop": [0.45, 0.20, 0.15, 0.10, 0.10],
    "reggaeton": [0.40, 0.25, 0.20, 0.15],
}
_BASS_FEEL_W: dict[str, list[float]] = {
    # offbeat total ~0.45 (owner: "doesn't always need the offbeat pump")
    "techhouse": [0.30, 0.20, 0.15, 0.20, 0.15],
    # the whole-bar reese drone (index 2) deweighted hard
    "dnb": [0.25, 0.20, 0.10, 0.15, 0.20, 0.10],
    "garage": [0.30, 0.30, 0.25, 0.15],
    "hiphop": [0.45, 0.35, 0.20],
    "reggaeton": [0.25, 0.35, 0.20, 0.20],
}

# R19 staccato articulation lever: multiplies every bass-note duration.
# drill/hiphop keep their 808 tails (that IS the genre); everyone else gets a
# real chance of a short-gated bassline.
_BASS_GATE: dict[str, tuple[list, list | None]] = {
    "techhouse": ([1.0, 0.6, 0.35], [0.50, 0.30, 0.20]),
    "dnb": ([1.0, 0.6, 0.35], [0.60, 0.25, 0.15]),
    "garage": ([1.0, 0.6], [0.70, 0.30]),
    "hiphop": ([1.0, 0.6], [0.80, 0.20]),
    "reggaeton": ([1.0, 0.6, 0.35], [0.50, 0.30, 0.20]),
    "drill": ([1.0], None),
}

# R19 per-press sidechain pump depth (None = the genre preset). Techhouse
# only: pump_depth 0.50 on every take was part of the "cheesy" read.
_PUMP_MENU: dict[str, tuple[list, list | None]] = {
    "techhouse": ([None, 0.35, 0.22], [0.50, 0.30, 0.20]),
}

# ---------------------------------------------------------------------------
# R31 PRODUCER STYLES (owner: "6 producers per genre with unique identifiable
# popular styles … so a second press on the same sequence never uses the same
# sound palette"). Techhouse first (supersedes the R21 house_style axis — the
# owner called that brief's references "old artists"); other genres add their
# own six later by extending these per-genre tables, no schema change.
# Internal keys are descriptive; the reference producers (comments/docs only):
#   bassled    — Dom Dolla         (rubber wobble bass IS the melody, talkbox)
#   discofunk  — Purple Disco Machine (octave funk bass, chuck, Italo strings)
#   latin      — HUGEL             (conga/bongo tumbao, accordion/brass hooks)
#   pianohouse — MK                (90s piano/organ stabs, vocal-chop lead)
#   lofi       — Fred again..      (felt piano, crackle bed, deep pump)
#   bigroom    — David Guetta      (supersaw stabs, long builds — R21 assets)
# ---------------------------------------------------------------------------

_PRODUCER_MENU: dict[str, tuple[list, list]] = {
    # balanced 6-way (NOT signature-first): every press should feel like a
    # different producer took the session
    "techhouse": (["bassled", "discofunk", "latin", "pianohouse", "lofi",
                   "bigroom"], [1, 1, 1, 1, 1, 1]),
}
_PRODUCER_PAD_MENU: dict[str, list[str]] = {
    "bassled": ["pluck", "piano", "dark"],
    "discofunk": ["string_machine", "clav", "epiano"],
    "latin": ["brass_stab", "organ", "accordion", "piano"],
    "pianohouse": ["piano", "organ", "epiano"],
    "lofi": ["felt_piano", "epiano", "warm"],
    "bigroom": ["supersaw_chord", "piano", "glass"],
}
# pad_rhythm per producer (indices into _PAD_RHYTHMS["techhouse"]: 2 = R21
# whole-bar sustain, 3 = R31 disco 8th-chuck, 4 = R31 offbeat organ skank)
_PRODUCER_RHYTHM: dict[str, tuple[list, list | None]] = {
    "bassled": ([0, 1], None),
    "discofunk": ([3, 1], [0.60, 0.40]),
    "latin": ([4, 0], [0.60, 0.40]),
    "pianohouse": ([4, 1], [0.60, 0.40]),
    "lofi": ([2], None),          # held emotional chords — the pump moves them
    "bigroom": ([2, 1], [0.60, 0.40]),
}
# bass is the strongest producer differentiator — patch + feel + gate are all
# producer-routed for techhouse (the _GENRE_MENU bass entries stay for
# reference/fallback but are no longer drawn from)
_PRODUCER_BASS: dict[str, tuple[list, list | None]] = {
    "bassled": (["bass_wobble", "bass_funk", "bass_fm"], [0.60, 0.25, 0.15]),
    "discofunk": (["bass_moog", "bass_pluck"], [0.65, 0.35]),
    "latin": (["bass_pluck", "bass_round"], [0.65, 0.35]),
    "pianohouse": (["bass_organ", "bass_round", "bass_pluck"],
                   [0.50, 0.25, 0.25]),
    "lofi": (["bass_round", "bass"], [0.70, 0.30]),
    "bigroom": (["bass", "bass_pluck"], [0.70, 0.30]),
}
# feel indices into _BASS_FEELS["techhouse"] (5-8 = the R31 producer feels)
_PRODUCER_FEEL: dict[str, tuple[list, list | None]] = {
    "bassled": ([7, 4], [0.55, 0.45]),     # kick call-response / funk 16ths
    "discofunk": ([5], None),              # octave-pop 8ths
    "latin": ([6, 0], [0.60, 0.40]),       # tumbao locks / offbeat
    "pianohouse": ([0, 4], [0.55, 0.45]),
    "lofi": ([8, 3], [0.60, 0.40]),        # held roots / on-beat quarters
    "bigroom": ([1], None),                # rolling 8th pairs — the engine room
}
_PRODUCER_GATE: dict[str, tuple[list, list | None]] = {
    "bassled": ([0.35, 0.6], [0.60, 0.40]),
    "discofunk": ([0.35, 0.6], [0.70, 0.30]),
    "latin": ([0.6, 0.35], [0.60, 0.40]),
    "pianohouse": ([0.6, 0.35], [0.60, 0.40]),
    "lofi": ([1.0], None),                 # soft cushion, never gated
    "bigroom": ([1.0, 0.6], [0.70, 0.30]),
}
# pump per producer (None = preset 0.50; 0.62 sits under master's 0.65 cap):
# lofi/bigroom treat the pump AS the feel, discofunk stays gentle
_PRODUCER_PUMP: dict[str, tuple[list, list | None]] = {
    "bassled": ([None, 0.35], [0.60, 0.40]),
    "discofunk": ([0.35, None, 0.22], [0.50, 0.30, 0.20]),
    "latin": ([0.35, None], [0.60, 0.40]),
    "pianohouse": ([0.35, 0.22], [0.60, 0.40]),
    "lofi": ([0.62, None], [0.60, 0.40]),
    "bigroom": ([None, 0.62], [0.60, 0.40]),
}
# rumble bed was a Berlin-techno flavour — only bassled/bigroom keep a taste
_PRODUCER_RUMBLE: dict[str, tuple[list, list | None]] = {
    "bassled": ([False, True], [0.60, 0.40]),
    "discofunk": ([False], None),
    "latin": ([False], None),
    "pianohouse": ([False], None),
    "lofi": ([False], None),
    "bigroom": ([False, True], [0.70, 0.30]),
}
# per-press hat-lane swing (drums.swung_step_offset override; kick/clap are
# even-step so the pinned backbone can never move): bigroom machine-straight,
# pianohouse carries the MK shuffle
_PRODUCER_SWING: dict[str, tuple[list, list | None]] = {
    "bassled": ([0.06], None),
    "discofunk": ([0.05], None),
    "latin": ([0.10], None),
    "pianohouse": ([0.13], None),
    "lofi": ([0.11], None),
    "bigroom": ([0.02], None),
}
# seasoning-variant menus (indices into DRUM_VARIANTS["techhouse"]; 0 = base,
# 4 = conga tumbao, 5 = disco perc, 6 = foley knocks, 7 = bongo conversation).
# latin never runs bare — the percussion IS its identity.
_PRODUCER_DRUMV: dict[str, list[int]] = {
    "bassled": [0, 1, 2],
    "discofunk": [5, 2],
    "latin": [4, 7, 2],
    "pianohouse": [0, 1],
    "lofi": [6, 0],
    "bigroom": [0, 1],
}
# lead-stack sit-out weight (replaces the R21 minimal special-case): the
# bassled hook should almost always speak
_PRODUCER_LEAD_NONE: dict[str, float] = {"bassled": 0.15, "lofi": 0.20}
# pads on/off per producer: bassled leaves space (his pads are rare/low);
# lofi PINS pads on (the felt-piano chords are the emotional core)
_PRODUCER_PADS_ON: dict[str, tuple[list, list | None]] = {
    "bassled": ([True, False], [0.55, 0.45]),
    "lofi": ([True], None),
}
# FX routing per producer (consumed by _choose_fx_palette):
# bigroom PINS the riser on (the long filtered build IS the signature;
# riser_restraint still tames later drops); latin/lofi lean off
_PRODUCER_RISER_ON: dict[str, tuple[list, list | None]] = {
    "bigroom": ([True], None),
    "pianohouse": ([True, False], [0.60, 0.40]),
    "latin": ([False, True], [0.60, 0.40]),
    "lofi": ([False, True], [0.70, 0.30]),
}
_PRODUCER_RISER_DB: dict[str, tuple[list, list]] = {
    "bigroom": ([-14.0, -17.0, -20.0], [0.50, 0.30, 0.20]),
    "lofi": ([-20.0, -17.0], [0.60, 0.40]),
}
# fill shapes (subset of _FILL_MENU["techhouse"]): bigroom rides the
# subdivision-doubling roll, latin's hat-roll stands in for a timbale roll
_PRODUCER_FILL: dict[str, list[int]] = {
    "bigroom": [3, 0],
    "latin": [2],
    "lofi": [0],
}
_PRODUCER_FILL_DEFAULT: list[int] = [0, 2, 4]
# lofi gets the reverse-riff swell (Fred's reverse-reverb-into-downbeat move)
_PRODUCER_SWELL: dict[str, tuple[list, list | None]] = {
    "lofi": (["reverb", None], [0.60, 0.40]),
}
# R32e: each producer's ear-candy menu now leads with its SAMPLED fx one-shots
# (smp_*, played by fx_samples.fx_shot; remap to the synth kind when the pack is
# absent). smp_slide/smp_riser are sweep-family (R28 cap applies). pianohouse
# stays restrained (MK) — a subtle hat lift only, no sampled fx.
_PRODUCER_CANDY: dict[str, tuple] = {
    "bassled": ("smp_slide", "smp_rev", "hat_lift"),
    "discofunk": ("smp_tom_zap", "hat_lift"),
    "latin": ("smp_crowd", "smp_perk", "smp_rev_perk", "hat_lift"),
    "lofi": ("smp_rev_swell", "rev_swell_riff"),
    "bigroom": ("smp_riser", "smp_impact", "smp_slide", "hat_lift"),
    "pianohouse": ("hat_lift",),
}
# stack weights for the LEGACY techhouse fallback bank only (producer banks
# draw uniform); kept because the renderability walk requires a per-genre bank
_STACK_W: dict[str, list[float]] = {
    "techhouse": [0.40, 0.30, 0.15, 0.15],
}


def lead_stack_key(genre: str | None, producer: str | None) -> str:
    """LEAD_STACKS key for a render: producer styles get their own stack
    banks (`<genre>:<key>`); everything else uses the genre key."""
    g = genre or ""
    if producer:
        key = f"{g}:{producer}"
        if key in LEAD_STACKS:
            return key
    return g


# R20 sparse instrumentation (owner: "don't have to use all types of
# instruments in every song — some tracks don't need pads/organs/string long
# sounds"): probability the lead stack sits out, and the pads on/off menu.
# choose_style guards the combination: a take never drops BOTH unless a
# texture bed carries the mid.
_LEAD_NONE_W: dict[str, float] = {"drill": 0.30, "hiphop": 0.30}
_LEAD_NONE_DEFAULT = 0.25
_PADS_ON: dict[str, tuple[list, list | None]] = {
    "drill": ([True, False], [0.70, 0.30]),
}
_PADS_ON_DEFAULT: tuple[list, list | None] = ([True, False], [0.80, 0.20])


def _menu_for(genre: str | None) -> dict[str, list]:
    return _GENRE_MENU.get(genre or "", _GENRE_MENU["techhouse"])


# R24 percussive texture REFERENCE flavours (owner picked all three):
# Photek/Source Direct = dnb+drill (metal, surgical), Burial = garage+hiphop
# (crackle, ghostly), Rhythm & Sound dub breath via drone. R30: "wash" is
# BANNED — a filtered-noise bed IS a continuous swoosh, which is exactly
# what the owner keeps flagging ("swooshes all the way through sounds
# crap"). Tonal/textural beds only. techhouse leans crackle over drone
# ("too dubbed out — still need to hear that it is tech house").
_PERC_TEXTURE: dict[str, tuple[list, list]] = {
    "dnb": (["metal", "drone", "crackle"], [0.45, 0.35, 0.20]),
    "drill": (["metal", "drone", "crackle"], [0.45, 0.35, 0.20]),
    "garage": (["crackle", "drone", "metal"], [0.50, 0.30, 0.20]),
    "hiphop": (["crackle", "drone", "metal"], [0.50, 0.30, 0.20]),
    "techhouse": (["crackle", "drone", "metal"], [0.45, 0.35, 0.20]),
    "reggaeton": (["crackle", "drone", "metal"], [0.50, 0.30, 0.20]),
}

# percussive-mode drone roles per genre (no chord-implying comping sounds)
_DRONE_ROLES: dict[str, list[str]] = {
    "drill": ["dark", "choir"],
    "hiphop": ["dark", "choir", "warm"],
    "dnb": ["dark", "glass", "strings_pad"],
    "techhouse": ["dark", "glass"],
    "garage": ["dark", "glass", "warm"],
    "reggaeton": ["dark", "warm"],
}


# ---------------------------------------------------------------------------
# Choosers
# ---------------------------------------------------------------------------


#: song shapes plan_song understands (see its docstring for the grammars)
SONG_SHAPES = ("classic", "cold_open", "double_drop", "late_break")


def choose_structure(variation: int = 0) -> StructureStyle:
    """Skeleton choices from the nonce alone — the section skeleton itself
    varies per press: different song shapes, shorter or longer builds and
    drops, different intro/break/outro sizes. plan_song's corrective loop
    keeps every combination inside the 180–240 s window."""
    return StructureStyle(
        song_shape=_pick(variation, "song_shape", list(SONG_SHAPES),
                         [0.40, 0.20, 0.20, 0.20]),
        intro_bars=_pick(variation, "intro_bars", [4, 8], [0.60, 0.40]),
        break_bars=_pick(variation, "break_bars", [8, 4], [0.60, 0.40]),
        outro_bars=_pick(variation, "outro_bars", [4, 8], [0.70, 0.30]),
        build_frac=_pick(variation, "build_frac",
                         [1 / 3.0, 1 / 4.0, 2 / 5.0, 1 / 5.0, 1 / 2.0],
                         [0.30, 0.20, 0.20, 0.15, 0.15]),
        drop_bias=_pick(variation, "drop_bias", ["normal", "short", "long"],
                        [0.50, 0.25, 0.25]),
        intro_character=_pick(variation, "intro_character",
                              ["sparse", "pad_open", "fragment", "high", "low",
                               "drums_first", "atmos"],
                              [0.24, 0.16, 0.16, 0.12, 0.12, 0.10, 0.10]),
        escalation=_pick(variation, "escalation", ["full", "gain_only", "off"],
                         [0.60, 0.25, 0.15]),
    )


# genre -> impact boom (f0, f1, level dB). drill/hiphop dive deeper (they
# already run quiet_fx_db -5); garage keeps it light; dnb slightly higher f0.
# reggaeton tuned in R22 (owner: it read more amateur than the rest — it was
# the only genre still on the generic default).
_IMPACT: dict[str, tuple[float, float, float]] = {
    "drill": (60.0, 28.0, -6.0),
    "hiphop": (60.0, 28.0, -12.0),   # R27: boom-bap drops arrive, not explode
    "dnb": (70.0, 35.0, -6.0),
    "garage": (80.0, 35.0, -9.0),
    "reggaeton": (70.0, 32.0, -7.0),
}

# genre -> allowed fill shapes (see arrange/render.py _fill_pattern):
# 0 = snare roll, 1 = rim-led into snare, 2 = hat-roll landing on snare,
# 3 = 2-bar subdivision-doubling roll (quarters->8ths->16ths — Adam Douglas'
# build mechanics), 4 = rug-pull 16th roll that stops dead at beat 3.
# Rolls are not the drill/hiphop vocabulary — they keep the rim fill.
_FILL_MENU: dict[str, list[int]] = {
    "techhouse": [0, 2, 3, 4], "garage": [0, 2, 3], "reggaeton": [0, 3],
    "drill": [1], "hiphop": [1], "dnb": [0, 3, 4],
}

# R17 — base-beat SKELETON variant menus (drums.DRUM_SKELETONS; 0 = legacy).
# dnb spreads widest (owner: its beat was identical every song); the genres
# the owner called good stay legacy-heavy.
_SKELETON_MENU: dict[str, tuple[list, list | None]] = {
    # dnb skeleton 3 (half-feel) is OUT of the song-level menu (owner R26:
    # "would work for some sections but not the whole song") — it lives on
    # as the half_switch section switch-up instead
    "dnb": ([0, 1, 2], [0.40, 0.30, 0.30]),
    "drill": ([0, 1, 2], [0.60, 0.25, 0.15]),
    "garage": ([0, 1], [0.70, 0.30]),
    "hiphop": ([0, 1], [0.70, 0.30]),
    "reggaeton": ([0, 1], [0.75, 0.25]),
    "techhouse": ([0, 1], [0.75, 0.25]),
}

# R17 — per-press sample-take swaps (sample_kit.KIT_ALTS; 0 = the pack
# default). Only dnb has alternates so far (the owner's own library).
_SNARE_TAKES: dict[str, tuple[list, list | None]] = {
    "dnb": ([0, 1, 2, 3, 4], [0.32, 0.17, 0.17, 0.17, 0.17]),
}
_HAT_TAKES: dict[str, tuple[list, list | None]] = {
    "dnb": ([0, 1], [0.65, 0.35]),
}

# R17 — sampled breakbeat fill takes (sample_kit.KIT_FILLS; 0 = synthesized).
_FILL_TAKES: dict[str, tuple[list, list | None]] = {
    "dnb": ([0, 1, 2, 3, 4], [0.30, 0.175, 0.175, 0.175, 0.175]),
}

# R18/R26 — per-press DRUMMER personality (owner R26: "still need drum beat
# variety AT LEAST every 16 bars"). Sets the in-drop gesture cadence
# (render._drummer_gestures): busy = every 4 bars, regular = 8, sparse = 16.
# "static" is GONE from every menu — sparse (16) is the floor now; dnb
# leans busiest (its beats read most repetitive).
_DRUMMER_MENU: dict[str, tuple[list, list | None]] = {
    "dnb": (["busy", "regular", "sparse"], [0.40, 0.40, 0.20]),
    "techhouse": (["regular", "sparse", "busy"], [0.45, 0.30, 0.25]),
    "garage": (["regular", "busy", "sparse"], [0.40, 0.35, 0.25]),
    "drill": (["sparse", "regular"], [0.60, 0.40]),
    "hiphop": (["sparse", "regular"], [0.60, 0.40]),
    "reggaeton": (["sparse", "regular"], [0.55, 0.45]),
}

# genre -> pre-drop gap length menu, in BEATS (clamped to 1.1 s at render so
# slow tempos never read as broken). The pros cut a real breath — but NOT on
# every song (owner R15: overused gaps read obvious/ineffective). The big
# 2-beat cut is now the exception; hiphop NEVER gets more than the legacy
# micro-breath; drill leans micro. A big gap also excludes bass starvation
# (see _choose_fx_palette) — stacking both was too much.
_GAP_BEATS: dict[str, tuple[list, list]] = {
    "drill": ([0.15, 1.0], [0.65, 0.35]),
    "hiphop": ([0.15], None),
    "reggaeton": ([1.0, 0.15, 2.0], [0.45, 0.30, 0.25]),
}
_GAP_BEATS_DEFAULT: tuple[list, list] = ([1.0, 0.15, 2.0], [0.40, 0.35, 0.25])

# genre -> bass-starvation menu (bars of HP'd bass at the end of each build —
# Noisia: no low end right before the drop makes the drop read bass-heavy)
_STARVE_BARS: dict[str, tuple[list, list]] = {
    "garage": ([1, 0], [0.60, 0.40]),
    "reggaeton": ([1, 0], [0.60, 0.40]),
    "drill": ([0, 1], [0.60, 0.40]),
    "hiphop": ([0, 1], [0.60, 0.40]),
}
_STARVE_BARS_DEFAULT: tuple[list, list] = ([1, 2, 0], [0.50, 0.30, 0.20])

# genre -> riser style menu ("shepard" = the cyclic endless-rise layers,
# Sub Focus' 'Vapourise' move — a dnb/techno flavour first)
_RISER_STYLE: dict[str, tuple[list, list]] = {
    "garage": (["classic", "shepard"], [0.70, 0.30]),
    "reggaeton": (["classic", "shepard"], [0.70, 0.30]),
    "drill": (["classic"], None),
    "hiphop": (["classic"], None),
}
_RISER_STYLE_DEFAULT: tuple[list, list] = (["classic", "shepard"], [0.55, 0.45])

# riser LEVEL menu (dBFS peak) — pros keep risers well under the mix (owner
# R15: -12 read too prominent everywhere). Varied per press so even two
# riser-led takes don't sit identically.
_RISER_DB_MENU: tuple[list, list] = ([-17.0, -14.0, -20.0], [0.50, 0.30, 0.20])

# riser COLOUR menu (fx._RISER_COLORS): smooth / textured / airy — one
# white-noise recipe for every riser is what read samey. drill/hiphop lean
# textured (dark organic sweeps fit their palettes).
_RISER_COLOR: dict[str, tuple[list, list]] = {
    "drill": (["textured", "smooth"], [0.60, 0.40]),
    "hiphop": (["textured", "smooth"], [0.60, 0.40]),
}
_RISER_COLOR_DEFAULT: tuple[list, list] = (["smooth", "textured", "airy"],
                                           [0.40, 0.35, 0.25])

# genre -> phrase-boundary ear-candy vocabulary (render/fx.candy_blip kinds
# plus the placement kinds "kick_fill" and "drum_stop" handled in render.py).
# All breath-level. hiphop's single gesture is the scratch (its own field) —
# Premier: one DJ element per record, so no rolling candy cadence there.
_CANDY_MENU: dict[str, tuple] = {
    "techhouse": ("sweep_up", "sweep_down", "hat_lift"),
    # R15: mini_downlifter out of dnb — the falling tone read cheap in the
    # dnb take; its candy is now swells/sirens/textured falls only
    "dnb": ("rev_swell_delay", "siren_blip", "sweep_down"),
    "garage": ("kick_fill", "rev_cymbal", "siren_blip"),
    "drill": ("rev_swell_riff", "sig_chirp"),
    "hiphop": (),
    "reggaeton": ("drum_stop", "siren_blip"),
}
_CANDY_EVERY: dict[str, tuple[list, list | None]] = {
    "techhouse": ([8, 4, 0], [0.5, 0.3, 0.2]),
    "dnb": ([8, 4, 0], [0.5, 0.3, 0.2]),
    "garage": ([8, 4, 0], [0.4, 0.4, 0.2]),
    "drill": ([8, 0], [0.6, 0.4]),
    "hiphop": ([0], None),
    "reggaeton": ([8, 4], [0.5, 0.5]),
}

# genre -> reverse-riff swell into drops 2+ (the drill/dnb/garage move: the
# transition is made of the track's own melodic material)
_SWELL: dict[str, tuple[list, list | None]] = {
    "drill": (["reverb", None], [0.60, 0.40]),
    "dnb": (["delay", "reverb", None], [0.40, 0.30, 0.30]),
    "garage": (["delay", None], [0.50, 0.50]),
}

# genre -> breakdown-entry bomb (dnb/techhouse/drill lean in; others rare)
_BOMB: dict[str, tuple[list, list]] = {
    "dnb": ([True, False], [0.5, 0.5]),
    "techhouse": ([True, False], [0.5, 0.5]),
    "drill": ([True, False], [0.5, 0.5]),
}
_BOMB_DEFAULT: tuple[list, list] = ([False, True], [0.75, 0.25])

# genre -> noise-riser sweep band: dark low-mid swells for drill/hiphop,
# wide fast sweeps for dnb, classic white for the four-to-floor styles
_RISER_BAND: dict[str, tuple[float, float]] = {
    "drill": (200.0, 2500.0), "hiphop": (200.0, 2500.0),
    "dnb": (400.0, 12000.0), "garage": (300.0, 6000.0),
}

# genre -> riser-kind menu (spinback = vinyl brake, the garage/hiphop move)
_RISER_KIND: dict[str, tuple[list, list]] = {
    "garage": (["noise", "spinback"], [0.60, 0.40]),
    "hiphop": (["spinback", "noise"], [0.60, 0.40]),
}


def _choose_fx_palette(seed: int, genre: str | None,
                       percussive: bool = False,
                       producer: str | None = None) -> FxPalette:
    """Seeded dressing choices within the genre's taste. Boom-bap doesn't ride
    white-noise risers — hiphop defaults them OFF (reverse crash still swells).
    R16 (owner: swooshes everywhere reads 90s-rave amateur): a real share of
    takes now run NO riser at all — the reverse crash and fills carry those
    transitions; percussive/industrial takes lean riser-off harder. R31: a
    producer style recolours riser/fill/candy/swell/rumble — but the hiphop
    and percussive disciplines above always win the riser decision."""
    g = genre or ""
    if g == "hiphop":
        # R27 (owner: "hip hop doesn't EVER need such a big build and drop —
        # that's not the style at all"): risers never fire
        riser_menu = ([False], None)
    elif percussive:
        # R30: percussive/sparse takes barely ever ride a riser — sweeps
        # were reading as wall-to-wall swoosh on top of the beds
        riser_menu = ([False, True], [0.75, 0.25])
    elif producer and producer in _PRODUCER_RISER_ON:
        riser_menu = _PRODUCER_RISER_ON[producer]
    else:
        riser_menu = ([True, False], [0.70, 0.30])
    f0, f1, db = _IMPACT.get(g, (80.0, 35.0, -6.0))
    rf0, rf1 = _RISER_BAND.get(g, (300.0, 8000.0))
    kind_menu = _RISER_KIND.get(g, (["noise"], None))
    # gap + starvation interplay (owner R15: stacking both was too much) —
    # a big 2-beat cut never also starves the bass; a 1-beat cut caps it at 1
    gap_beats = _pick(seed, "gap_beats", *_GAP_BEATS.get(g, _GAP_BEATS_DEFAULT))
    starve = _pick(seed, "bass_starve_bars",
                   *_STARVE_BARS.get(g, _STARVE_BARS_DEFAULT))
    if gap_beats >= 2.0:
        starve = 0
    elif gap_beats >= 1.0:
        starve = min(starve, 1)
    riser_on = _pick(seed, "riser_on", *riser_menu)
    # R28 swoosh discipline (owner: "never have the swoosh going up and down
    # over and over"): the downlifter is rarer overall, and rarer still on
    # takes whose drops already ride a riser — up-then-down-then-up is the
    # exact shape that read as crap.
    dl_menu = ([True, False], [0.35, 0.65]) if riser_on \
        else ([True, False], [0.50, 0.50])
    crash_menu = ([True, False], [0.40, 0.60]) if g == "hiphop" \
        else ([True, False], [0.8, 0.2])
    return FxPalette(
        riser_on=riser_on,
        riser_kind=_pick(seed, "riser_kind", *kind_menu),
        riser_bars=_pick(seed, "riser_bars", [8, 4, 2], [0.50, 0.35, 0.15]),
        riser_f0=rf0, riser_f1=rf1,
        gate_depth=_pick(seed, "gate_depth", [0.5, 0.7], [0.6, 0.4]),
        impact_f0=f0, impact_f1=f1, impact_db=db,
        downlifter_on=_pick(seed, "downlifter_on", *dl_menu),
        reverse_crash_on=_pick(seed, "reverse_crash_on", *crash_menu),
        fill_shape=_pick(seed, "fill_shape",
                         (_PRODUCER_FILL.get(producer, _PRODUCER_FILL_DEFAULT)
                          if producer else _FILL_MENU.get(g, [0]))),
        fill_take=_pick(seed, "fill_take", *_FILL_TAKES.get(g, ([0], None))),
        # None = auto (fx.throw_fits decides); False = suppressed this take
        throw=_pick(seed, "throw", [None, False], [0.75, 0.25]),
        # varied intro colour: dark tease .. wide open (>=15k skips the filter)
        intro_lpf=_pick(seed, "intro_lpf", [2500.0, 1500.0, 4000.0, 18000.0],
                        [0.35, 0.25, 0.25, 0.15]),
        gap_beats=gap_beats,
        gap_carry=_pick(seed, "gap_carry", [None, "texture"], [0.70, 0.30]),
        bass_starve_bars=starve,
        riser_restraint=_pick(seed, "riser_restraint", [True, False],
                              [0.70, 0.30]),
        riser_style=_pick(seed, "riser_style",
                          *_RISER_STYLE.get(g, _RISER_STYLE_DEFAULT)),
        riser_db=_pick(seed, "riser_db",
                       *((producer and _PRODUCER_RISER_DB.get(producer))
                         or _RISER_DB_MENU)),
        riser_color=_pick(seed, "riser_color",
                          *_RISER_COLOR.get(g, _RISER_COLOR_DEFAULT)),
        earcandy_every=_pick(seed, "earcandy_every",
                             *_CANDY_EVERY.get(g, ([0], None))),
        earcandy_menu=(_PRODUCER_CANDY.get(producer, _CANDY_MENU.get(g, ()))
                       if producer else _CANDY_MENU.get(g, ())),
        swell_kind=_pick(seed, "swell_kind",
                         *(_PRODUCER_SWELL.get(producer, ([None], None))
                           if producer else _SWELL.get(g, ([None], None)))),
        scratch_on=_pick(seed, "scratch_on",
                         *(([True, False], [0.5, 0.5]) if g == "hiphop"
                           else ([False], None))),
        drop_open=_pick(seed, "drop_open",
                        *((["no_pads", None], [0.5, 0.5]) if g == "garage"
                          else ([None], None))),
        bomb_on=_pick(seed, "bomb_on", *_BOMB.get(g, _BOMB_DEFAULT)),
        rumble_on=_pick(seed, "rumble_on",
                        *((producer and _PRODUCER_RUMBLE.get(producer))
                          or (([True, False], [0.6, 0.4])
                              if g == "techhouse" else ([False], None)))),
        odd_loop_on=_pick(seed, "odd_loop_on",
                          *(([False, True], [0.65, 0.35]) if g == "techhouse"
                            else ([False, True], [0.70, 0.30]) if g == "garage"
                            # R22: the shaker odd-cell gives reggaeton drops
                            # a live-percussion undercurrent
                            else ([False, True], [0.60, 0.40]) if g == "reggaeton"
                            else ([False], None))),
    )


def choose_style(riff: Riff, variation: int = 0) -> ArrangeStyle:
    """Derive every nonce-driven decision for one render. Deterministic:
    same (riff, variation) => equal ArrangeStyle.

    PRODUCTION MODE comes from the riff itself (riff_tonality): a pattern the
    diatonic triads can't explain gets the PERCUSSIVE treatment — rhythm and
    sound-development driven (root pedal, open-fifth drone, no chord pads) —
    instead of having chords forced under it. Borderline riffs let the nonce
    tip the choice, so re-presses can explore both readings."""
    from . import riff_tonality  # local import avoids a module cycle

    seed = fx.song_seed(riff, variation)
    menu = _menu_for(riff.drum_style)
    tone = riff_tonality(riff)
    if tone < 0.45:
        mode = "percussive"
    elif tone < 0.60:
        mode = _pick(seed, "production_mode", ["melodic", "percussive"],
                     [0.6, 0.4])
    else:
        mode = "melodic"
    # R31: the producer-style pick recolours the whole take — pads, lead
    # stacks, bass, drum seasoning, swing, pump, rumble and FX routing.
    # Drawn for any genre with a _PRODUCER_MENU entry (techhouse today), in
    # BOTH production modes (percussive takes still get producer-coloured
    # rumble/FX/swing; drones/skeletal doctrine stays in charge of the rest).
    producer = (_pick(seed, "producer_style",
                      *_PRODUCER_MENU[riff.drum_style])
                if riff.drum_style in _PRODUCER_MENU else None)
    # percussive tracks always run an atmosphere bed (sound-development
    # driven). R24: the bed follows the genre's REFERENCE flavour (Photek /
    # Burial / Rhythm & Sound) instead of a flat pool.
    if mode == "melodic":
        texture_menu, texture_w = menu["texture"], None
        if producer == "lofi":
            # the ever-present vinyl bed IS the lofi fingerprint (pinned)
            texture_menu, texture_w = ["crackle"], None
        elif producer in ("discofunk", "bigroom"):
            # zero lo-fi grit in the glossy palettes — crackle stays rare
            texture_menu, texture_w = [None, "crackle"], [0.70, 0.30]
    else:
        texture_menu, texture_w = _PERC_TEXTURE.get(
            riff.drum_style or "", (["drone", "wash", "metal"], None))
    # percussive drone ROLE varies too (owner: fixed recipes make every
    # percussive track converge) — dark is the anchor, colours per genre
    if mode != "melodic":
        pad_menu = _DRONE_ROLES.get(riff.drum_style or "", ["dark", "glass"])
    elif producer:
        pad_menu = _PRODUCER_PAD_MENU[producer]
    else:
        pad_menu = menu["pad_role"]
    rhythm_menu = (_PRODUCER_RHYTHM[producer] if producer
                   else (menu["pad_rhythm"], None))
    pump_menu = (_PRODUCER_PUMP[producer] if producer
                 else _PUMP_MENU.get(riff.drum_style or "", ([None], None)))
    # R20 sparse draws (hoisted so the guard below can correct the combo):
    texture = _pick(seed, "texture", texture_menu, texture_w)
    # R23 low-bed cap (owner: percussive mixes muddy/murky): a fifth-drone
    # pad take never ALSO runs a drone-family texture — one sustained dark
    # bed at a time; the metal/drone textures stay the pad-free takes'
    # signature. Deterministic correction, same pattern as the R20 guard.
    # R24: pad-free is now the percussive DEFAULT (skeletal doctrine).
    perc_pads = _pick(seed, "percussive_pads", ["none", "drone"],
                      [0.60, 0.40])
    if mode == "percussive" and perc_pads == "drone" \
            and texture in ("drone", "metal"):
        texture = "crackle"   # R30: never "wash" — noise beds read as swoosh
    skey = lead_stack_key(riff.drum_style, producer)
    stacks = LEAD_STACKS.get(skey, [[]])
    n_stacks = len(stacks)
    none_w = (_PRODUCER_LEAD_NONE.get(producer, _LEAD_NONE_DEFAULT) if producer
              else _LEAD_NONE_W.get(riff.drum_style or "", _LEAD_NONE_DEFAULT))
    stack_w = _STACK_W.get(skey, [1.0 / n_stacks] * n_stacks)
    lead_stack = _pick(seed, "lead_stack",
                       list(range(n_stacks)) + [None],
                       [w * (1.0 - none_w) for w in stack_w] + [none_w])
    pads_menu = _PADS_ON.get(riff.drum_style or "", _PADS_ON_DEFAULT)
    if producer:
        pads_menu = _PRODUCER_PADS_ON.get(producer, pads_menu)
    pads_on = _pick(seed, "pads_on", *pads_menu)
    # the mid must not go hollow: a take never drops BOTH the lead stack and
    # the pads unless a texture bed is carrying (percussive mode always has
    # texture, so this only ever bites melodic takes)
    if lead_stack is None and not pads_on and texture is None:
        pads_on = True
    return ArrangeStyle(
        production_mode=mode,
        structure=choose_structure(variation),
        # index into choose_progression's quality-floored candidates (up to 4;
        # clamped there) — best colour favoured, all candidates cover the riff
        prog_pick=_pick(seed, "progression", [0, 1, 2, 3],
                        [0.40, 0.30, 0.20, 0.10]),
        # R31: bass is the strongest producer differentiator — patch/feel are
        # producer-routed whenever a producer style is in play
        bass_patch=_pick(seed, "bass_patch",
                         *(_PRODUCER_BASS[producer] if producer
                           else (menu["bass_patch"],
                                 _BASS_PATCH_W.get(riff.drum_style or "")))),
        bass_feel=_pick(seed, "bass_feel",
                        *(_PRODUCER_FEEL[producer] if producer
                          else (menu["bass_feel"],
                                _BASS_FEEL_W.get(riff.drum_style or "")))),
        pad_role=_pick(seed, "pad_role", pad_menu),
        pad_rhythm=_pick(seed, "pad_rhythm", *rhythm_menu),
        pad_voicing=_pick(seed, "pad_voicing", menu["pad_voicing"]),
        texture=texture,
        # R23: the moving pedals lead (a static low root all track = mud);
        # 2 = the alternating root/fifth walk
        percussive_pedal=_pick(seed, "percussive_pedal", [0, 1, 2],
                               [0.30, 0.40, 0.30]),
        # the TRUE Photek treatment (owner R16): some percussive takes carry
        # NO pads/drones at all — just hits, bass pedal and the texture bed
        percussive_pads=perc_pads,
        drum_variant=_pick(seed, "drum_variant",
                           (_PRODUCER_DRUMV[producer] if producer
                            else menu["drum_variant"])),
        drum_skeleton=_pick(seed, "drum_skeleton",
                            *_SKELETON_MENU.get(riff.drum_style or "",
                                                ([0], None))),
        snare_take=_pick(seed, "snare_take",
                         *_SNARE_TAKES.get(riff.drum_style or "", ([0], None))),
        hat_take=_pick(seed, "hat_take",
                       *_HAT_TAKES.get(riff.drum_style or "", ([0], None))),
        drummer=_pick(seed, "drummer",
                      *_DRUMMER_MENU.get(riff.drum_style or "",
                                         (["static"], None))),
        bass_gate=_pick(seed, "bass_gate",
                        *(_PRODUCER_GATE[producer] if producer
                          else _BASS_GATE.get(riff.drum_style or "",
                                              ([1.0], None)))),
        pump_depth=_pick(seed, "pump_depth", *pump_menu),
        producer_style=producer,
        drum_swing=(_pick(seed, "drum_swing", *_PRODUCER_SWING[producer])
                    if producer else None),
        perc_low=_pick(seed, "perc_low", ["stabs", "accents"], [0.55, 0.45]),
        perc_note_style=_pick(seed, "perc_note_style",
                              ["dry_echo", "washed"], [0.55, 0.45]),
        half_switch=_pick(seed, "half_switch",
                          *(([False, True], [0.65, 0.35])
                            if riff.drum_style == "dnb" and mode == "melodic"
                            else ([False], None))),
        riff_break_variant=_pick(seed, "riff_break_variant", menu["riff_break_variant"]),
        riff_ornament=(_orn := _pick(seed, "riff_ornament",
                                     menu["riff_ornament"],
                                     [0.25, 0.20, 0.20, 0.15, 0.10, 0.10])),
        riff_ornament_b=_pick(seed, "riff_ornament_b",
                              [k for k in menu["riff_ornament"] if k != _orn]),
        lead_stack=lead_stack,
        pads_on=pads_on,
        fx_palette=_choose_fx_palette(seed, riff.drum_style,
                                      percussive=(mode == "percussive"),
                                      producer=producer),
    )
