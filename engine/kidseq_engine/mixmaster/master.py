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
    Distortion,
    Gain,
    HighpassFilter,
    HighShelfFilter,
    Limiter,
    LowpassFilter,
    LowShelfFilter,
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


# Since per-layer LUFS calibration (below) sets the base balance, genre gains are
# small CREATIVE offsets from that calibrated balance, not the balance itself.
_DEFAULT = GenrePreset(
    layer_gain_db={},
    pump_depth=0.45,
    pump_release_s=0.16,
)

GENRE_PRESETS: dict[str, GenrePreset] = {
    "default": _DEFAULT,
    "techhouse": GenrePreset(layer_gain_db={"drums": 0.5},
                             pump_depth=0.50, pump_release_s=0.18),
    "dnb": GenrePreset(layer_gain_db={"drums": 1.0, "bass": 0.5, "pads": -1.0},
                       pump_depth=0.35, pump_release_s=0.10),
    "garage": GenrePreset(layer_gain_db={},
                          pump_depth=0.30, pump_release_s=0.12),
    "drill": GenrePreset(layer_gain_db={"bass": 1.0, "riff": -0.5},
                         pump_depth=0.25, pump_release_s=0.14),
    "hiphop": GenrePreset(layer_gain_db={},
                          pump_depth=0.25, pump_release_s=0.16),
    "reggaeton": GenrePreset(layer_gain_db={"drums": 0.5},
                             pump_depth=0.40, pump_release_s=0.15),
}

# Layers ducked by the sidechain pump (drums are the trigger, never ducked),
# with per-layer depth multipliers: pads/texture pump hardest (the EDM wash),
# the riff only breathes (it must stay legible — it IS the song).
_PUMP_MULT = {"bass": 1.0, "pads": 1.15, "texture": 1.15, "riff": 0.5,
              "fx": 1.0, "fx_sub": 1.0, "rumble": 1.25}
_PUMPED_LAYERS = tuple(_PUMP_MULT)
_PUMP_DEPTH_CAP = 0.65

# Post-board layer LUFS targets (active regions only) — the calibrated mix
# balance genre gains offset from. rumble pumps hardest AND sits deepest —
# it ducks out of the dry kick's way like Hades' sidechained return.
# riff_echo (R24) = the percussive note's ghost delay tail, well under.
_LAYER_LUFS = {"drums": -18.0, "riff": -20.0, "bass": -21.0, "pads": -26.0,
               "texture": -30.0, "rumble": -31.0, "riff_echo": -27.0}

# Layers locked dead-centre (mono) after their board — low-end mono-compatibility.
_MONO_LOCK = ("bass", "fx_sub", "rumble")

# R23/R24 (owner: percussive mixes muddy/murky; "the kid's note is the
# loudest event"): percussive takes run their sustained beds deeper, the
# drums step back a touch and the RIFF steps forward (negative = boost).
_PERC_LUFS_DROP = {"texture": 2.0, "pads": 2.0, "rumble": 2.0,
                   "drums": 1.0, "riff": -1.0}

# Haas-on-sides width (Camo & Krooked): a delayed mono copy added as pure
# Side on the WIDTH layers only — mono sum bit-unchanged by construction,
# drums/bass/riff core stays untouched. Per-genre side level (dB): drill/
# hiphop stay narrower (width belongs to ear-candy layers only — MixedByAli).
_HAAS_LAYERS = ("pads", "texture")
_HAAS_SIDE_DB = {"drill": -18.0, "hiphop": -18.0, "reggaeton": -15.0}
_HAAS_DEFAULT_DB = -14.0
_HAAS_DELAY_MS = 12.0

# ---------------------------------------------------------------------------
# Shared space (one wet-only reverb return replaces every insert reverb) and
# the parallel "NY" drum compression bus.
# ---------------------------------------------------------------------------

# post-board send levels into the shared reverb (dB); everything else stays
# dry. fx is deliberately wet (Aisher/Attack: risers sit in a hall — a dry
# riser reads pasted-on; tails also wash 1-2 bars across section boundaries)
# drums -22 -> -20 (R17): the SHARED return does more of the drum-space work
# as the boxy parallel room bus does less — owner: drums sat in a different
# space from the melody ("boxey").
_SEND_DB = {"riff": -14.0, "pads": -9.0, "drums": -20.0, "fx": -16.0}
_RIFF_WET_DB = -7.0        # riff send inside wet spans (the "distant" intro)
# garage/reggaeton 0.50 -> 0.44 (R17): the big room read as midrange box
_ROOM_SIZE = {"techhouse": 0.40, "dnb": 0.40, "drill": 0.35, "hiphop": 0.35,
              "garage": 0.44, "reggaeton": 0.44}   # never exceed 0.55 (metallic)
_PREDELAY_S = 0.020

# parallel drum crush, summed under the dry kit (dB by genre)
_NY_GAIN_DB = {"hiphop": -6.0, "drill": -6.0, "techhouse": -8.0, "garage": -9.0,
               "reggaeton": -8.0, "dnb": -10.0}

# parallel distorted 'room' bus under the kit (Noisia's overhead-mics trick:
# programmed drums read as a kit in a space). drill/hiphop stay OFF — their
# 'drums just need to knock' (Metro Boomin's engineer). R17: pulled 4 dB and
# the board de-boxed (owner: "reverb on the drums … boxey, not in the same
# space as the rest") — the shared return carries more of the space instead.
_ROOM_GAIN_DB = {"dnb": -20.0, "techhouse": -20.0, "garage": -21.0,
                 "reggaeton": -21.0}

