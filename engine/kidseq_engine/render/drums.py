"""Drum rendering from the app's existing step patterns.

DRUM_PATTERNS mirrors public/index.html:650-709 (the values are step velocities,
0..1). One-shots are synthesized here as a fallback; the pro path swaps these for
real sampled kits (Unison/Splice) — same pattern data, better sounds.
"""

from __future__ import annotations

import numpy as np

from ..audio import SR, add_at, seconds_per_beat

# 16-step velocity patterns per genre (subset/copy of the app's DRUM_PATTERNS).
DRUM_PATTERNS: dict[str, dict[str, list[float]]] = {
    # sub doubles each kick at low level for weight (2026-07-02). Mirrors the app.
    "techhouse": {
        "kick": [1.2,0,0,0, 1.2,0,0,0, 1.2,0,0,0, 1.2,0,0,0],
        "sub":  [.65,0,0,0, .65,0,0,0, .65,0,0,0, .65,0,0,0],
        "clap": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hatC": [.26,.14,.20,.14, .26,.14,.20,.14, .26,.14,.20,.14, .26,.14,.20,.14],
        "hatO": [0,0,.24,0, 0,0,.24,0, 0,0,.24,0, 0,0,.24,0],
    },
    # Ported from the approved 170bpm pack beat (2026-07-02): ghost snares on the
    # offbeats, subtle hats on 8ths, no open hat. Mirrors the app.
    "dnb": {
        "kick":  [1,0,0,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
        "snare": [0,0,0,.20, 1,0,.18,0, 0,.20,0,0, 1,0,.19,0],
        "hatC":  [.22,0,.15,0, .22,0,.15,0, .22,0,.15,0, .22,0,.17,0],
    },
    # "garage" slot = UK Garage 2-step. Mirrors the app (which also applies a
    # heavy 0.16 swing to this style). Key was "funk" before 2026-07-10.
    "garage": {
        "kick":  [1,0,0,0, 0,0,.90,0, 0,0,.85,0, 0,0,0,0],
        "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "rim":   [0,0,0,.25, 0,0,0,0, 0,.25,0,0, 0,0,0,.30],
        "hatC":  [.28,0,.16,.12, .28,0,.16,0, .28,0,.16,.12, .28,0,.18,0],
        "hatO":  [0,0,.22,0, 0,0,.22,0, 0,0,.22,0, 0,0,.22,0],
    },
    # Ported from the approved 140bpm pack beat (2026-07-02): harder kicks +
    # pickup into the downbeat, rim counter after the snare. Mirrors the app.
    "drill": {
        "kick":  [1,0,0,0, 0,0,.90,0, 0,0,0,0, .90,0,0,.60],
        "snare": [0,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
        "rim":   [0,0,0,0, 0,0,0,0, 0,0,0,.35, 0,0,0,0],
        "hatC":  [.25,.18,.25,.45, .25,.18,.28,.18, .25,.18,.25,.45, .25,.18,.28,.18],
        "hatO":  [0,0,0,0, 0,0,.20,0, 0,0,0,0, 0,0,.20,0],
    },
    "hiphop": {
        "kick":  [1,0,0,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
        "snare": [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
        "hatC":  [.26,.16,.24,.16, .26,.16,.24,.16, .26,.16,.24,.16, .26,.16,.24,.16],
        "hatO":  [0,0,0,0, 0,0,.22,0, 0,0,0,0, 0,0,.22,0],
        "rim":   [0,0,0,.30, 0,0,0,0, 0,.30,0,0, 0,0,0,.30],
    },
    "reggaeton": {
        "kick":    [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
        "snare":   [0,0,0,1, 0,0,1,0, 0,0,0,1, 0,0,1,0],
        "shaker":  [.28,.22,.28,.22, .28,.22,.28,.22, .28,.22,.28,.22, .28,.22,.28,.22],
        "cowbell": [.35,0,0,0, 0,0,0,0, .35,0,0,0, 0,0,0,0],
    },
}


def _kick(sr: int) -> np.ndarray:
    n = int(0.22 * sr); t = np.arange(n) / sr
    f = 120 * np.exp(-t * 22) + 45
    env = np.exp(-t * 9)
    return (np.sin(2 * np.pi * np.cumsum(f) / sr) * env).astype(np.float32)


def _sub(sr: int) -> np.ndarray:
    n = int(0.4 * sr); t = np.arange(n) / sr
    return (np.sin(2 * np.pi * 50 * t) * np.exp(-t * 5)).astype(np.float32)


def _noise(dur: float, sr: int, decay: float) -> np.ndarray:
    # Seeded per (dur, decay, sr): a synth one-shot is a fixed "sample", so the
    # same hit renders the same bytes every time. The old unseeded global RNG
    # broke the same-(riff, nonce)-=>-same-track guarantee whenever this
    # fallback path fired (no kit assets on disk).
    rng = np.random.default_rng([int(dur * 1e6), int(decay * 1000), sr])
    n = int(dur * sr); t = np.arange(n) / sr
    return (rng.uniform(-1, 1, n) * np.exp(-t * decay)).astype(np.float32)


def _snare(sr: int) -> np.ndarray:
    n = int(0.18 * sr); t = np.arange(n) / sr
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 24)
    return ((_noise(0.18, sr, 26) * 0.8 + tone * 0.5)).astype(np.float32)


def _clap(sr: int) -> np.ndarray:
    base = _noise(0.16, sr, 30)
    out = np.zeros_like(base)
    for off in (0, int(0.008 * sr), int(0.016 * sr)):
        add_at(out, base, off)
    return (out * 0.6).astype(np.float32)


def _hat(dur: float, sr: int) -> np.ndarray:
    sig = _noise(dur, sr, 70 if dur < 0.06 else 30)
    # crude high-pass: subtract a smoothed copy
    k = max(1, int(sr * 0.0005))
    smooth = np.convolve(sig, np.ones(k) / k, mode="same")
    return (sig - smooth).astype(np.float32)


def _tone(freq: float, dur: float, sr: int, decay: float) -> np.ndarray:
    n = int(dur * sr); t = np.arange(n) / sr
    return (np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)).astype(np.float32)


def _voice(name: str, sr: int) -> np.ndarray:
    if name == "kick": return _kick(sr)
    if name == "sub": return _sub(sr)
    if name == "snare": return _snare(sr)
    if name == "clap": return _clap(sr)
    if name == "hatC": return _hat(0.04, sr)
    if name == "hatO": return _hat(0.12, sr)
    if name == "rim": return _tone(330, 0.05, sr, 60)
    if name == "cowbell": return _tone(540, 0.12, sr, 18) * 0.5 + _tone(810, 0.12, sr, 18) * 0.3
    if name == "shaker": return _hat(0.05, sr) * 0.6
    return _hat(0.04, sr)


# Per-voice mix gains (rough balance).
_GAIN = {"kick": 1.0, "sub": 0.9, "snare": 0.7, "clap": 0.7, "hatC": 0.35,
         "hatO": 0.4, "rim": 0.5, "cowbell": 0.4, "shaker": 0.3}

# Seasoning overlays: per-genre pattern VARIANTS that replace only hat / rim /
# shaker / cowbell rows — NEVER kick/snare/clap/sub (kick+snare = the genre's
# skeleton; hats are the seasoning). Variant 0 = the base pattern untouched;
# style.drum_variant picks. pattern_for() merges.
_SEASONING_VOICES = {"hatC", "hatO", "rim", "shaker", "cowbell"}

DRUM_VARIANTS: dict[str, list[dict[str, list[float]]]] = {
    "techhouse": [
        # open-hat shuffle: the offbeat answer moves around the bar
        {"hatO": [0, 0, .24, 0, 0, .20, 0, 0, 0, 0, .24, 0, 0, .20, 0, 0]},
        # shaker 16ths riding under the hats
        {"shaker": [.18] * 16},
        # the classic 909 cowbell on the offbeats
        {"cowbell": [0, 0, .25, 0, 0, 0, .25, 0, 0, 0, .25, 0, 0, 0, .25, 0]},
    ],
    "dnb": [
        # offbeat-8th hats only (rolling top)
        {"hatC": [0, 0, .22, 0, 0, 0, .22, 0, 0, 0, .22, 0, 0, 0, .22, 0]},
        # light 16ths
        {"hatC": [.20, .10, .14, .10, .20, .10, .14, .10,
                  .20, .10, .14, .10, .20, .10, .16, .10]},
        # shaker 16ths riding under the hats (Matador: thickness = layered
        # tops, not more EQ on one lane)
        {"shaker": [.12] * 16},
    ],
    "garage": [
        # rim skips displaced (the 2-step chatter moves)
        {"rim": [0, .25, 0, 0, 0, 0, 0, .25, 0, 0, .25, 0, 0, .30, 0, 0]},
        # denser open-hat offbeats
        {"hatO": [0, 0, .22, 0, 0, .18, .22, 0, 0, 0, .22, 0, 0, .18, .22, 0]},
        # shaker 16ths under the swing
        {"shaker": [.16] * 16},
    ],
    "drill": [
        # the triplet-feel hat stutter on the back half
        {"hatC": [.25, .18, .25, .45, .25, 0, .35, .35,
                  .25, .18, .25, .45, .25, 0, .35, .35]},
        # sparser hats (more menace, more space)
        {"hatC": [.25, 0, .25, 0, .25, 0, .28, .18, .25, 0, .25, 0, .25, 0, .28, .18]},
    ],
    "hiphop": [
        # 8th hats instead of 16ths (classic head-nod space)
        {"hatC": [.26, 0, .24, 0, .26, 0, .24, 0, .26, 0, .24, 0, .26, 0, .24, 0]},
        # busier rim conversation
        {"rim": [0, 0, .30, 0, 0, .25, 0, 0, 0, 0, .30, 0, 0, .25, 0, .30]},
        # lazy shaker 8ths under the hats
        {"shaker": [.15, 0, .12, 0, .15, 0, .12, 0, .15, 0, .12, 0, .15, 0, .12, 0]},
    ],
    "reggaeton": [
        # cowbell answering on beat 3
        {"cowbell": [.35, 0, 0, 0, 0, 0, .30, 0, .35, 0, 0, 0, 0, 0, .30, 0]},
        # shaker dembow accents
        {"shaker": [.28, .22, .28, .22, .28, .30, .28, .22,
                    .28, .22, .28, .22, .28, .30, .28, .22]},
        # woodblock rim on the dembow skips
        {"rim": [0, 0, 0, .30, 0, 0, .28, 0, 0, 0, 0, .30, 0, 0, .28, 0]},
        # ghost closed hats between the shaker (a second top layer)
        {"hatC": [.14, 0, .10, 0, .14, 0, .10, 0,
                  .14, 0, .10, 0, .14, 0, .12, 0]},
    ],
}


def render_odd_cell(style: str | None, tempo: float, dur_s: float,
                    sr: int = SR, voice: str = "shaker",
                    cell_beats: float = 3.0) -> np.ndarray:
    """KiNK's odd-length loop: a 3-beat percussion cell tiled edge to edge so
    it mutates against the 4/4 kit and re-aligns every 3 bars — deterministic
    hypnosis. An ADDED quiet lane only (the skeleton never mutates); the
    caller mixes it well under the kit."""
    spb = seconds_per_beat(tempo)
    n = int(dur_s * sr)
    buf = np.zeros(n, dtype=np.float32)
    one = _voice(voice, sr) * _GAIN.get(voice, 0.4)
    hits = (0.0, 1.5, 2.25)          # the cell's internal rhythm
    vels = (0.9, 0.6, 0.75)
    cell_s = cell_beats * spb
    c = 0
    while c * cell_s < dur_s:
        for h, v in zip(hits, vels):
            at = int((c * cell_s + h * spb) * sr)
            if at < n:
                add_at(buf, one * v, at)
        c += 1
    return buf


def pattern_for(style: str | None, variant: int = 0) -> dict | None:
    """The genre's DRUM_PATTERNS entry with a seasoning overlay merged in.
    Variant 0 (or an unknown style) = the base pattern object untouched."""
    base = DRUM_PATTERNS.get(style or "")
    if base is None or variant <= 0:
        return base
    variants = DRUM_VARIANTS.get(style or "")
    if not variants:
        return base
    overlay = variants[(variant - 1) % len(variants)]
    assert set(overlay) <= _SEASONING_VOICES, (style, sorted(overlay))
    merged = dict(base)
    merged.update(overlay)
    return merged


# Per-style swing (mirrors the app's SWING map in playDrumsAtStep): odd 16th
# steps are delayed by swing x one step. garage = UK Garage's defining shuffle.
SWING: dict[str, float] = {"garage": 0.16, "techhouse": 0.08}


def swung_step_offset(style: str | None, step: int) -> float:
    """Step position in step-units with swing applied (odd 16ths delayed).
    THE shared groove clock: drum renderers AND the sidechain pump both use
    this, so the duck always lands exactly on the (possibly swung) hit."""
    return step + (SWING.get(style or "", 0.0) if step % 2 else 0.0)


def render_drums(style: str, tempo: float, bars: int, sr: int = SR,
                 pattern: dict | None = None) -> np.ndarray:
    """Render `bars` bars of the named drum style to a mono float buffer.

    `pattern` overrides the style's DRUM_PATTERNS entry (arranger voice subsets)."""
    pat = pattern if pattern is not None else DRUM_PATTERNS.get(style)
    if not pat:
        return np.zeros(int(bars * 4 * seconds_per_beat(tempo) * sr) + sr, dtype=np.float32)
    spb = seconds_per_beat(tempo)
    step_s = spb / 4.0  # 16 steps per bar = 4 steps/beat
    bar_samples = int(4 * spb * sr)
    total = bars * bar_samples + sr
    buf = np.zeros(total, dtype=np.float32)
    cache = {name: _voice(name, sr) for name in pat}
    for b in range(bars):
        for name, steps in pat.items():
            oneshot = cache[name]
            g = _GAIN.get(name, 0.4)
            for i, vel in enumerate(steps):
                if vel <= 0:
                    continue
                at = int((b * 4 * spb + swung_step_offset(style, i) * step_s) * sr)
                add_at(buf, oneshot * float(vel) * g, at)
    return buf[: bars * bar_samples + int(0.4 * sr)]
