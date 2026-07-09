"""Step 3 smoke test: full arranged song (structure + progression + bass + pads).

    python smoke_song.py [examples/sample_riff.json]

Writes out/song.mp3 (+ song_master.wav) and prints the plan, the chosen
progression, per-layer presence and the master metrics.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kidseq_engine.arrange import choose_progression  # noqa: E402
from kidseq_engine.arrange.render import build_song  # noqa: E402
from kidseq_engine.audio import SR, write_wav  # noqa: E402
from kidseq_engine.mixmaster import master  # noqa: E402
from kidseq_engine.mixmaster.master import write_mp3  # noqa: E402
from kidseq_engine.render import riff_source  # noqa: E402
from kidseq_engine.sequence import parse_sequence  # noqa: E402

_DEGREE = {True: ["i", "ii", "III", "iv", "v", "VI", "VII"],
           False: ["I", "ii", "iii", "IV", "V", "vi", "vii"]}


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path(__file__).parent / "examples" / "sample_riff.json"
    riff = parse_sequence(json.loads(path.read_text(encoding="utf-8")))

    prog = choose_progression(riff)
    names = _DEGREE[riff.key.endswith("m")]
    print(f"riff: {len(riff.notes)} notes | key={riff.key} tempo={riff.tempo:g} "
          f"instrument={riff.instrument} ({riff_source(riff.instrument)}) "
          f"drums={riff.drum_style}")
    print(f"progression: {'–'.join(names[d] for d in prog)}")

    layers, kick_onsets, plan, _ = build_song(riff, SR)
    total_bars = sum(s.bars for s in plan)
    print("plan: " + "  ".join(f"{s.name}[{s.bars}]" for s in plan)
          + f"  = {total_bars} bars ≈ {total_bars * 4 * 60 / riff.tempo:.0f}s")
    print(f"layers: {sorted(layers)} | kicks={len(kick_onsets)}")

    # the intro rides a wetter riff send — "distant" open that dries up at the build
    intro_end = int(plan[0].bars * riff.bar_beats * (60.0 / riff.tempo) * SR)
    res = master(layers, SR, genre=riff.drum_style, kick_onsets=kick_onsets,
                 tempo=riff.tempo, riff_wet_spans=[(0, intro_end)])
    out = Path(__file__).parent / "out"
    write_wav(out / "song_master.wav", res.audio)
    write_mp3(out / "song.mp3", res.audio, res.sr)

    dur = res.audio.shape[0] / res.sr
    print(f"\nwrote {out}: song_master.wav, song.mp3  ({dur:.1f}s)")
    print(f"  integrated loudness: {res.lufs:.2f} LUFS")
    print(f"  true peak:           {res.true_peak_db:.2f} dBTP")
    assert -13.0 <= res.lufs <= -7.0, f"loudness {res.lufs:.2f} outside master range"
    assert res.true_peak_db <= -0.5, f"true peak {res.true_peak_db:.2f} too hot"
    assert float(np.max(np.abs(res.audio))) > 0.1, "master is silent"
    print("  OK: loudness in range, peak controlled, non-silent")


if __name__ == "__main__":
    main()
