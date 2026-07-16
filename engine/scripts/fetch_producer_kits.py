"""Unpack every engine/packs/producer_<genre>.pack — the R32 PRODUCER sound
sources.

tools/install_producer_kits.py packs each producer's own drum voices (and, from
R32c/R32e, smp chops + sampled FX) into engine/packs/producer_<genre>.pack
(committed — they ride into the Modal image). This scans for ALL such packs and
unpacks each onto the assets volume for sample_kit.KITS / smp_render /
fx_samples. Each pack's header keys are already "<genre>:<producer>", so the
destination paths derive per pack with no per-genre logic here:

  drums["<genre>:<producer>"][voice] -> assets/drums/<genre>/<producer>/<voice>.wav
  melodic["<genre>:<producer>"][name] -> assets/melodic_oneshots/<genre>/<producer>/<name>.wav (+ meta.json)
  fx["<genre>:<producer>"][kind]      -> assets/fx_oneshots/<genre>/<producer>/<kind>.wav (+ meta.json)

Pack format: [4-byte LE headerLen][UTF-8 JSON header][concatenated wav bytes].

    python scripts/fetch_producer_kits.py [--force]
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
PACKS_DIR = Path(__file__).resolve().parents[1] / "packs"

# pack section -> (assets subdir, whether to drop a meta.json of the non-o/n keys)
_SECTIONS = {
    "drums": ("drums", False),
    "melodic": ("melodic_oneshots", True),
    "fx": ("fx_oneshots", True),
}


def _unpack(pack_path: Path, force: bool) -> int:
    pack = pack_path.read_bytes()
    head_len = struct.unpack("<I", pack[:4])[0]
    header = json.loads(pack[4 : 4 + head_len].decode("utf-8"))
    base = 4 + head_len
    written = 0
    for section, (subdir, want_meta) in _SECTIONS.items():
        for key, items in header.get(section, {}).items():
            # "<genre>:<producer>" -> <genre>/<producer>
            rel = key.replace(":", "/")
            dst_dir = ASSETS / subdir / rel
            dst_dir.mkdir(parents=True, exist_ok=True)
            meta: dict = {}
            for name, e in items.items():
                dst = dst_dir / f"{name}.wav"
                meta[name] = {k: v for k, v in e.items() if k not in ("o", "n")}
                if dst.exists() and not force:
                    continue
                dst.write_bytes(pack[base + e["o"] : base + e["o"] + e["n"]])
                written += 1
            if want_meta and meta:
                (dst_dir / "meta.json").write_text(
                    json.dumps(meta, indent=1), encoding="utf-8")
    return written


def main() -> None:
    force = "--force" in sys.argv[1:]
    packs = sorted(PACKS_DIR.glob("producer_*.pack"))
    if not packs:
        print(f"! no producer_*.pack in {PACKS_DIR} — skipped (producer kits "
              f"fall back to the base genre kit)")
        return
    written = 0
    for pk in packs:
        n = _unpack(pk, force)
        written += n
        print(f"  {pk.name}: {n} wav(s)")
    print(f"fetch_producer_kits: {written} wav(s) written -> {ASSETS}")


if __name__ == "__main__":
    main()
