"""Extract one-shot vocal/stab CHOPS from the owner's sung-vocal + synth loops.

The quintessential UK garage lead is a pitched-up sung R&B vocal chop — but the
library's sung vocals are multi-second LOOPS, and the pack builder's
`_condition_melodic` head-trims the first 1.4 s from byte 0, so loops can't be
chop sources directly. This slices them into syllable-length one-shots that
triage/audition/install can treat like any other candidate bank.

Method (pure numpy + pedalboard — same stack as triage, no new deps):
smoothed RMS envelope -> onset where the envelope rises through a threshold
relative to the file's peak -> cut until it falls back (or the 1.4 s cap),
keep segments 0.35-1.4 s with enough energy, 5 ms/30 ms edge fades. Segments
are written at the source sample rate; peak-matching happens later at pack
build. Deterministic: sorted sources, ordered slicing, no RNG.

Output goes INSIDE the sample library so LIB-relative candidate paths keep
working for audition/install:
    <LIB>/Kid-Sequencer samples/ukg-chops/<pack>/<loopstem>_cNN.wav

Re-run after a library refresh (idempotent — the staging dir is rebuilt).

    python tools/extract_chops.py [--max-per-file 12]
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
from pathlib import Path

import numpy as np
from pedalboard.io import AudioFile

LIB = Path(os.environ.get("KIDSEQ_SAMPLE_LIB",
                          r"C:\Users\Joe_C\Documents\MyMusic\Samples"))
STAGE = LIB / "Kid-Sequencer samples" / "ukg-chops"

# pack tag -> LIB-relative glob of source loops
SOURCES: dict[str, str] = {
    "orchid": "Cymatics - Orchid Sample Pack/Vocal Loops/*.wav",
    "infinity": "Cymatics- inifity pack/**/Infinity Vocal Collection*/*.wav",
    "gs_vox": "GarageSessionsVol3_GHOSTSYNDICATE_WAV/GS_GSV3_Vox Loops/*.wav",
    "lchz_vox": "LCHZ_samples/LCHZ_vox loops/*.wav",
    "lchz_synth": "LCHZ_samples/LCHZ_synth loops/*.wav",
}

MIN_S, MAX_S = 0.35, 1.4
_ON_DB, _OFF_DB = -30.0, -38.0    # onset/release thresholds rel. file peak
_SMOOTH_S = 0.008
_MIN_GAP_S = 0.10                 # merge onsets closer than this


def _segments(x: np.ndarray, sr: int) -> list[tuple[int, int]]:
    """(start, end) sample spans of energy events in mono signal x."""
    env = np.abs(x)
    win = max(1, int(_SMOOTH_S * sr))
    env = np.convolve(env, np.ones(win) / win, mode="same")
    peak = float(env.max()) or 1.0
    on = peak * (10.0 ** (_ON_DB / 20.0))
    off = peak * (10.0 ** (_OFF_DB / 20.0))
    spans: list[tuple[int, int]] = []
    i, n = 0, len(env)
    while i < n:
        if env[i] >= on:
            start = i
            j = i
            quiet = 0
            max_quiet = int(0.06 * sr)   # 60 ms below release ends the segment
            while j < n and quiet < max_quiet and (j - start) < int(MAX_S * sr):
                quiet = quiet + 1 if env[j] < off else 0
                j += 1
            end = j - quiet
            if spans and (start - spans[-1][1]) < int(_MIN_GAP_S * sr):
                spans[-1] = (spans[-1][0], end)   # merge into previous
            else:
                spans.append((start, end))
            i = j
        else:
            i += 1
    return [(s, e) for s, e in spans if (e - s) >= int(MIN_S * sr)]


def _write_wav(dst: Path, x: np.ndarray, sr: int) -> None:
    buf = io.BytesIO()
    with AudioFile(buf, "w", format="wav", samplerate=sr, num_channels=1) as w:
        w.write(x[np.newaxis, :].astype(np.float32))
    dst.write_bytes(buf.getvalue())


def extract(max_per_file: int) -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    total = 0
    for tag, glob in sorted(SOURCES.items()):
        out_dir = STAGE / tag
        out_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(p for p in LIB.glob(glob)
                       if p.is_file() and p.suffix.lower() in (".wav", ".aif", ".aiff"))
        n_tag = 0
        for src in files:
            try:
                with AudioFile(str(src)) as f:
                    sr = int(f.samplerate)
                    a = f.read(f.frames)
            except Exception:  # noqa: BLE001
                continue
            x = a.mean(axis=0).astype(np.float32)
            for k, (s, e) in enumerate(_segments(x, sr)[:max_per_file]):
                seg = x[s:e].copy()
                fi = min(int(0.005 * sr), seg.size)
                fo = min(int(0.030 * sr), seg.size)
                if fi:
                    seg[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)
                if fo:
                    seg[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)
                stem = src.stem.replace(" ", "_")[:48]
                _write_wav(out_dir / f"{stem}_c{k:02d}.wav", seg, sr)
                n_tag += 1
        total += n_tag
        print(f"  {tag:10s}: {len(files):3d} loops -> {n_tag:4d} chops")
    print(f"\n{total} chops staged -> {STAGE}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-per-file", type=int, default=12)
    extract(ap.parse_args().max_per_file)
