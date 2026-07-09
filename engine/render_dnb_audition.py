"""DnB drum audition: 8 bars of the dnb pattern at 170 BPM, drums only (no riff),
rendered with the Virtuosity acoustic kit through the real dnb master chain.

    .venv/Scripts/python render_dnb_audition.py [bpm]

Writes out/dnb_drums_170.mp3 (filename follows the bpm argument).
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

STYLE = "dnb"
BARS = 8


def main() -> None:
    bpm = float(sys.argv[1]) if len(sys.argv) > 1 else 170.0
    src = drum_source(STYLE)
    assert src == "sample-kit", f"dnb kit not on the sample path (got {src}) — run scripts/fetch_drumkits.py"

    drums = normalize(drums_audio(STYLE, bpm, BARS), 0.95)
    kicks = kick_onsets_from_pattern(DRUM_PATTERNS[STYLE], bpm, BARS, SR, style=STYLE)
    # master() requires a riff layer; a silent one keeps this an honest drums-only render
    layers = {"riff": np.zeros_like(drums), "drums": drums}
    res = master(layers, SR, genre=STYLE, kick_onsets=kicks)

    out = Path(__file__).parent / "out" / f"dnb_drums_{bpm:g}.mp3"
    write_mp3(out, res.audio, res.sr)
    dur = res.audio.shape[0] / res.sr
    print(f"wrote {out}")
    print(f"  {BARS} bars @ {bpm:g} BPM  duration={dur:.2f}s  drums={src}")
    print(f"  LUFS={res.lufs:.2f}  TP={res.true_peak_db:.2f} dBTP")
    assert float(np.max(np.abs(res.audio))) > 0.1, "render is silent"


if __name__ == "__main__":
    main()