# drum-bus clipper drive (Sub Focus: clip drums, don't limit them — shaves
# peaks without transient-dulling pump). Memoryless tanh(k*x)/tanh(k); the
# layer LUFS calibration restores level, so only crest/harmonics change.
_DRUM_CLIP_K = {"dnb": 1.3, "techhouse": 1.3, "garage": 1.15,
                "reggaeton": 1.15, "drill": 1.1, "hiphop": 1.1}

# bass band-split saturation wet mix (Noisia: multiband dirt on EVERY bass,
# sub band clean/mono; Young Guru: restraint — never everything). dnb runs
# hottest (R15: its reese read cheap without harmonic thickness).
_BASS_SAT_WET = {"dnb": 0.35, "techhouse": 0.25, "garage": 0.20,
                 "reggaeton": 0.20, "drill": 0.20, "hiphop": 0.15}
_BASS_SAT_SPLIT_HZ = 150.0
_BASS_SAT_DRIVE = 2.5

# R19 (owner: "bass can often sound dry, underproduced compared to rest of
# the mix"): harmonics-only send into the shared reverb return — the band
# above _BASS_SAT_SPLIT_HZ at this level; the sub never leaves the centre.
_BASS_SEND_DB = -18.0


def _bass_band_sat(x: np.ndarray, sr: int, genre: str | None) -> np.ndarray:
    """Split the bass at _BASS_SAT_SPLIT_HZ; the sub band passes CLEAN, the
    band above gets tanh harmonics blended at the genre's wet mix (RMS-matched
    so it is a tone change, not a level change). wet 0 = bit-identical."""
    wet = _BASS_SAT_WET.get(genre or "", 0.0)
    if wet <= 0.0 or x.size == 0:
        return x
    from scipy.signal import butter, sosfilt

    sos = butter(4, _BASS_SAT_SPLIT_HZ, btype="low", fs=sr, output="sos")
    low = sosfilt(sos, x, axis=0).astype(np.float32)
    mids = x - low
    rms = float(np.sqrt(np.mean(mids ** 2))) + 1e-12
    driven = np.tanh(_BASS_SAT_DRIVE * mids / rms)
    d_rms = float(np.sqrt(np.mean(driven ** 2))) + 1e-12
    driven = (driven * (rms / d_rms)).astype(np.float32)
    return (low + mids * (1.0 - wet) + driven * wet).astype(np.float32)

# Bob Katz's over-compression alarm: PLR (true peak - integrated LUFS) floor
# per genre. Breach = one bounded re-convergence at a lowered target.
_PLR_FLOOR = {"default": 7.0, "dnb": 7.5, "techhouse": 7.5, "garage": 7.0,
              "reggaeton": 7.0, "drill": 8.0, "hiphop": 8.0}

# +0.5 dB whole-mix push inside drops (DJ Swivel, 'Closer') — pre-soft-clip,
# 30 ms ramps, exactly half a decibel; the short-term LUFS guard backstops it.
_DROP_PUSH_DB = 0.5


def _reverb_return_board(genre: str | None) -> Pedalboard:
    room = _ROOM_SIZE.get(genre or "", 0.40)
    return Pedalboard([
        HighpassFilter(cutoff_frequency_hz=300.0),   # keep mud out of the tail
        LowpassFilter(cutoff_frequency_hz=7500.0),
        Reverb(room_size=room, damping=0.55, wet_level=1.0, dry_level=0.0, width=1.0),
    ])


def _room_bus_board() -> Pedalboard:
    """Noisia's distorted 'overheads': HP keeps kick sub off the drive (punch
    stays dry), heavy distortion + a SHORT wet-only room + LP against fizz —
    summed quietly under the kit for shared-space glue. Smear is the point:
    this bus is deliberately NOT impulse-aligned (unlike the NY crush)."""
    return Pedalboard([
        HighpassFilter(cutoff_frequency_hz=250.0),
        # R17: drive 12 -> 6 and LP 6k -> 8k — the hard-driven, dark, tiny
        # (0.25) room was the "boxey" tone the owner flagged; softer dirt +
        # more air keeps the glue without the shoebox
        Distortion(drive_db=6.0),
        Reverb(room_size=0.25, damping=0.6, wet_level=1.0, dry_level=0.0,
               width=0.6),
        LowpassFilter(cutoff_frequency_hz=8000.0),
    ])


def _haas_sides(x: np.ndarray, sr: int, delay_ms: float = 12.0,
                side_db: float = -14.0) -> np.ndarray:
    """Haas width on the SIDES only: a delayed mono copy added antisymmetric
    (+L/-R). (L+s)+(R-s) == L+R — the mono fold is unchanged by construction,
    so this cannot break mono compatibility; it only adds side energy."""
    d = int(delay_ms / 1000.0 * sr)
    if d <= 0 or x.shape[0] <= d:
        return x
    mono = x.mean(axis=1)
    side = np.zeros_like(mono)
    side[d:] = mono[:-d]
    side *= np.float32(10.0 ** (side_db / 20.0))
    out = x.copy()
    out[:, 0] += side
    out[:, 1] -= side
    return out


def _ny_crush_board() -> Pedalboard:
    # HP120 is load-bearing: the crush amplifies SUSTAIN, and un-filtered that
    # means kick tails = boom. Owner rule: kicks punch, never boom. The crushed
    # path adds mid-band density only; low-end punch stays on the dry transient.
    return Pedalboard([
        HighpassFilter(cutoff_frequency_hz=120.0),
        Compressor(threshold_db=-32.0, ratio=8.0, attack_ms=1.0, release_ms=90.0),
        LowpassFilter(cutoff_frequency_hz=8000.0),
        Gain(gain_db=6.0),
    ])


