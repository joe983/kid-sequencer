"""R32e — sampled FX one-shots (producer ear-candy: risers / crowds / swells).

Each techhouse producer gets its OWN sampled FX flavour (bassled filter slide,
latin crowd 'hey' + perc reverse, lofi reverse-swell, discofunk tom zap,
bigroom riser/impact/slide) instead of the shared synthesized candy. Played by
the candy scheduler at phrase boundaries, breath-level (the peak is baked into
the pack at build time — see tools/install_producer_kits.py FX_PEAK_DBFS).

Assets: scripts/fetch_producer_kits.py unpacks the pack's "fx" section to
assets/fx_oneshots/techhouse/<producer>/<kind>.wav. When absent, the caller
remaps to the declared synth candy fallback so local dev still renders.

Pure numpy => deterministic.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..audio import SR, pan_stereo, read_wav

FX_DIR = Path(__file__).resolve().parents[2] / "assets" / "fx_oneshots"

# smp fx kind -> synth candy kind to remap to when the pack is absent (None =
# just skip the event). Keys double as the registry of valid sampled fx kinds.
FX_FALLBACK: dict[str, str | None] = {
    "smp_slide": "sweep_up",
    "smp_rev": "rev_cymbal",
    "smp_rev_perk": "rev_cymbal",
    "smp_rev_swell": "rev_cymbal",
    "smp_crowd": "hat_lift",
    "smp_perk": "sig_chirp",
    "smp_tom_zap": "sig_chirp",
    "smp_riser": "sweep_up",
    "smp_impact": "sig_chirp",
}

# sampled sweep-family kinds — join the R28 sweep cap (never twice in a row,
# <=2 per track) alongside the synth sweep_up/sweep_down.
SAMPLED_SWEEP_KINDS = {"smp_slide", "smp_riser"}

_cache: dict[str, np.ndarray] = {}


def _rel(kit_key: str, kind: str) -> str:
    return f"{kit_key.replace(':', '/')}/{kind}.wav"


def fx_shot_available(kit_key: str | None, kind: str) -> bool:
    if not kit_key or kind not in FX_FALLBACK:
        return False
    return (FX_DIR / _rel(kit_key, kind)).exists()


def _load(rel: str) -> np.ndarray:
    if rel not in _cache:
        s = read_wav(FX_DIR / rel, SR)  # already peak-conditioned in the pack
        fi = min(int(0.003 * SR), s.size)
        fo = min(int(0.02 * SR), s.size)
        if fi:
            s[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)
        if fo:
            s[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)
        _cache[rel] = s
    return _cache[rel]


def fx_shot(kit_key: str, kind: str, bar_s: float | None = None,
            sr: int = SR) -> np.ndarray:
    """The producer's sampled fx one-shot as stereo (N, 2), centre-panned. The
    peak is already baked to breath-level in the pack. `bar_s` caps the length
    (a candy event never runs longer than a bar); None keeps the full shot.
    EMPTY (0, 2) if the asset is missing so the caller can fall back."""
    rel = _rel(kit_key, kind)
    if not (FX_DIR / rel).exists():
        return np.zeros((0, 2), dtype=np.float32)
    s = _load(rel)
    if bar_s is not None:
        cap = int(bar_s * sr)
        if s.size > cap > 0:
            s = s[:cap].copy()
            fo = min(int(0.02 * sr), s.size)
            if fo:
                s[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)
    return pan_stereo(s, 0.0)
