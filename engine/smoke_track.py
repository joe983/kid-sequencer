"""Step 4 smoke test: riff + drums -> mixed & mastered track (MP3 + WAV).

    .venv/Scripts/python smoke_track.py [examples/sample_riff.json]

Writes out/track_master.wav and out/track.mp3, and prints the loudness/true-peak
metrics so the master can be verified by numbers (target ~-9 to -11 LUFS, <=-1 dBTP).
A/B these against a reference commercial kids-EDM track by ear.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kidseq_engine.audio import SR, normalize, write_wav  # noqa: E402
from kidseq_engine.mixmaster import kick_onsets_from_pattern, master  # noqa: E402
from kidseq_engine.mixmaster.master import preset_for, write_mp3  # noqa: E402
from kidseq_engine.render import drums_audio, riff_audio, using_soundfont  # noqa: E402
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402
from kidseq_engine.sequence import parse_sequence  # noqa: E402

BARS = 4


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "examples" / "sample_riff.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    riff = parse_sequence(payload)

    print(f"riff: {len(riff.notes)} notes | key={riff.key} tempo={riff.tempo:g} "
          f"instrument={riff.instrument} drums={riff.drum_style}")
    print(f"  renderer: {'soundfont' if using_soundfont() else 'numpy synth fallback'}")

    # --- render layers (riff is rendered verbatim — the hook is preserved) ---
    layers: dict[str, np.ndarray] = {
        "riff": normalize(riff_audio(riff.notes, riff.tempo, riff.instrument, BARS), 0.9),
    }
    kick_onsets: list[int] = []
    if riff.drum_style and riff.drum_style in DRUM_PATTERNS:
        layers["drums"] = normalize(drums_audio(riff.drum_style, riff.tempo, BARS), 0.95)
        kick_onsets = kick_onsets_from_pattern(DRUM_PATTERNS[riff.drum_style], riff.tempo, BARS, SR)

    preset = preset_for(riff.drum_style)
    print(f"  preset: {riff.drum_style or 'default'} | pump_depth={preset.pump_depth} "
          f"target={preset.lufs_target} LUFS | kicks={len(kick_onsets)}")

    # --- mix + master ---
    res = master(layers, SR, genre=riff.drum_style, kick_onsets=kick_onsets, tempo=riff.tempo)

    out = Path(__file__).parent / "out"
    write_wav(out / "track_master.wav", res.audio)
    write_mp3(out / "track.mp3", res.audio, res.sr)

    dur = res.audio.shape[0] / res.sr
    print(f"\nwrote {out}: track_master.wav, track.mp3")
    print(f"  layers={res.layers}  duration={dur:.2f}s")
    print(f"  integrated loudness: {res.lufs:.2f} LUFS")
    print(f"  true peak:           {res.true_peak_db:.2f} dBTP")

    # numeric master gates (the part that doesn't need ears)
    assert -13.0 <= res.lufs <= -7.0, f"loudness {res.lufs:.2f} LUFS outside sane master range"
    assert res.true_peak_db <= -0.5, f"true peak {res.true_peak_db:.2f} dBTP too hot"
    assert float(np.max(np.abs(res.audio))) > 0.1, "master is silent"
    print("  OK: loudness in range, peak controlled, non-silent")


if __name__ == "__main__":
    main()
