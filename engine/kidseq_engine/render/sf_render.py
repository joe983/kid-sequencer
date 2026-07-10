"""Sample-based rendering via tinysoundfont + dedicated SF2 sample libraries.

Cross-platform, pure-pip (no native FluidSynth), works locally and on Modal/Linux.
The riff notes rendered here are the exact MIDI from sequence.py — the hook is
preserved; only the timbre changes.

Per-instrument soundfont registry (INSTRUMENT_SF) lets each instrument be upgraded
independently. Today: piano = Salamander Grand (real Yamaha C5, CC-BY); the rest =
GeneralUser GS (real GM samples) until dedicated libraries are added. Drums = GM kit
(placeholder until Splice kits land — see plan).

A module-level synth cache loads each soundfont once (Salamander is ~9s to load) and
reuses it across renders.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..audio import SR, seconds_per_beat
from ..sequence import Note

_SF_DIR = Path(__file__).resolve().parents[2] / "assets" / "soundfonts"
GENERALUSER_SF = _SF_DIR / "GeneralUser-GS.sf2"
SALAMANDER_SF = _SF_DIR / "SalamanderGrandPiano-V3+20200602.sf2"
SYNTHSQUARE_SF = _SF_DIR / "SynthSquare 20200512.sf2"   # FreePats, CC0
LATELYBASS_SF = _SF_DIR / "LatelyBass 20240409.sf2"     # FreePats, CC0

# instrument -> (soundfont path, bank, preset). Dedicated libs override GM where present.
# Dedicated/real: piano (Salamander), synth (FreePats square), bass (FreePats Lately Bass).
# Still GM (no clean SF2 alternative; premium path = VSCO via sfizz on Modal):
#   trumpet, strings, bells.
INSTRUMENT_SF: dict[str, tuple[Path, int, int]] = {
    "piano": (SALAMANDER_SF, 0, 0),
    "synth": (SYNTHSQUARE_SF, 0, 0),     # matches the app's square-wave synth
    "bass": (LATELYBASS_SF, 0, 0),       # punchy FM EDM bass
    "trumpet": (GENERALUSER_SF, 0, 56),  # GM Trumpet (sample-based preset, TSF-safe)
    "strings": (GENERALUSER_SF, 0, 48),  # GM String Ensemble 1
    "bells": (GENERALUSER_SF, 0, 9),     # GM Glockenspiel
    "pads": (GENERALUSER_SF, 0, 50),     # GM Synth Strings 1 — arranger pad fallback
    # arranger pad ROLES (genre-authentic keys-family sounds; see arrange/style.py
    # PAD_ROLES — Surge handles the synth-family roles)
    "pad_organ": (GENERALUSER_SF, 0, 17),   # GM Percussive Organ — garage skank
    "pad_epiano": (GENERALUSER_SF, 0, 4),   # GM Electric Piano 1 — hiphop keys
    "pad_pizz": (GENERALUSER_SF, 0, 45),    # GM Pizzicato Strings — reggaeton pluck
    "pad_warm": (GENERALUSER_SF, 0, 89),    # GM Pad 2 (warm) — soft alternate
    "pad_strings": (GENERALUSER_SF, 0, 49), # GM String Ensemble 2 — cinematic alt
    "pad_newage": (GENERALUSER_SF, 0, 88),  # GM Pad 1 (new age) — bell-glass alt
    # extended palette (real GM samples — twinkles, keys, plucks, sections):
    "pad_celesta": (GENERALUSER_SF, 0, 8),     # twinkle
    "pad_musicbox": (GENERALUSER_SF, 0, 10),   # twinkle
    "pad_vibes": (GENERALUSER_SF, 0, 11),      # vibraphone
    "pad_marimba": (GENERALUSER_SF, 0, 12),
    "pad_tubular": (GENERALUSER_SF, 0, 14),    # tubular bells
    "pad_fmep": (GENERALUSER_SF, 0, 5),        # FM tines (EP2)
    "pad_clav": (GENERALUSER_SF, 0, 7),        # clavinet — funky comping
    "pad_harp": (GENERALUSER_SF, 0, 46),       # orchestral harp — twinkly arps
    "pad_nylon": (GENERALUSER_SF, 0, 24),      # nylon guitar
    "pad_brass": (GENERALUSER_SF, 0, 61),      # brass section stabs
    "pad_choir": (GENERALUSER_SF, 0, 52),      # choir aahs
    "pad_kalimba": (GENERALUSER_SF, 0, 108),
    "lead_square": (GENERALUSER_SF, 0, 80),    # GM square lead
    "lead_sawgm": (GENERALUSER_SF, 0, 81),     # GM saw lead
    "lead_calliope": (GENERALUSER_SF, 0, 82),
    "lead_fifths": (GENERALUSER_SF, 0, 86),    # rave-y fifths lead
}
_DRUM_SF = (GENERALUSER_SF, 128, 0)

# Drum-voice name (DRUM_PATTERNS) -> GM percussion key (channel 9).
_GM_DRUM_NOTE = {
    "kick": 36, "sub": 35, "snare": 38, "clap": 39,
    "hatC": 42, "hatO": 46, "rim": 37, "cowbell": 56, "shaker": 70,
}

# sr -> (Synth, {sf_path_str: sfid}) — load each soundfont once, reuse.
_CACHE: dict[int, tuple[object, dict[str, int]]] = {}


def any_soundfont_available() -> bool:
    return GENERALUSER_SF.exists() or SALAMANDER_SF.exists()


def resolve_instrument(instrument: str) -> tuple[Path, int, int]:
    """Registry lookup with graceful fallback to GeneralUser GM if a lib is missing."""
    path, bank, preset = INSTRUMENT_SF.get(instrument, (GENERALUSER_SF, 0, 0))
    if not path.exists():
        # fall back to the GM preset on GeneralUser for this instrument
        from .drums import DRUM_PATTERNS  # noqa: F401  (avoid unused import lints elsewhere)
        gm = {"piano": 0, "trumpet": 56, "synth": 81, "bass": 38, "strings": 48,
              "bells": 9, "pads": 50, "pad_organ": 17, "pad_epiano": 4,
              "pad_pizz": 45, "pad_warm": 89, "pad_strings": 49, "pad_newage": 88,
              "pad_celesta": 8, "pad_musicbox": 10, "pad_vibes": 11,
              "pad_marimba": 12, "pad_tubular": 14, "pad_fmep": 5,
              "pad_clav": 7, "pad_harp": 46, "pad_nylon": 24, "pad_brass": 61,
              "pad_choir": 52, "pad_kalimba": 108, "lead_square": 80,
              "lead_sawgm": 81, "lead_calliope": 82, "lead_fifths": 86}
        return GENERALUSER_SF, 0, gm.get(instrument, 0)
    return path, bank, preset


_LIB_NAMES = {
    SALAMANDER_SF: "Salamander Grand (real, CC-BY)",
    SYNTHSQUARE_SF: "FreePats SynthSquare (real, CC0)",
    LATELYBASS_SF: "FreePats Lately Bass (real, CC0)",
    GENERALUSER_SF: "GeneralUser GS (GM)",
}


def library_name(instrument: str) -> str:
    path, _, _ = resolve_instrument(instrument)
    return _LIB_NAMES.get(path, path.name)


def _get_synth(sr: int):
    if sr not in _CACHE:
        import tinysoundfont
        _CACHE[sr] = (tinysoundfont.Synth(samplerate=sr), {})
    return _CACHE[sr]


def _load(synth, loaded: dict[str, int], path: Path) -> int:
    key = str(path)
    if key not in loaded:
        loaded[key] = synth.sfload(key)
    return loaded[key]


def _to_stereo_il(floats: np.ndarray) -> np.ndarray:
    """tinysoundfont emits interleaved LRLR… stereo float32 → (N, 2)."""
    return floats.reshape(-1, 2).astype(np.float32)


def _render_timeline(setup, events, total_frames: int, sr: int, channels=(0, 9)) -> np.ndarray:
    synth, loaded = _get_synth(sr)
    for ch in channels:
        try:
            synth.sounds_off(ch)
        except Exception:
            pass
    setup(synth, loaded)

    events = sorted(events, key=lambda e: (e[0], 0 if e[1] == "off" else 1))
    chunks: list[np.ndarray] = []
    cur = 0
    for frame, kind, chan, key, vel in events:
        frame = min(frame, total_frames)
        if frame > cur:
            chunks.append(np.frombuffer(synth.generate(frame - cur), dtype=np.float32).copy())
            cur = frame
        if kind == "on":
            synth.noteon(chan, key, vel)
        else:
            synth.noteoff(chan, key)
    if total_frames > cur:
        chunks.append(np.frombuffer(synth.generate(total_frames - cur), dtype=np.float32).copy())

    return _to_stereo_il(np.concatenate(chunks)) if chunks else np.zeros((0, 2), dtype=np.float32)


def render_riff_sf(notes, tempo, instrument, bars, bar_beats=4.0, sr=SR) -> np.ndarray:
    """Render the exact riff, looped verbatim across `bars` bars, with a real instrument."""
    path, bank, preset = resolve_instrument(instrument)
    spb = seconds_per_beat(tempo)
    total_frames = int((bars * bar_beats * spb + 0.8) * sr)

    events = []
    for b in range(bars):
        bar_off = b * bar_beats * spb
        for n in notes:
            on_f = int((bar_off + n.start_beats * spb) * sr)
            off_f = int((bar_off + (n.start_beats + n.dur_beats) * spb) * sr)
            events.append((on_f, "on", 0, n.pitch, n.velocity))
            events.append((max(off_f, on_f + 1), "off", 0, n.pitch, 0))

    def setup(synth, loaded):
        sfid = _load(synth, loaded, path)
        synth.program_select(0, sfid, bank, preset)

    return _render_timeline(setup, events, total_frames, sr)


def render_drums_sf(pattern, tempo, bars, sr=SR, style: str | None = None) -> np.ndarray:
    """Render a drum step-pattern with the GM drum kit (channel 9)."""
    from .drums import swung_step_offset

    path, bank, preset = _DRUM_SF
    spb = seconds_per_beat(tempo)
    step_s = spb / 4.0
    total_frames = int((bars * 4 * spb + 0.8) * sr)
    hit_dur_f = int(0.18 * sr)

    events = []
    for b in range(bars):
        for name, steps in pattern.items():
            key = _GM_DRUM_NOTE.get(name)
            if key is None:
                continue
            for i, vel in enumerate(steps):
                if vel <= 0:
                    continue
                at = int((b * 4 * spb + swung_step_offset(style, i) * step_s) * sr)
                v = max(1, min(127, int(vel * 127)))
                events.append((at, "on", 9, key, v))
                events.append((at + hit_dur_f, "off", 9, key, 0))

    def setup(synth, loaded):
        sfid = _load(synth, loaded, path)
        synth.program_select(9, sfid, bank, preset, is_drums=True)

    return _render_timeline(setup, events, total_frames, sr)


# Back-compat alias used by the render dispatcher.
def default_soundfont() -> Path | None:
    return GENERALUSER_SF if any_soundfont_available() else None
