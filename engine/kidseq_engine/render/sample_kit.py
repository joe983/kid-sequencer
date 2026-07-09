"""Real one-shot drum kits (CC0) — the top-priority drum path.

Replaces the GM-soundfont placeholder. `drums_audio` prefers this when the kit's
samples are present on disk, else falls back to the soundfont, else the numpy synth.
Output contract is unchanged (mono float buffer; the mixmaster's kick onsets still
come from the symbolic DRUM_PATTERNS, not the audio), so the mix stage is untouched.

Samples are curated flat into engine/assets/drums/<flavour>/<voice>.wav by
scripts/fetch_drumkits.py from two CC0 sources (see LICENSES.md):
  - Boochi44/free-drum-samples (CC0) — kick/sub/snare/clap/hatC/hatO per flavour
  - sgossner/VCSL            (CC0)   — cowbell/shaker/woodblock aux percussion

Per-genre kits map each engine voice to a list of (relpath, gain) LAYERS. v1 uses a
single layer per voice; the list form is the hook for per-voice layering (e.g. stack
a sub + a click under one kick) without touching the renderer.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..audio import SR, add_at, normalize, read_wav, seconds_per_beat

DRUM_DIR = Path(__file__).resolve().parents[2] / "assets" / "drums"

# genre -> voice -> [(relpath under assets/drums, layer_gain), ...]
# Voices MUST cover every voice present in that genre's DRUM_PATTERNS entry, or
# those hits render silent.
KITS: dict[str, dict[str, list[tuple[str, float]]]] = {
    "techhouse": {
        "kick": [("bounce/kick.wav", 1.0)],
        "sub":  [("bounce/sub.wav", 1.0)],
        "clap": [("bounce/clap.wav", 1.0)],
        "hatC": [("bounce/hatC.wav", 1.0)],
        "hatO": [("bounce/hatO.wav", 1.0)],
    },
    # DnB = breakbeat DNA: real acoustic kit (Virtuosity, CC0), NOT electro one-shots.
    # Snare is layered: full centre hit + rimshot on top for the DnB crack.
    "dnb": {
        "kick":  [("virtuosity/kick.wav", 1.0)],
        "snare": [("virtuosity/snare.wav", 1.0), ("virtuosity/rim.wav", 0.55)],
        "hatC":  [("virtuosity/hatC.wav", 1.0)],
        "hatO":  [("virtuosity/hatO.wav", 1.0)],
    },
    "drill": {
        "kick":  [("hard-trap/kick.wav", 1.0)],
        "sub":   [("hard-trap/sub.wav", 1.0)],
        "snare": [("hard-trap/snare.wav", 1.0)],
        "rim":   [("perc/woodblock.wav", 0.8)],
        "hatC":  [("hard-trap/hatC.wav", 1.0)],
        "hatO":  [("hard-trap/hatO.wav", 1.0)],
    },
    "hiphop": {
        "kick":  [("bounce/kick.wav", 1.0)],
        "snare": [("bounce/snare.wav", 1.0)],
        "hatC":  [("bounce/hatC.wav", 1.0)],
        "hatO":  [("bounce/hatO.wav", 1.0)],
        "rim":   [("perc/woodblock.wav", 0.85)],
    },
    "reggaeton": {
        "kick":    [("bounce/kick.wav", 1.0)],
        "snare":   [("bounce/snare.wav", 1.0)],
        "shaker":  [("perc/shaker.wav", 0.9)],
        "cowbell": [("perc/cowbell.wav", 0.8)],
    },
    # "funk" slot = UK Garage: bounce kit + woodblock rim skip
    "funk": {
        "kick":  [("bounce/kick.wav", 1.0)],
        "snare": [("bounce/snare.wav", 1.0)],
        "rim":   [("perc/woodblock.wav", 0.8)],
        "hatC":  [("bounce/hatC.wav", 1.0)],
        "hatO":  [("bounce/hatO.wav", 1.0)],
    },
}

# Per-voice mix balance (each one-shot is peak-normalised first, so this is a clean
# relative balance the user can tune by ear).
_GAIN = {"kick": 1.0, "sub": 0.95, "snare": 0.78, "clap": 0.72, "hatC": 0.45,
         "hatO": 0.5, "rim": 0.6, "cowbell": 0.5, "shaker": 0.38}

_cache: dict[str, np.ndarray] = {}


def kit_available(style: str) -> bool:
    """True only if every sample the genre's kit references exists on disk."""
    kit = KITS.get(style)
    if not kit:
        return False
    return all((DRUM_DIR / rel).exists() for layers in kit.values() for rel, _ in layers)


def _load(rel: str) -> np.ndarray:
    """Load + peak-normalise a one-shot, with tiny fades to kill edge clicks."""
    if rel not in _cache:
        s = normalize(read_wav(DRUM_DIR / rel), 0.95)
        fi = min(int(0.001 * SR), s.size)
        fo = min(int(0.005 * SR), s.size)
        if fi:
            s[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)
        if fo:
            s[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)
        _cache[rel] = s
    return _cache[rel]


def _voice_buffer(name: str, layers: list[tuple[str, float]]) -> np.ndarray:
    """Sum a voice's layers into one one-shot, then apply its mix gain."""
    mix: np.ndarray | None = None
    for rel, lg in layers:
        s = _load(rel) * float(lg)
        if mix is None:
            mix = s.astype(np.float32).copy()
        else:
            if s.size > mix.size:
                mix = np.pad(mix, (0, s.size - mix.size))
            mix[: s.size] += s
    if mix is None:
        return np.zeros(1, dtype=np.float32)
    return mix * _GAIN.get(name, 0.4)


def render_drums_samples(style: str, tempo: float, bars: int, sr: int = SR,
                         pattern: dict | None = None) -> np.ndarray:
    """Render `bars` of the named genre's drums from real CC0 one-shots (mono).

    `pattern` overrides the style's DRUM_PATTERNS entry (the arranger passes
    voice subsets for lite sections); the kit lookup stays by style."""
    from .drums import DRUM_PATTERNS  # local import avoids a cycle

    pat = pattern if pattern is not None else DRUM_PATTERNS.get(style)
    kit = KITS.get(style)
    spb = seconds_per_beat(tempo)
    bar_samples = int(4 * spb * sr)
    if not pat or not kit:
        return np.zeros(bars * bar_samples + sr, dtype=np.float32)
    step_s = spb / 4.0  # 16 steps/bar
    buf = np.zeros(bars * bar_samples + sr, dtype=np.float32)
    voices = {name: _voice_buffer(name, kit[name]) for name in pat if name in kit}
    for b in range(bars):
        for name, steps in pat.items():
            one = voices.get(name)
            if one is None:
                continue
            for i, vel in enumerate(steps):
                if vel <= 0:
                    continue
                at = int((b * 4 * spb + i * step_s) * sr)
                add_at(buf, one * float(vel), at)
    return buf[: bars * bar_samples + int(0.4 * sr)]
