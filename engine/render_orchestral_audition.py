"""Audition the VSCO/sfizz orchestral voices: trumpet, strings, bells.

    python render_orchestral_audition.py [bpm]

Renders the sample riff once per instrument through the full master chain ->
out/orch_<instrument>.mp3, printing which renderer served each voice (should be
"sfz(VSCO 2 CE …)" on the Modal build, "soundfont" on plain Windows).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kidseq_engine.audio import SR, normalize, write_wav  # noqa: E402
from kidseq_engine.mixmaster import kick_onsets_from_pattern, master  # noqa: E402
from kidseq_engine.mixmaster.master import write_mp3  # noqa: E402
from kidseq_engine.render import drums_audio, riff_audio, riff_source  # noqa: E402
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402
from kidseq_engine.sequence import parse_sequence  # noqa: E402

BARS = 4
INSTRUMENTS = ("trumpet", "strings", "bells")


def main() -> None:
    payload = json.loads(
        (Path(__file__).parent / "examples" / "sample_riff.json").read_text(encoding="utf-8"))
    if len(sys.argv) > 1:
        payload["tempo"] = float(sys.argv[1])

    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)

    for instrument in INSTRUMENTS:
        payload["instrument"] = instrument
        riff = parse_sequence(payload)
        print(f"{instrument}: renderer={riff_source(instrument)} tempo={riff.tempo:g}")

        layers = {"riff": normalize(riff_audio(riff.notes, riff.tempo, instrument, BARS), 0.9)}
        kick_onsets: list[int] = []
        if riff.drum_style in DRUM_PATTERNS:
            layers["drums"] = normalize(drums_audio(riff.drum_style, riff.tempo, BARS), 0.95)
            kick_onsets = kick_onsets_from_pattern(
                DRUM_PATTERNS[riff.drum_style], riff.tempo, BARS, SR)

        res = master(layers, SR, genre=riff.drum_style, kick_onsets=kick_onsets)
        write_wav(out / f"orch_{instrument}.wav", res.audio)
        write_mp3(out / f"orch_{instrument}.mp3", res.audio, res.sr)
        assert float(np.max(np.abs(res.audio))) > 0.1, f"{instrument} master is silent"
        print(f"  -> orch_{instrument}.mp3  {res.lufs:.2f} LUFS  {res.true_peak_db:.2f} dBTP")


if __name__ == "__main__":
    main()