def preset_for(genre: str | None) -> GenrePreset:
    return GENRE_PRESETS.get(genre or "default", _DEFAULT)


# ---------------------------------------------------------------------------
# Per-layer processing boards
# ---------------------------------------------------------------------------


def _kick_slot(genre: str | None) -> float:
    """Genre kick fundamental (Hz) — the frequency the mix slots around."""
    try:
        from ..render.sample_kit import kick_slot_hz
        return kick_slot_hz(genre)
    except Exception:  # noqa: BLE001 — never let slot detection break a master
        return 55.0


def _board_for(name: str, genre: str | None,
               percussive: bool = False) -> Pedalboard:
    """Per-layer processing, EQ-slotted around the genre's kick fundamental:
    drums are boosted AT the kick slot, bass is notched exactly there (and takes
    80–120 Hz instead); the riff owns 2–4 kHz presence and pads are cut there
    so they physically cannot mask the melody."""
    if name == "drums":
        slot = _kick_slot(genre)
        # Owner rule: kicks PUNCH, never boom — tight slot boost (q1.4, +1 dB),
        # rumble HP, and on dnb (acoustic kit with real room) shelve the low
        # sustain down so the transient carries the weight.
        chain = [
            HighpassFilter(cutoff_frequency_hz=35.0),
            PeakFilter(cutoff_frequency_hz=slot, gain_db=1.0, q=1.4),
            PeakFilter(cutoff_frequency_hz=250.0, gain_db=-2.0, q=1.2),   # boxiness
            Compressor(threshold_db=-14.0, ratio=3.0, attack_ms=4.0, release_ms=120.0),
            HighShelfFilter(cutoff_frequency_hz=8000.0, gain_db=2.5, q=0.7),  # air
        ]
        if genre == "dnb":
            chain.insert(2, LowShelfFilter(cutoff_frequency_hz=85.0, gain_db=-2.0, q=0.8))
        elif genre == "techhouse":
            # R25 (owner: boomy kick eats the mix, must be punchier): shelve
            # the low sustain down so the slot-boosted transient carries the
            # weight — punch is the first 20 ms, boom is everything after
            chain.insert(2, LowShelfFilter(cutoff_frequency_hz=90.0, gain_db=-1.5, q=0.8))
        elif genre == "drill" and percussive:
            # R23: percussive drill low tidy — the Big Kick's sustain shelves
            # down so the pedal + hits don't smear (melodic drill untouched —
            # owner: it sounds great)
            chain.insert(2, LowShelfFilter(cutoff_frequency_hz=85.0, gain_db=-1.5, q=0.8))
        return Pedalboard(chain)
    if name == "bass":
        slot = _kick_slot(genre)
        return Pedalboard([
            HighpassFilter(cutoff_frequency_hz=30.0),
            PeakFilter(cutoff_frequency_hz=slot, gain_db=-3.0, q=1.4),    # kick's slot
            PeakFilter(cutoff_frequency_hz=95.0, gain_db=2.0, q=1.0),     # bass body
            HighShelfFilter(cutoff_frequency_hz=2500.0, gain_db=-1.5, q=0.71),
            LowpassFilter(cutoff_frequency_hz=6000.0),
            Compressor(threshold_db=-18.0, ratio=4.0, attack_ms=10.0, release_ms=120.0),
        ])
    if name == "riff":
        # EQ ONLY — no compressor, nothing time/pitch. Space comes from the
        # shared reverb send (one coherent room for the whole mix).
        return Pedalboard([
            HighpassFilter(cutoff_frequency_hz=140.0),   # bass owns below; grid is C4-range
            PeakFilter(cutoff_frequency_hz=300.0, gain_db=-2.0, q=1.0),
            PeakFilter(cutoff_frequency_hz=3000.0, gain_db=2.0, q=0.8),   # presence
        ])
    if name == "pads":
        return Pedalboard([
            HighpassFilter(cutoff_frequency_hz=220.0),
            LowpassFilter(cutoff_frequency_hz=9000.0),
            PeakFilter(cutoff_frequency_hz=3000.0, gain_db=-3.0, q=0.9),  # inverse of riff
            Compressor(threshold_db=-18.0, ratio=2.0, attack_ms=10.0, release_ms=150.0),
        ])
    if name == "texture":
        return Pedalboard([
            HighpassFilter(cutoff_frequency_hz=400.0),
            Compressor(threshold_db=-18.0, ratio=2.0, attack_ms=10.0, release_ms=150.0),
        ])
    if name == "fx_sub":
        # the Bomb's path: sub weight is the whole point — rumble guard only
        return Pedalboard([HighpassFilter(cutoff_frequency_hz=28.0)])
    if name == "rumble":
        # the techno rumble bed: strictly low-band (the drums keep the slot
        # boost; this is the space BETWEEN the kicks)
        return Pedalboard([HighpassFilter(cutoff_frequency_hz=30.0),
                           LowpassFilter(cutoff_frequency_hz=110.0)])
    if name == "fx":
        return Pedalboard([HighpassFilter(cutoff_frequency_hz=150.0)])
    return Pedalboard([Compressor(threshold_db=-18.0, ratio=2.0, attack_ms=10.0, release_ms=150.0)])


