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
          gate_depth: float = 0.5, peak_db: float = -12.0,
          f0: float = 300.0, f1: float = 8000.0) -> np.ndarray:
    """Noise sweep f0→f1 (default 300 Hz→8 kHz) with (t/T)^2.5 crescendo + a
    sine riser two octaves up underneath. Genres tune the band: dark low-mid
    sweeps for drill/hiphop, wide fast sweeps for dnb. Optional 16th-note
    gating over the final bar (gate_hz = 16ths per second) with 3 ms cosine
    edges. Ends in a 10 ms fade so the drop downbeat starts clean."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    t = np.arange(n) / sr
    env = (t / dur_s) ** 2.5

    ch = []
    for _ in range(2):  # independent noise per channel = real width
        ch.append(_swept_noise(dur_s, sr, rng, f0, f1) * env)
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


def shepard_riser(dur_s: float, sr: int = SR, seed: int = 0,
                  peak_db: float = -12.0, f0: float = 300.0,
                  f1: float = 8000.0) -> np.ndarray:
    """Endless-rise illusion: two octave-staggered noise sweeps crossfaded so
    a lower layer takes over underneath as the top layer peaks out — the
    Shepard-tone riser (Sub Focus, 'Vapourise'). Ungated (the handover is the
    feature); same (t/T)^2.5 crescendo and clean 10 ms end fade as riser()."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    t = np.arange(n) / sr
    env = (t / dur_s) ** 2.5
    # crossfade curves: top layer bows out over the final 40%, the octave-down
    # layer fades in over the same span — equal-power so the rise never dips
    xf = np.clip((t / dur_s - 0.6) / 0.4, 0.0, 1.0)
    fade_out = np.cos(xf * np.pi / 2.0) ** 2
    fade_in = 1.0 - fade_out
    ch = []
    for _ in range(2):  # independent noise per channel = real width
        top = _swept_noise(dur_s, sr, rng, f0, f1) * fade_out
        low = _swept_noise(dur_s, sr, rng, f0 * 0.5, f1 * 0.5) * fade_in
        ch.append((top + low) * env)
    x = _peak_scale(np.stack(ch, axis=1), 0.0).astype(np.float64)

    # dual tonal glides an octave apart, crossfaded the same way, 8 dB under
    # the noise (the classic riser's noise:sine ratio)
    g1 = np.sin(np.cumsum(2 * np.pi * 220.0 * (2.0 ** (2.0 * t / dur_s)) / sr))
    g2 = np.sin(np.cumsum(2 * np.pi * 110.0 * (2.0 ** (2.0 * t / dur_s)) / sr))
    sine = (g1 * fade_out + g2 * fade_in) * env
    x += _peak_scale(np.stack([sine, sine], axis=1), -8.0)
    x = _peak_scale(x, peak_db).astype(np.float64)  # composite holds the pin

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


def spinback(dur_s: float = 1.5, sr: int = SR, seed: int = 0,
             peak_db: float = -14.0) -> np.ndarray:
    """Vinyl/tape spinback into a drop: a pitched cluster + noise spiralling
    down as the 'record' brakes — the garage/hiphop alternative to a noise
    riser. Ends in a fade so the drop downbeat starts clean."""
    from scipy.signal import butter, sosfilt

    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    t = np.arange(n) / sr
    fall = (1.0 - t / dur_s) ** 1.6            # braking curve
    mono = np.zeros(n)
    for mult, amp in ((1.0, 1.0), (1.5, 0.5), (2.02, 0.35)):
        f = 420.0 * mult * (0.12 + 0.88 * fall)
        mono += amp * np.sin(np.cumsum(2 * np.pi * f / sr))
    sos = butter(2, [300.0, 3500.0], btype="band", fs=sr, output="sos")
    mono = (mono + sosfilt(sos, rng.standard_normal(n)) * 0.5) * (0.35 + 0.65 * fall)
    x = np.stack([mono, mono], axis=1)
    fade = max(2, int(0.012 * sr))
    x[-fade:] *= _cos_edge(fade, up=False)[:, None]
    return _peak_scale(x, peak_db)


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
# Ear candy & event FX (R11). LEVEL DOCTRINE (Alex Tumay, RBMA: background
# SFX sit at the level of a breath — felt, not heard): everything in this
# section peaks at -18 dBFS or below, most at -24..-30. The bomb (-10) is the
# one exception — it is a boundary event, not candy, and routes via the
# dedicated "fx_sub" layer. Nothing here may ever read alarm-like at level —
# this is a kids' product.
# ---------------------------------------------------------------------------


