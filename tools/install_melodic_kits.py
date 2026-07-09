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
  piano   = Versilian VCSL "Grand Piano, Kawai" (github.com/sgossner/VCSL, CC0),
            velocity v3. (An FM electric piano set, VCSL TX81Z, is also staged —
            swap PIANO_SRC to PIANO_EP to A/B; user chose the acoustic by ear.)
  strings = VSCO 2 Community Edition "Violin Section" susVib v1
            (github.com/sgossner/VSCO-2-CE, CC0) — real section sustains.

All staged files are named by REAL scientific pitch (VCSL/VSCO octave labels
run one octave low and were corrected at staging; roots are still auto-detected
at build so naming is only for humans).

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
PIANO_GRAND = KS / "VCSL-Grand-Piano-Kawai-CC0"     # acoustic grand (in use)
PIANO_EP = KS / "VCSL-TX81Z-FM-Piano-CC0"           # FM electric piano (A/B alt)
PIANO_SRC = PIANO_GRAND                              # <- active source for the piano voice
STRINGS_SRC = KS / "VSCO2-Violin-Section-CC0"       # violin section susVib
TRUMPET_SRC = KS / "VSCO2-Trumpet-CC0"              # trumpet susvib, takes v1 + take2/

# public/samples relative to this file (tools/ -> repo root -> public/samples),
# so it writes into whatever worktree the tool lives in.
DST = Path(__file__).resolve().parents[1] / "public" / "samples"
MEL = DST / "melodic"

OUT_SR = 32000           # mono, plenty for a kids' web app; reverb bus adds gloss
LEAD_DB = -42.0          # strip leading silence up to first sample above this

# instrument -> {files, trim (s of tail kept), fade (s fade-out at the trim)}.
# Root pitch is auto-detected per file. Decaying instruments (piano) use a short
# trim — their own decay does the work. Sustaining instruments (strings) keep a
# longer tail: a whole note at tempo 60 holds ~4 s, so trim must exceed that.
KITS = {
    "piano": {
        # 8 zones every ~4 semitones, G#3–C6, covering the grid (C4–C5) + keys.
        # trim 6.0: a whole note at tempo 40 holds 6 s — 3.0 cut long notes off
        # (user report). The Kawai sustains are 8-25 s long, so real decay all
        # the way; the fade only smooths the last second.
        "files": [PIANO_SRC / f"{n}.wav" for n in
                  ["G#3", "C4", "E4", "G#4", "C5", "E5", "G#5", "C6"]],
        "trim": 6.0, "fade": 1.0,
    },
    "trumpet": {
        # Real trumpet (VSCO susvib) replacing the thin saw+bandpass synth —
        # 9 zones real A3-C6, dual-take stereo blend (same recipe as strings).
        "files": [TRUMPET_SRC / f"{n}.wav" for n in
                  ["A3", "C4", "D#4", "G4", "A#4", "D5", "F5", "A5", "C6"]],
        "blend_take2": TRUMPET_SRC / "take2",
        "trim": 5.0, "fade": 0.8,
    },
    "strings": {
        # 9 zones every ~3-4 semitones, G3–B5 — grid + every key-selector root.
        # Stereo dual-take blend: VSCO's two independent takes panned L/R.
        # Mono-summing a section phase-flattens it into a synth-like pad, and a
        # single take repeats vibrato identically per strike — the two-take
        # stereo blend restores the decorrelated "many players" cue.
        "files": [STRINGS_SRC / f"{n}.wav" for n in
                  ["G3", "B3", "D4", "F#4", "A4", "C5", "E5", "G5", "B5"]],
        "blend_take2": STRINGS_SRC / "take2",   # second take, same filenames
        "trim": 5.0, "fade": 0.8,
    },
    "synth": {
        # Rave lead — RENDERED, not sampled: a synth's "sample" is a render,
        # and rendering per zone gives exact pitch with zero stretch artifacts.
        # "hoover" = the classic Alpha Juno Mentasm/Dominator stab (user picked
        # it over a Reese by ear): PWM pulse snarl + sub-octave saw growl +
        # unison saw, heavy chorus for width, bright ladder LPF with drive,
        # and the signature short pitch-rise into each note.
        # (A "reese" renderer is also available in _RENDERERS to A/B.)
        "render": "hoover",
        "roots": ["G3", "B3", "D4", "F#4", "A4", "C5", "E5", "G5", "B5"],
        "trim": 5.0, "fade": 0.6,
    },
    "bells": {
        # NOT bells any more — the slot is an old-school rave pad (user swap,
        # 2026-07-07). Key stays "bells" for saved-sequence compat; the app
        # plays this kit at GRID pitch (the old x4 octave shift only applies
        # to the synth glockenspiel fallback). Stereo, ~220ms bloom attack.
        "render": "ravepad",
        "roots": ["G3", "B3", "D4", "F#4", "A4", "C5", "E5", "G5", "B5"],
        "trim": 5.0, "fade": 0.8,
    },
}

