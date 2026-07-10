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
        "cmake", "build-essential", "pkg-config", "libsndfile1-dev",  # sfizz build
    )
    # sfizz_render: no Debian package exists, so build the CLI from source.
    # One-time cached layer (~4 min). Renders SFZ instruments (VSCO orchestral).
    .run_commands(
        "git clone --recursive --depth 1 --shallow-submodules "
        "https://github.com/sfztools/sfizz.git /tmp/sfizz-src",
        "cmake -S /tmp/sfizz-src -B /tmp/sfizz-build -DCMAKE_BUILD_TYPE=Release "
        "-DSFIZZ_JACK=OFF -DSFIZZ_LV2=OFF -DSFIZZ_VST=OFF -DSFIZZ_AU=OFF "
        "-DSFIZZ_RENDER=ON -DSFIZZ_DEMOS=OFF -DSFIZZ_BENCHMARKS=OFF -DSFIZZ_TESTS=OFF",
        "cmake --build /tmp/sfizz-build -j 8 --target sfizz_render",
        "find /tmp/sfizz-build -name sfizz_render -type f -exec cp {} /usr/local/bin/ ';'",
        "rm -rf /tmp/sfizz-src /tmp/sfizz-build",
    )
    # Surge XT (GPL, server-side only): soft synth for the synth/bass voices,
    # hosted headless by pedalboard. libasound2 is its one non-default runtime dep.
    .apt_install("libasound2", "curl", "ca-certificates")
    .run_commands(
        "curl -sL -o /tmp/surge.deb https://github.com/surge-synthesizer/releases-xt/"
        "releases/download/1.3.4/surge-xt-linux-x64-1.3.4.deb",
        "apt-get update -q",
        "dpkg -i /tmp/surge.deb || apt-get install -fy -q",
        "dpkg -s surge-xt | grep 'Status: install ok installed'",
        "rm /tmp/surge.deb",
    )
    .pip_install_from_requirements(str(ENGINE_LOCAL / "requirements.txt"))
    .pip_install("fastapi[standard]")  # the production /render web endpoint
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
def populate_assets(force_vsco: bool = False) -> str:
    """Fetch soundfonts + drum kits onto the persistent volume (idempotent)."""
    _wire_assets()
    for sub in ("soundfonts", "drums", "sfz"):
        (Path(ASSETS_MOUNT) / sub).mkdir(parents=True, exist_ok=True)
    out = _run("scripts/fetch_soundfonts.py")
    out += _run("scripts/fetch_drumkits.py")
    out += _run("scripts/fetch_vsco.py", *(["--force"] if force_vsco else []))
    volume.commit()
    listing = sorted(str(p.relative_to(ASSETS_MOUNT)) for p in Path(ASSETS_MOUNT).rglob("*") if p.is_file())
    print(f"{len(listing)} asset files on volume")
    return out


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=900)
def run_tests() -> str:
    """Run the engine's full test suite on Linux."""
    _wire_assets()
    out = ""
    for t in ("tests/test_sequence.py", "tests/test_master.py",
              "tests/test_sample_kit.py", "tests/test_sfz.py", "tests/test_vst.py",
              "tests/test_arrange.py", "tests/test_master_gates.py",
              "tests/test_fx.py"):
        out += _run(t)
    return out


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=1800)
def exec_script(script: str) -> str:
    """Run any engine script remotely (diagnostics / one-offs)."""
    _wire_assets()
    return _run(script)


@app.local_entrypoint()
def probe(script: str) -> None:
    print(exec_script.remote(script))


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


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=1800)
def render_orchestral() -> dict[str, bytes]:
    """Audition renders for the sfizz/VSCO voices; returns {name: mp3 bytes}."""
    _wire_assets()
    _run("render_orchestral_audition.py")
    out = Path(ENGINE_REMOTE) / "out"
    return {p.name: p.read_bytes() for p in out.glob("orch_*.mp3")}


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=1800)
def render_song() -> bytes:
    """Full arranged song (structure + progression + bass + pads); returns MP3."""
    _wire_assets()
    _run("smoke_song.py")
    return (Path(ENGINE_REMOTE) / "out" / "song.mp3").read_bytes()


# ---------------------------------------------------------------------------
# Production endpoint — the app's generateAiTrack Cloud Function POSTs the
# user's sequence here and gets the finished MP3 back. Deployed persistently
# via `modal deploy infra/modal_app.py`. Auth = shared token (Modal Secret
# "kidseq-engine-auth" / Firebase Secret ENGINE_TOKEN — same value).
# ---------------------------------------------------------------------------

