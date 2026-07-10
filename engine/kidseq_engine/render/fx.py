"""Transition FX generators — synthesized, deterministic, CC0-free.

Everything a produced EDM track uses to glue sections together: risers into
drops, impacts on drop downbeats, crash washes, reverse crashes, downlifters.
All numpy-synthesized (no sample licenses), all seeded from the riff itself
(`song_seed`) so the same sequence always renders the same track.

Every generator returns stereo (N, 2) float32 at the requested sr, peak-scaled
to its design level (dBFS). Noise-based FX use independent L/R noise for real
width; tonal FX (impact, downlifter) stay centred.
"""

from __future__ import annotations

import zlib

import numpy as np

from ..audio import SR
from ..sequence import Riff


def song_seed(riff: Riff, variation: int = 0) -> int:
    """Deterministic seed from the riff's exact notes + meta + the per-press
    variation nonce: same (riff, variation) always renders the same track;
    a new nonce per AI-button press gives a fresh-but-riff-true production."""
    blob = repr([(n.pitch, n.start_beats, n.dur_beats, n.velocity) for n in riff.notes]
                + [riff.key, riff.tempo, riff.instrument, riff.drum_style,
                   int(variation)]).encode()
    return zlib.crc32(blob)


def _peak_scale(x: np.ndarray, peak_db: float) -> np.ndarray:
    m = float(np.max(np.abs(x)))
    if m < 1e-12:
        return x.astype(np.float32)
    return (x * (10.0 ** (peak_db / 20.0) / m)).astype(np.float32)


def _cos_edge(n: int, up: bool) -> np.ndarray:
    t = np.linspace(0.0, np.pi, n)
    e = (1.0 - np.cos(t)) * 0.5
    return e if up else e[::-1]


def _swept_noise(dur_s: float, sr: int, rng: np.random.Generator,
                 f0: float, f1: float, q: float = 1.2) -> np.ndarray:
    """White noise through a time-varying bandpass sweeping f0→f1 (exp),
    block-processed with carried filter state (no clicks at block edges)."""
    from scipy.signal import butter, sosfilt, sosfilt_zi

    n = int(dur_s * sr)
    out = np.empty(n, dtype=np.float64)
    noise = rng.standard_normal(n)
    blk = 512
    zi = None
    for s in range(0, n, blk):
        e = min(n, s + blk)
        f = f0 * (f1 / f0) ** ((s + blk * 0.5) / n)
        lo, hi = f / (1.0 + 0.5 / q), f * (1.0 + 0.5 / q)
        hi = min(hi, sr / 2 * 0.95)
        sos = butter(2, [lo, hi], btype="band", fs=sr, output="sos")
        if zi is None:
            zi = sosfilt_zi(sos) * 0.0
        out[s:e], zi = sosfilt(sos, noise[s:e], zi=zi)
    return out


