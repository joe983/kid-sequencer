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


# pad role -> (renderer, patch-or-preset name). Grown per increment; the menu
# validity test walks this so a menu can never name an unrenderable role.
PAD_ROLES: dict[str, tuple[str, str]] = {
    "supersaw": ("vst", "pad"),
}


# ---------------------------------------------------------------------------
# Genre menus (signature option FIRST — it carries ~50% of the weight)
# ---------------------------------------------------------------------------

# Increment 1: every menu holds exactly today's behaviour, so the style layer
# is a pure refactor (output bit-identical). Later increments widen the menus.
_BASE_MENU: dict[str, list] = {
    "bass_patch": ["bass"],
    "bass_feel": [0],
    "pad_role": ["supersaw"],
    "pad_rhythm": [0],
    "texture": [None],
    "drum_variant": [0],
    "riff_break_variant": ["sparse_low"],
}

_GENRE_MENU: dict[str, dict[str, list]] = {
    "techhouse": dict(_BASE_MENU),
    "dnb": dict(_BASE_MENU),
    "garage": dict(_BASE_MENU),
    "drill": dict(_BASE_MENU),
    "hiphop": dict(_BASE_MENU),
    "reggaeton": dict(_BASE_MENU),
}


def _menu_for(genre: str | None) -> dict[str, list]:
    return _GENRE_MENU.get(genre or "", _GENRE_MENU["techhouse"])


# ---------------------------------------------------------------------------
# Choosers
# ---------------------------------------------------------------------------


def choose_structure(variation: int = 0) -> StructureStyle:
    """Skeleton choices from the nonce alone.

    Increment 1: reproduces the legacy formulas exactly (build_frac was
    `(1/3, 1/4, 2/5)[variation % 3]`; everything else was hardcoded)."""
    return StructureStyle(
        song_shape="classic",
        intro_bars=4,
        break_bars=8,
        outro_bars=4,
        build_frac=(1 / 3.0, 1 / 4.0, 2 / 5.0)[variation % 3],
        drop_bias="normal",
        intro_character="sparse",
        escalation="full",
    )


def _choose_fx_palette(seed: int, genre: str | None) -> FxPalette:
    """Increment 1: the legacy constants for every genre."""
    return FxPalette()


def choose_style(riff: Riff, variation: int = 0) -> ArrangeStyle:
    """Derive every nonce-driven decision for one render. Deterministic:
    same (riff, variation) => equal ArrangeStyle."""
    seed = fx.song_seed(riff, variation)
    menu = _menu_for(riff.drum_style)
    return ArrangeStyle(
        structure=choose_structure(variation),
        prog_pick=variation % 2,   # legacy top-2 alternation (widened later)
        bass_patch=_pick(seed, "bass_patch", menu["bass_patch"]),
        bass_feel=_pick(seed, "bass_feel", menu["bass_feel"]),
        pad_role=_pick(seed, "pad_role", menu["pad_role"]),
        pad_rhythm=_pick(seed, "pad_rhythm", menu["pad_rhythm"]),
        texture=_pick(seed, "texture", menu["texture"]),
        drum_variant=_pick(seed, "drum_variant", menu["drum_variant"]),
        riff_break_variant=_pick(seed, "riff_break_variant", menu["riff_break_variant"]),
        fx_palette=_choose_fx_palette(seed, riff.drum_style),
    )
