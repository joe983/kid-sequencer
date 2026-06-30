"""Step 1-2 smoke test: exact riff stem + drums = 'sounds like a track'.

    .venv/Scripts/python smoke_step1.py [examples/sample_riff.json]

Writes out/ : riff_stem.wav (exact riff alone), drums.wav, mix.wav.
A/B riff_stem.wav against the in-mix riff to confirm the hook is preserved.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kidseq_engine.audio import SR, normalize, write_wav  # noqa: E402
from kidseq_engine.render import drums_audio, riff_audio, using_soundfont  # noqa: E402
from kidseq_engine.sequence import parse_sequence, to_midi_bytes  # noqa: E402

BARS = 4


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "examples" / "sample_riff.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    riff = parse_sequence(payload)

    print(f"riff: {len(riff.notes)} notes | key={riff.key} tempo={riff.tempo:g} "
          f"instrument={riff.instrument} drums={riff.drum_style}")
    print("  MIDI pitches:", [n.pitch for n in riff.notes])
    if using_soundfont():
        from kidseq_engine.render.sf_render import library_name
        print(f"  renderer: soundfont | {riff.instrument} -> {library_name(riff.instrument)}")
    else:
        print("  renderer: numpy synth fallback")

    out = Path(__file__).parent / "out"

    # exact riff, rendered verbatim each bar
    riff_buf = normalize(riff_audio(riff.notes, riff.tempo, riff.instrument, BARS), 0.85)
    write_wav(out / "riff_stem.wav", riff_buf * 0.8)

    # drums under it
    if riff.drum_style:
        drums = normalize(drums_audio(riff.drum_style, riff.tempo, BARS), 0.95)
    else:
        drums = np.zeros_like(riff_buf)

    # align lengths and mix
    n = min(len(riff_buf), len(drums)) if riff.drum_style else len(riff_buf)
    mix = riff_buf[:n] * 0.7 + (drums[:n] * 0.9 if riff.drum_style else 0.0)
    mix = normalize(mix, 0.95)

    write_wav(out / "drums.wav", drums)
    write_wav(out / "mix.wav", mix)
    (out / "riff.mid").write_bytes(to_midi_bytes(riff))

    dur = n / SR
    print(f"wrote {out}\\:  riff_stem.wav, drums.wav, mix.wav, riff.mid")
    print(f"  mix duration: {dur:.2f}s ({BARS} bars @ {riff.tempo:g} BPM)")
    expected = BARS * 4 * (60.0 / riff.tempo)  # musical length; +~0.8s release tail is expected
    assert expected - 0.3 <= dur <= expected + 1.5, f"duration {dur:.2f}s != ~{expected:.2f}s (+tail)"
    assert np.max(np.abs(mix)) > 0.1, "mix is silent"
    print(f"  OK: non-silent, {expected:.1f}s music + release tail")


if __name__ == "__main__":
    main()
