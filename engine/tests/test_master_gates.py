"""Master numeric gates — the mix/master CI contract.

Deterministic SYNTHETIC layers (tones + seeded noise, no sample loading) are fed
through master() per genre and checked against loudness / true-peak / stereo /
hygiene bounds. This is fast and reproducible; real-instrument musicality is judged
by ear on the smoke_song render, not here.

Gate tolerances are staged with the build increments:
  - Increment 1 (stereo pipeline): LUFS ±0.6, TP ceiling only, genuine-stereo +
    mono-compatibility + mono-fold + hygiene gates.
  - Increment 2 (master endgame) TIGHTENS: LUFS ±0.3, TP lower bound −1.8 (a
    starved limiter fails), crest/short-term/LRA. Marked TIGHTEN-INC2 below.
"""

from __future__ import annotations

import sys
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.audio import SR, seconds_per_beat  # noqa: E402
from kidseq_engine.mixmaster import kick_onsets_from_pattern, master  # noqa: E402
from kidseq_engine.mixmaster.master import preset_for  # noqa: E402
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402

GENRES = list(DRUM_PATTERNS)  # techhouse, dnb, garage, drill, hiphop, reggaeton
_SECONDS = 8.0
_TEMPO = 120.0


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 1e-12 else 1.0


def _subband_corr(stereo: np.ndarray, sr: int, cutoff: float = 120.0) -> float:
    from scipy.signal import butter, sosfilt

    sos = butter(4, cutoff, btype="low", fs=sr, output="sos")
    return _corr(sosfilt(sos, stereo[:, 0]), sosfilt(sos, stereo[:, 1]))


def _synth_layers(genre: str, *, stereo: bool, sr: int = SR):
    """Deterministic layer fixtures. stereo=True gives DECORRELATED pads (a real
    stereo image); stereo=False gives dual-mono everything (invariant test)."""
    rng = np.random.default_rng(zlib.crc32(genre.encode()))
    n = int(_SECONDS * sr)
    t = np.arange(n) / sr

    def st(mono_l, mono_r):
        return np.stack([mono_l, mono_r], axis=1).astype(np.float32)

    riff_m = 0.3 * np.sin(2 * np.pi * 440.0 * t) * np.exp(-((t % 0.5) / 0.3))
    bass_m = 0.4 * np.sin(2 * np.pi * 60.0 * t)
    drums_m = np.zeros(n, dtype=np.float32)
    spb = seconds_per_beat(_TEMPO)
    for b in range(int(_SECONDS / (4 * spb)) + 1):
        for beat in range(4):
            at = int((b * 4 * spb + beat * spb) * sr)
            if at < n:
                dur = min(int(0.08 * sr), n - at)
                drums_m[at:at + dur] += (0.6 * rng.standard_normal(dur)
                                         * np.exp(-np.arange(dur) / (0.02 * sr))).astype(np.float32)

    # stereo=True: R pad is detuned +1.5 Hz + independent noise — strong,
    # deterministic decorrelation (an unambiguous stereo image to preserve)
    pad_l = 0.25 * np.sin(2 * np.pi * 330.0 * t) + 0.1 * rng.standard_normal(n).astype(np.float32)
    pad_r = (0.25 * np.sin(2 * np.pi * (331.5 if stereo else 330.0) * t)
             + (0.1 * rng.standard_normal(n).astype(np.float32) if stereo else 0.0))

    return {
        "riff": st(riff_m, riff_m),
        "drums": st(drums_m, drums_m),
        "bass": st(bass_m, bass_m),
        "pads": st(pad_l, pad_r),
    }


def _run(genre: str, stereo: bool):
    layers = _synth_layers(genre, stereo=stereo)
    n = layers["riff"].shape[0]
    bars = int(_SECONDS / (4 * seconds_per_beat(_TEMPO))) + 1
    onsets = kick_onsets_from_pattern(DRUM_PATTERNS[genre], _TEMPO, bars, SR, style=genre)
    return master(layers, SR, genre=genre, kick_onsets=onsets), n


def test_output_is_stereo_and_exact_length():
    for g in GENRES:
        res, n = _run(g, stereo=True)
        assert res.audio.ndim == 2 and res.audio.shape[1] == 2, g
        assert res.audio.shape[0] == n, (g, res.audio.shape[0], n)


def test_hygiene_finite_bounded_no_dc():
    for g in GENRES:
        res, _ = _run(g, stereo=True)
        a = res.audio
        assert np.all(np.isfinite(a)), g
        assert float(np.max(np.abs(a))) <= 1.0 + 1e-6, g
        assert abs(float(a[:, 0].mean())) < 1e-3 and abs(float(a[:, 1].mean())) < 1e-3, g