def bomb(sr: int = SR, seed: int = 0, peak_db: float = -10.0) -> np.ndarray:
    """Breakdown-entry impact ('The Bomb', Attack masterclass, kid-adapted):
    a deep pitch-dropping boom whose band-limited reverb bloom marks energy
    LEAVING — placed at the START of breaks, the counterpart of the drop
    impact. Dry sub decay ~1.2 s + wet tail, total <= 6 s."""
    from pedalboard import HighpassFilter, LowpassFilter, Pedalboard, Reverb
    from scipy.signal import butter, sosfilt

    n_dry = int(1.2 * sr)
    t = np.arange(n_dry) / sr
    f = 50.0 * (30.0 / 50.0) ** np.minimum(t / 0.4, 1.0)
    boom = np.tanh(1.4 * np.sin(np.cumsum(2 * np.pi * f / sr))) * np.exp(-t / 0.45)
    rng = np.random.default_rng(seed)
    thump_n = int(0.06 * sr)
    sos = butter(2, 500.0, btype="low", fs=sr, output="sos")
    boom[:thump_n] += sosfilt(sos, rng.standard_normal(thump_n)) * \
        np.exp(-np.arange(thump_n) / (0.02 * sr)) * 0.4
    dry = np.stack([boom, boom], axis=1).astype(np.float32)

    total = int(5.5 * sr)
    padded = np.concatenate([dry, np.zeros((total - n_dry, 2), dtype=np.float32)])
    board = Pedalboard([   # band-limited wet bloom: no mud, no fizz (Attack)
        HighpassFilter(cutoff_frequency_hz=400.0),
        Reverb(room_size=0.9, damping=0.4, wet_level=1.0, dry_level=0.0, width=1.0),
        LowpassFilter(cutoff_frequency_hz=8000.0),
    ])
    wet = np.asarray(board(padded, sr), dtype=np.float64)[:total]
    x = _peak_scale(padded.astype(np.float64), 0.0) + _peak_scale(wet, -7.0)
    x = _peak_scale(x, peak_db).astype(np.float64)
    fade = max(2, int(0.050 * sr))
    x[-fade:] *= _cos_edge(fade, up=False)[:, None]
    return x.astype(np.float32)


