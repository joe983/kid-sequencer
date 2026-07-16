"""R32a — producer sound-source AUDITION contact sheets.

Renders one MP3 "contact sheet" per (producer, section): each candidate
one-shot is peak-matched and played in a numbered slot, preceded by a rising
pitch-ladder marker (slot 1 = lowest pip, slot 2 = next up …) so the owner can
count slots by ear and cross-reference the printed index. Purpose: the owner
listens, notes the slot they want per section, and I lock that as the FINAL
PICK in docs/producer_recipes.md before R32b builds producer_techhouse.pack.

Candidates live in tools/producer_candidates.json (paths relative to the
owner's local sample library LIB — same convention as install_engine_extras).
The first entry per section is the spectral-triage top pick (my proposed
default); the rest are a diverse spread to swap in.

Standalone: numpy + pedalboard + lameenc, NO engine imports (the candidate
file for a genre is read from that genre's manifest with a plain json.load).

    python tools/audition_producer_kits.py [--genre techhouse] [--producers bassled,latin] [--sections kick,clap]
    -> engine/out/audition/<producer>/<producer>__<section>.mp3  (+ .txt index)
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import lameenc
import numpy as np
from pedalboard.io import AudioFile

LIB = Path(r"C:\Users\Joe_C\Documents\MyMusic\Samples")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "engine" / "out" / "audition"


def _candidates_file_for(genre: str) -> Path:
    """Resolve the genre's candidate spreads from its manifest (repo-root
    relative candidates_file). Plain json — keeps this tool engine-import-free."""
    man = json.loads((ROOT / "engine" / "producers" / f"{genre}.json")
                     .read_text(encoding="utf-8"))
    return ROOT / man["candidates_file"]

SR = 44100
SLOT_S = 0.9          # audible window per candidate
GAP_S = 0.22          # silence between slots
MARK_S = 0.07         # pitch-ladder marker length


def _load_mono(path: Path, max_s: float) -> np.ndarray:
    with AudioFile(str(path)) as f:
        sr = int(f.samplerate)
        a = f.read(min(f.frames, int(sr * max_s)))
    x = a.mean(axis=0).astype(np.float32)  # -> mono
    if sr != SR and x.size:
        idx = np.linspace(0.0, x.size - 1.0, int(round(x.size * SR / sr)))
        x = np.interp(idx, np.arange(x.size), x).astype(np.float32)
    peak = float(np.max(np.abs(x))) or 1.0
    x = x * (0.944 / peak)  # -0.5 dBFS peak-match, so slots are level-fair
    return x


def _marker(slot: int) -> np.ndarray:
    """A short sine pip whose pitch rises with the slot number."""
    n = int(MARK_S * SR)
    t = np.arange(n) / SR
    hz = 360.0 + 90.0 * slot
    tone = 0.5 * np.sin(2 * np.pi * hz * t).astype(np.float32)
    env = np.ones(n, dtype=np.float32)
    fade = int(0.01 * SR)
    env[:fade] = np.linspace(0, 1, fade)
    env[-fade:] = np.linspace(1, 0, fade)
    return tone * env


def _fit_slot(x: np.ndarray) -> np.ndarray:
    """Pad/truncate one candidate to the slot window with edge fades."""
    n = int(SLOT_S * SR)
    if x.size >= n:
        x = x[:n].copy()
    else:
        x = np.pad(x, (0, n - x.size))
    fi, fo = int(0.002 * SR), int(0.02 * SR)
    x[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    x[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)
    return x


def _encode_mp3(mono: np.ndarray, dst: Path) -> None:
    enc = lameenc.Encoder()
    enc.set_bit_rate(160)
    enc.set_in_sample_rate(SR)
    enc.set_channels(2)
    enc.set_quality(2)
    peak = float(np.max(np.abs(mono))) or 1.0
    st = np.repeat((mono * (0.98 / peak))[:, None], 2, axis=1)
    pcm = (np.clip(st, -1, 1) * 32767).astype("<i2").tobytes()
    data = enc.encode(pcm) + enc.flush()
    dst.write_bytes(data)


def render_sheet(producer: str, section: str, relpaths: list[str]) -> None:
    gap = np.zeros(int(GAP_S * SR), dtype=np.float32)
    parts: list[np.ndarray] = []
    index: list[str] = [f"{producer} / {section}  ({len(relpaths)} candidates)",
                        "slot = rising pip; higher pip = higher slot number", ""]
    missing = 0
    for i, rel in enumerate(relpaths, 1):
        p = LIB / rel
        if not p.exists():
            index.append(f"  slot {i}: MISSING  {rel}")
            missing += 1
            continue
        try:
            x = _load_mono(p, SLOT_S)
        except Exception as e:  # noqa: BLE001
            index.append(f"  slot {i}: UNREADABLE ({e})  {rel}")
            missing += 1
            continue
        parts.append(_marker(i))
        parts.append(np.zeros(int(0.03 * SR), dtype=np.float32))
        parts.append(_fit_slot(x))
        parts.append(gap)
        index.append(f"  slot {i}: {Path(rel).name}")
    if not parts:
        print(f"  ! {producer}/{section}: no renderable candidates")
        return
    buf = np.concatenate(parts)
    dst_dir = OUT / producer
    dst_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{producer}__{section}"
    _encode_mp3(buf, dst_dir / f"{stem}.mp3")
    (dst_dir / f"{stem}.txt").write_text("\n".join(index), encoding="utf-8")
    tag = f" ({missing} missing)" if missing else ""
    print(f"  {producer}/{section}: {len(parts)//4} slots -> {stem}.mp3{tag}")


def main() -> None:
    args = sys.argv[1:]
    only_prod = only_sec = None
    genre = "techhouse"
    for a in args:
        if a.startswith("--producers"):
            only_prod = set(a.split("=", 1)[1].split(",")) if "=" in a else None
        if a.startswith("--sections"):
            only_sec = set(a.split("=", 1)[1].split(",")) if "=" in a else None
        if a.startswith("--genre="):
            genre = a.split("=", 1)[1]
    # support "--producers x,y" / "--genre g" (space-separated) too
    for i, a in enumerate(args):
        if a == "--producers" and i + 1 < len(args):
            only_prod = set(args[i + 1].split(","))
        if a == "--sections" and i + 1 < len(args):
            only_sec = set(args[i + 1].split(","))
        if a == "--genre" and i + 1 < len(args):
            genre = args[i + 1]

    doc = json.loads(_candidates_file_for(genre).read_text(encoding="utf-8"))
    cand = doc["candidates"]
    print(f"== genre: {genre} ==")
    for producer, sections in cand.items():
        if only_prod and producer not in only_prod:
            continue
        print(f"== {producer} ==")
        for section, relpaths in sections.items():
            if only_sec and section not in only_sec:
                continue
            render_sheet(producer, section, relpaths)
    print(f"\nContact sheets -> {OUT}")


if __name__ == "__main__":
    main()
