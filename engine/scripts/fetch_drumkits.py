"""Download + curate the CC0 drum one-shot kits the sample renderer uses.

Samples are large/licensed, so they're NOT committed (engine/.gitignore: assets/).
Run once after cloning, and in the Modal image build:

    ../.venv/Scripts/python fetch_drumkits.py

Sources (all CC0 1.0 — see ../LICENSES.md):
  Boochi44/free-drum-samples      — 3 flavours (hard-trap / bounce / soulful-vintage),
                                    voice-organised one-shots. Derived from the CC0
                                    tidalcycles/sounds-tr808-fischer TR-808 set.
  sgossner/VCSL                   — CC0 orchestral/world sample library; we take just a
                                    few aux-percussion one-shots (cowbell/shaker/woodblock).
  sfzinstruments/virtuosity_drums — CC0 real acoustic kit (drummer Austin McMahon,
                                    Versilian/Karoryfer). Top-velocity one-shots for the
                                    breakbeat-DNA genres (DnB). FLAC → WAV via pedalboard.

Curates a flat layout the renderer maps directly:
  assets/drums/{hard-trap,bounce,soulful}/{kick,snare,clap,hatC,hatO,sub}.wav
  assets/drums/perc/{cowbell,shaker,woodblock}.wav
  assets/drums/virtuosity/{kick,kick-live,snare,rim,hatC,hatO}.wav
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

DRUM_DIR = Path(__file__).resolve().parents[1] / "assets" / "drums"
UA = {"User-Agent": "Mozilla/5.0"}

BOOCHI_REPO = "https://github.com/Boochi44/free-drum-samples.git"
# output flavour -> source kit folder in the Boochi repo
BOOCHI_FLAVOURS = {
    "hard-trap": "01-hard-trap",
    "bounce": "02-bounce",
    "soulful": "03-soulful-vintage",
}
# engine voice -> (Boochi voice subfolder, filename-substring preferences)
BOOCHI_VOICES: dict[str, tuple[str, list[str]]] = {
    "kick":  ("kicks", []),
    "snare": ("snares", []),
    "clap":  ("claps", []),
    "hatC":  ("hi-hats", ["closed", "ch"]),
    "hatO":  ("open-hats", []),
    "sub":   ("808s", ["bass-sub", "sub"]),
}

VCSL_RAW = "https://raw.githubusercontent.com/sgossner/VCSL/master/"
# output name -> path within the VCSL repo
VCSL_PERC = {
    "cowbell":   "Idiophones/Struck Idiophones/Cowbells/Cowbell1_Hit_v2_rr1_Mid.wav",
    "shaker":    "Idiophones/Struck Idiophones/Shaker, Large/LShaker_Hit_rr1_Mid.wav",
    "woodblock": "Idiophones/Struck Idiophones/Woodblock/wood_click2_mp.wav",
}


def _pick(folder: Path, prefs: list[str]) -> Path | None:
    wavs = sorted(folder.glob("*.wav"))
    if not wavs:
        return None
    for pref in prefs:
        for w in wavs:
            if pref in w.name.lower():
                return w
    return wavs[0]


def fetch_boochi() -> None:
    if all((DRUM_DIR / flav).exists() for flav in BOOCHI_FLAVOURS):
        print("Boochi flavours already present, skipping.")
        return
    tmp = Path(tempfile.mkdtemp())
    try:
        print("Boochi44/free-drum-samples (CC0): cloning…")
        subprocess.run(["git", "clone", "--depth", "1", BOOCHI_REPO, str(tmp / "repo")],
                       check=True, capture_output=True)
        base = tmp / "repo" / "drum-samples"
        for flav, srcdir in BOOCHI_FLAVOURS.items():
            out = DRUM_DIR / flav
            out.mkdir(parents=True, exist_ok=True)
            for voice, (sub, prefs) in BOOCHI_VOICES.items():
                src = _pick(base / srcdir / sub, prefs)
                if src is None:
                    print(f"  ! {flav}/{voice}: no wav in {srcdir}/{sub}")
                    continue
                shutil.copy(src, out / f"{voice}.wav")
                print(f"  {flav}/{voice}.wav  <- {src.name}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def fetch_vcsl_perc() -> None:
    out = DRUM_DIR / "perc"
    out.mkdir(parents=True, exist_ok=True)
    for name, relpath in VCSL_PERC.items():
        dst = out / f"{name}.wav"
        if dst.exists():
            print(f"perc/{name}.wav already present, skipping.")
            continue
        url = VCSL_RAW + urllib.parse.quote(relpath)
        print(f"VCSL {name} (CC0): {relpath}")
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            dst.write_bytes(r.read())
        print(f"  -> {dst} ({dst.stat().st_size:,} bytes)")


VIRT_RAW = "https://raw.githubusercontent.com/sfzinstruments/virtuosity_drums/master/"
# output name -> repo path (top-velocity hits; close mics: kickmic for kick,
# snaremic for snare, mid pair for hats)
VIRT_ONESHOTS = {
    "kick":      "Samples/kickmic/kick/kickmic_kick_snoff_vl4_rr4.flac",   # tight, snares off
    "kick-live": "Samples/kickmic/kick/kickmic_kick_snon_vl4_rr4.flac",    # livelier, wire rattle
    "snare":     "Samples/snaremic/snare/snaremic_snare_center_vl36.flac",  # full crack
    "rim":       "Samples/snaremic/snare/snaremic_snare_rimshot_vl12.flac", # layer for attack
    "hatC":      "Samples/mid/hh/mid_hh_closed_vl4_rr4.flac",
    "hatO":      "Samples/mid/hh/mid_hh_open_vl4_rr3.flac",
}


def fetch_virtuosity() -> None:
    """Fetch + decode the Virtuosity Drums one-shots (FLAC) to WAV."""
    out = DRUM_DIR / "virtuosity"
    out.mkdir(parents=True, exist_ok=True)
    todo = {n: p for n, p in VIRT_ONESHOTS.items() if not (out / f"{n}.wav").exists()}
    if not todo:
        print("Virtuosity one-shots already present, skipping.")
        return
    from pedalboard.io import AudioFile  # decodes flac; already an engine dep

    for name, relpath in todo.items():
        url = VIRT_RAW + urllib.parse.quote(relpath)
        print(f"Virtuosity {name} (CC0): {relpath}")
        req = urllib.request.Request(url, headers=UA)
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as tf:
            with urllib.request.urlopen(req, timeout=120) as r:
                tf.write(r.read())
            tmp_flac = Path(tf.name)
        try:
            with AudioFile(str(tmp_flac)) as f:
                sr = int(f.samplerate)
                audio = f.read(f.frames)  # (channels, frames) float32
            dst = out / f"{name}.wav"
            with AudioFile(str(dst), "w", samplerate=sr, num_channels=audio.shape[0]) as w:
                w.write(audio)
            print(f"  -> {dst} ({dst.stat().st_size:,} bytes, {sr} Hz)")
        finally:
            tmp_flac.unlink(missing_ok=True)


def main() -> None:
    DRUM_DIR.mkdir(parents=True, exist_ok=True)
    fetch_boochi()
    fetch_vcsl_perc()
    fetch_virtuosity()
    print("done.")


if __name__ == "__main__":
    main()