def dub_siren(dur_s: float, sr: int = SR, seed: int = 0, bar_s: float = 2.0,
              peak_db: float = -24.0) -> np.ndarray:
    """Tasteful dub siren (Attack masterclass): a soft tanh-shaped tone with a
    saw-down pitch LFO synced to one bar, playing a seeded on/off phrase, into
    a dotted filtered-feedback delay. Breath-level by construction — a
    background flavour event for garage / dnb / reggaeton, never a lead."""
    from pedalboard import Delay, LowpassFilter, Pedalboard

    rng = np.random.default_rng(seed)
    n = int(dur_s * sr)
    t = np.arange(n) / sr
    lfo = 1.0 - (t % bar_s) / bar_s                    # saw-down, 1/1 bar
    freq = (480.0 + 380.0 * lfo)

    # seeded phrase: half-bar cells, ~55% sounding, varied length + register
    cell_len = bar_s / 2.0
    gate = np.zeros(n)
    pitch_mult = np.ones(n)
    n_cells = int(np.ceil(dur_s / cell_len))
    for i in range(n_cells):
        s0 = int(i * cell_len * sr)
        if s0 >= n:
            break
        on = rng.random() < 0.55
        length = (0.3 + 0.5 * rng.random()) * cell_len
        mult = float(rng.choice([0.75, 1.0, 1.0, 1.33]))
        if on:
            e0 = min(n, s0 + int(length * sr))
            gate[s0:e0] = 1.0
            pitch_mult[s0:e0] = mult
    # 5 ms smoothed gate edges (no clicks)
    win_n = max(3, int(0.005 * sr) | 1)
    win = np.hanning(win_n)
    gate = np.convolve(gate, win / win.sum(), mode="same")

    tone = np.tanh(2.5 * np.sin(np.cumsum(2 * np.pi * freq * pitch_mult / sr)))
    mono = (tone * gate).astype(np.float32)
    board = Pedalboard([
        Delay(delay_seconds=max(0.05, 0.1875 * bar_s), feedback=0.45, mix=0.5),
        LowpassFilter(cutoff_frequency_hz=3500.0),
    ])
    x = np.asarray(board(np.stack([mono, mono], axis=1), sr), dtype=np.float64)[:n]
    x = _peak_scale(x, peak_db)
    return _edge_fades(x.astype(np.float64), sr).astype(np.float32)


def scratch(sr: int = SR, seed: int = 0, peak_db: float = -18.0) -> np.ndarray:
    """~0.6 s turntable gesture (DJ Premier's one-DJ-element rule): three
    alternating pitch strokes of tone + bandpassed noise — a vinyl hand
    stroke entering the hook, not an alarm. One per track, hiphop only."""
    from scipy.signal import butter, sosfilt

    rng = np.random.default_rng(seed)
    dur = 0.6
    n = int(dur * sr)
    t = np.arange(n) / sr
    strokes = 3
    edges = np.linspace(0, n, strokes + 1).astype(int)
    freq = np.zeros(n)
    for i in range(strokes):
        f_a = 300.0 + 500.0 * rng.random()
        f_b = 900.0 + 900.0 * rng.random()
        if i % 2:
            f_a, f_b = f_b, f_a
        freq[edges[i]:edges[i + 1]] = np.linspace(f_a, f_b, edges[i + 1] - edges[i])
    tone = np.sin(np.cumsum(2 * np.pi * freq / sr))
    sos = butter(2, [500.0, 4000.0], btype="band", fs=sr, output="sos")
    noise = sosfilt(sos, rng.standard_normal(n)) * 0.6
    amp = 0.6 + 0.4 * np.abs(np.sin(np.pi * strokes * t / dur))  # stroke pulses
    mono = (tone * 0.7 + noise) * amp
    x = np.stack([mono, mono], axis=1)
    return _edge_fades(_peak_scale(x, peak_db).astype(np.float64), sr,
                       fade_s=0.008).astype(np.float32)


