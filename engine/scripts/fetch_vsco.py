"""Fetch VSCO 2 CE (CC0) orchestral samples + GENERATE the SFZ instruments.

There is no maintained SFZ port of VSCO 2 CE, but the raw library's filenames carry
pitch/velocity/round-robin metadata, so we build our own mappings: sparse-clone just
the three folders the engine needs, auto-detect every sample's TRUE root
(filename octaves run one octave below real pitch and player tuning drifts —
same lesson as tools/install_melodic_kits.py), and write .sfz files with
pitch_keycenter + per-region tune correction.

Articulations mirror the app's sampled voices (#42):
  trumpet -> Brass/Trumpet/susvib            (11 pitches x v1/v2)
  strings -> Strings/Violin Section/susVib   (11 pitches x v1/v2)
  bells   -> Percussion/Glock                (6 pitches, single dynamic)

Output (gitignored, like all assets):
  assets/sfz/VSCO-2-CE/{trumpet,violins,glock}/samples/*.wav
  assets/sfz/VSCO-2-CE/trumpet/trumpet_susvib.sfz   (etc.)

Run once locally or on Modal:  python scripts/fetch_vsco.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kidseq_engine.audio import read_wav  # noqa: E402

SFZ_DIR = Path(__file__).resolve().parents[1] / "assets" / "sfz" / "VSCO-2-CE"
VSCO_REPO = "https://github.com/sgossner/VSCO-2-CE.git"

# engine instrument -> (repo folder, output folder, sfz name, ampeg_release s, detect mode)
INSTRUMENTS = {
    "trumpet": ("Brass/Trumpet/susvib", "trumpet", "trumpet_susvib.sfz", 0.18, "harmonic"),
    "strings": ("Strings/Violin Section/susVib", "violins", "violins_susvib.sfz", 0.35, "harmonic"),
    "bells": ("Percussion/Glock", "glock", "glock.sfz", 2.5, "bell"),
}

_VEL_RE = re.compile(r"_v(\d+)", re.IGNORECASE)
_NOTE_RE = re.compile(r"_([A-G]#?)(\d)(?=_|\.|$)")
_NOTE_SEMI = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
              "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def _named_midi(path: Path) -> int:
    m = _NOTE_RE.search(path.stem)
    if not m:
        raise RuntimeError(f"no note name in filename: {path.name}")
    return 12 * (int(m.group(2)) + 1) + _NOTE_SEMI[m.group(1)]


def _detect_root_midi(path: Path, mode: str) -> float:
    """True fundamental as float MIDI.

    mode="harmonic" (trumpet/violins): plain autocorrelation on the sustain —
      empirically rock-solid for these libs (uniform +1-octave offset vs the
      filenames, drift < 25 cents) — then an octave sanity-snap against the
      filename prior. (An FFT octave-picker was tried and is WORSE here: strong
      2nd harmonics flip it an octave up on random takes.)
    mode="bell" (glock): autocorrelation fails (inharmonic partials +
      fundamentals above a low-pitch detector's range), but the fundamental is
      the loudest spectral peak and the filenames are at sounding pitch — so
      take the strongest FFT peak near the named note, fall back to named.
    """
    named = _named_midi(path)
    mono = read_wav(path)  # mono float32 @ 44100
    sr = 44100

    if mode == "bell":
        seg = mono[: int(0.5 * sr)].astype(np.float64)
        seg = seg * np.hanning(len(seg))
        mag = np.abs(np.fft.rfft(seg))
        freqs = np.fft.rfftfreq(len(seg), 1.0 / sr)
        base = 440.0 * 2.0 ** ((named - 69) / 12.0)
        sel = np.nonzero((freqs > base * 0.94) & (freqs < base * 1.06))[0]
        if len(sel) < 3:
            return float(named)
        i = sel[np.argmax(mag[sel])]
        # require a real peak (not noise floor): 4x the local median
        window = mag[max(0, i - 200):i + 200]
        if mag[i] < 4.0 * float(np.median(window)):
            return float(named)
        a, b, c = mag[i - 1], mag[i], mag[i + 1]
        denom = a - 2 * b + c
        shift = 0.5 * (a - c) / denom if abs(denom) > 1e-12 else 0.0
        f0 = float(freqs[i] + shift * (freqs[1] - freqs[0]))
        return 69.0 + 12.0 * float(np.log2(f0 / 440.0))

    # harmonic: original autocorrelation (proven on these libraries)
    s = int(0.12 * sr)
    seg = mono[s:s + int(0.4 * sr)].astype(np.float64)
    if len(seg) < sr // 40:
        seg = mono.astype(np.float64)
    seg = seg - seg.mean()
    corr = np.correlate(seg, seg, "full")[len(seg) - 1:]
    lo, hi = int(sr / 1500), int(sr / 50)
    lag = int(np.argmax(corr[lo:hi]) + lo)
    detected = 69.0 + 12.0 * np.log2((sr / lag) / 440.0)
    # sanity-snap: VSCO names run one octave below real pitch; if detection
    # strays > 2 semitones from named+12, trust the prior
    if abs(detected - (named + 12)) > 2.0:
        print(f"    WARN {path.name}: detected {detected:.2f} far from prior "
              f"{named + 12}, using prior")
        return float(named + 12)
    return float(detected)


def _sparse_clone(tmp: Path) -> Path:
    dst = tmp / "vsco"
    subprocess.run(
        ["git", "clone", "--filter=blob:none", "--depth", "1", "--sparse",
         VSCO_REPO, str(dst)],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(dst), "sparse-checkout", "set",
         *(v[0] for v in INSTRUMENTS.values())],
        check=True, capture_output=True, text=True,
    )
    return dst


def _regions(files: list[Path], mode: str) -> list[dict]:
    """One region per (pitch-group, velocity take), key ranges from detected roots."""
    # group files by detected root rounded to nearest semitone
    detected = []
    for f in files:
        m = _detect_root_midi(f, mode)
        vel_m = _VEL_RE.search(f.stem)
        take = int(vel_m.group(1)) if vel_m else 1
        detected.append({"file": f, "midi": m, "take": take})
        print(f"    {f.name}: root={m:.2f} take=v{take}")

    # pitch groups keyed by rounded midi
    groups: dict[int, list[dict]] = {}
    for d in detected:
        groups.setdefault(int(round(d["midi"])), []).append(d)
    centers = sorted(groups)

    regions = []
    for i, c in enumerate(centers):
        lokey = 0 if i == 0 else (centers[i - 1] + c) // 2 + 1
        hikey = 127 if i == len(centers) - 1 else (c + centers[i + 1]) // 2
        takes = sorted(groups[c], key=lambda d: d["take"])
        n = len(takes)
        for j, d in enumerate(takes):
            lovel = 1 if j == 0 else j * 128 // n
            hivel = 127 if j == n - 1 else (j + 1) * 128 // n - 1
            tune = int(round((c - d["midi"]) * 100))  # correct sample to keycenter
            regions.append({
                "sample": d["file"].name, "keycenter": c, "lokey": lokey,
                "hikey": hikey, "lovel": lovel, "hivel": hivel, "tune": tune,
            })
    return regions


def build_instrument(name: str, src_root: Path) -> None:
    folder, out_name, sfz_name, release, mode = INSTRUMENTS[name]
    src = src_root / folder
    out = SFZ_DIR / out_name
    samples = out / "samples"
    samples.mkdir(parents=True, exist_ok=True)

    files = sorted(src.glob("*.wav"))
    if not files:
        raise RuntimeError(f"no wavs found in {src}")
    print(f"  {name}: {len(files)} samples from {folder}")
    copied = []
    for f in files:
        dst = samples / f.name.replace(" ", "_")
        if not dst.exists():
            shutil.copy2(f, dst)
        copied.append(dst)

    lines = [
        f"// generated by scripts/fetch_vsco.py — VSCO 2 CE (CC0), {folder}",
        "// roots auto-detected; filename octaves are NOT trusted (see tool docstring)",
        "<control>",
        "default_path=samples/",
        "<group>",
        f"ampeg_release={release}",
        "amp_veltrack=0",  # takes are timbre layers, not a volume curve
    ]
    for r in _regions(copied, mode):
        lines.append(
            f"<region> sample={r['sample']} pitch_keycenter={r['keycenter']} "
            f"lokey={r['lokey']} hikey={r['hikey']} lovel={r['lovel']} "
            f"hivel={r['hivel']} tune={r['tune']}"
        )
    (out / sfz_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {out / sfz_name} ({len(lines)} lines)")


def main() -> None:
    if "--force" in sys.argv and SFZ_DIR.exists():
        shutil.rmtree(SFZ_DIR)
    done = [n for n, v in INSTRUMENTS.items() if (SFZ_DIR / v[1] / v[2]).exists()]
    if len(done) == len(INSTRUMENTS):
        print("VSCO SFZ instruments already present, skipping.")
        return
    with tempfile.TemporaryDirectory() as td:
        print("sparse-cloning VSCO-2-CE (3 folders)…")
        root = _sparse_clone(Path(td))
        for name in INSTRUMENTS:
            build_instrument(name, root)
    print("done.")


if __name__ == "__main__":
    main()