# note name -> Hz (A4 = 440), for render roots
_NOTE_IDX = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
             "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def _note_hz(name: str) -> float:
    midi = (int(name[-1]) + 1) * 12 + _NOTE_IDX[name[:-1]]
    return 440.0 * 2 ** ((midi - 69) / 12)


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


def _load_prepped(src: Path, trim_s: float, fade_s: float):
    """Load one take: mono-sum, highpass, strip lead silence, trim+fade.
    Returns (mono_float32 @ source sr, sr, root_hz)."""
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
    n_keep = int(trim_s * sr)
    mono = mono[:n_keep]
    n_fade = min(int(fade_s * sr), len(mono))
    if n_fade:
        mono[-n_fade:] *= np.linspace(1.0, 0.0, n_fade)
    return mono.astype(np.float32), sr, root


def _render_reese(f: float, dur: float) -> np.ndarray:
    """Classic Reese at root f: detuned saw pair + centre saw -> ladder LPF
    with drive, sub sine added post-filter. Additive saws (harmonics summed to
    14 kHz) so there is zero aliasing at any zone pitch. Returns mono @ OUT_SR."""
    from pedalboard import LadderFilter

    t = np.arange(int(dur * OUT_SR)) / OUT_SR

    def saw(freq: float, phase: float) -> np.ndarray:
        out = np.zeros_like(t)
        for k in range(1, int(14000 / freq) + 1):
            out += np.sin(2 * np.pi * k * freq * t + k * phase) / k
        return out * (2 / np.pi)

    det = 2 ** (14 / 1200)                       # ±14 cents — the Reese beat
    x = saw(f * det, 0.3) + saw(f / det, 1.7) + 0.5 * saw(f, 0.9)
    x /= 2.5

    cutoff = min(2600.0, max(900.0, 2.6 * f))    # dark low zones, open enough up top
    x = Pedalboard([LadderFilter(mode=LadderFilter.Mode.LPF24,
                                 cutoff_hz=cutoff, resonance=0.2, drive=4.0)])(
        x[np.newaxis, :], OUT_SR)[0]

    x = x + 0.22 * np.sin(2 * np.pi * (f / 2) * t)   # sub weight, post-filter

    n_att = int(0.008 * OUT_SR)                  # fast attack, no click
    x[:n_att] *= np.linspace(0.0, 1.0, n_att)
    return x.astype(np.float32)


def _render_hoover(f: float, dur: float) -> np.ndarray:
    """Classic hoover (Alpha Juno Mentasm/Dominator): PWM pulse snarl at f +
    sub-octave saw growl + unison saw, chorused for the ensemble shimmer,
    through a bright ladder LPF with drive. Short pitch-rise into the note —
    the signature hoover 'zip'. Additive synthesis, so alias-free. Mono @ OUT_SR."""
    from pedalboard import Chorus, LadderFilter

    t = np.arange(int(dur * OUT_SR)) / OUT_SR

    def saw(freq: float, phase_t) -> np.ndarray:
        out = np.zeros_like(t)
        w = 2 * np.pi * freq * t
        for k in range(1, int(14000 / freq) + 1):
            out += np.sin(k * (w + phase_t)) / k
        return out * (2 / np.pi)

    # PWM pulse = difference of two saws with a moving phase offset (the snarl)
    pwm_phase = np.pi * (1.0 + 0.30 * np.sin(2 * np.pi * 2.5 * t))
    pulse = saw(f, 0.0) - saw(f, pwm_phase)

    x = 0.90 * pulse + 0.60 * saw(f * 0.5, 1.7) + 0.50 * saw(f, 0.6)
    x /= 2.0

    # signature zip: first 60ms read at rising speed (~-3 semitones -> pitch)
    n_zip = int(0.060 * OUT_SR)
    speed = np.ones(len(x)); speed[:n_zip] = np.linspace(0.84, 1.0, n_zip)
    pos = np.cumsum(speed); pos -= pos[0]
    x = np.interp(pos, np.arange(len(x)), x)

    cutoff = min(9000.0, max(4500.0, 8 * f))     # bright — hoovers are brash
    x = Pedalboard([
        Chorus(rate_hz=0.9, depth=0.45, centre_delay_ms=6.0, feedback=0.15, mix=0.5),
        LadderFilter(mode=LadderFilter.Mode.LPF24,
                     cutoff_hz=cutoff, resonance=0.15, drive=2.5),
    ])(x[np.newaxis, :].astype(np.float32), OUT_SR)[0]

    n_att = int(0.006 * OUT_SR)
    x[:n_att] *= np.linspace(0.0, 1.0, n_att)
    return x.astype(np.float32)