def riser(dur_s: float, sr: int = SR, seed: int = 0, gate_hz: float | None = None,
          gate_depth: float = 0.5, peak_db: float = -12.0) -> np.ndarray:
    """Noise sweep 300 Hz→8 kHz with (t/T)^2.5 crescendo + a sine riser two
    octaves up underneath. Optional 16th-note gating over the final bar
    (gate_hz = 16ths per second) with 3 ms cosine edges. Ends in a 10 ms fade
    so the drop downbeat starts clean."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    t = np.arange(n) / sr
    env = (t / dur_s) ** 2.5

    ch = []
    for _ in range(2):  # independent noise per channel = real width
        ch.append(_swept_noise(dur_s, sr, rng, 300.0, 8000.0) * env)
    x = np.stack(ch, axis=1)
    x = _peak_scale(x, peak_db)

    # tonal riser underneath: 220 Hz gliding up 2 octaves, centred, -20 dBFS
    phase = np.cumsum(2 * np.pi * 220.0 * (2.0 ** (2.0 * t / dur_s)) / sr)
    sine = np.sin(phase) * env
    x += _peak_scale(np.stack([sine, sine], axis=1), -20.0)

    if gate_hz:
        gate_len = min(n, int(sr / gate_hz))
        edge = max(2, int(0.003 * sr))
        cell = np.ones(gate_len)
        half = gate_len // 2
        cell[half:] = 1.0 - gate_depth
        cell[half - edge:half] = 1.0 - gate_depth * _cos_edge(edge, up=True)
        gate = np.tile(cell, n // gate_len + 1)[:n]
        # gate only the final bar's worth (the last quarter of the riser)
        g = np.ones(n)
        q0 = int(n * 0.75)
        g[q0:] = gate[q0:]
        x *= g[:, None]

    fade = max(2, int(0.010 * sr))
    x[-fade:] *= _cos_edge(fade, up=False)[:, None]
    return x.astype(np.float32)


def impact(sr: int = SR, peak_db: float = -6.0, f0: float = 80.0,
           f1: float = 35.0) -> np.ndarray:
    """Drop-downbeat boom: f0→f1 Hz sine drop + 80 ms LP noise burst, tanh'd.
    Defaults = the original signature sound; genres tune the depth via the
    style's FxPalette (drill/hiphop dive to ~28 Hz, garage sits lighter)."""
    dur = 2.0
    n = int(dur * sr)
    t = np.arange(n) / sr
    f = f0 * (f1 / f0) ** np.minimum(t / 0.5, 1.0)
    boom = np.sin(np.cumsum(2 * np.pi * f / sr)) * np.exp(-t / 0.7)

    from scipy.signal import butter, sosfilt
    rng = np.random.default_rng(1)  # fixed — the impact is a signature sound
    burst_n = int(0.08 * sr)
    burst = np.zeros(n)
    sos = butter(2, 600.0, btype="low", fs=sr, output="sos")
    burst[:burst_n] = sosfilt(sos, rng.standard_normal(burst_n)) * np.exp(
        -np.arange(burst_n) / (0.03 * sr))

    mono = np.tanh(1.5 * (boom + 0.8 * burst))
    return _peak_scale(np.stack([mono, mono], axis=1), peak_db)


def crash(sr: int = SR, seed: int = 0, peak_db: float = -14.0) -> np.ndarray:
    """Cymbal-ish wash: 4–12 kHz noise with a 3 s exponential decay."""
    from scipy.signal import butter, sosfilt

    rng = np.random.default_rng(seed)
    n = int(3.0 * sr)
    env = np.exp(-np.arange(n) / (1.2 * sr))
    sos = butter(2, [4000.0, 12000.0], btype="band", fs=sr, output="sos")
    ch = [sosfilt(sos, rng.standard_normal(n)) * env for _ in range(2)]
    return _peak_scale(np.stack(ch, axis=1), peak_db)


def reverse_crash(base: np.ndarray, sr: int = SR, peak_db: float = -16.0) -> np.ndarray:
    """The drop's own crash, flipped and swelling into the boundary."""
    x = np.flip(base, axis=0).astype(np.float64)
    n = x.shape[0]
    x *= ((np.arange(n) / n) ** 2.0)[:, None]
    return _peak_scale(x, peak_db)


def downlifter(dur_s: float = 2.0, sr: int = SR, peak_db: float = -16.0) -> np.ndarray:
    """Falling sine 6 kHz→250 Hz with linear decay — the drop→break exhale."""
    n = int(dur_s * sr)
    t = np.arange(n) / sr
    f = 6000.0 * (250.0 / 6000.0) ** (t / dur_s)
    mono = np.sin(np.cumsum(2 * np.pi * f / sr)) * (1.0 - t / dur_s)
    return _peak_scale(np.stack([mono, mono], axis=1), peak_db)


# ---------------------------------------------------------------------------
# Texture beds — subliminal genre-flavour layers (builds+drops only; the mix
# calibrates the "texture" layer to -30 LUFS so these sit UNDER everything)
# ---------------------------------------------------------------------------


