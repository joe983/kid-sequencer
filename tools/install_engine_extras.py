"""Build engine/packs/engine_extras.pack — ENGINE-ONLY drum extras (R17).

The owner supplied a library with alternate snares/hats and whole breakbeat
FILLS that the app pack (one hit per voice) never used ("I fed you a variety
of different drum hits and fills … you aren't using them"). This packs the
curated extras for the AI track engine only — the app's public/samples/
drums.pack is deliberately untouched (owner decision 2026-07-14).

Same container as drums.pack: [4-byte LE headerLen][UTF-8 JSON header]
[concatenated wav bytes]; header = {genre: {name: {o,n,g,bpm?,beats?}}}.
Names are flat one-shots (snare_alt1, hat_alt1, fill1…) — the engine's
sample_kit.KIT_ALTS / KIT_FILLS reference them as <genre>/<name>.wav after
scripts/fetch_extras.py unpacks the pack onto the assets volume.

Conditioning mirrors tools/install_app_kits.py (peak-match -0.5 dBFS +
25 Hz rumble clean) so pack gains mean the same thing across packs.

Run locally (needs the owner's sample library):  python tools/install_engine_extras.py
"""

import json
import struct
from pathlib import Path

LIB = Path(r"C:\Users\Joe_C\Documents\MyMusic\Samples")
DNB = LIB / "Kid-Sequencer samples" / "DnB"

DST = Path(__file__).resolve().parents[1] / "engine" / "packs"

# genre -> name -> (source, gain, {meta}) — fills carry native bpm + their
# musical length in beats (hand-set from the slice lengths; tails excluded)
EXTRAS: dict[str, dict[str, tuple[Path, float, dict]]] = {
    "dnb": {
        "snare_alt1": (DNB / "DC_Kit14_170_Snr2.wav", 0.85, {}),
        "snare_alt2": (DNB / "DC_Kit01_175_Snr3.wav", 0.85, {}),
        "snare_alt3": (DNB / "DC_Kit01_175_Snr4.wav", 0.85, {}),
        "snare_alt4": (DNB / "DC_Kit02_170_Snr.wav", 0.85, {}),
        "hat_alt1":   (DNB / "DC_Kit14_170_Hat2.wav", 1.0, {"trimMs": 75}),
        "fill1": (DNB / "DC_Kit01_175_Fill.wav", 1.0, {"bpm": 175, "beats": 1.5}),
        "fill2": (DNB / "DC_Kit03_175_Fill.wav", 1.0, {"bpm": 175, "beats": 2.0}),
        "fill3": (DNB / "DC_Kit05_170_Fill.wav", 1.0, {"bpm": 170, "beats": 1.5}),
        "fill4": (DNB / "DC_Kit14_170_Fill.wav", 1.0, {"bpm": 170, "beats": 1.5}),
    },
}


def _condition(src: Path, trim_ms: int | None = None) -> bytes:
    """Peak-normalize to -0.5 dBFS + clean sub-rumble below 25 Hz (and apply
    the app-kit hat trim where noted); return the conditioned WAV bytes."""
    import io

    import numpy as np
    from pedalboard import HighpassFilter, Pedalboard
    from pedalboard.io import AudioFile

    with AudioFile(str(src)) as f:
        sr = int(f.samplerate)
        audio = f.read(f.frames)  # (ch, n) float32
    if trim_ms:
        keep = min(audio.shape[1], int(sr * trim_ms / 1000.0))
        audio = audio[:, :keep].copy()
        fade = min(keep, int(0.020 * sr))
        if fade:
            audio[:, -fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    audio = Pedalboard([HighpassFilter(cutoff_frequency_hz=25.0)])(audio, sr)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = audio * (0.944 / peak)  # -0.5 dBFS
    buf = io.BytesIO()
    with AudioFile(buf, "w", format="wav", samplerate=sr,
                   num_channels=audio.shape[0]) as w:
        w.write(audio.astype(np.float32))
    return buf.getvalue()


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    data = bytearray()
    header: dict = {}
    n_files = 0
    for genre, items in EXTRAS.items():
        header[genre] = {}
        for name, (src, gain, meta) in items.items():
            assert src.exists(), f"missing: {src}"
            raw = _condition(src, meta.get("trimMs"))
            entry = {"o": len(data), "n": len(raw), "g": gain}
            for k in ("bpm", "beats"):
                if k in meta:
                    entry[k] = meta[k]
            data.extend(raw)
            header[genre][name] = entry
            n_files += 1
    head = json.dumps(header, separators=(",", ":")).encode("utf-8")
    pack = DST / "engine_extras.pack"
    with open(pack, "wb") as f:
        f.write(struct.pack("<I", len(head)))
        f.write(head)
        f.write(bytes(data))
    print(f"packed {n_files} extras -> {pack} "
          f"({pack.stat().st_size:,} bytes, {len(data):,} audio)")


if __name__ == "__main__":
    main()
