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
    riser_bars: int = 8            # cap; still clamped to the build length
    gate_depth: float = 0.5        # first-drop riser gate (later drops deepen)
    impact_f0: float = 80.0
    impact_f1: float = 35.0
    impact_db: float = -6.0
    downlifter_on: bool = True
    reverse_crash_on: bool = True
    fill_shape: int = 0            # index into the fill-shape menu
    throw: bool | None = None      # None = auto via fx.throw_fits


@dataclass(frozen=True)
class ArrangeStyle:
    """Everything the nonce decides for one render."""
    structure: StructureStyle
    prog_pick: int                 # index into choose_progression's candidates
    bass_patch: str                # Surge patch for the bass LAYER
    bass_feel: int                 # per-genre rhythm variant index
    pad_role: str                  # key into PAD_ROLES
    pad_rhythm: int                # per-genre rhythm variant index
    texture: str | None            # "crackle" | "wash" | "drone" | None
    drum_variant: int              # seasoning overlay index (0 = base pattern)
    riff_break_variant: str        # riff transform used in breaks
    fx_palette: FxPalette


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
}


# ---------------------------------------------------------------------------
# Genre menus (signature option FIRST — it carries ~50% of the weight)
# ---------------------------------------------------------------------------

# Menus widen per increment; fields not yet genre-differentiated share _BASE.
_BASE_MENU: dict[str, list] = {
    "bass_patch": ["bass"],
    "bass_feel": [0],
    "pad_role": ["supersaw"],
    "pad_rhythm": [0],
    "texture": [None],
    "drum_variant": [0],
    "riff_break_variant": ["sparse_low"],
}


def _menu(**over) -> dict[str, list]:
    m = dict(_BASE_MENU)
    m.update(over)
    return m


_GENRE_MENU: dict[str, dict[str, list]] = {
    # pluck stabs are the tech-house signature; the supersaw wash is the alt.
    # Bass: plucky rolling line first, reese as the darker alt.
    "techhouse": _menu(pad_role=["pluck", "supersaw"], pad_rhythm=[0, 1],
                       bass_patch=["bass_pluck", "bass"], bass_feel=[0, 1],
                       drum_variant=[0, 1, 2], texture=["wash", None],
                       riff_break_variant=["sparse_low", "octave_echo", "call_response"]),
    # dnb keeps the supersaw wash (its pad identity); the reese IS dnb bass —
    # feels vary (two-step / roller / whole-bar drone)
    "dnb": _menu(pad_role=["supersaw"], pad_rhythm=[0, 1],
                 bass_patch=["bass"], bass_feel=[0, 1, 2],
                 drum_variant=[0, 1, 2],
                 riff_break_variant=["sparse_low", "octave_echo"]),
    # organ skank IS UK garage; pluck as the alternate colour. Bouncy bass.
    "garage": _menu(pad_role=["organ", "pluck"], pad_rhythm=[0, 1],
                    bass_patch=["bass_pluck", "bass"], bass_feel=[0, 1],
                    drum_variant=[0, 1, 2], texture=["crackle", None],
                    riff_break_variant=["sparse_low", "octave_echo", "call_response"]),
    # drill: dark closed-down sustain only — bright pads read wrong. 808 sub.
    # Breaks stay low (sparse_low / deep call-response — no bright echoes).
    "drill": _menu(pad_role=["dark"], pad_rhythm=[0, 1],
                   bass_patch=["bass_sub808"], bass_feel=[0, 1],
                   drum_variant=[0, 1, 2], texture=["drone", None],
                   riff_break_variant=["sparse_low", "call_response"]),
    # hiphop: e-piano comping (boom-bap keys); warm pad as the soft alt. 808.
    "hiphop": _menu(pad_role=["epiano", "warm"], pad_rhythm=[0, 1],
                    bass_patch=["bass_sub808", "bass"], bass_feel=[0, 1],
                    drum_variant=[0, 1, 2], texture=["crackle", None],
                    riff_break_variant=["sparse_low", "call_response"]),
    # reggaeton: pizzicato dembow-accent plucks; warm wash alt. Tresillo bass.
    "reggaeton": _menu(pad_role=["pizz", "warm"], pad_rhythm=[0, 1],
                       bass_patch=["bass_pluck", "bass"], bass_feel=[0, 1],
                       drum_variant=[0, 1, 2],
                       riff_break_variant=["sparse_low", "octave_echo", "call_response"]),
}


