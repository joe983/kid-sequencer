"""Build engine/packs/producer_<genre>.pack — the R32 PRODUCER sound sources.

R31 gave every producer of a genre the same drum kit; the owner heard "they all
sound the same". This packs each producer's OWN drum voices (from the owner's
commercial libraries, chosen by spectral triage — see producer_recipes.md) so
the producers are audibly distinct.

Same container as drums.pack / engine_extras.pack:
  [4-byte LE headerLen][UTF-8 JSON header][concatenated wav bytes]
Header schema v1 has THREE sections (R32b fills "drums"; R32c/R32e add
"melodic" smp chops and "fx" one-shots — same pack, rebuilt):
  {"drums":   {"<genre>:<producer>": {voice: {o,n,g}}},
   "melodic": {"<genre>:<producer>": {name:  {o,n,g,root_hz}}},
   "fx":      {"<genre>:<producer>": {kind:  {o,n,g,peak_dbfs}}}}

Everything genre-specific (the producer list, the drum/melodic/fx voice ->
candidate-section maps, per-voice trims, the pack filename, the candidate file)
comes from the genre's manifest at engine/producers/<genre>.json — add a genre
by dropping in a manifest, not by editing this tool. The picks come from the
manifest's candidates_file (first entry per section = the locked FINAL PICK;
owner swaps by reordering that file). Voices are conditioned exactly like
install_engine_extras (peak -0.5 dBFS + 25 Hz HP + optional trim) so pack gains
mean the same across packs. scripts/fetch_producer_kits.py unpacks ->
assets/drums/<genre>/<producer>/.

Run locally (needs the owner's sample library):
    python tools/install_producer_kits.py [--genre techhouse]
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

LIB = Path(r"C:\Users\Joe_C\Documents\MyMusic\Samples")
HERE = Path(__file__).resolve().parent
DST = HERE.parent / "engine" / "packs"

# import the shared manifest loader (lives under engine/)
sys.path.insert(0, str(HERE.parent / "engine"))
from kidseq_engine.producer_manifest import load_manifest  # noqa: E402


def _condition_fx(src: Path, trim_ms: int, peak_dbfs: float) -> bytes:
    """Mono-sum + peak to a breath-level spec + 25 Hz HP + trim/fade. Returns
    conditioned WAV bytes (the peak is baked so fx_shot just loads + fades)."""
    import io

    import numpy as np
    from pedalboard import HighpassFilter, Pedalboard
    from pedalboard.io import AudioFile

    with AudioFile(str(src)) as f:
        sr = int(f.samplerate)
        audio = f.read(f.frames)
    mono = audio.mean(axis=0)[np.newaxis, :]  # (1, n)
    a = Pedalboard([HighpassFilter(cutoff_frequency_hz=25.0)])(mono, sr)
    if trim_ms:
        keep = min(a.shape[1], int(sr * trim_ms / 1000.0))
        a = a[:, :keep].copy()
        fade = min(keep, int(0.03 * sr))
        if fade:
            a[:, -fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    peak = float(np.max(np.abs(a))) or 1.0
    a = a * (10.0 ** (peak_dbfs / 20.0) / peak)
    buf = io.BytesIO()
    with AudioFile(buf, "w", format="wav", samplerate=sr, num_channels=1) as w:
        w.write(a.astype(np.float32))
    return buf.getvalue()


def _detect_root_hz(mono, sr: int) -> float:
    """Autocorrelation pitch of the post-attack sustain (ported from
    install_melodic_kits). Repitch uses this as the sample's natural pitch."""
    import numpy as np
    s = int(0.05 * sr)
    seg = mono[s:s + int(0.4 * sr)].astype(np.float64)
    if len(seg) < sr // 40:
        seg = mono.astype(np.float64)
    seg = seg - seg.mean()
    corr = np.correlate(seg, seg, "full")[len(seg) - 1:]
    lo, hi = int(sr / 1500), int(sr / 50)
    if hi <= lo or hi >= len(corr):
        return 220.0
    lag = int(np.argmax(corr[lo:hi]) + lo)
    return sr / lag if lag else 220.0


