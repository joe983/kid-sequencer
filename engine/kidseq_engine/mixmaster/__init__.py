"""Stage D — mix + master.

Takes the rendered layers (riff, drums, and later bass/pads/texture) and turns them
into a single produced, loud, final mix. Pure CPU via `pedalboard` (Spotify, MIT) +
`pyloudnorm` (MIT). No stems are exported (project rule) — only the final mix.

The riff layer is treated as sacred: it receives EQ/space only, never anything that
alters pitch or timing (riff-fidelity rule). All "produced" character comes from the
drum punch, the sidechain pump, the glue bus, and the loudness master.
"""

from __future__ import annotations

from .master import GENRE_PRESETS, MasterResult, kick_onsets_from_pattern, master, pump_envelope

__all__ = [
    "master",
    "MasterResult",
    "pump_envelope",
    "kick_onsets_from_pattern",
    "GENRE_PRESETS",
]