def _menu_for(genre: str | None) -> dict[str, list]:
    return _GENRE_MENU.get(genre or "", _GENRE_MENU["techhouse"])


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
                              ["sparse", "pad_open", "low"], [0.50, 0.30, 0.20]),
        escalation=_pick(variation, "escalation", ["full", "gain_only", "off"],
                         [0.60, 0.25, 0.15]),
    )


# genre -> impact boom (f0, f1, level dB). drill/hiphop dive deeper (they
# already run quiet_fx_db -5); garage keeps it light; dnb slightly higher f0.
_IMPACT: dict[str, tuple[float, float, float]] = {
    "drill": (60.0, 28.0, -6.0),
    "hiphop": (60.0, 28.0, -6.0),
    "dnb": (70.0, 35.0, -6.0),
    "garage": (80.0, 35.0, -9.0),
}

# genre -> allowed fill shapes (see arrange/render.py _fill_pattern):
# 0 = snare roll, 1 = rim-led into snare, 2 = hat-roll landing on snare
_FILL_MENU: dict[str, list[int]] = {
    "techhouse": [0, 2], "garage": [0, 2], "reggaeton": [0],
    "drill": [1], "hiphop": [1], "dnb": [0],
}


def _choose_fx_palette(seed: int, genre: str | None) -> FxPalette:
    """Seeded dressing choices within the genre's taste. Boom-bap doesn't ride
    white-noise risers — hiphop defaults them OFF (reverse crash still swells)."""
    g = genre or ""
    riser_menu = ([False, True], [0.70, 0.30]) if g == "hiphop" else \
        ([True, False], [0.85, 0.15])
    f0, f1, db = _IMPACT.get(g, (80.0, 35.0, -6.0))
    return FxPalette(
        riser_on=_pick(seed, "riser_on", *riser_menu),
        riser_bars=_pick(seed, "riser_bars", [8, 4], [0.65, 0.35]),
        gate_depth=_pick(seed, "gate_depth", [0.5, 0.7], [0.6, 0.4]),
        impact_f0=f0, impact_f1=f1, impact_db=db,
        downlifter_on=_pick(seed, "downlifter_on", [True, False], [0.8, 0.2]),
        reverse_crash_on=_pick(seed, "reverse_crash_on", [True, False], [0.8, 0.2]),
        fill_shape=_pick(seed, "fill_shape", _FILL_MENU.get(g, [0])),
        # None = auto (fx.throw_fits decides); False = suppressed this take
        throw=_pick(seed, "throw", [None, False], [0.75, 0.25]),
    )


def choose_style(riff: Riff, variation: int = 0) -> ArrangeStyle:
    """Derive every nonce-driven decision for one render. Deterministic:
    same (riff, variation) => equal ArrangeStyle."""
    seed = fx.song_seed(riff, variation)
    menu = _menu_for(riff.drum_style)
    return ArrangeStyle(
        structure=choose_structure(variation),
        # index into choose_progression's quality-floored candidates (up to 4;
        # clamped there) — best colour favoured, all candidates cover the riff
        prog_pick=_pick(seed, "progression", [0, 1, 2, 3],
                        [0.40, 0.30, 0.20, 0.10]),
        bass_patch=_pick(seed, "bass_patch", menu["bass_patch"]),
        bass_feel=_pick(seed, "bass_feel", menu["bass_feel"]),
        pad_role=_pick(seed, "pad_role", menu["pad_role"]),
        pad_rhythm=_pick(seed, "pad_rhythm", menu["pad_rhythm"]),
        texture=_pick(seed, "texture", menu["texture"]),
        drum_variant=_pick(seed, "drum_variant", menu["drum_variant"]),
        riff_break_variant=_pick(seed, "riff_break_variant", menu["riff_break_variant"]),
        fx_palette=_choose_fx_palette(seed, riff.drum_style),
    )
