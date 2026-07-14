"""Unpack engine_extras.pack — the ENGINE-ONLY drum extras (R17).

The owner's library holds alternate snares/hats and whole breakbeat fills the
app pack never used. tools/install_engine_extras.py packs the curated set into
engine/packs/engine_extras.pack (committed — it rides into the Modal image);
this script unpacks it to assets/drums/<genre>/<name>.wav for
sample_kit.KIT_ALTS / KIT_FILLS.

Pack format: [4-byte LE headerLen][UTF-8 JSON header][concatenated wav bytes],
header = {genre: {name: {o,n,g,bpm?,beats?}}}.

    python scripts/fetch_extras.py [--force]
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

DRUM_DIR = Path(__file__).resolve().parents[1] / "assets" / "drums"
PACK = Path(__file__).resolve().parents[1] / "packs" / "engine_extras.pack"


def main() -> None:
    force = "--force" in sys.argv[1:]
    if not PACK.exists():
        print(f"! extras pack missing ({PACK}) — skipped (KIT_ALTS/KIT_FILLS "
              f"fall back to the default takes)")
        return
    pack = PACK.read_bytes()
    head_len = struct.unpack("<I", pack[:4])[0]
    header = json.loads(pack[4 : 4 + head_len].decode("utf-8"))
    base = 4 + head_len
    written = 0
    for genre, items in header.items():
        (DRUM_DIR / genre).mkdir(parents=True, exist_ok=True)
        meta: dict = {}
        for name, e in items.items():
            dst = DRUM_DIR / genre / f"{name}.wav"
            meta[name] = {k: v for k, v in e.items() if k not in ("o", "n")}
            if dst.exists() and not force:
                continue
            dst.write_bytes(pack[base + e["o"] : base + e["o"] + e["n"]])
            written += 1
        (DRUM_DIR / genre / "extras.json").write_text(
            json.dumps(meta, indent=1), encoding="utf-8")
    print(f"fetch_extras: {written} wav(s) written -> {DRUM_DIR}")


if __name__ == "__main__":
    main()