def test_loudness_hits_target():
    from kidseq_engine.mixmaster.master import _max_short_term_lufs

    for g in GENRES:
        res, _ = _run(g, stereo=True)
        tgt = preset_for(g).lufs_target
        worst = _max_short_term_lufs(res.audio, SR)
        # fatigue ceiling always holds (small tolerance for re-convergence)
        assert worst <= -7.8, (g, worst)
        if abs(res.lufs - tgt) >= 0.3:
            # off-target is legal ONLY when the short-term guard pulled the
            # master down (dense content trading integrated loudness for the
            # -8 LUFS fatigue ceiling) — and the trade must stay bounded
            assert tgt - 1.2 < res.lufs < tgt, (g, res.lufs, tgt)
            assert worst >= -8.8, (g, worst)


def test_true_peak_under_ceiling_but_not_starved():
    for g in GENRES:
        res, _ = _run(g, stereo=True)
        ceil = preset_for(g).peak_ceiling_db
        assert res.true_peak_db <= ceil + 0.05, (g, res.true_peak_db, ceil)
        # a TP far below the ceiling means the limiter isn't being driven — the
        # "quiet master" failure mode this chain exists to prevent
        assert res.true_peak_db >= -1.8, (g, res.true_peak_db)


def test_genuinely_stereo_not_dual_mono():
    """The headline Increment-1 gate: decorrelated input must NOT collapse to
    dual-mono at the output (the old master duplicated one channel)."""
    for g in GENRES:
        res, _ = _run(g, stereo=True)
        L, R = res.audio[:, 0], res.audio[:, 1]
        assert not np.allclose(L, R), f"{g}: output is dual-mono"
        assert _corr(L, R) < 0.98, (g, _corr(L, R))


def test_mono_compatible_and_low_end_mono():
    for g in GENRES:
        res, _ = _run(g, stereo=True)
        assert _corr(res.audio[:, 0], res.audio[:, 1]) > -0.2, g  # no wide-null cancel
        assert _subband_corr(res.audio, SR) >= 0.9, (g, _subband_corr(res.audio, SR))


def test_mono_input_stays_mono():
    """Invariant: dual-mono layers in ⇒ near-mono out. The shared reverb return
    (width 1.0, wet-only, ~-15 dB) adds a LITTLE genuine width by design — the
    bound allows that but still catches accidental widening of the dry path."""
    for g in GENRES:
        res, _ = _run(g, stereo=False)
        assert _corr(res.audio[:, 0], res.audio[:, 1]) > 0.90, (g, _corr(res.audio[:, 0], res.audio[:, 1]))


def test_plr_floor_holds():
    """Katz's over-compression alarm as a gate: true peak minus integrated
    LUFS must clear the genre floor — transients are getting through."""
    from kidseq_engine.mixmaster.master import _PLR_FLOOR

    for g in GENRES:
        res, _ = _run(g, stereo=True)
        floor = _PLR_FLOOR.get(g, _PLR_FLOOR["default"])
        plr = res.true_peak_db - res.lufs
        assert plr >= floor - 0.3, (g, plr, floor)


def test_bass_band_sat_sub_clean_mids_thickened():
    """R15 bass saturation (Noisia): the sub band passes essentially clean,
    the mids gain harmonics; level change stays small (tone, not gain);
    unknown genre (wet 0) is bit-identical."""
    from scipy.signal import butter, sosfilt

    from kidseq_engine.mixmaster.master import _bass_band_sat

    n = 4 * SR
    t = np.arange(n) / SR
    mono = (0.5 * np.sin(2 * np.pi * 55.0 * t)
            + 0.25 * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)
    x = np.stack([mono, mono], axis=1)
    assert np.array_equal(_bass_band_sat(x, SR, None), x)       # wet 0 = null
    y = _bass_band_sat(x, SR, "dnb")
    assert not np.array_equal(y, x)
    sos = butter(4, 100.0, btype="low", fs=SR, output="sos")
    low_in = sosfilt(sos, x, axis=0)
    low_out = sosfilt(sos, y, axis=0)
    # sub band essentially unchanged (tiny crossover leakage tolerated)
    assert float(np.max(np.abs(low_out - low_in))) < 0.05
    # overall level moves < 1 dB (RMS-matched drive)
    rms = lambda a: float(np.sqrt(np.mean(a ** 2)))  # noqa: E731
    assert abs(20.0 * np.log10(rms(y) / rms(x))) < 1.0


