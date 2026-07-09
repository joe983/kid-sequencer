"""Modal app: the kid-sequencer track engine running on Linux in the cloud.

This is the production home the engine was designed for (see ../NEXT.md — "Local" =
dev/testing only). The Windows-painful pieces (sfizz/VSCO orchestral, VST soft synths)
land here.

Layout:
  image   — debian_slim + engine requirements (+ git for the drumkit fetch)
  volume  "kidseq-assets" — soundfonts + drum one-shots, fetched ONCE by
          populate_assets() (the fetch scripts skip anything already present)
  engine/ — added into the image at /root/engine (code only; assets/ + out/ are
          gitignored locally and excluded here, assets come from the volume)

Every function symlinks /root/engine/assets -> the mounted volume so the engine's
relative asset paths just work.

Usage (from engine/, Windows host):
  set PYTHONUTF8=1
  python -m modal run infra/modal_app.py::populate_assets   # once (~400 MB fetch)
  python -m modal run infra/modal_app.py::run_tests         # full suite remotely
  python -m modal run infra/modal_app.py::smoke             # mastered MP3 -> out/modal_track.mp3
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import modal

ENGINE_LOCAL = Path(__file__).resolve().parents[1]
ENGINE_REMOTE = "/root/engine"
ASSETS_MOUNT = "/assets"

app = modal.App("kidseq-engine")

volume = modal.Volume.from_name("kidseq-assets", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(
        "git",  # fetch_drumkits shallow-clones sample repos
        "portaudio19-dev",  # pyaudio (tinysoundfont dep) builds from source on Linux
    )
    .pip_install_from_requirements(str(ENGINE_LOCAL / "requirements.txt"))
    .add_local_dir(
        str(ENGINE_LOCAL),
        remote_path=ENGINE_REMOTE,
        # code only — big/generated stuff stays out of the image
        ignore=["assets/**", "out/**", ".venv/**", "__pycache__/**", "*.pyc"],
    )
)


def _wire_assets() -> None:
    """Point engine/assets at the persistent volume (engine paths are relative)."""
    import os

    link = Path(ENGINE_REMOTE) / "assets"
    if not link.exists():
        os.symlink(ASSETS_MOUNT, link)


def _run(script: str, *args: str) -> str:
    """Run an engine script in-container, echoing + returning its output."""
    r = subprocess.run(
        [sys.executable, script, *args],
        cwd=ENGINE_REMOTE,
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    print(f"$ python {script} {' '.join(args)}\n{out}")
    if r.returncode != 0:
        raise RuntimeError(f"{script} exited {r.returncode}")
    return out


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=3600)
def populate_assets() -> str:
    """Fetch soundfonts + drum kits onto the persistent volume (idempotent)."""
    _wire_assets()
    for sub in ("soundfonts", "drums"):
        (Path(ASSETS_MOUNT) / sub).mkdir(parents=True, exist_ok=True)
    out = _run("scripts/fetch_soundfonts.py")
    out += _run("scripts/fetch_drumkits.py")
    volume.commit()
    listing = sorted(str(p.relative_to(ASSETS_MOUNT)) for p in Path(ASSETS_MOUNT).rglob("*") if p.is_file())
    print(f"{len(listing)} asset files on volume")
    return out


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=900)
def run_tests() -> str:
    """Run the engine's full test suite on Linux."""
    _wire_assets()
    out = ""
    for t in ("tests/test_sequence.py", "tests/test_master.py", "tests/test_sample_kit.py"):
        out += _run(t)
    return out


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=1800)
def render_track() -> bytes:
    """Full mastered smoke render; returns the MP3 bytes."""
    _wire_assets()
    _run("smoke_track.py")
    return (Path(ENGINE_REMOTE) / "out" / "track.mp3").read_bytes()


@app.local_entrypoint()
def smoke() -> None:
    mp3 = render_track.remote()
    dst = ENGINE_LOCAL / "out" / "modal_track.mp3"
    dst.parent.mkdir(exist_ok=True)
    dst.write_bytes(mp3)
    print(f"saved {dst} ({len(mp3):,} bytes)")
