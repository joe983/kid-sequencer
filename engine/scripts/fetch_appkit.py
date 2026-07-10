"""Unpack the app's approved drum samples into engine assets — ALL genres.

The live sequencer app plays `public/samples/drums.pack` — the owner-approved
TR-909/Candy/Greeze/etc. library. The AI track engine reuses those exact
samples so an AI track's drums match what the kid hears on play (see the
`feedback-engine-drums-reuse-app` note), NOT bespoke CC0 kits.

Extraction rules:
  * every genre in APPKIT_GENRES -> assets/drums/<genre>/<voice>[.N].wav
    (layer 0 = `<voice>.wav`, extra layers = `<voice>.1.wav`, ... — the dnb
    kick is 2 layers; the engine's KITS lists mirror this)
  * a layer with `trimMs` in the pack header (dnb hatC = 75 ms) is trimmed at
    unpack time with a 20 ms fade — the engine plays one-shots whole, and the
    app's trim is part of the approved sound
  * `kit.json` per genre records the pack's per-layer gain/trim/room so a
    pack-gain drift is visible against the hardcoded KITS gains

Pack format: [4-byte LE headerLen][UTF-8 JSON header][concatenated wav bytes],
header = {style:{voice:[{o,n,g,trimMs?,room?}]}} where o/n slice the data.

Source order: local repo copy (dev) -> prod hosting URL (Modal, where the
repo's public/ folder isn't in the image). Old packs shipped UK Garage under
the legacy "funk" key; both are accepted.

    python scripts/fetch_appkit.py [--force]
"""

from __future__ import annotations

import json
import struct
import sys
import urllib.request
from pathlib import Path

# genre -> acceptable pack style keys (first match wins)
APPKIT_GENRES: dict[str, tuple[str, ...]] = {
    "garage": ("garage", "funk"),   # renamed 2026-07-10; old packs say "funk"
    "dnb": ("dnb",),
    "drill": ("drill",),
    "hiphop": ("hiphop",),
    "reggaeton": ("reggaeton",),
    "techhouse": ("techhouse",),    # clap/hats only — app uses a synth kick
}

APP_PACK_URL = "https://kid-sequencer.web.app/samples/drums.pack"
DRUM_DIR = Path(__file__).resolve().parents[1] / "assets" / "drums"
# scripts/ -> engine/ -> repo root -> public/samples/drums.pack
LOCAL_PACK = Path(__file__).resolve().parents[2] / "public" / "samples" / "drums.pack"


def _read_pack() -> bytes:
    if LOCAL_PACK.exists():
        print(f"using local pack {LOCAL_PACK}")
        return LOCAL_PACK.read_bytes()
    print(f"fetching pack {APP_PACK_URL}")
    with urllib.request.urlopen(APP_PACK_URL, timeout=60) as r:  # noqa: S310
        return r.read()


def _parse(pack: bytes) -> tuple[dict, int]:
    head_len = struct.unpack("<I", pack[:4])[0]
    header = json.loads(pack[4 : 4 + head_len].decode("utf-8"))
    return header, 4 + head_len


def _layer_name(voice: str, i: int) -> str:
    return f"{voice}.wav" if i == 0 else f"{voice}.{i}.wav"


def _write_trimmed(wav_bytes: bytes, dst: Path, trim_ms: int) -> None:
    """Trim a WAV to trim_ms with a 20 ms fade-out (the app applies this trim
    at play time; the engine plays one-shots whole, so bake it in)."""
    import io

    import numpy as np
    from pedalboard.io import AudioFile

    with AudioFile(io.BytesIO(wav_bytes)) as f:
        sr = int(f.samplerate)
        audio = f.read(f.frames)  # (ch, n) float32
    keep = min(audio.shape[1], int(sr * trim_ms / 1000.0))
    audio = audio[:, :keep].copy()
    fade = min(keep, int(0.020 * sr))
    if fade:
        audio[:, -fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    with AudioFile(str(dst), "w", samplerate=sr, num_channels=audio.shape[0]) as w:
        w.write(audio)


def main() -> None:
    force = "--force" in sys.argv[1:]
    written = 0
    pack: bytes | None = None
    header: dict = {}
    data_base = 0

    for genre, keys in APPKIT_GENRES.items():
        if pack is None:
            pack = _read_pack()
            header, data_base = _parse(pack)
        kit = next((header[k] for k in keys if k in header), None)
        if not kit:
            print(f"! {genre}: no matching key {keys} in pack — skipped")
            continue
        have_all = all((DRUM_DIR / genre / _layer_name(v, i)).exists()
                       for v, layers in kit.items() for i in range(len(layers)))
        if not force and have_all and (DRUM_DIR / genre / "kit.json").exists():
            print(f"= {genre}: already present ({len(kit)} voices)")
            continue
        (DRUM_DIR / genre).mkdir(parents=True, exist_ok=True)
        meta: dict = {}
        for voice, layers in kit.items():
            meta[voice] = []
            for i, layer in enumerate(layers):
                raw = pack[data_base + layer["o"] : data_base + layer["o"] + layer["n"]]
                dst = DRUM_DIR / genre / _layer_name(voice, i)
                if layer.get("trimMs"):
                    _write_trimmed(raw, dst, int(layer["trimMs"]))
                else:
                    dst.write_bytes(raw)
                entry = {"f": _layer_name(voice, i), "g": layer.get("g", 1.0)}
                if layer.get("trimMs"):
                    entry["trimMs"] = layer["trimMs"]
                if layer.get("room"):
                    entry["room"] = layer["room"]
                meta[voice].append(entry)
                written += 1
        (DRUM_DIR / genre / "kit.json").write_text(
            json.dumps(meta, indent=1), encoding="utf-8")
        print(f"+ {genre}: wrote {sum(len(v) for v in kit.values())} layer(s), "
              f"{len(kit)} voices from app pack")

    print(f"fetch_appkit: {written} wav(s) written -> {DRUM_DIR}")


if __name__ == "__main__":
    main()