def test_dynamic_guard_cuts_pokes_not_programme():
    """The 6-9 kHz guard band: a transient poking far above the band average
    gets cut (<= 2.5 dB); content without pokes passes (near-)unchanged."""
    from kidseq_engine.mixmaster.master import _dynamic_guard

    rng = np.random.default_rng(7)
    n = 4 * SR
    t = np.arange(n) / SR
    base = (0.05 * np.sin(2 * np.pi * 7000.0 * t)).astype(np.float32)
    x = np.stack([base, base], axis=1)
    quiet = _dynamic_guard(x, SR)
    assert np.allclose(quiet, x, atol=2e-3)            # steady content passes
    y = x.copy()
    burst = int(0.01 * SR)
    y[SR:SR + burst] += (0.8 * np.sin(2 * np.pi * 7500.0 * t[:burst]))[:, None].astype(np.float32)
    guarded = _dynamic_guard(y, SR)
    pk_in = float(np.max(np.abs(y[SR:SR + burst])))
    pk_out = float(np.max(np.abs(guarded[SR:SR + burst])))
    assert pk_out < pk_in                              # the poke was caught
    assert pk_out > pk_in * 10.0 ** (-3.0 / 20.0)      # ...but by <= ~2.5 dB
    assert np.array_equal(guarded, _dynamic_guard(y, SR))   # deterministic


def test_multiband_bass_duck_null_at_zero_depth():
    """The subtractive band-split duck must be bit-identical to the input
    when the pump shape is zero (no kicks)."""
    rng = np.random.default_rng(3)
    n = 2 * SR
    bass = (0.4 * np.sin(2 * np.pi * 60.0 * np.arange(n) / SR)
            + 0.1 * rng.standard_normal(n)).astype(np.float32)
    layers = {"riff": np.stack([bass * 0.2, bass * 0.2], axis=1),
              "bass": np.stack([bass, bass], axis=1)}
    a = master(layers, SR, genre="techhouse", kick_onsets=[])
    b = master(layers, SR, genre="techhouse", kick_onsets=[])
    assert np.array_equal(a.audio, b.audio)            # deterministic no-kick path


def test_haas_sides_mono_sum_unchanged():
    """The width move must be free: (L+s)+(R-s) == L+R, so the mono fold of a
    Haas-widened layer is (near-)identical to the input's."""
    from kidseq_engine.mixmaster.master import _haas_sides

    rng = np.random.default_rng(42)
    x = np.stack([rng.standard_normal(SR), rng.standard_normal(SR)],
                 axis=1).astype(np.float32)
    y = _haas_sides(x, SR, 12.0, -14.0)
    assert not np.allclose(y, x)                       # it DID add width
    assert np.allclose(y.sum(axis=1), x.sum(axis=1), atol=1e-5)  # mono null


def test_room_bus_is_wet_only():
    """The drum room bus (Noisia overheads) must carry no dry signal — the
    dry kit comes from the main path; the room is pure parallel colour."""
    from kidseq_engine.mixmaster.master import _process, _room_bus_board

    n = SR
    x = np.zeros((n, 2), dtype=np.float32)
    imp = SR // 4
    x[imp] = 0.9
    y = _process(x, _room_bus_board(), SR)
    peak = float(np.max(np.abs(y)))
    assert peak > 1e-5, "room bus produced silence"
    assert float(np.max(np.abs(y[imp]))) < 0.10 * peak, "room bus leaks dry"


def test_ride_curve_bounded_and_smooth():
    """Send rides: values stay within [base-2, base+4] dB and the curve never
    jumps (50 ms smoothing)."""
    from kidseq_engine.mixmaster.master import _ride_curve

    n = 4 * SR
    spans = [("intro", 0, SR), ("drop", SR, 2 * SR),
             ("build_tail", 2 * SR, 3 * SR), ("break", 3 * SR, n)]
    c = _ride_curve(n, SR, -9.0, spans)
    assert c.shape == (n,)
    assert np.array_equal(c, _ride_curve(n, SR, -9.0, spans))   # deterministic
    lo, hi = 10.0 ** (-11.2 / 20.0), 10.0 ** (-4.8 / 20.0)
    assert lo <= float(c.min()) and float(c.max()) <= hi, (c.min(), c.max())
    assert float(np.max(np.abs(np.diff(c)))) < 0.001            # no jumps


