"""Copy the collected drum kits into the app's local samples folder + manifest.
Destination is gitignored / excluded from hosting deploys. Re-runnable."""

import json
import shutil
from pathlib import Path

LIB = Path(r"C:\Users\Joe_C\Documents\MyMusic\Samples")
VAULT = LIB / "Drill Samples" / "Jay Cactus - The Vault 2.0"
GREEZE = VAULT / "Jay Cactus - Greeze (UK Drill)"
TRAPL = VAULT / "Jay Cactus - Trap Lordz (Trap)"
SOURCE = VAULT / "Jay Cactus - The Source (Boom Bap)"
CANDY = VAULT / "Jay Cactus - Candy (R&B Drum Kit)"
DNB = LIB / "Kid-Sequencer samples" / "DnB"
HFUNK = LIB / "[VB] Hyperfunk" / "[VB] Hyperfunk" / "Drums"
DHALL = LIB / "musicradar-dancehall-samples" / "Kit C 120bpm" / "Drums" / "Hits"
TR909 = LIB / "Roland-TR-909" / "Roland TR-909"
TR808 = LIB / "Roland TR-808"

DST = Path(r"C:\Users\Joe_C\Documents\kid-sequencer-repo\.claude\worktrees\sess-5efc3f50\public\samples\drums")

# style -> voice -> [(source path, gain, trimMs|None), ...]
KITS = {
    "dnb": {
        "kick":  [(DNB / "VEH1 Soft Kick - 004.wav", 1.0, None),
                  (DNB / "VEH1 Soft Kick - 005.wav", 0.5, None)],
        "snare": [(DNB / "DC_Kit14_170_Snr.wav", 0.85, None)],
        "hatC":  [(DNB / "DC_Kit14_170_Hat.wav", 1.0, 75)],
    },
    "drill": {
        "kick":  [(GREEZE / "Kicks" / "Greeze - Big Kick.wav", 1.0, None)],
        "sub":   [(GREEZE / "808s" / "Greeze - Psycho 808 (C).wav", 0.95, None)],
        "snare": [(GREEZE / "Snares" / "Greeze - Brickz Snare.wav", 0.8, None)],
        "rim":   [(GREEZE / "Rimshots" / "Greeze - Ruckus Rim.wav", 0.55, None)],
        "hatC":  [(TRAPL / "Hi-Hats" / "TrapLordz - Essential Hi-Hat.wav", 0.4, None)],
        "hatO":  [(GREEZE / "Open-Hats" / "Greeze - Classic Open Hat.wav", 0.4, None)],
    },
    # NB no "kick" here: user prefers the app's synthesized techno kick, so the
    # voice falls back to playKick (2026-07-02: "use the kick from the techno
    # beat instead of the 909 kick").
    # clap gets a room send (4th tuple slot) — raw 909 clap read as too dry.
    "techhouse": {
        "clap": [(TR909 / "HANDCLP1.WAV", 0.8, None, 0.4)],
        "hatC": [(TR909 / "HHCD0.WAV", 0.5, None)],
        "hatO": [(TR909 / "HHOD0.WAV", 0.5, None)],
    },
    "hiphop": {
        "kick":  [(SOURCE / "Kicks" / "The Source - Boom Kick (G#).wav", 1.0, None)],
        "snare": [(SOURCE / "Snares" / "The Source - Boom Snare.wav", 0.85, None)],
        "hatC":  [(SOURCE / "Hi-Hats" / "The Source - Bap Hi-Hat.wav", 0.5, None)],
        "hatO":  [(SOURCE / "Open-Hats" / "The Source - Chamber Open Hat.wav", 0.5, None)],
        "rim":   [(SOURCE / "Rimshots" / "The Source - Clean Rim.wav", 0.6, None)],
    },
    # "funk" slot = UK Garage (2026-07-02): Candy kick/snare/rim + 909 hats
    # (garage's house lineage — the 909 hats are period-correct)
    "funk": {
        "kick":  [(CANDY / "Kicks" / "Candy - Chunky Kick (C).wav", 1.0, None)],
        "snare": [(CANDY / "Snares" / "Candy - Hitter Snare.wav", 0.85, None)],
        "rim":   [(CANDY / "Rims" / "Candy - Straight Rim.wav", 0.6, None)],
        "hatC":  [(TR909 / "HHCD0.WAV", 0.5, None)],
        "hatO":  [(TR909 / "HHOD0.WAV", 0.5, None)],
    },
    "reggaeton": {
        "kick":    [(DHALL / "DHitC-Kick01.wav", 1.0, None)],
        "snare":   [(DHALL / "DHitC-Snare01.wav", 0.85, None)],
        "shaker":  [(SOURCE / "Shakers" / "The Source - Straight Shaker.wav", 0.45, None)],
        "cowbell": [(TR808 / "CB" / "CB.WAV", 0.45, None)],
    },
}


