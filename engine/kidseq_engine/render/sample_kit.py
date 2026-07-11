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

from ..audio import SR, add_at, normalize, pan_stereo, read_wav, seconds_per_beat

# Constant-power stereo placement per voice: low-end / backbeat dead-centre for
# mono-compatibility, hats & aux perc spread. (mono-below-120 fold is a backstop.)
_PAN = {"kick": 0.0, "sub": 0.0, "snare": 0.0, "clap": 0.0,
        "hatC": 0.25, "hatO": -0.20, "rim": -0.30, "shaker": 0.35, "cowbell": -0.15}

DRUM_DIR = Path(__file__).resolve().parents[2] / "assets" / "drums"

# genre -> voice -> [(relpath under assets/drums, layer_gain), ...]
# Voices MUST cover every voice present in that genre's DRUM_PATTERNS entry, or
# those hits render silent.
#
# ALL genres now reuse the APP's approved drums.pack samples (owner feedback:
# an AI track's drums should match what the kid hears on play — never bespoke
# CC0 kits). Unpacked to assets/drums/<genre>/ by scripts/fetch_appkit.py.
# Voice balance lives in _GAIN (each one-shot is peak-normalised first);
# multi-layer voices carry the pack's relative layer gains here.
KITS: dict[str, dict[str, list[tuple[str, float]]]] = {
    # techhouse: app deliberately uses a SYNTH kick (owner pick) — the pack has
    # no kick/sub, so those stay on the Boochi bounce one-shots (Modal volume);
    # clap/hats are the app's real TR-909.
    "techhouse": {
        "kick": [("bounce/kick.wav", 1.0)],
        "sub":  [("bounce/sub.wav", 1.0)],
        "clap": [("techhouse/clap.wav", 1.0)],
        "hatC": [("techhouse/hatC.wav", 1.0)],
        "hatO": [("techhouse/hatO.wav", 1.0)],
        "shaker": [("perc/shaker.wav", 1.0)],   # seasoning-variant voice
        "cowbell": [("perc/cowbell.wav", 1.0)],  # seasoning-variant voice
    },
    # dnb: the app's kit — layered soft kick (VEH1 004 + 005 at 0.5, the pack's
    # relative gains), DC_Kit14 snare + 75ms-trimmed hat (trim baked at unpack).
    "dnb": {
        "kick":  [("dnb/kick.wav", 1.0), ("dnb/kick.1.wav", 0.5)],
        "snare": [("dnb/snare.wav", 1.0)],
        "hatC":  [("dnb/hatC.wav", 1.0)],
        "shaker": [("perc/shaker.wav", 1.0)],   # seasoning-variant voice
    },
    # drill: Jay Cactus Greeze (Big Kick / Psycho 808 / Brickz / Ruckus rim) +
    # TrapLordz hat — the exact app kit.
    "drill": {
        "kick":  [("drill/kick.wav", 1.0)],
        "sub":   [("drill/sub.wav", 1.0)],
        "snare": [("drill/snare.wav", 1.0)],
        "rim":   [("drill/rim.wav", 1.0)],
        "hatC":  [("drill/hatC.wav", 1.0)],
        "hatO":  [("drill/hatO.wav", 1.0)],
    },
    # hiphop: The Source boom-bap kit (was lofi Boochi bounce).
    "hiphop": {
        "kick":  [("hiphop/kick.wav", 1.0)],
        "snare": [("hiphop/snare.wav", 1.0)],
        "hatC":  [("hiphop/hatC.wav", 1.0)],
        "hatO":  [("hiphop/hatO.wav", 1.0)],
        "rim":   [("hiphop/rim.wav", 1.0)],
        "shaker": [("perc/shaker.wav", 1.0)],   # seasoning-variant voice
    },
    # reggaeton: dancehall Kit C + Source shaker + 808 cowbell (was Boochi).
    "reggaeton": {
        "kick":    [("reggaeton/kick.wav", 1.0)],
        "snare":   [("reggaeton/snare.wav", 1.0)],
        "shaker":  [("reggaeton/shaker.wav", 1.0)],
        "cowbell": [("reggaeton/cowbell.wav", 1.0)],
        "rim":     [("perc/woodblock.wav", 1.0)],  # seasoning-variant voice
        "hatC":    [("garage/hatC.wav", 0.9)],     # seasoning-variant voice (909)
    },
    # garage: Candy kick/snare/rim + TR-909 hats. Key was "funk" pre-2026-07-10.
    "garage": {
        "kick":  [("garage/kick.wav", 1.0)],
        "snare": [("garage/snare.wav", 1.0)],
        "rim":   [("garage/rim.wav", 1.0)],
        "hatC":  [("garage/hatC.wav", 1.0)],
        "hatO":  [("garage/hatO.wav", 1.0)],
        "shaker": [("perc/shaker.wav", 1.0)],   # seasoning-variant voice
    },
}

# Per-voice mix balance (each one-shot is peak-normalised first, so this is a clean
# relative balance the user can tune by ear).
_GAIN = {"kick": 1.0, "sub": 0.95, "snare": 0.78, "clap": 0.72, "hatC": 0.45,
         "hatO": 0.5, "rim": 0.6, "cowbell": 0.5, "shaker": 0.38}

_cache: dict[str, np.ndarray] = {}


# kick fundamental fallbacks when the kit isn't on disk (Hz, by genre character)
_SLOT_FALLBACK = {"drill": 45.0, "hiphop": 45.0, "dnb": 50.0}
_slot_cache: dict[str, float] = {}


def kick_slot_hz(style: str | None) -> float:
    """The genre kick's fundamental (35–70 Hz), FFT-detected from the actual
    one-shot. The mix boards slot around this: drums boosted AT it, bass
    notched AT it. Falls back to genre-typical values without assets."""
    key = style or ""
    if key in _slot_cache:
        return _slot_cache[key]
    val = _SLOT_FALLBACK.get(key, 55.0)
    kit = KITS.get(key)
    if kit and kit.get("kick") and kit_available(key):
        one = _voice_buffer("kick", kit["kick"])
        seg = one[: int(0.4 * SR)].astype(np.float64)
        if seg.size > SR // 50:
            mag = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
            freqs = np.fft.rfftfreq(len(seg), 1.0 / SR)
            sel = (freqs >= 35.0) & (freqs <= 70.0)
            if sel.any() and float(mag[sel].max()) > 0:
                val = float(freqs[sel][np.argmax(mag[sel])])
    _slot_cache[key] = val
    return val


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
        return np.zeros((bars * bar_samples + sr, 2), dtype=np.float32)
    step_s = spb / 4.0  # 16 steps/bar
    buf = np.zeros((bars * bar_samples + sr, 2), dtype=np.float32)
    # pan each mono one-shot to stereo once, up front (not per hit)
    voices = {name: pan_stereo(_voice_buffer(name, kit[name]), _PAN.get(name, 0.0))
              for name in pat if name in kit}
    from .drums import swung_step_offset  # shared groove clock (pump uses it too)

    for b in range(bars):
        for name, steps in pat.items():
            one = voices.get(name)  # (M, 2)
            if one is None:
                continue
            for i, vel in enumerate(steps):
                if vel <= 0:
                    continue
                at = int((b * 4 * spb + swung_step_offset(style, i) * step_s) * sr)
                add_at(buf, one * float(vel), at)
    return buf[: bars * bar_samples + int(0.4 * sr)]
