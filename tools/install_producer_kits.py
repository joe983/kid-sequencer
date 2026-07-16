"""Build engine/packs/producer_techhouse.pack — the R32 PRODUCER sound sources.

R31 gave every techhouse producer the same drum kit; the owner heard "they all
sound the same". This packs each producer's OWN drum voices (from the owner's
commercial libraries, chosen by spectral triage — see producer_recipes.md) so
the six producers are audibly distinct.

Same container as drums.pack / engine_extras.pack:
  [4-byte LE headerLen][UTF-8 JSON header][concatenated wav bytes]
Header schema v1 has THREE sections (R32b fills "drums"; R32c/R32e add
"melodic" smp chops and "fx" one-shots — same pack, rebuilt):
  {"drums":   {"techhouse:<producer>": {voice: {o,n,g}}},
   "melodic": {"techhouse:<producer>": {name:  {o,n,g,root_hz}}},
   "fx":      {"techhouse:<producer>": {kind:  {o,n,g,peak_dbfs}}}}

The DRUM picks come from tools/producer_candidates.json (first entry per
section = the locked FINAL PICK; owner swaps by reordering that file). Voices
are conditioned exactly like install_engine_extras (peak -0.5 dBFS + 25 Hz HP
+ optional trim) so pack gains mean the same across packs.
scripts/fetch_producer_kits.py unpacks -> assets/drums/techhouse/<producer>/.

Run locally (needs the owner's sample library):
    python tools/install_producer_kits.py
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

LIB = Path(r"C:\Users\Joe_C\Documents\MyMusic\Samples")
HERE = Path(__file__).resolve().parent
CAND = json.loads((HERE / "producer_candidates.json").read_text(encoding="utf-8"))["candidates"]
DST = HERE.parent / "engine" / "packs"

# producer -> engine drum voice -> candidate-map section (first entry = pick).
# Only the producer-SPECIFIC voices are packed; the rest of each kit reuses the
# base techhouse relpaths in sample_kit.KITS (kit_available still covers them).
DRUM_MAP: dict[str, dict[str, str]] = {
    "bassled":   {"kick": "kick", "clap": "clap", "hatC": "hatC", "hatO": "hatO"},
    "discofunk": {"kick": "kick", "clap": "clap", "hatC": "hatC", "hatO": "hatO",
                  "shaker": "shaker"},
    "latin":     {"kick": "kick", "clap": "clap", "hatO": "hatO", "bongo": "bongo",
                  "rim": "rim", "shaker": "shaker", "conga": "perc"},
    "pianohouse": {"kick": "kick_909", "clap": "clap", "hatC": "hatC",
                   "hatO": "hatO", "rim": "rim"},
    "lofi":      {"kick": "kick", "clap": "clap", "hatC": "hatC", "shaker": "foley"},
    "bigroom":   {"kick": "kick", "clap": "clap", "hatC": "hatC", "hatO": "hatO"},
}

# per-(producer, voice) trim in ms where the raw one-shot rings too long for its
# lane (lofi's foley "shaker" is up to ~1.7 s; a 16th-note lane needs it short).
TRIMS: dict[tuple[str, str], int] = {("lofi", "shaker"): 240}

# R32c MELODIC section: producer -> smp voice name -> candidate-map section.
# These become the "melodic" pack section (mono + root_hz), unpacked to
# assets/melodic_oneshots/techhouse/<producer>/<name>.wav for smp_render.
MELODIC_MAP: dict[str, dict[str, str]] = {
    "bassled":   {"chop": "chop"},        # Dom Dolla talkbox-alien vocal chop
    "discofunk": {"funk_stab": "funk_stab"},  # PDM funk one-shot stab
    "latin":     {"chant": "chant"},      # HUGEL cumbia vocal chant
    "pianohouse": {"chop": "chop"},       # MK dub vocal-sample syllable
    "lofi":      {"chop": "chop"},        # Fred voice-note fragment
    "bigroom":   {"rave_shot": "stab_madeon"},  # Guetta supersaw/rave stab
}
MELODIC_TRIM_MS = 1400   # chops repitch per note; cap the ring

# R32e FX section: producer -> fx kind (smp_*) -> candidate-map section. These
# become the "fx" pack section, unpacked to assets/fx_oneshots/techhouse/
# <producer>/<kind>.wav and played by the candy scheduler (breath-level, at
# phrase boundaries) via fx_samples.fx_shot. Producers with no fx candidate
# (pianohouse — MK is restrained) use the genre's synth FX unchanged.
FX_MAP: dict[str, dict[str, str]] = {
    "bassled":   {"smp_slide": "fx_sweep", "smp_rev": "fx_rev"},
    "discofunk": {"smp_tom_zap": "tom_zap"},
    "latin":     {"smp_rev_perk": "fx_rev", "smp_crowd": "crowd", "smp_perk": "perk"},
    "lofi":      {"smp_rev_swell": "fx_rev"},
    "bigroom":   {"smp_riser": "riser", "smp_impact": "impact", "smp_slide": "slide"},
}
FX_PEAK_DBFS = -18.0     # breath-level (Tumay ear-candy law)
FX_TRIM_MS = 1600        # candy-sized; risers/crowd are ~3 s raw


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


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    data = bytearray()
    header: dict = {"drums": {}, "melodic": {}, "fx": {}}
    n_files = 0
    for producer, voices in DRUM_MAP.items():
        key = f"techhouse:{producer}"
        header["drums"][key] = {}
        for voice, section in voices.items():
            cands = CAND.get(producer, {}).get(section)
            assert cands, f"no candidates for {producer}/{section}"
            rel = cands[0]  # locked FINAL PICK
            src = LIB / rel
            assert src.exists(), f"missing pick: {src}"
            raw = _condition(src, TRIMS.get((producer, voice)))
            header["drums"][key][voice] = {"o": len(data), "n": len(raw), "g": 1.0}
            data.extend(raw)
            n_files += 1
            print(f"  {producer:10s} {voice:7s} <- {Path(rel).name}")
    # ---- MELODIC section (R32c): smp chops/stabs/chants + root_hz ----------
    for producer, voices in MELODIC_MAP.items():
        key = f"techhouse:{producer}"
        header["melodic"][key] = {}
        for name, section in voices.items():
            cands = CAND.get(producer, {}).get(section)
            assert cands, f"no candidates for {producer}/{section} (melodic)"
            rel = cands[0]
            src = LIB / rel
            assert src.exists(), f"missing melodic pick: {src}"
            raw, root = _condition_melodic(src, MELODIC_TRIM_MS)
            header["melodic"][key][name] = {"o": len(data), "n": len(raw),
                                            "g": 1.0, "root_hz": round(root, 2)}
            data.extend(raw)
            n_files += 1
            print(f"  [mel] {producer:10s} {name:9s} <- {Path(rel).name}  "
                  f"root={root:.1f}Hz")
    # ---- FX section (R32e): sampled candy one-shots + baked peak_dbfs -------
    for producer, kinds in FX_MAP.items():
        key = f"techhouse:{producer}"
        header["fx"][key] = {}
        for kind, section in kinds.items():
            cands = CAND.get(producer, {}).get(section)
            assert cands, f"no candidates for {producer}/{section} (fx)"
            rel = cands[0]
            src = LIB / rel
            assert src.exists(), f"missing fx pick: {src}"
            raw = _condition_fx(src, FX_TRIM_MS, FX_PEAK_DBFS)
            header["fx"][key][kind] = {"o": len(data), "n": len(raw), "g": 1.0,
                                       "peak_dbfs": FX_PEAK_DBFS}
            data.extend(raw)
            n_files += 1
            print(f"  [fx]  {producer:10s} {kind:12s} <- {Path(rel).name}")
    head = json.dumps(header, separators=(",", ":")).encode("utf-8")
    pack = DST / "producer_techhouse.pack"
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
    main()
