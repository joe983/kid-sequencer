"""Unpack the app's approved drum samples into engine assets.

The live sequencer app plays `public/samples/drums.pack` — the owner-approved
TR-909/Candy/etc. library. The AI track engine should reuse those exact samples
so an AI track's drums match what the kid hears on play (see the
`feedback-engine-drums-reuse-app` note), NOT a bespoke CC0 kit.

This extracts the genres we've repointed at the app kit into
`assets/drums/<genre>/<voice>.wav`. Each pack layer is already a complete
conditioned WAV (peak-matched + rumble-cleaned at build time), so we just slice
the bytes out — no decode, stdlib only.

Pack format: [4-byte LE headerLen][UTF-8 JSON header][concatenated wav bytes],
header = {style:{voice:[{o,n,g,...}]}} where o/n slice the data section.

Source order: the local repo copy (dev) → the prod hosting URL (Modal, where the
repo's public/ folder isn't in the image). The prod pack may still carry the
legacy "funk" key for UK Garage; we accept either.

    python scripts/fetch_appkit.py [--force]
"""

from __future__ import annotations

import json
import struct
import sys
import urllib.request
from pathlib import Path

# Genres whose engine kit reuses the app pack -> which app-pack style key feeds it.
# UK Garage is "garage" post-2026-07-10 but older packs shipped it as "funk".
APPKIT_GENRES = {"garage": ("garage", "funk")}

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


def main() -> None:
    force = "--force" in sys.argv[1:]
    written = 0

    def _have(genre: str, kit: dict) -> bool:
        return all((DRUM_DIR / genre / f"{v}.wav").exists() for v in kit)

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
        if not force and _have(genre, kit):
            print(f"= {genre}: already present ({len(kit)} voices)")
            continue
        (DRUM_DIR / genre).mkdir(parents=True, exist_ok=True)
        for voice, layers in kit.items():
            if not layers:
                continue
            layer = layers[0]  # one sample per voice for these kits
            wav = pack[data_base + layer["o"] : data_base + layer["o"] + layer["n"]]
            (DRUM_DIR / genre / f"{voice}.wav").write_bytes(wav)
            written += 1
        print(f"+ {genre}: wrote {len(kit)} voices from app pack")

    print(f"fetch_appkit: {written} wav(s) written -> {DRUM_DIR}")


if __name__ == "__main__":
    main()