def _render_ravepad(f: float, dur: float) -> np.ndarray:
    """Old-school rave/trance pad (Juno/JP lineage): 4-saw detuned stack + a
    quiet octave-up shimmer, warm 12dB ladder LPF, chorus. Almost no attack —
    a ~220ms bloom baked into the render. Stereo: each channel is rendered
    with its own oscillator phases and chorus rate (decorrelated width, the
    same lesson as the strings dual-take blend). Additive = alias-free."""
    from pedalboard import Chorus, LadderFilter

    t = np.arange(int(dur * OUT_SR)) / OUT_SR

    def saw(freq: float, phase: float) -> np.ndarray:
        out = np.zeros_like(t)
        w = 2 * np.pi * freq * t
        for k in range(1, int(14000 / freq) + 1):
            out += np.sin(k * w + k * phase) / k
        return out * (2 / np.pi)

    def channel(phases, chorus_rate: float) -> np.ndarray:
        d1, d2 = 2 ** (7 / 1200), 2 ** (14 / 1200)
        x = (saw(f * d1, phases[0]) + saw(f / d1, phases[1]) +
             saw(f * d2, phases[2]) + saw(f / d2, phases[3]) +
             0.25 * saw(f * 2, phases[4]))
        x /= 4.25
        cutoff = min(5000.0, max(2200.0, 4 * f))
        x = Pedalboard([
            LadderFilter(mode=LadderFilter.Mode.LPF12,
                         cutoff_hz=cutoff, resonance=0.1, drive=1.2),
            Chorus(rate_hz=chorus_rate, depth=0.5, centre_delay_ms=7.0,
                   feedback=0.1, mix=0.45),
        ])(x[np.newaxis, :].astype(np.float32), OUT_SR)[0]
        return x

    left = channel([0.3, 1.7, 2.6, 4.1, 5.3], 0.70)
    right = channel([3.9, 0.8, 5.7, 1.9, 2.4], 0.95)

    audio = np.stack([left, right])
    n_att = int(0.22 * OUT_SR)                   # the "not much attack" bloom
    ramp = np.sin(np.linspace(0, np.pi / 2, n_att)) ** 2
    audio[:, :n_att] *= ramp
    return audio.astype(np.float32)


_RENDERERS = {"reese": _render_reese, "hoover": _render_hoover,
              "ravepad": _render_ravepad}


def _resample(x: np.ndarray, sr: int) -> np.ndarray:
    if sr == OUT_SR:
        return x.astype(np.float32)
    n_out = int(round(len(x) * OUT_SR / sr))
    return np.interp(np.linspace(0, len(x) - 1, n_out),
                     np.arange(len(x)), x).astype(np.float32)


def _condition(src: Path, trim_s: float, fade_s: float, take2: Path | None = None):
    """Return (audio (ch, n) float32 @ OUT_SR, root_hz).
    Mono normally; if take2 is given, a stereo L/R blend of the two independent
    takes (decorrelated ensemble — mono-summing kills the section realism)."""
    a, sr, root = _load_prepped(src, trim_s, fade_s)
    a = _resample(a, sr)

    if take2 is not None:
        b, sr2, _ = _load_prepped(take2 / src.name, trim_s, fade_s)
        b = _resample(b, sr2)
        n = min(len(a), len(b))
        a, b = a[:n], b[:n]
        left = 0.80 * a + 0.30 * b
        right = 0.30 * a + 0.80 * b
        audio = np.stack([left, right])
    else:
        audio = a[np.newaxis, :]

    # peak-normalize to -1 dBFS (headroom for polyphony)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = (audio * (0.891 / peak)).astype(np.float32)
    return audio, root


