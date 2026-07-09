"""Mix + master chain (stage D).

Signal flow (mirrors docs/PLAN.md section D):

    per-layer EQ/comp/space   (riff = EQ/space ONLY — never pitch/time)
      -> sidechain pump        (duck melodic layers to the kick = the EDM "pump")
      -> genre gain preset     (per-layer balance)
      -> sum to mix bus
      -> bus glue compressor
      -> loudness normalise     (pyloudnorm -> target LUFS)
      -> brickwall limiter      (true-peak kept <= ceiling)
      -> final stereo mix       (-> WAV / MP3)

Everything works in mono float32 internally (all current renders are mono) and is
spread to stereo only at the very end. Matchering (GPL, reference-match) is a later
add — for v1 we hit a fixed loudness target, which needs no reference file.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyloudnorm as pyln
from pedalboard import (
    Compressor,
    Gain,
    HighpassFilter,
    HighShelfFilter,
    Limiter,
    LowpassFilter,
    Pedalboard,
    PeakFilter,
    Reverb,
)

from ..audio import as_stereo, collapse_lows_to_mono, hard_mono

# ---------------------------------------------------------------------------
# Genre presets: per-layer gain (dB) + pump depth + master target.
# Only the layers that exist are used; missing layers are ignored.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenrePreset:
    layer_gain_db: dict[str, float]   # per-layer trim before the bus
    pump_depth: float                 # 0..1 sidechain duck depth on melodic layers
    pump_release_s: float             # how fast the duck recovers
    lufs_target: float = -10.0        # integrated loudness target
    peak_ceiling_db: float = -1.0     # limiter true-peak ceiling


# Default works for any genre; specific genres override feel.
_DEFAULT = GenrePreset(
    layer_gain_db={"riff": -1.0, "drums": -2.0, "bass": -3.0, "pads": -8.0, "texture": -12.0},
    pump_depth=0.45,
    pump_release_s=0.16,
)

GENRE_PRESETS: dict[str, GenrePreset] = {
    "default": _DEFAULT,
    "techhouse": GenrePreset(
        layer_gain_db={"riff": -1.0, "drums": -1.5, "bass": -3.0, "pads": -8.0, "texture": -12.0},
        pump_depth=0.6, pump_release_s=0.18,
    ),
    "dnb": GenrePreset(
        layer_gain_db={"riff": -1.0, "drums": -1.0, "bass": -2.5, "pads": -9.0, "texture": -12.0},
        pump_depth=0.35, pump_release_s=0.10,
    ),
    "funk": GenrePreset(
        layer_gain_db={"riff": -1.0, "drums": -2.0, "bass": -3.0, "pads": -9.0, "texture": -13.0},
        pump_depth=0.25, pump_release_s=0.12,
    ),
    "drill": GenrePreset(
        layer_gain_db={"riff": -1.5, "drums": -1.5, "bass": -2.0, "pads": -9.0, "texture": -12.0},
        pump_depth=0.3, pump_release_s=0.14,
    ),
    "hiphop": GenrePreset(
        layer_gain_db={"riff": -1.0, "drums": -2.0, "bass": -2.5, "pads": -9.0, "texture": -12.0},
        pump_depth=0.25, pump_release_s=0.16,
    ),
    "reggaeton": GenrePreset(
        layer_gain_db={"riff": -1.0, "drums": -1.5, "bass": -3.0, "pads": -8.0, "texture": -12.0},
        pump_depth=0.4, pump_release_s=0.15,
    ),
}

# Layers ducked by the sidechain pump (drums are the trigger, never ducked).
_PUMPED_LAYERS = ("riff", "bass", "pads", "texture")

# Layers locked dead-centre (mono) after their board — low-end mono-compatibility.
_MONO_LOCK = ("bass",)


def preset_for(genre: str | None) -> GenrePreset:
    return GENRE_PRESETS.get(genre or "default", _DEFAULT)


# ---------------------------------------------------------------------------
# Per-layer processing boards
# ---------------------------------------------------------------------------


def _riff_board() -> Pedalboard:
    # EQ + space ONLY. No compressor that pumps the transients, nothing time/pitch.
    return Pedalboard([
        HighpassFilter(cutoff_frequency_hz=45.0),      # clear sub-mud so kick/bass own the lows
        PeakFilter(cutoff_frequency_hz=3000.0, gain_db=2.0, q=0.8),  # presence
        Reverb(room_size=0.22, damping=0.5, wet_level=0.10, dry_level=0.95, width=0.9),
    ])


def _drums_board() -> Pedalboard:
    return Pedalboard([
        Compressor(threshold_db=-14.0, ratio=3.0, attack_ms=4.0, release_ms=120.0),  # punch
        HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=2.5, q=0.7),             # air on hats
    ])


def _bass_board() -> Pedalboard:
    return Pedalboard([
        Compressor(threshold_db=-18.0, ratio=4.0, attack_ms=10.0, release_ms=120.0),
        LowpassFilter(cutoff_frequency_hz=4000.0),  # keep it round, out of the riff's way
    ])


def _generic_board() -> Pedalboard:
    return Pedalboard([Compressor(threshold_db=-18.0, ratio=2.0, attack_ms=10.0, release_ms=150.0)])


_LAYER_BOARD = {
    "riff": _riff_board,
    "drums": _drums_board,
    "bass": _bass_board,
}


# ---------------------------------------------------------------------------
# Sidechain pump
# ---------------------------------------------------------------------------


def kick_onsets_from_pattern(pattern: dict[str, list[float]], tempo: float, bars: int,
                             sr: int) -> list[int]:
    """Sample indices of every kick hit across `bars` bars (the pump trigger).

    Uses the symbolic pattern (not audio detection) so the pump is musically locked.
    Falls back to `sub` if a pattern has no kick (e.g. pure-808 styles).
    """
    steps = pattern.get("kick") or pattern.get("sub")
    if not steps:
        return []
    spb = 60.0 / tempo
    step_s = spb / 4.0  # 16 steps per bar
    onsets: list[int] = []
    for b in range(bars):
        for i, vel in enumerate(steps):
            if vel > 0:
                onsets.append(int((b * 4 * spb + i * step_s) * sr))
    return onsets


def pump_envelope(n_samples: int, sr: int, onsets: list[int], depth: float,
                  release_s: float, attack_s: float = 0.004) -> np.ndarray:
    """A 1.0-baseline gain envelope that dips to (1-depth) at each kick then recovers.

    Overlapping kicks take the deeper duck (np.minimum). attack_s is a short pre-onset
    ramp down so the dip has no click.
    """
    env = np.ones(n_samples, dtype=np.float32)
    if not onsets or depth <= 0:
        return env
    tau = max(release_s / 3.0, 1e-3)
    rel_n = max(int(release_s * sr), 1)
    atk_n = max(int(attack_s * sr), 1)
    t = np.arange(rel_n) / sr
    # recovery curve: starts at (1-depth), exponentially returns toward 1.0
    recovery = (1.0 - depth) + depth * (1.0 - np.exp(-t / tau))
    recovery = recovery.astype(np.float32)
    for on in onsets:
        if on < 0 or on >= n_samples:
            continue
        # short attack ramp into the dip (ends exactly at the onset)
        a0 = max(0, on - atk_n)
        if on > a0:
            ramp = np.linspace(1.0, 1.0 - depth, on - a0, endpoint=False, dtype=np.float32)
            env[a0:on] = np.minimum(env[a0:on], ramp)
        end = min(n_samples, on + rel_n)
        if end > on:
            env[on:end] = np.minimum(env[on:end], recovery[: end - on])
    return env


# ---------------------------------------------------------------------------
# Metering
# ---------------------------------------------------------------------------


def _true_peak_db(stereo: np.ndarray, sr: int, oversample: int = 4) -> float:
    """4x-oversampled inter-sample peak estimate, in dBTP."""
    from scipy.signal import resample_poly
    up = resample_poly(stereo, oversample, 1, axis=0)
    peak = float(np.max(np.abs(up))) if up.size else 0.0
    return 20.0 * np.log10(peak) if peak > 1e-9 else -120.0


def _integrated_lufs(stereo: np.ndarray, sr: int) -> float:
    meter = pyln.Meter(sr)
    return float(meter.integrated_loudness(stereo))


# ---------------------------------------------------------------------------
# Master
# ---------------------------------------------------------------------------


@dataclass
class MasterResult:
    audio: np.ndarray        # stereo float32, shape (N, 2)
    sr: int
    lufs: float              # final integrated loudness
    true_peak_db: float      # final dBTP
    layers: tuple[str, ...]  # which layers were present


def _process(audio: np.ndarray, board: Pedalboard, sr: int) -> np.ndarray:
    """Run a stereo (N, 2) buffer through a pedalboard, shape-preserving.
    (Was _process_mono + reshape(-1), which silently scrambled stereo.)"""
    out = board(audio.astype(np.float32), sr)
    return np.asarray(out, dtype=np.float32)


def master(layers: dict[str, np.ndarray], sr: int, *, genre: str | None,
           kick_onsets: list[int], lufs_target: float | None = None) -> MasterResult:
    """Mix + master a dict of mono layers into a final stereo track.

    layers: {"riff": mono, "drums": mono, ...}. Lengths may differ; all are zero-padded
            to the longest. Only "riff" is required.
    kick_onsets: sample indices that trigger the sidechain pump.
    """
    if "riff" not in layers or layers["riff"].size == 0:
        raise ValueError("master() needs a non-empty 'riff' layer")

    preset = preset_for(genre)
    target = lufs_target if lufs_target is not None else preset.lufs_target

    # Coerce every layer to stereo (N, 2); mono inputs (e.g. tests) are upmixed.
    st_layers = {name: as_stereo(buf) for name, buf in layers.items() if buf.size}
    n = max(buf.shape[0] for buf in st_layers.values())
    pump = pump_envelope(n, sr, kick_onsets, preset.pump_depth, preset.pump_release_s)
    pump2 = pump[:, None]  # (n, 1) → broadcasts across both channels

    bus = np.zeros((n, 2), dtype=np.float32)
    for name, buf in st_layers.items():
        board = _LAYER_BOARD.get(name, _generic_board)()
        proc = _process(buf, board, sr)  # (M, 2)
        if proc.shape[0] < n:
            proc = np.pad(proc, ((0, n - proc.shape[0]), (0, 0)))
        else:
            proc = proc[:n]
        if name in _MONO_LOCK:      # lock low-end sources dead-centre
            proc = hard_mono(proc)
        if name in _PUMPED_LAYERS:
            proc = proc * pump2
        gain = 10.0 ** (preset.layer_gain_db.get(name, -6.0) / 20.0)
        bus += proc * gain

    # bus glue compressor (gentle, slow)
    glue = Pedalboard([Compressor(threshold_db=-10.0, ratio=2.0, attack_ms=30.0, release_ms=220.0)])
    bus = _process(bus, glue, sr)

    # keep the sub mono (phasey lows fold to centre); highs stay wide
    stereo = collapse_lows_to_mono(bus, sr, 120.0)

    # 1) consistent drive into the limiter: peak-normalise to ~-1 dBFS
    peak = float(np.max(np.abs(stereo)))
    if peak > 1e-9:
        stereo = stereo * (10.0 ** (-1.0 / 20.0) / peak)

    # 2) brickwall limiter for density (catches peaks over the ceiling)
    limiter = Pedalboard([Limiter(threshold_db=preset.peak_ceiling_db, release_ms=100.0)])
    stereo = np.asarray(limiter(stereo, sr), dtype=np.float32)

    # 3) loudness is set LAST, as a downward trim toward target — this also pulls the
    #    true peak safely under the ceiling (gain <= 1 for dense content).
    loud = _integrated_lufs(stereo, sr)
    if np.isfinite(loud):
        gain = 10.0 ** ((target - loud) / 20.0)
        if gain > 1.0:  # sparse content: re-limit instead of raising peaks past the ceiling
            stereo = np.asarray(limiter(stereo * gain, sr), dtype=np.float32)
        else:
            stereo = stereo * gain

    # 4) true-peak safety: trim down if inter-sample peaks still exceed the ceiling
    tp = _true_peak_db(stereo, sr)
    if tp > preset.peak_ceiling_db:
        stereo = stereo * (10.0 ** ((preset.peak_ceiling_db - tp) / 20.0))
        tp = _true_peak_db(stereo, sr)

    final_lufs = _integrated_lufs(stereo, sr)
    stereo = np.clip(stereo, -1.0, 1.0)

    return MasterResult(audio=stereo, sr=sr, lufs=final_lufs, true_peak_db=tp,
                        layers=tuple(k for k, v in layers.items() if v.size))


# ---------------------------------------------------------------------------
# MP3 export (lameenc — final mix only, no stems)
# ---------------------------------------------------------------------------


def write_mp3(path, stereo: np.ndarray, sr: int, bitrate_kbps: int = 320) -> None:
    import lameenc
    from pathlib import Path

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(stereo, -1.0, 1.0)
    if pcm.ndim == 1:
        pcm = np.stack([pcm, pcm], axis=1)
    interleaved = (pcm.reshape(-1) * 32767.0).astype("<i2").tobytes()

    enc = lameenc.Encoder()
    enc.set_bit_rate(bitrate_kbps)
    enc.set_in_sample_rate(sr)
    enc.set_channels(2)
    enc.set_quality(2)  # 2 = high quality, reasonable speed
    data = enc.encode(interleaved) + enc.flush()
    path.write_bytes(data)
