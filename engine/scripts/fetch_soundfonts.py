"""Download the sample libraries the engine renders with.

Soundfonts are large and licensed, so they're NOT committed (see engine/.gitignore).
Run this once after cloning, and in the Modal image build.

    ../.venv/Scripts/python fetch_soundfonts.py

Libraries:
  GeneralUser GS  — GM bank (all instruments + drums). Free for commercial music use.
                    https://github.com/mrbumpy409/GeneralUser-GS
  Salamander Grand Piano V3 — real Yamaha C5, multi-velocity. CC-BY 3.0.
                    https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html
"""

from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

SF_DIR = Path(__file__).resolve().parents[1] / "assets" / "soundfonts"
UA = {"User-Agent": "Mozilla/5.0"}

GENERALUSER_URL = "https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/main/GeneralUser-GS.sf2"
GENERALUSER_DST = SF_DIR / "GeneralUser-GS.sf2"

SALAMANDER_URL = (
    "https://freepats.zenvoid.org/Piano/SalamanderGrandPiano/"
    "SalamanderGrandPiano-SF2-V3+20200602.tar.xz"
)
SALAMANDER_DST = SF_DIR / "SalamanderGrandPiano-V3+20200602.sf2"

# FreePats CC0 dedicated synth/bass (.7z archives). Synth matches the app's square lead.
FREEPATS_7Z = {
    "SynthSquare": "https://github.com/freepats/synth-square/releases/download/2020-05-12/SynthSquare-SF2-20200512.7z",
    "LatelyBass": "https://github.com/freepats/lately-bass/releases/download/2024-04-09/LatelyBass-SF2-20240409.7z",
}


def _download(url: str, dst: Path) -> None:
    print(f"  GET {url}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r, open(dst, "wb") as f:
        f.write(r.read())
    print(f"  -> {dst} ({dst.stat().st_size:,} bytes)")


def fetch_generaluser() -> None:
    if GENERALUSER_DST.exists():
        print("GeneralUser GS already present, skipping.")
        return
    print("GeneralUser GS:")
    _download(GENERALUSER_URL, GENERALUSER_DST)


def fetch_salamander() -> None:
    if SALAMANDER_DST.exists():
        print("Salamander Grand already present, skipping.")
        return
    print("Salamander Grand Piano (296 MiB download, ~1.3 GB extracted):")
    arc = SF_DIR / "salamander.tar.xz"
    _download(SALAMANDER_URL, arc)
    with tarfile.open(arc, "r:xz") as t:
        for m in t.getmembers():
            if m.name.lower().endswith(".sf2"):
                with t.extractfile(m) as src, open(SALAMANDER_DST, "wb") as out:
                    out.write(src.read())
                print(f"  -> {SALAMANDER_DST} ({SALAMANDER_DST.stat().st_size:,} bytes)")
    arc.unlink(missing_ok=True)


def fetch_freepats_synths() -> None:
    import io
    import shutil
    import tempfile

    import py7zr

    for name, url in FREEPATS_7Z.items():
        existing = list(SF_DIR.glob(f"{name}*.sf2"))
        if existing:
            print(f"{name} already present, skipping.")
            continue
        print(f"FreePats {name} (CC0):")
        req = urllib.request.Request(url, headers=UA)
        data = urllib.request.urlopen(req, timeout=120).read()
        tmp = Path(tempfile.mkdtemp())
        with py7zr.SevenZipFile(io.BytesIO(data), "r") as z:
            z.extractall(path=tmp)
        for sf2 in tmp.rglob("*.sf2"):
            dst = SF_DIR / sf2.name
            shutil.copy(sf2, dst)
            print(f"  -> {dst} ({dst.stat().st_size:,} bytes)")
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    SF_DIR.mkdir(parents=True, exist_ok=True)
    fetch_generaluser()
    fetch_salamander()
    fetch_freepats_synths()
    print("done.")


if __name__ == "__main__":
    main()