def _write_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    with AudioFile(str(path), "w", samplerate=sr, num_channels=audio.shape[0]) as w:
        w.write(audio)


def main() -> None:
    manifest: dict = {}
    for instr, spec in KITS.items():
        (MEL / instr).mkdir(parents=True, exist_ok=True)
        zones = []
        if "render" in spec:
            renderer = _RENDERERS[spec["render"]]
            for i, name in enumerate(spec["roots"]):
                root = _note_hz(name)
                audio = np.atleast_2d(renderer(root, spec["trim"]))   # (ch, n)
                n_fade = min(int(spec["fade"] * OUT_SR), audio.shape[1])
                if n_fade:
                    audio[:, -n_fade:] *= np.linspace(1.0, 0.0, n_fade)
                peak = float(np.max(np.abs(audio))) or 1.0
                audio = (audio * (0.891 / peak)).astype(np.float32)
                rel = f"{instr}/{i}.wav"
                _write_wav(MEL / rel, audio, OUT_SR)
                zones.append({"f": rel, "root": round(root, 2), "g": 1.0})
                ch = "stereo" if audio.shape[0] == 2 else "mono"
                print(f"  {instr}[{i}] render:{spec['render']} {name:5s} -> {root:6.1f} Hz  ({audio.shape[1]/OUT_SR:.2f}s {ch})")
            manifest[instr] = zones
            continue
        for i, src in enumerate(spec["files"]):
            assert src.exists(), f"missing: {src}"
            audio, root = _condition(src, spec["trim"], spec["fade"],
                                     spec.get("blend_take2"))
            rel = f"{instr}/{i}.wav"
            _write_wav(MEL / rel, audio, OUT_SR)
            zones.append({"f": rel, "root": round(root, 2), "g": 1.0})
            ch = "stereo" if audio.shape[0] == 2 else "mono"
            print(f"  {instr}[{i}] {src.name:28s} -> {root:6.1f} Hz  ({audio.shape[1]/OUT_SR:.2f}s {ch})")
        # sort by root ascending so the app can nearest-match quickly
        zones.sort(key=lambda z: z["root"])
        manifest[instr] = zones
    (MEL / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"installed melodic samples + manifest -> {MEL}")
    _build_pack(manifest)


def _build_pack(manifest: dict) -> None:
    """[4-byte LE headerLen][UTF-8 JSON header][concatenated MP3 bytes].
    Header = {instr:[{o,n,root,g}]} with o/n slicing the data blob.
    Pack payload is MP3 (~6x smaller than WAV — mobile data), decoded by
    decodeAudioData everywhere incl. iOS Safari. The dev folder keeps WAV.
    MP3 adds ~30-50ms encoder-delay silence at the head of every clip; the
    app loader measures it per zone after decode and starts playback past it
    (see the melodic-pack loader in index.html) — do not try to trim it here."""
    import tempfile

    data = bytearray()
    header: dict = {}
    for instr, zones in manifest.items():
        out = []
        for z in zones:
            with AudioFile(str(MEL / z["f"])) as f:
                sr = int(f.samplerate)
                audio = f.read(f.frames)
            kbps = "128" if audio.shape[0] == 2 else "96"
            tmp = Path(tempfile.gettempdir()) / "kidseq_zone.mp3"
            with AudioFile(str(tmp), "w", samplerate=sr,
                           num_channels=audio.shape[0], quality=kbps) as w:
                w.write(audio)
            raw = tmp.read_bytes()
            out.append({"o": len(data), "n": len(raw), "root": z["root"], "g": z["g"]})
            data.extend(raw)
        header[instr] = out
    head = json.dumps(header, separators=(",", ":")).encode("utf-8")
    pack = DST / "melodic.pack"
    with open(pack, "wb") as f:
        f.write(struct.pack("<I", len(head)))
        f.write(head)
        f.write(bytes(data))
    print(f"packed -> {pack} ({pack.stat().st_size:,} bytes, {len(data):,} audio, mp3)")


if __name__ == "__main__":
    main()