def _condition_melodic(src: Path, trim_ms: int) -> tuple[bytes, float]:
    """Mono-sum + peak -0.5 dBFS + 25 Hz HP + trim; returns (wav bytes,
    detected root_hz). Mono because smp_render repitches a mono one-shot."""
    import io

    import numpy as np
    from pedalboard import HighpassFilter, Pedalboard
    from pedalboard.io import AudioFile

    with AudioFile(str(src)) as f:
        sr = int(f.samplerate)
        audio = f.read(f.frames)  # (ch, n)
    mono = audio.mean(axis=0)
    root = _detect_root_hz(mono, sr)
    a = Pedalboard([HighpassFilter(cutoff_frequency_hz=25.0)])(
        mono[np.newaxis, :], sr)  # (1, n)
    if trim_ms:
        keep = min(a.shape[1], int(sr * trim_ms / 1000.0))
        a = a[:, :keep].copy()
        fade = min(keep, int(0.02 * sr))
        if fade:
            a[:, -fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    peak = float(np.max(np.abs(a))) or 1.0
    a = a * (0.944 / peak)
    buf = io.BytesIO()
    with AudioFile(buf, "w", format="wav", samplerate=sr, num_channels=1) as w:
        w.write(a.astype(np.float32))
    return buf.getvalue(), root


def _condition(src: Path, trim_ms: int | None = None) -> bytes:
    """Peak-normalize to -0.5 dBFS + clean sub-rumble below 25 Hz (+ optional
    trim with a 20 ms tail fade); return the conditioned WAV bytes. Mirrors
    tools/install_engine_extras.py so gains mean the same across packs."""
    import io

    import numpy as np
    from pedalboard import HighpassFilter, Pedalboard
    from pedalboard.io import AudioFile

    with AudioFile(str(src)) as f:
        sr = int(f.samplerate)
        audio = f.read(f.frames)  # (ch, n) float32
    if trim_ms:
        keep = min(audio.shape[1], int(sr * trim_ms / 1000.0))
        audio = audio[:, :keep].copy()
        fade = min(keep, int(0.020 * sr))
        if fade:
            audio[:, -fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    audio = Pedalboard([HighpassFilter(cutoff_frequency_hz=25.0)])(audio, sr)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = audio * (0.944 / peak)  # -0.5 dBFS
    buf = io.BytesIO()
    with AudioFile(buf, "w", format="wav", samplerate=sr,
                   num_channels=audio.shape[0]) as w:
        w.write(audio.astype(np.float32))
    return buf.getvalue()


def main(genre: str = "techhouse") -> None:
    man = load_manifest(genre)
    cand = man.candidates()
    trims = man.trims_ms
    DST.mkdir(parents=True, exist_ok=True)
    data = bytearray()
    header: dict = {"drums": {}, "melodic": {}, "fx": {}}
    n_files = 0
    for producer, voices in man.drum_map.items():
        key = f"{genre}:{producer}"
        header["drums"][key] = {}
        for voice, section in voices.items():
            cands = cand.get(producer, {}).get(section)
            assert cands, f"no candidates for {producer}/{section}"
            rel = cands[0]  # locked FINAL PICK
            src = LIB / rel
            assert src.exists(), f"missing pick: {src}"
            raw = _condition(src, trims.get((producer, voice)))
            header["drums"][key][voice] = {"o": len(data), "n": len(raw), "g": 1.0}
            data.extend(raw)
            n_files += 1
            print(f"  {producer:10s} {voice:7s} <- {Path(rel).name}")
    # ---- MELODIC section (R32c): smp chops/stabs/chants + root_hz ----------
    for producer, voices in man.melodic_map.items():
        key = f"{genre}:{producer}"
        header["melodic"][key] = {}
        for name, section in voices.items():
            cands = cand.get(producer, {}).get(section)
            assert cands, f"no candidates for {producer}/{section} (melodic)"
            rel = cands[0]
            src = LIB / rel
            assert src.exists(), f"missing melodic pick: {src}"
            raw, root = _condition_melodic(src, man.melodic_trim_ms)
            header["melodic"][key][name] = {"o": len(data), "n": len(raw),
                                            "g": 1.0, "root_hz": round(root, 2)}
            data.extend(raw)
            n_files += 1
            print(f"  [mel] {producer:10s} {name:9s} <- {Path(rel).name}  "
                  f"root={root:.1f}Hz")
    # ---- FX section (R32e): sampled candy one-shots + baked peak_dbfs -------
    for producer, kinds in man.fx_map.items():
        key = f"{genre}:{producer}"
        header["fx"][key] = {}
        for kind, section in kinds.items():
            cands = cand.get(producer, {}).get(section)
            assert cands, f"no candidates for {producer}/{section} (fx)"
            rel = cands[0]
            src = LIB / rel
            assert src.exists(), f"missing fx pick: {src}"
            raw = _condition_fx(src, man.fx_trim_ms, man.fx_peak_dbfs)
            header["fx"][key][kind] = {"o": len(data), "n": len(raw), "g": 1.0,
                                       "peak_dbfs": man.fx_peak_dbfs}
            data.extend(raw)
            n_files += 1
            print(f"  [fx]  {producer:10s} {kind:12s} <- {Path(rel).name}")
    head = json.dumps(header, separators=(",", ":")).encode("utf-8")
    pack = DST / man.pack
    with open(pack, "wb") as f:
        f.write(struct.pack("<I", len(head)))
        f.write(head)
        f.write(bytes(data))
    n_drum = sum(len(v) for v in header["drums"].values())
    n_mel = sum(len(v) for v in header["melodic"].values())
    n_fx = sum(len(v) for v in header["fx"].values())
    print(f"\npacked {n_drum} drum + {n_mel} melodic + {n_fx} fx ({n_files} total) "
          f"-> {pack} ({pack.stat().st_size:,} bytes, {len(data):,} audio)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--genre", default="techhouse",
                    help="which genre's manifest to build (engine/producers/<genre>.json)")
    main(ap.parse_args().genre)