def reverse_swell(base: np.ndarray, sr: int = SR, mode: str = "reverb",
                  delay_s: float = 0.125, peak_db: float = -18.0) -> np.ndarray:
    """Reverse swell built from the track's OWN material (808Melo / DJ Swivel
    / MJ Cole): reverse the source, print the effect, reverse the print — the
    effect tail swells INTO the entry, made of the riff itself rather than a
    stock sweep. mode 'reverb' = crescendo hall; 'delay' = Attack's reverse
    1/16 delay. Returns empty when the source slice is silent."""
    from pedalboard import Delay, HighpassFilter, Pedalboard, Reverb

    if base.shape[0] < int(0.1 * sr) or float(np.max(np.abs(base))) < 1e-4:
        return np.zeros((0, 2), dtype=np.float32)
    rev = np.ascontiguousarray(np.flip(base, axis=0), dtype=np.float32)
    if mode == "delay":
        board = Pedalboard([
            Delay(delay_seconds=max(0.03, delay_s), feedback=0.48, mix=0.62),
            HighpassFilter(cutoff_frequency_hz=250.0),
        ])
        tail_s = 1.0
    else:
        board = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=250.0),
            Reverb(room_size=0.85, damping=0.4, wet_level=1.0, dry_level=0.0,
                   width=1.0),
        ])
        tail_s = 1.5
    padded = np.concatenate([rev, np.zeros((int(tail_s * sr), 2), dtype=np.float32)])
    wet = np.asarray(board(padded, sr), dtype=np.float64)
    x = np.ascontiguousarray(np.flip(wet, axis=0))
    nn = x.shape[0]
    x *= ((np.arange(nn) / nn) ** 1.5)[:, None]        # swell shape
    fade = max(2, int(0.010 * sr))
    x[-fade:] *= _cos_edge(fade, up=False)[:, None]    # clean into the entry
    return _peak_scale(x, peak_db)


#: candy kinds -> design peak dBFS (the breath-level law, pinned by tests)
CANDY_LEVELS = {"sweep_up": -26.0, "sweep_down": -26.0, "hat_lift": -26.0,
                "mini_downlifter": -24.0, "rev_cymbal": -20.0,
                "siren_blip": -24.0, "sig_chirp": -24.0}


def candy_blip(kind: str, bar_s: float, sr: int = SR, seed: int = 0) -> np.ndarray:
    """Phrase-boundary ear-candy one-shots (Camo & Krooked: something small
    happening every 4-8 bars). All breath-level (CANDY_LEVELS); each kind is
    seeded so a given track's candy is deterministic."""
    rng = np.random.default_rng(seed)
    peak = CANDY_LEVELS[kind]
    if kind in ("sweep_up", "sweep_down"):
        dur = bar_s
        n = int(dur * sr)
        f0, f1 = (400.0, 6000.0) if kind == "sweep_up" else (6000.0, 400.0)
        env = np.sin(np.pi * np.arange(n) / n)          # triangle-ish swell
        ch = [_swept_noise(dur, sr, rng, f0, f1) * env for _ in range(2)]
        x = _peak_scale(np.stack(ch, axis=1), peak)
        return _edge_fades(x.astype(np.float64), sr, 0.01).astype(np.float32)
    if kind == "hat_lift":
        from scipy.signal import butter, sosfilt
        dur = bar_s / 2.0
        n = int(dur * sr)
        sos = butter(2, [6000.0, 11000.0], btype="band", fs=sr, output="sos")
        env = (np.arange(n) / n) ** 1.5
        ch = [sosfilt(sos, rng.standard_normal(n)) * env for _ in range(2)]
        x = _peak_scale(np.stack(ch, axis=1), peak)
        return _edge_fades(x.astype(np.float64), sr, 0.008).astype(np.float32)
    if kind == "mini_downlifter":
        return downlifter(min(1.5, bar_s), sr, peak_db=peak)
    if kind == "rev_cymbal":
        return reverse_crash(crash(sr, seed), sr, peak_db=peak)
    if kind == "siren_blip":
        return dub_siren(2.0 * bar_s, sr, seed, bar_s, peak_db=peak)
    if kind == "sig_chirp":
        # the 808Melo signature: a tiny recurring chirp, SAME every occurrence
        dur = 0.18
        n = int(dur * sr)
        t = np.arange(n) / sr
        f_a = 700.0 + 500.0 * rng.random()
        f = f_a * (2.2 ** (t / dur))
        mono = np.sin(np.cumsum(2 * np.pi * f / sr)) * np.sin(np.pi * t / dur)
        x = _peak_scale(np.stack([mono, mono], axis=1), peak)
        return _edge_fades(x.astype(np.float64), sr, 0.005).astype(np.float32)
    raise ValueError(f"unknown candy kind: {kind}")


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