@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=900,
              secrets=[modal.Secret.from_name("kidseq-engine-auth")])
@modal.fastapi_endpoint(method="POST")
def render(payload: dict):
    """POST {token, sequence, variation} -> audio/mpeg bytes.

    `sequence` is the app's saved-state shape (riff.notes/key/tempo/instrument/
    drumStyle) — exactly what kidseq_engine.sequence.parse_sequence takes.
    `variation` is the per-press nonce (same sequence + same nonce = same track).
    """
    import json
    import os as _os

    from fastapi.responses import Response

    if not payload or payload.get("token") != _os.environ.get("ENGINE_TOKEN"):
        return Response(status_code=401, content=b"unauthorized")
    seq = payload.get("sequence")
    if not isinstance(seq, dict) or not (seq.get("riff") or {}).get("notes"):
        return Response(status_code=422, content=b"bad sequence")
    variation = int(payload.get("variation") or 0)

    _wire_assets()
    tmp = Path(ENGINE_REMOTE) / "out" / "_request_riff.json"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(json.dumps(seq), encoding="utf-8")
    try:
        _run("smoke_song.py", str(tmp), str(variation))
    except RuntimeError as e:
        print(f"[render] engine failed: {e}")
        return Response(status_code=500, content=b"render failed")
    mp3 = (Path(ENGINE_REMOTE) / "out" / "song.mp3").read_bytes()
    return Response(content=mp3, media_type="audio/mpeg")


# representative tempo per genre for the full-song ear sweep
_GENRE_TEMPOS = {"techhouse": 124, "dnb": 172, "funk": 132,
                 "drill": 142, "hiphop": 92, "reggaeton": 96}


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=3600)
def render_song_genre(style: str, tempo: int) -> bytes:
    """Full arranged song for one genre at its representative tempo."""
    import json

    _wire_assets()
    src = Path(ENGINE_REMOTE) / "examples" / "sample_riff.json"
    payload = json.loads(src.read_text(encoding="utf-8"))
    payload["drumStyle"] = style
    payload["tempo"] = tempo
    tmp = Path(ENGINE_REMOTE) / "out" / f"_riff_{style}.json"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    _run("smoke_song.py", str(tmp))
    return (Path(ENGINE_REMOTE) / "out" / "song.mp3").read_bytes()


@app.local_entrypoint()
def songs() -> None:
    """Render the full-song genre sweep (6 tracks, in parallel) and pull local."""
    dst_dir = ENGINE_LOCAL / "out"
    dst_dir.mkdir(exist_ok=True)
    args = list(_GENRE_TEMPOS.items())
    for (style, _), mp3 in zip(args, render_song_genre.starmap(args)):
        dst = dst_dir / f"song_{style}.mp3"
        dst.write_bytes(mp3)
        print(f"saved {dst} ({len(mp3):,} bytes)")


@app.local_entrypoint()
def song() -> None:
    mp3 = render_song.remote()
    dst = ENGINE_LOCAL / "out" / "modal_song.mp3"
    dst.parent.mkdir(exist_ok=True)
    dst.write_bytes(mp3)
    print(f"saved {dst} ({len(mp3):,} bytes)")


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=900)
def render_drums(style: str, tempo: int) -> bytes:
    """Drums-only audition for one genre (judge the kit, no melody)."""
    _wire_assets()
    _run("render_drums_audition.py", style, str(tempo))
    return (Path(ENGINE_REMOTE) / "out" / f"{style}_drums_{tempo}.mp3").read_bytes()


@app.local_entrypoint()
def drums(styles: str = "funk,reggaeton") -> None:
    """Drums-only auditions for a comma-list of genres -> out/<style>_drums.mp3."""
    dst_dir = ENGINE_LOCAL / "out"
    dst_dir.mkdir(exist_ok=True)
    pairs = [(s, _GENRE_TEMPOS.get(s, 120)) for s in styles.split(",")]
    for (style, _), mp3 in zip(pairs, render_drums.starmap(pairs)):
        dst = dst_dir / f"{style}_drums.mp3"
        dst.write_bytes(mp3)
        print(f"saved {dst} ({len(mp3):,} bytes)")


@app.local_entrypoint()
def orchestral() -> None:
    files = render_orchestral.remote()
    dst_dir = ENGINE_LOCAL / "out"
    dst_dir.mkdir(exist_ok=True)
    for name, data in files.items():
        (dst_dir / name).write_bytes(data)
        print(f"saved {dst_dir / name} ({len(data):,} bytes)")