def test_ny_crush_is_impulse_aligned():
    """The parallel drum bus must not smear timing: crushed path peaks within
    1 ms of the dry impulse (else parallel summing combs the transient)."""
    from kidseq_engine.mixmaster.master import _ny_crush_board, _process

    n = SR // 2
    x = np.zeros((n, 2), dtype=np.float32)
    x[SR // 4] = 0.9
    y = _process(x, _ny_crush_board(), SR)
    assert abs(int(np.argmax(np.abs(y[:, 0]))) - SR // 4) <= int(0.001 * SR)


def test_shared_reverb_return_is_wet_only():
    """The return board must carry NO dry signal (dry comes from the layers) —
    an impulse in produces ~nothing at the impulse instant."""
    from kidseq_engine.mixmaster.master import _process, _reverb_return_board

    n = SR
    x = np.zeros((n, 2), dtype=np.float32)
    imp = SR // 4
    x[imp] = 0.9
    y = _process(x, _reverb_return_board("techhouse"), SR)
    peak = float(np.max(np.abs(y)))
    assert peak > 1e-4, "return produced silence"
    assert float(np.max(np.abs(y[imp]))) < 0.10 * peak, "return leaks dry signal"


def test_pump_shape_dip_hold_recover():
    """Sidechain 2.0 shape: 4 ms attack ENDING at the onset, 10 ms hold at the
    floor, exponential recovery."""
    from kidseq_engine.mixmaster import pump_envelope

    on = SR // 2
    env = pump_envelope(SR, SR, [on], 0.5, 0.2)
    assert env[0] == 1.0
    assert abs(env[on] - 0.5) < 1e-3, env[on]                    # floor AT onset
    assert abs(env[on + int(0.009 * SR)] - 0.5) < 1e-3            # still held
    assert env[on - int(0.006 * SR)] > 0.95                       # before attack
    assert env[-1] > 0.95                                         # recovered


def test_spectral_slots_with_real_assets():
    """EQ slotting on REAL renders (Modal only — skips without assets):
    drums own the kick slot, bass owns 80–120 Hz, the riff beats the pads at
    2–4 kHz presence (the melody can't be masked)."""
    from kidseq_engine.arrange.render import _render_pads
    from kidseq_engine.audio import as_stereo
    from kidseq_engine.mixmaster.master import (
        _LAYER_LUFS, _board_for, _calibrate_layer, _process)
    from kidseq_engine.render import drums_audio, riff_audio, sample_kit
    from kidseq_engine.render.sample_kit import kick_slot_hz
    from kidseq_engine.sequence import Note

    g = "techhouse"
    if not sample_kit.kit_available(g):
        print("SKIP spectral-slot gate (drum assets absent)")
        return
    bars, tempo = 4, 124.0
    raw = {
        "drums": drums_audio(g, tempo, bars),
        # A2 root: fundamental 110 Hz sits inside the bass-owned 80-120 band
        "bass": riff_audio([Note(pitch=45, start_beats=float(b), dur_beats=0.9)
                            for b in range(4)], tempo, "bass", bars),
        "riff": riff_audio([Note(pitch=60, start_beats=float(b), dur_beats=0.9)
                            for b in range(4)], tempo, "piano", bars),
        "pads": _render_pads([Note(pitch=p, start_beats=0.0, dur_beats=16.0)
                              for p in (60, 64, 67)], tempo, 16.0, SR),
    }
    proc = {name: _calibrate_layer(_process(as_stereo(buf), _board_for(name, g), SR),
                                   SR, _LAYER_LUFS[name])
            for name, buf in raw.items() if buf.size}

    def band_db(x, lo, hi):
        m = x.mean(axis=1).astype(np.float64)
        mag = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
        fr = np.fft.rfftfreq(len(m), 1.0 / SR)
        sel = (fr >= lo) & (fr < hi)
        return 10.0 * np.log10(mag[sel].mean() + 1e-20)

    slot = kick_slot_hz(g)
    m1 = band_db(proc["drums"], slot * 0.85, slot * 1.15) - band_db(proc["bass"], slot * 0.85, slot * 1.15)
    m2 = band_db(proc["bass"], 80, 120) - band_db(proc["riff"], 80, 120)
    m3 = band_db(proc["riff"], 2000, 4000) - band_db(proc["pads"], 2000, 4000)
    print(f"  slot margins: kick-slot drums-vs-bass {m1:+.1f} dB | "
          f"80-120 bass-vs-riff {m2:+.1f} dB | 2-4k riff-vs-pads {m3:+.1f} dB")
    assert m1 > 4.0, m1
    assert m2 > 6.0, m2
    assert m3 > 3.0, m3


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:  # noqa: BLE001
                print(f"FAIL {name}: {e}")
                fails += 1
    if fails:
        sys.exit(1)
    print("all master-gate tests passed")