def _calibrate_layer(buf: np.ndarray, sr: int, target_lufs: float) -> np.ndarray:
    """Trim a layer so its ACTIVE regions (100 ms blocks with RMS > −60 dBFS)
    measure `target_lufs`. Layers spend much of a song silent (drums drop out
    in breaks, pads out of intros) — measuring the whole buffer would make
    sparse layers loud. This sets the calibrated mix balance; genre gains are
    creative offsets on top."""
    blk = int(0.1 * sr)
    nb = buf.shape[0] // blk
    if nb < 4:
        return buf
    blocks = buf[: nb * blk].reshape(nb, blk, buf.shape[1])
    rms = np.sqrt((blocks ** 2).mean(axis=(1, 2)))
    act = rms > 10.0 ** (-60.0 / 20.0)
    if not act.any():
        return buf
    active = blocks[act].reshape(-1, buf.shape[1])
    if active.shape[0] < sr:  # pyloudnorm needs a usable length
        reps = int(np.ceil(sr / active.shape[0]))
        active = np.tile(active, (reps, 1))
    loud = _integrated_lufs(active.astype(np.float32), sr)
    if not np.isfinite(loud):
        return buf
    return (buf * (10.0 ** ((target_lufs - loud) / 20.0))).astype(np.float32)


# ---------------------------------------------------------------------------
# Sidechain pump
# ---------------------------------------------------------------------------


def kick_onsets_from_pattern(pattern: dict[str, list[float]], tempo: float, bars: int,
                             sr: int, style: str | None = None) -> list[int]:
    """Sample indices of every kick hit across `bars` bars (the pump trigger).

    Uses the symbolic pattern (not audio detection) so the pump is musically locked.
    `style` applies the same swing as the drum renderers — the duck lands exactly
    on the swung hit. Falls back to `sub` if a pattern has no kick.
    """
    from ..render.drums import swung_step_offset

    steps = pattern.get("kick") or pattern.get("sub")
    if not steps:
        return []
    spb = 60.0 / tempo
    step_s = spb / 4.0  # 16 steps per bar
    onsets: list[int] = []
    for b in range(bars):
        for i, vel in enumerate(steps):
            if vel > 0:
                onsets.append(int((b * 4 * spb + swung_step_offset(style, i) * step_s) * sr))
    return onsets


def pump_envelope(n_samples: int, sr: int, onsets: list[int], depth: float,
                  release_s: float, attack_s: float = 0.004,
                  hold_s: float = 0.010) -> np.ndarray:
    """A 1.0-baseline gain envelope: 4 ms dip ENDING at each kick onset, 10 ms
    hold at (1-depth), then exponential recovery (τ = release_s/3, ~95% back by
    release_s). Overlapping kicks take the deeper duck (np.minimum)."""
    env = np.ones(n_samples, dtype=np.float32)
    if not onsets or depth <= 0:
        return env
    tau = max(release_s / 3.0, 1e-3)
    rel_n = max(int(release_s * sr), 1)
    atk_n = max(int(attack_s * sr), 1)
    hold_n = max(int(hold_s * sr), 1)
    t = np.arange(rel_n) / sr
    recovery = ((1.0 - depth) + depth * (1.0 - np.exp(-t / tau))).astype(np.float32)
    for on in onsets:
        if on < 0 or on >= n_samples:
            continue
        a0 = max(0, on - atk_n)
        if on > a0:  # attack ramp lands AT the onset (duck ready before the hit)
            ramp = np.linspace(1.0, 1.0 - depth, on - a0, endpoint=False, dtype=np.float32)
            env[a0:on] = np.minimum(env[a0:on], ramp)
        h_end = min(n_samples, on + hold_n)
        env[on:h_end] = np.minimum(env[on:h_end], np.float32(1.0 - depth))
        end = min(n_samples, h_end + rel_n)
        if end > h_end:
            env[h_end:end] = np.minimum(env[h_end:end], recovery[: end - h_end])
    return env


# ---------------------------------------------------------------------------
# Master-bus endgame helpers (EQ, calibration, saturation, limiter loop)
# ---------------------------------------------------------------------------


def _master_eq(genre: str | None, percussive: bool = False) -> Pedalboard:
    """Master tone shape, applied BEFORE every nonlinearity (HP first so
    subsonics don't eat clipper/limiter headroom). The 3.2 kHz dip is the
    kid-specific anti-fatigue move; 280 Hz clears stacked low-mid mud.
    Hawkes moves (R13): 30 Hz HP makes the low end punch harder, not thinner
    (drill/hiphop keep 24 for 808 tails); DnB weight lives ~60 Hz; the top
    lift is TWO small cascaded shelves, never one big boost. Percussive
    takes (R23 — owner: muddy/murky) cut the low-mid mud band deeper: their
    beds/drones/pedal all live there."""
    if genre in ("drill", "hiphop"):
        hp_hz, low = 24.0, (60.0, 1.5, 0.8)
    elif genre == "dnb":
        hp_hz, low = 30.0, (65.0, 1.5, 0.8)
    else:
        hp_hz, low = 30.0, (100.0, 1.2, 0.71)
    mud_db = -2.5 if percussive else -1.5
    return Pedalboard([
        HighpassFilter(cutoff_frequency_hz=hp_hz),
        LowShelfFilter(cutoff_frequency_hz=low[0], gain_db=low[1], q=low[2]),
        PeakFilter(cutoff_frequency_hz=280.0, gain_db=mud_db, q=1.1),
        PeakFilter(cutoff_frequency_hz=3200.0, gain_db=-1.0, q=1.4),
        HighShelfFilter(cutoff_frequency_hz=9500.0, gain_db=1.0, q=0.71),
        HighShelfFilter(cutoff_frequency_hz=13500.0, gain_db=0.8, q=0.71),
    ])