def _condition(src: Path, dst: Path) -> None:
    """Copy with mastering-consistency conditioning: peak-normalize to -0.5 dBFS
    and clean sub-rumble below 25 Hz, so every kit sits on the same ruler and
    the manifest gains mean the same thing across packs."""
    import numpy as np
    from pedalboard import HighpassFilter, Pedalboard
    from pedalboard.io import AudioFile

    with AudioFile(str(src)) as f:
        sr = int(f.samplerate)
        audio = f.read(f.frames)  # (ch, n) float32
    audio = Pedalboard([HighpassFilter(cutoff_frequency_hz=25.0)])(audio, sr)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = audio * (0.944 / peak)  # -0.5 dBFS
    with AudioFile(str(dst), "w", samplerate=sr, num_channels=audio.shape[0]) as w:
        w.write(audio.astype(np.float32))


def main() -> None:
    manifest: dict = {}
    for style, voices in KITS.items():
        (DST / style).mkdir(parents=True, exist_ok=True)
        manifest[style] = {}
        for voice, layers in voices.items():
            entries = []
            for i, spec in enumerate(layers):
                src, gain, trim = spec[0], spec[1], spec[2]
                room = spec[3] if len(spec) > 3 else None
                assert src.exists(), f"missing: {src}"
                rel = f"{style}/{voice}{i}.wav"
                _condition(src, DST / rel)
                e = {"f": rel, "g": gain}
                if trim:
                    e["trimMs"] = trim
                if room:
                    e["room"] = room
                entries.append(e)
            manifest[style][voice] = entries
    (DST / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    n = sum(len(ls) for vs in KITS.values() for ls in vs.values())
    print(f"installed {n} samples (peak-matched, rumble-cleaned) + manifest -> {DST}")
    _build_pack(manifest)


def _build_pack(manifest: dict) -> None:
    """Pack all conditioned WAVs + a byte-offset index into a single deployable
    file: [4-byte LE headerLen][UTF-8 JSON header][concatenated wav bytes].
    Header mirrors the manifest but each layer carries {o,n} into the data blob.
    This is what ships to prod (one request, hosting-served); the raw folder is
    dev-only."""
    import struct

    data = bytearray()
    header: dict = {}
    for style, voices in manifest.items():
        header[style] = {}
        for voice, layers in voices.items():
            out_layers = []
            for l in layers:
                raw = (DST / l["f"]).read_bytes()
                entry = {"o": len(data), "n": len(raw), "g": l["g"]}
                if "trimMs" in l:
                    entry["trimMs"] = l["trimMs"]
                if "room" in l:
                    entry["room"] = l["room"]
                data.extend(raw)
                out_layers.append(entry)
            header[style][voice] = out_layers
    head = json.dumps(header, separators=(",", ":")).encode("utf-8")
    pack = DST.parent / "drums.pack"
    with open(pack, "wb") as f:
        f.write(struct.pack("<I", len(head)))
        f.write(head)
        f.write(bytes(data))
    print(f"packed -> {pack} ({pack.stat().st_size:,} bytes, {len(data):,} audio)")


if __name__ == "__main__":
    main()
