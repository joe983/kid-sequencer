"""Audition aid: render the sample riff with each genre's CC0 sample-kit drums,
mixed & mastered, to out/genre_<style>.mp3. Lets the user A/B the new drums per genre.

    .venv/Scripts/python render_all_genres.py [examples/sample_riff.json]
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
from kidseq_engine.render import drum_source, drums_audio, riff_audio, using_soundfont  # noqa: E402
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402
from kidseq_engine.sequence import parse_sequence  # noqa: E402

BARS = 4
GENRES = ["techhouse", "dnb", "garage", "drill", "hiphop", "reggaeton"]


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "examples" / "sample_riff.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    out = Path(__file__).parent / "out"

    print(f"riff renderer: {'soundfont' if using_soundfont() else 'numpy synth fallback'}")
    for style in GENRES:
        payload["drumStyle"] = style
        riff = parse_sequence(payload)
        riff_buf = normalize(riff_audio(riff.notes, riff.tempo, riff.instrument, BARS), 0.9)
        drum_buf = normalize(drums_audio(style, riff.tempo, BARS), 0.95)
        kicks = kick_onsets_from_pattern(DRUM_PATTERNS[style], riff.tempo, BARS, SR, style=style)
        layers = {"riff": riff_buf, "drums": drum_buf}
        res = master(layers, SR, genre=style, kick_onsets=kicks)
        mp3 = out / f"genre_{style}.mp3"
        write_mp3(mp3, res.audio, res.sr)
        preset = preset_for(style)
        print(f"  {style:10} drums={drum_source(style):11} "
              f"LUFS={res.lufs:6.2f}  TP={res.true_peak_db:6.2f}  pump={preset.pump_depth}  -> {mp3.name}")
        assert float(np.max(np.abs(res.audio))) > 0.1, f"{style} master is silent"

    print(f"\nwrote {len(GENRES)} tracks to {out}/  (genre_<style>.mp3)")


if __name__ == "__main__":
    main()