def _dynamic_guard(x: np.ndarray, sr: int, lo: float = 6000.0,
                   hi: float = 9000.0, max_cut_db: float = 2.5) -> np.ndarray:
    """Beau Thomas' movable dynamics band: catch harsh snare/hat transients
    in the 6-9 kHz zone BEFORE the nonlinearities exaggerate them. Downward
    only, max 2.5 dB, threshold auto-set ~6 dB above the band's programme
    average; subtractive application so quiet content passes bit-identical.
    Vectorized (the _brickwall idiom): max-filter hold + Hann smooth."""
    from scipy.ndimage import maximum_filter1d
    from scipy.signal import butter, fftconvolve, sosfilt

    sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    band = sosfilt(sos, x, axis=0).astype(np.float32)
    lvl = np.abs(band).max(axis=1).astype(np.float64)
    win = np.hanning(max(3, int(0.005 * sr)))
    lvl = fftconvolve(lvl, win / win.sum(), mode="same")
    active = lvl[lvl > 1e-5]
    if active.size == 0:
        return x
    thresh = float(active.mean()) * 2.0
    over = np.maximum(lvl / max(thresh, 1e-12), 1.0)
    cut_db = np.minimum(20.0 * np.log10(over), max_cut_db)
    if float(cut_db.max()) <= 1e-6:
        return x
    rel = max(2, int(0.080 * sr))
    cut_db = maximum_filter1d(cut_db, size=rel)
    cut_db = fftconvolve(cut_db, win / win.sum(), mode="same")
    gain = (10.0 ** (-cut_db / 20.0)).astype(np.float32)
    return (x - band * (1.0 - gain[:, None])).astype(np.float32)


def _windowed_lufs_calibrate(stereo: np.ndarray, sr: int, ref_lufs: float = -16.0) -> np.ndarray:
    """Gain the bus so the LOUDEST 30% of 3 s windows average `ref_lufs`.

    LUFS-based staging replaces peak-normalisation (peak staging made glue
    behaviour a content lottery); using only the loudest windows keeps quiet
    intros/outros from skewing the reference."""
    meter = pyln.Meter(sr)
    win, hop = 3 * sr, sr
    vals = []
    for s in range(0, max(1, stereo.shape[0] - win), hop):
        v = meter.integrated_loudness(stereo[s:s + win])
        if np.isfinite(v):
            vals.append(v)
    if not vals:
        return stereo
    vals.sort(reverse=True)
    loud = float(np.mean(vals[:max(1, int(len(vals) * 0.3))]))
    return (stereo * (10.0 ** ((ref_lufs - loud) / 20.0))).astype(np.float32)


# full-band tanh soft clip: harmonic density before the limiter. Harder knee on
# the aggressive four-to-floor/drill styles.
_CLIP_K = {"techhouse": 1.6, "dnb": 1.6, "drill": 1.6}


def _soft_clip(stereo: np.ndarray, genre: str | None) -> np.ndarray:
    k = _CLIP_K.get(genre or "", 1.3)
    return (np.tanh(k * stereo) / np.tanh(k)).astype(np.float32)


