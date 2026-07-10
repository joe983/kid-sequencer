"""Drums-only audition for one genre — judge the KIT without the melody on top.

    python render_drums_audition.py <style> [bpm] [bars]

8 bars of the genre's pattern through the real per-genre master chain (silent
riff layer keeps master() honest). Writes out/<style>_drums_<bpm>.mp3.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kidseq_engine.audio import SR, normalize  # noqa: E402
from kidseq_engine.mixmaster import kick_onsets_from_pattern, master  # noqa: E402
from kidseq_engine.mixmaster.master import write_mp3  # noqa: E402
from kidseq_engine.render import drum_source, drums_audio  # noqa: E402
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402

_DEFAULT_BPM = {"techhouse": 124, "dnb": 172, "funk": 132, "drill": 142,
                "hiphop": 92, "reggaeton": 96}


def main() -> None:
    style = sys.argv[1] if len(sys.argv) > 1 else "reggaeton"
    bpm = float(sys.argv[2]) if len(sys.argv) > 2 else float(_DEFAULT_BPM.get(style, 120))
    bars = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    assert style in DRUM_PATTERNS, f"unknown style {style!r}"

    src = drum_source(style)
    drums = normalize(drums_audio(style, bpm, bars), 0.95)
    kicks = kick_onsets_from_pattern(DRUM_PATTERNS[style], bpm, bars, SR, style=style)
    layers = {"riff": np.zeros_like(drums), "drums": drums}
    res = master(layers, SR, genre=style, kick_onsets=kicks, tempo=bpm)

    out = Path(__file__).parent / "out" / f"{style}_drums_{bpm:g}.mp3"
    write_mp3(out, res.audio, res.sr)
    print(f"wrote {out}")
    print(f"  {bars} bars @ {bpm:g} BPM  drums={src}  "
          f"LUFS={res.lufs:.2f}  TP={res.true_peak_db:.2f} dBTP")
    assert float(np.max(np.abs(res.audio))) > 0.1, "render is silent"


if __name__ == "__main__":
    main()
