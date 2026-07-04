"""Build the app's melodic instrument sample pack (piano first) from CC0 sources.

Mirror of install_app_kits.py but for *pitched* multisamples: each instrument is a
set of one-shot notes at known root pitches; the app pitch-shifts the nearest zone
(playbackRate = targetFreq / root) across the 8 grid rows + key transposition.

Output (parity with drums):
  public/samples/melodic.pack   -> committed, hosting-served, ships to prod
  public/samples/melodic/**     -> dev-only raw WAVs + manifest.json (gitignored,
                                    hosting-ignored); pack is what actually ships.

Conditioning per note: mono-sum, highpass 25 Hz, strip leading silence, trim to a
fixed tail with a fade, peak-normalize to -1 dBFS, resample to 32 kHz, 16-bit PCM.
Each note's true fundamental is auto-detected (autocorrelation) and stored as its
root Hz, so the app never depends on filename/octave-label conventions.

Sources (CC0 / public domain), staged locally under MyMusic/Samples:
  piano = Versilian VCSL "TX81Z / FM Piano" (github.com/sgossner/VCSL, CC0),
          velocity vl2 — a DX/TX-era FM electric piano (Rhodes-ish) that fits
          the app's electronic/urban styles better than an acoustic grand.
          (The acoustic "Grand Piano, Kawai" set is also staged — swap PIANO_SRC
          back to PIANO_GRAND to A/B.)

Re-runnable.
"""

import json
import struct
from pathlib import Path

import numpy as np
from pedalboard import HighpassFilter, Pedalboard
from pedalboard.io import AudioFile

LIB = Path(r"C:\Users\Joe_C\Documents\MyMusic\Samples")
KS = LIB / "Kid-Sequencer samples"
PIANO_GRAND = KS / "VCSL-Grand-Piano-Kawai-CC0"     # acoustic grand (A/B alt)
PIANO_EP = KS / "VCSL-TX81Z-FM-Piano-CC0"           # FM electric piano (in use)
PIANO_SRC = PIANO_EP                                 # <- active source for the piano voice

# public/samples relative to this file (tools/ -> repo root -> public/samples),
# so it writes into whatever worktree the tool lives in.
DST = Path(__file__).resolve().parents[1] / "public" / "samples"
MEL = DST / "melodic"

OUT_SR = 32000           # mono, plenty for a kids' web app; reverb bus adds gloss
TRIM_S = 3.0             # note tail length before fade (covers a whole bar)
FADE_S = 0.22            # fade-out at the trimmed tail
LEAD_DB = -42.0          # strip leading silence up to first sample above this

# instrument -> [source WAV, ...]  (root pitch auto-detected per file)
# 8 zones every ~4 semitones, G#3–C6, covering the grid (C4–C5) + key transposition.
KITS = {
    "piano": [PIANO_SRC / f"{n}.wav" for n in
              ["G#3", "C4", "E4", "G#4", "C5", "E5", "G#5", "C6"]],
}


def _detect_root_hz(mono: np.ndarray, sr: int) -> float:
    """Autocorrelation pitch detection on the post-attack sustain."""
    s = int(0.12 * sr)
    seg = mono[s:s + int(0.4 * sr)].astype(np.float64)
    if len(seg) < sr // 40:
        seg = mono.astype(np.float64)
    seg = seg - seg.mean()
    corr = np.correlate(seg, seg, "full")[len(seg) - 1:]
    lo, hi = int(sr / 1500), int(sr / 50)
    lag = int(np.argmax(corr[lo:hi]) + lo)
    return sr / lag


def _condition(src: Path):
    """Return (audio_mono_float32 @ OUT_SR, root_hz)."""
    with AudioFile(str(src)) as f:
        sr = int(f.samplerate)
        audio = f.read(f.frames)              # (ch, n)
    mono = audio.mean(axis=0)                  # (n,)

    root = _detect_root_hz(mono, sr)

    # highpass rumble (2D for pedalboard, then back to 1D)
    mono = Pedalboard([HighpassFilter(cutoff_frequency_hz=25.0)])(
        mono[np.newaxis, :], sr)[0]

    # strip leading silence
    thresh = 10 ** (LEAD_DB / 20.0)
    above = np.nonzero(np.abs(mono) > thresh)[0]
    if len(above):
        mono = mono[above[0]:]

    # trim tail + fade
    n_keep = int(TRIM_S * sr)
    mono = mono[:n_keep]
    n_fade = min(int(FADE_S * sr), len(mono))
    if n_fade:
        mono[-n_fade:] *= np.linspace(1.0, 0.0, n_fade)

    # resample to OUT_SR (linear; source is already clean)
    if sr != OUT_SR:
        n_out = int(round(len(mono) * OUT_SR / sr))
        mono = np.interp(
            np.linspace(0, len(mono) - 1, n_out),
            np.arange(len(mono)), mono).astype(np.float32)

    # peak-normalize to -1 dBFS (headroom for polyphony)
    peak = float(np.max(np.abs(mono))) or 1.0
    mono = (mono * (0.891 / peak)).astype(np.float32)
    return mono, root


def _write_wav(path: Path, mono: np.ndarray, sr: int) -> None:
    with AudioFile(str(path), "w", samplerate=sr, num_channels=1) as w:
        w.write(mono[np.newaxis, :])


def main() -> None:
    manifest: dict = {}
    for instr, srcs in KITS.items():
        (MEL / instr).mkdir(parents=True, exist_ok=True)
        zones = []
        for i, src in enumerate(srcs):
            assert src.exists(), f"missing: {src}"
            mono, root = _condition(src)
            rel = f"{instr}/{i}.wav"
            _write_wav(MEL / rel, mono, OUT_SR)
            zones.append({"f": rel, "root": round(root, 2), "g": 1.0})
            print(f"  {instr}[{i}] {src.name:28s} -> {root:6.1f} Hz  ({len(mono)/OUT_SR:.2f}s)")
        # sort by root ascending so the app can nearest-match quickly
        zones.sort(key=lambda z: z["root"])
        manifest[instr] = zones
    (MEL / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"installed melodic samples + manifest -> {MEL}")
    _build_pack(manifest)


def _build_pack(manifest: dict) -> None:
    """[4-byte LE headerLen][UTF-8 JSON header][concatenated wav bytes].
    Header = {instr:[{o,n,root,g}]} with o/n slicing the data blob."""
    data = bytearray()
    header: dict = {}
    for instr, zones in manifest.items():
        out = []
        for z in zones:
            raw = (MEL / z["f"]).read_bytes()
            out.append({"o": len(data), "n": len(raw), "root": z["root"], "g": z["g"]})
            data.extend(raw)
        header[instr] = out
    head = json.dumps(header, separators=(",", ":")).encode("utf-8")
    pack = DST / "melodic.pack"
    with open(pack, "wb") as f:
        f.write(struct.pack("<I", len(head)))
        f.write(head)
        f.write(bytes(data))
    print(f"packed -> {pack} ({pack.stat().st_size:,} bytes, {len(data):,} audio)")


if __name__ == "__main__":
    main()