def _brickwall(x: np.ndarray, sr: int, ceiling_lin: float,
               lookahead_s: float = 0.002, release_s: float = 0.060) -> np.ndarray:
    """Deterministic stereo-linked lookahead brickwall limiter (vectorized).

    NB: pedalboard's `Limiter` is a JUCE limiter WITH make-up gain — its output
    ceiling is NOT the threshold (measured +2.2 dBTP at threshold −1.2), which
    made loudness convergence impossible.

    Construction with a hard guarantee (gain[n] <= required[n] for every n, so
    NO hard-clip stage — hard clipping at 4x re-creates inter-sample overshoot
    after decimation):
      deficit d[n] = 1 - min(1, ceiling/|x|)
      d2 = asymmetric running MAX of d over [n - release, n + lookahead]
           (attack via lookahead, hold-style release)
      d3 = Hann FIR smooth of d2, support ±lookahead — because every point of
           the FIR support carries a max-window that contains n, the smoothed
           deficit stays >= d[n] (weighted average of values each >= d[n]).
      gain = 1 - d3
    """
    from scipy.ndimage import maximum_filter1d
    from scipy.signal import fftconvolve

    amp = np.max(np.abs(x), axis=1)                       # stereo-linked peak
    d = 1.0 - np.minimum(1.0, ceiling_lin / np.maximum(amp, 1e-9))
    la = max(2, int(lookahead_s * sr))
    rel = max(la, int(release_s * sr))
    # window spanning [n - rel, n + la]: size rel+la+1, shifted right by la
    size = rel + la + 1
    origin = (size // 2) - rel  # left edge lands at n - rel
    origin = int(np.clip(origin, -(size // 2), size // 2))
    d2 = maximum_filter1d(d, size=size, mode="nearest", origin=origin)
    w = np.hanning(2 * la + 1)
    w /= w.sum()
    d3 = fftconvolve(d2, w, mode="same")
    gain = (1.0 - d3).astype(np.float32)
    return (x * gain[:, None]).astype(np.float32)


def _limit_to_lufs(stereo: np.ndarray, sr: int, target: float,
                   ceiling_db: float = -1.2, max_iters: int = 5) -> np.ndarray:
    # max_iters=5: past the clipper, loudness rises sublinearly with drive, so
    # each (target - got) correction under-delivers; 3 passes left dense swung
    # content ~0.3 LU shy of target.
    """Drive-INTO-limiter convergence: gain the ORIGINAL buffer up into a
    4x-oversampled brickwall until integrated loudness lands on target (±0.2 LU).

    Replaces the old downward-only trim (which left dense masters 2.5-4 dB
    quiet). Limiting at 4x sample rate controls inter-sample peaks at the
    source; the −1.2 ceiling budgets MP3-encoder overshoot under −1.0. Each
    iteration re-limits from the clean input, never a limited signal."""
    from scipy.signal import resample_poly

    import os

    debug = bool(os.environ.get("KIDSEQ_DEBUG_MASTER"))
    ceiling_lin = 10.0 ** (ceiling_db / 20.0)
    meas = _integrated_lufs(stereo, sr)
    if not np.isfinite(meas):
        return stereo
    drive = target - meas + 0.7  # overshoot budget pushes into the limiter
    out = stereo
    n = stereo.shape[0]
    pad = 2048  # resample_poly edge-ringing lands in padding, not the audio
    for i in range(max_iters):
        driven = stereo * (10.0 ** (drive / 20.0))
        driven = np.pad(driven, ((pad, pad), (0, 0)))
        up = resample_poly(driven, 4, 1, axis=0)
        lim = _brickwall(up.astype(np.float32), sr * 4, ceiling_lin)
        down = resample_poly(lim, 1, 4, axis=0).astype(np.float32)
        out = down[pad:pad + n]
        if out.shape[0] < n:
            out = np.pad(out, ((0, n - out.shape[0]), (0, 0)))
        # decimation re-introduces content-dependent inter-sample overshoot
        # (0.1-0.6 dB on clip-dense material). Apply the final-ceiling trim
        # INSIDE the loop so drive targets the post-trim loudness — otherwise
        # master()'s TP trim silently pulls converged masters off-target.
        tp = _true_peak_db(out, sr)
        if tp > ceiling_db + 0.2:
            out = out * (10.0 ** ((ceiling_db + 0.2 - tp) / 20.0))
        got = _integrated_lufs(out, sr)
        if debug:
            print(f"    [limit_to_lufs] iter {i}: drive={drive:+.2f} -> "
                  f"lufs={got:.2f} tp={_true_peak_db(out, sr):.2f}")
        if not np.isfinite(got) or abs(got - target) <= 0.2:
            break
        drive += target - got
    return out


def _max_short_term_lufs(stereo: np.ndarray, sr: int) -> float:
    meter = pyln.Meter(sr)
    win, hop = 3 * sr, sr
    worst = -120.0
    for s in range(0, max(1, stereo.shape[0] - win), hop):
        v = meter.integrated_loudness(stereo[s:s + win])
        if np.isfinite(v):
            worst = max(worst, float(v))
    return worst


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


# per-section reverb-send rides for pads/fx (Rødhåd's wet-fader move / Eric J
# Dubowsky's return automation): wet blooms in breaks and the final build bar,
# snaps drier inside drops for clarity. Keys are section-name prefixes.
_SEND_RIDE_DB = {"break": 4.0, "build_tail": 4.0, "drop": -2.0}


def _ride_curve(n: int, sr: int, base_db: float,
                section_spans: list[tuple[str, int, int]]) -> np.ndarray:
    """Per-sample send gain from a base level + per-section deltas, smoothed
    with a 50 ms window so rides never click."""
    curve = np.full(n, 10.0 ** (base_db / 20.0), dtype=np.float64)
    for name, s0, s1 in section_spans:
        delta = None
        for k, v in _SEND_RIDE_DB.items():
            if name.startswith(k):
                delta = v
                break
        if delta is None:
            continue
        s0c, s1c = max(0, s0), min(n, s1)
        if s1c > s0c:
            curve[s0c:s1c] = 10.0 ** ((base_db + delta) / 20.0)
    from scipy.signal import fftconvolve

    ramp = max(2, int(0.050 * sr))
    win = np.ones(ramp) / ramp
    padded = np.concatenate([np.full(ramp, curve[0]), curve,
                             np.full(ramp, curve[-1])])
    return fftconvolve(padded, win, mode="same")[ramp:-ramp].astype(np.float32)


def master(layers: dict[str, np.ndarray], sr: int, *, genre: str | None,
           kick_onsets: list[int], lufs_target: float | None = None,
           tempo: float = 120.0,
           riff_wet_spans: list[tuple[int, int]] | None = None,
           section_spans: list[tuple[str, int, int]] | None = None,
           pump_depth: float | None = None,
           percussive: bool = False) -> MasterResult:
    """Mix + master a dict of layers into the final stereo track.

    layers: {"riff": (N,2) or mono, ...}. Lengths may differ; all are zero-padded
            to the longest. Only "riff" is required.
    kick_onsets: sample indices that trigger the sidechain pump.
    tempo: used to sync the glue compressor's release to the groove.
    riff_wet_spans: (start, end) sample ranges where the riff's reverb send is
            raised to _RIFF_WET_DB (the arranger passes the intro — a "distant"
            open that dries up when the band arrives).
    section_spans: (section_name, start, end) sample ranges; when given, the
            pads/fx reverb sends ride per section (_SEND_RIDE_DB — wet breaks,
            drier drops). None = static sends (fixtures/tests unchanged).
    """
    if "riff" not in layers or layers["riff"].size == 0:
        raise ValueError("master() needs a non-empty 'riff' layer")

    preset = preset_for(genre)
    target = lufs_target if lufs_target is not None else preset.lufs_target
    # R19: per-press pump override (ArrangeStyle.pump_depth via the caller) —
    # techhouse's fixed 0.50 pump on every take was part of the "cheesy" read
    pump_base = pump_depth if pump_depth is not None else preset.pump_depth

    # Coerce every layer to stereo (N, 2); mono inputs (e.g. tests) are upmixed.
    st_layers = {name: as_stereo(buf) for name, buf in layers.items() if buf.size}
    n = max(buf.shape[0] for buf in st_layers.values())

    # One duck SHAPE (0 = no duck, 1 = full), scaled per layer: pads/texture pump
    # hardest, the riff only breathes. Recovery time follows the groove (~95%
    # back a bit past the next 8th).
    pump_release = 0.55 * (60.0 / tempo)
    shape = 1.0 - pump_envelope(n, sr, kick_onsets, 1.0, pump_release)

    bus = np.zeros((n, 2), dtype=np.float32)
    send_acc = np.zeros((n, 2), dtype=np.float32)
    for name, buf in st_layers.items():
        proc = _process(buf, _board_for(name, genre, percussive), sr)  # (M, 2)
        if proc.shape[0] < n:
            proc = np.pad(proc, ((0, n - proc.shape[0]), (0, 0)))
        else:
            proc = proc[:n]
        if name == "bass":
            # band-split saturation (Noisia: subtle multiband dirt on EVERY
            # bass, sub band clean) — harmonics thicken the mids so the bass
            # reads expensive on small speakers; calibration below restores
            # the level so this is tone, not gain (R15: dnb bass read cheap)
            proc = _bass_band_sat(proc, sr, genre)
        if name == "drums":
            # clip the kit, don't limit it (Sub Focus): gentle memoryless
            # drive shaves peaks; calibration below restores the level
            k = _DRUM_CLIP_K.get(genre or "", 1.15)
            proc = (np.tanh(k * proc) / np.tanh(k)).astype(np.float32)
            dry = proc
            # parallel NY crush under the dry kit (density without killing punch)
            crushed = _process(dry, _ny_crush_board(), sr)[:n]
            if crushed.shape[0] < n:
                crushed = np.pad(crushed, ((0, n - crushed.shape[0]), (0, 0)))
            proc = dry + crushed * (10.0 ** (_NY_GAIN_DB.get(genre or "", -8.0) / 20.0))
            # parallel distorted 'room' (Noisia's overheads) — fed from the
            # DRY kit so the crush and the room stay independent colours
            room_db = _ROOM_GAIN_DB.get(genre or "")
            if room_db is not None:
                room = _process(dry, _room_bus_board(), sr)[:n]
                if room.shape[0] < n:
                    room = np.pad(room, ((0, n - room.shape[0]), (0, 0)))
                proc = proc + room * (10.0 ** (room_db / 20.0))
        if name in _HAAS_LAYERS:
            proc = _haas_sides(proc, sr, _HAAS_DELAY_MS,
                               _HAAS_SIDE_DB.get(genre or "", _HAAS_DEFAULT_DB))
        if not name.startswith("fx"):  # FX layers are peak-specified by design — no calibration
            lufs_t = _LAYER_LUFS.get(name, -22.0)
            if percussive:
                lufs_t -= _PERC_LUFS_DROP.get(name, 0.0)   # R23 anti-mud
            proc = _calibrate_layer(proc, sr, lufs_t)
        if name in _MONO_LOCK:      # lock low-end sources dead-centre
            proc = hard_mono(proc)

        # tap the shared-reverb send pre-pump (the return gets its own duck)
        send_db = _SEND_DB.get(name)
        if send_db is not None:
            if name == "riff" and riff_wet_spans:
                curve = np.full(n, 10.0 ** (send_db / 20.0), dtype=np.float32)
                for s0, s1 in riff_wet_spans:
                    curve[max(0, s0):max(0, s1)] = 10.0 ** (_RIFF_WET_DB / 20.0)
                send_acc += proc * curve[:, None]
            elif name in ("pads", "fx") and section_spans:
                curve = _ride_curve(n, sr, send_db, section_spans)
                send_acc += proc * curve[:, None]
            else:
                send_acc += proc * (10.0 ** (send_db / 20.0))
        elif name == "bass":
            # R19 (owner: bass reads dry/underproduced vs the rest): the
            # bass's HARMONICS visit the shared room like every other layer;
            # the sub band stays bone dry and mono (Noisia doctrine — same
            # split as _bass_band_sat).
            from scipy.signal import butter, sosfilt
            sos = butter(4, _BASS_SAT_SPLIT_HZ, btype="low", fs=sr,
                         output="sos")
            low = sosfilt(sos, proc, axis=0).astype(np.float32)
            send_acc += (proc - low) * (10.0 ** (_BASS_SEND_DB / 20.0))

        if name in _PUMPED_LAYERS:
            depth = min(_PUMP_DEPTH_CAP, pump_base * _PUMP_MULT[name])
            if name == "bass":
                # multiband duck (Pretolesi: 'fix the bass, not the kick') —
                # only the band clashing with the kick ducks fully; the
                # bass's harmonics keep sustaining at 0.35x depth.
                # Subtractive split: bit-identical null when shape == 0.
                from scipy.signal import butter, sosfilt
                sos = butter(4, 170.0, btype="low", fs=sr, output="sos")
                low = sosfilt(sos, proc, axis=0).astype(np.float32)
                duck = (depth * shape).astype(np.float32)[:, None]
                proc = proc - low * duck - (proc - low) * (0.35 * duck)
            else:
                proc = proc * (1.0 - depth * shape)[:, None]
        gain = 10.0 ** (preset.layer_gain_db.get(name, 0.0) / 20.0)
        bus += proc * gain

    # shared space: ONE wet-only return for the whole mix (coherent room),
    # pre-delayed 20 ms and ducked at 0.8x the genre pump depth
    if float(np.max(np.abs(send_acc))) > 1e-9:
        pre = int(_PREDELAY_S * sr)
        sent = np.pad(send_acc, ((pre, 0), (0, 0)))[:n]
        ret = _process(sent, _reverb_return_board(genre), sr)[:n]
        if ret.shape[0] < n:
            ret = np.pad(ret, ((0, n - ret.shape[0]), (0, 0)))
        ret = ret * (1.0 - 0.8 * pump_base * shape)[:, None]
        bus += ret

    # --- master-bus endgame -------------------------------------------------
    # 1) DC removal, then tone (EQ precedes every nonlinearity: HP first so
    #    subsonics don't eat clip headroom)
    bus = bus - bus.mean(axis=0, keepdims=True).astype(np.float32)
    bus = _process(bus, _master_eq(genre, percussive), sr)

    # 2) keep the lows mono (phasey lows fold to centre); highs stay wide.
    #    250 Hz per Pretolesi/Reznikov width discipline (was 120): the
    #    100-300 Hz zone stops clouding the kick, width lives above.
    stereo = collapse_lows_to_mono(bus, sr, 250.0)

    # 3) level staging by LOUDNESS, not peaks — glue then behaves consistently
    stereo = _windowed_lufs_calibrate(stereo, sr, -16.0)
    glue_release = float(np.clip(60000.0 / tempo * 0.5, 120.0, 350.0))
    glue = Pedalboard([Compressor(threshold_db=-13.0, ratio=2.0, attack_ms=30.0,
                                  release_ms=glue_release)])
    stereo = _process(stereo, glue, sr)

    # 3b) dynamic guard band (Beau Thomas): tame harsh snare/hat pokes in
    #     6-9 kHz BEFORE the nonlinearities exaggerate them
    stereo = _dynamic_guard(stereo, sr)

    # 3c) +0.5 dB whole-mix push inside drops (DJ Swivel), 30 ms ramps —
    #     drops read bigger without re-balancing; the -8 LUFS short-term
    #     guard below backstops the trade
    if section_spans:
        from scipy.signal import fftconvolve
        g = np.ones(stereo.shape[0], dtype=np.float64)
        for sname, s0, s1 in section_spans:
            if sname.startswith("drop"):
                g[max(0, s0):min(stereo.shape[0], s1)] = \
                    10.0 ** (_DROP_PUSH_DB / 20.0)
        ramp = max(2, int(0.030 * sr))
        win = np.ones(ramp) / ramp
        padded = np.concatenate([np.full(ramp, g[0]), g, np.full(ramp, g[-1])])
        g = fftconvolve(padded, win, mode="same")[ramp:-ramp]
        stereo = (stereo * g[:, None].astype(np.float32)).astype(np.float32)

    # 4) density: full-band soft clip, then drive INTO the oversampled limiter
    #    until integrated loudness converges on target
    stereo = _soft_clip(stereo, genre) * (10.0 ** (-0.5 / 20.0))
    pre_limit = stereo  # the clean input every re-convergence starts from
    stereo = _limit_to_lufs(stereo, sr, target, ceiling_db=-1.2)

    # 5) true-peak check (limiter ran at 4x, so this should already hold)
    tp = _true_peak_db(stereo, sr)
    if tp > preset.peak_ceiling_db:
        stereo = stereo * (10.0 ** ((preset.peak_ceiling_db - tp) / 20.0))
        tp = _true_peak_db(stereo, sr)

    # 6) short-term guardrail: no 3 s stretch hotter than -8 LUFS (fatigue).
    #    One bounded pass: re-converge at a lower target, accept the trade.
    worst = _max_short_term_lufs(stereo, sr)
    if worst > -8.0:
        stereo = _limit_to_lufs(stereo, sr, target - (worst + 8.0), ceiling_db=-1.2)
        tp = _true_peak_db(stereo, sr)

    # 7) PLR floor (Bob Katz's over-compression alarm): if true peak minus
    #    integrated loudness falls under the genre floor, the LIMITER is
    #    eating transients — one bounded re-convergence at a lowered target.
    #    Guarded on the pre-limiter PLR: content that is intrinsically dense
    #    (its own crest already under the floor) cannot be "fixed" by backing
    #    off, so it is left at target (test fixtures, steady tones).
    final_lufs = _integrated_lufs(stereo, sr)
    plr_floor = _PLR_FLOOR.get(genre or "", _PLR_FLOOR["default"])
    if np.isfinite(final_lufs) and (tp - final_lufs) < plr_floor - 0.05:
        pre_lufs = _integrated_lufs(pre_limit, sr)
        pre_plr = _true_peak_db(pre_limit, sr) - pre_lufs
        if np.isfinite(pre_lufs) and pre_plr >= plr_floor:
            stereo = _limit_to_lufs(pre_limit, sr,
                                    target - (plr_floor - (tp - final_lufs)),
                                    ceiling_db=-1.2)
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