def _edge_fades(x: np.ndarray, sr: int, fade_s: float = 0.05) -> np.ndarray:
    n = min(len(x), max(2, int(fade_s * sr)))
    x[:n] *= _cos_edge(n, up=True)[:, None]
    x[-n:] *= _cos_edge(n, up=False)[:, None]
    return x


def vinyl_crackle(dur_s: float, sr: int = SR, seed: int = 0,
                  peak_db: float = -24.0, ticks_per_s: float = 8.0) -> np.ndarray:
    """Dusty record bed: sparse bandpassed ticks + a soft hiss floor.
    hiphop's signature texture; garage runs it at half tick rate."""
    from scipy.signal import butter, sosfilt

    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    sos = butter(2, [1200.0, 8000.0], btype="band", fs=sr, output="sos")
    ch = []
    for _ in range(2):  # independent ticks per channel = real width
        imp = np.zeros(n)
        mask = rng.random(n) < (ticks_per_s / sr)
        imp[mask] = rng.uniform(0.3, 1.0, int(mask.sum())) * \
            rng.choice([-1.0, 1.0], int(mask.sum()))
        ticks = sosfilt(sos, imp)
        hiss = sosfilt(sos, rng.standard_normal(n)) * 0.03
        ch.append(ticks + hiss)
    x = _peak_scale(np.stack(ch, axis=1), peak_db)
    return _edge_fades(x.astype(np.float64), sr).astype(np.float32)


def noise_wash(dur_s: float, sr: int = SR, seed: int = 0,
               peak_db: float = -26.0) -> np.ndarray:
    """Slow-breathing filtered noise bed (bandpass centre LFOs 400 Hz–2 kHz at
    0.25 Hz) — the tech-house 'air' behind the kit."""
    from scipy.signal import butter, sosfilt, sosfilt_zi

    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    ch = []
    for _ in range(2):
        noise = rng.standard_normal(n)
        out = np.empty(n)
        blk = 1024
        zi = None
        for s in range(0, n, blk):
            e = min(n, s + blk)
            t = (s + blk * 0.5) / sr
            f = 400.0 * (2000.0 / 400.0) ** (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t))
            sos = butter(2, [f / 1.4, min(f * 1.4, sr / 2 * 0.95)],
                         btype="band", fs=sr, output="sos")
            if zi is None:
                zi = sosfilt_zi(sos) * 0.0
            out[s:e], zi = sosfilt(sos, noise[s:e], zi=zi)
        ch.append(out)
    x = _peak_scale(np.stack(ch, axis=1), peak_db)
    return _edge_fades(x.astype(np.float64), sr).astype(np.float32)


def dark_drone(dur_s: float, sr: int = SR, seed: int = 0,
               root_hz: float = 65.41, peak_db: float = -26.0) -> np.ndarray:
    """Detuned low sine pair on the song's tonic + dark noise — drill's
    under-the-floor unease. Tonal, so it must sit on the key's root."""
    from scipy.signal import butter, sosfilt

    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    t = np.arange(n) / sr
    wob = 1.0 + 0.15 * np.sin(2 * np.pi * 0.11 * t)   # slow amplitude breathing
    a = np.sin(2 * np.pi * root_hz * t)
    b = np.sin(2 * np.pi * root_hz * 1.007 * t + 0.7)  # detune + phase offset
    sos = butter(2, 400.0, btype="low", fs=sr, output="sos")
    murk = sosfilt(sos, rng.standard_normal(n)) * 0.06
    left = (a + 0.7 * b) * wob + murk
    right = (a * 0.7 + b) * wob + murk
    x = _peak_scale(np.stack([left, right], axis=1), peak_db)
    return _edge_fades(x.astype(np.float64), sr).astype(np.float32)


def throw_fits(riff: Riff) -> bool:
    """Per-track auto-decision for the riff delay-throw into breaks: needs a
    note sounding near the bar end (something worth echoing), a tempo where
    echoes have room, and a riff that isn't already dense. Deterministic —
    derived only from the riff."""
    if riff.tempo > 150 or len(riff.notes) > 10:
        return False
    return any(n.start_beats + n.dur_beats > 3.0 for n in riff.notes)
