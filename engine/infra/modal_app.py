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
    out += _run("scripts/fetch_appkit.py")  # app-approved samples (UK Garage) from the prod pack
    out += _run("scripts/fetch_extras.py")  # engine-only alt hits + breakbeat fills (R17)
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
              "tests/test_arrange.py", "tests/test_style.py",
              "tests/test_master_gates.py", "tests/test_fx.py"):
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
def render_song(args: str = "") -> bytes:
    """Full arranged song; optional `args` = smoke_song.py CLI args
    (e.g. "examples/cluster_riff.json 3")."""
    _wire_assets()
    _run("smoke_song.py", *args.split())
    return (Path(ENGINE_REMOTE) / "out" / "song.mp3").read_bytes()


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=1800)
def render_variations(nonces: str = "0,1,2,3,4,5") -> dict[str, bytes]:
    """Same riff x several nonces — the per-press variety ear check."""
    _wire_assets()
    out = Path(ENGINE_REMOTE) / "out"
    files: dict[str, bytes] = {}
    for n in [s.strip() for s in nonces.split(",") if s.strip()]:
        _run("smoke_song.py", "examples/sample_riff.json", n)
        files[f"var_{n}.mp3"] = (out / "song.mp3").read_bytes()
    return files


@app.local_entrypoint()
def variations(nonces: str = "0,1,2,3,4,5") -> None:
    files = render_variations.remote(nonces)
    dst_dir = ENGINE_LOCAL / "out"
    dst_dir.mkdir(exist_ok=True)
    for name, data in files.items():
        (dst_dir / name).write_bytes(data)
        print(f"saved {dst_dir / name} ({len(data):,} bytes)")


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
_GENRE_TEMPOS = {"techhouse": 124, "dnb": 172, "garage": 132,
                 "drill": 142, "hiphop": 92, "reggaeton": 96}


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=1800)
def render_showcase_item(riff_file: str, style: str, tempo: int,
                         variation: int) -> bytes:
    """One showcase render: any example riff x genre x variation number."""
    import json

    _wire_assets()
    src = Path(ENGINE_REMOTE) / riff_file
    payload = json.loads(src.read_text(encoding="utf-8"))
    payload["drumStyle"] = style
    payload["tempo"] = tempo
    tmp = Path(ENGINE_REMOTE) / "out" / f"_riff_{style}_{variation}.json"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    _run("smoke_song.py", str(tmp), str(variation))
    return (Path(ENGINE_REMOTE) / "out" / "song.mp3").read_bytes()


# Showcase BATTERIES (R16): each battery is a full 24-track grid (per genre:
# major_a / major_b / minor / percussive) built from its OWN sequencer
# melodies, its own variation-number base (structures never repeat across
# batteries) and its own tempo per genre — folders A..D should sit as far
# apart as the engine can reach. A = the original riff set.
_BATTERIES: dict[str, dict] = {
    "A": {"major": "examples/sample_riff.json",
          "minor": "examples/minor_riff.json",
          "cluster": "examples/cluster_riff.json",
          "base": 1, "step": 7,
          "tempos": {"techhouse": 124, "dnb": 172, "garage": 132,
                     "drill": 142, "hiphop": 92, "reggaeton": 96}},
    # B: syncopated offbeat hook (synth) / falling lament (piano) /
    # two-row machine stabs (synth)
    "B": {"major": "examples/b_major.json",
          "minor": "examples/b_minor.json",
          "cluster": "examples/b_cluster.json",
          "base": 211, "step": 13,
          "tempos": {"techhouse": 128, "dnb": 176, "garage": 130,
                     "drill": 140, "hiphop": 88, "reggaeton": 100}},
    # C: 5-note sparse question/answer w/ octave leap (piano) / wall-to-wall
    # rising 16th arps (strings) / long overlapped seconds (bass — industrial)
    "C": {"major": "examples/c_major.json",
          "minor": "examples/c_minor.json",
          "cluster": "examples/c_cluster.json",
          "base": 421, "step": 17,
          "tempos": {"techhouse": 120, "dnb": 168, "garage": 134,
                     "drill": 144, "hiphop": 96, "reggaeton": 92}},
    # D: scalar climb into long holds (trumpet) / octave-pendulum leaps
    # (synth) / sparse irregular hits + silence (piano, rhythm-forward)
    "D": {"major": "examples/d_major.json",
          "minor": "examples/d_minor.json",
          "cluster": "examples/d_cluster.json",
          "base": 631, "step": 19,
          "tempos": {"techhouse": 126, "dnb": 174, "garage": 128,
                     "drill": 138, "hiphop": 84, "reggaeton": 98}},
}


@app.local_entrypoint()
def showcase(batteries: str = "B,C,D") -> None:
    """The variety demo, per battery: for each genre — two contrasting
    major-key takes, a minor-key take, and a percussive (cluster-riff) take.
    24 files per battery into out/showcase/<LETTER>/. Default renders B,C,D
    (A is the original set — pass --batteries A,B,C,D to re-cut it too)."""
    plan = []   # (riff_file, style, tempo, variation)
    dests = []  # (battery, tag)
    for bat in [b.strip().upper() for b in batteries.split(",") if b.strip()]:
        cfg = _BATTERIES[bat]
        for i, (style, tempo) in enumerate(cfg["tempos"].items()):
            base = cfg["base"] + i * cfg["step"]
            plan += [(cfg["major"], style, tempo, base),
                     (cfg["major"], style, tempo, base + 3),
                     (cfg["minor"], style, tempo, base + 5),
                     (cfg["cluster"], style, tempo, base + 1)]
            dests += [(bat, f"{style}_major_a"), (bat, f"{style}_major_b"),
                      (bat, f"{style}_minor"), (bat, f"{style}_percussive")]
    for (bat, tag), mp3 in zip(dests, render_showcase_item.starmap(plan)):
        dst_dir = ENGINE_LOCAL / "out" / "showcase" / bat
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"{tag}.mp3"
        dst.write_bytes(mp3)
        print(f"saved {dst} ({len(mp3):,} bytes)")


@app.function(image=image, volumes={ASSETS_MOUNT: volume}, timeout=3600)
def render_song_genre(style: str, tempo: int, variation: int = 0) -> bytes:
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
    _run("smoke_song.py", str(tmp), str(variation))
    return (Path(ENGINE_REMOTE) / "out" / "song.mp3").read_bytes()


@app.local_entrypoint()
def songs() -> None:
    """Render the full-song genre sweep (6 tracks, in parallel) and pull local.

    Each genre renders at a DIFFERENT nonce — an all-variation-0 sweep showed
    every genre's single plainest take and hid the per-press spread."""
    dst_dir = ENGINE_LOCAL / "out"
    dst_dir.mkdir(exist_ok=True)
    args = [(style, tempo, 1 + i * 3)
            for i, (style, tempo) in enumerate(_GENRE_TEMPOS.items())]
    for (style, _, nonce), mp3 in zip(args, render_song_genre.starmap(args)):
        dst = dst_dir / f"song_{style}.mp3"
        dst.write_bytes(mp3)
        print(f"saved {dst} (variation={nonce}, {len(mp3):,} bytes)")


@app.local_entrypoint()
def song(args: str = "", name: str = "modal_song.mp3") -> None:
    mp3 = render_song.remote(args)
    dst = ENGINE_LOCAL / "out" / name
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
def drums(styles: str = "garage,reggaeton") -> None:
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
