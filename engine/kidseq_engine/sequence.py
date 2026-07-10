"""Sequence → exact notes → MIDI.

This module is the heart of the riff-fidelity guarantee: it converts the Kid
Sequencer's grid state into precise MIDI notes using the SAME pitch/timing model
the app uses for playback, so what the engine renders is bit-for-bit the tune the
child made.

Authoritative source for the constants below (keep in sync):
  public/index.html:506-534   SCALES / pitchFor  (pitch model)
  public/index.html:2602-2606 stepDurationSec    (timing model: 4 steps/beat = 16th notes)
  public/index.html:3376-3385 playInstrument     (bass x0.25 = -24 semitones, bells x4 = +24)

Grid: rows=8 (row 7 = scale root at C4, row 0 = octave up), cols=16 = one 4/4 bar.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Pitch model (mirrors index.html:506-534) -------------------------------
KEY_ORDER = ["A", "Am", "B", "Bm", "C", "Cm", "D", "Dm", "E", "Em", "F", "Fm", "G", "Gm"]
_MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11, 12]
_MINOR_STEPS = [0, 2, 3, 5, 7, 8, 10, 12]  # natural minor
_ROOT_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# In the app, row 0 = top of grid = highest pitch (octave), row 7 = bottom = root.
# ascending[i] is the i-th scale degree above the root; row r reads ascending[7 - r].
# C4 = MIDI 60 in the convention where A4 = 440 Hz = MIDI 69 (the app's _C4_HZ=261.63).
_C4_MIDI = 60
ROWS = 8
COLS = 16
STEPS_PER_BEAT = 4  # index.html:2605 — full app: each column is a 16th note
BEATS_PER_BAR = 4

# Per-instrument octave shift applied in playInstrument() (index.html:3376-3385).
INSTRUMENT_SEMITONE_SHIFT = {
    "piano": 0,
    "trumpet": 0,
    "strings": 0,
    "synth": 0,
    "bass": -24,   # freq * 0.25  => two octaves down
    "bells": +24,  # freq * 4     => two octaves up
}


def _scale_steps(key: str) -> tuple[int, list[int]]:
    """Return (root_semitone, step_table) for a key like 'C' or 'Am'."""
    is_minor = key.endswith("m")
    root = key[:-1] if is_minor else key
    if root not in _ROOT_SEMITONES:
        root, is_minor = "C", False  # match the app's SCALES.C fallback
    semi = _ROOT_SEMITONES[root]
    steps = _MINOR_STEPS if is_minor else _MAJOR_STEPS
    return semi, steps


def row_to_midi(row: int, key: str = "C", instrument: str = "piano") -> int:
    """Map a grid row (0=top) to a MIDI note for the given key + instrument."""
    semi, steps = _scale_steps(key)
    degree = steps[ROWS - 1 - row]  # row 7 -> steps[0] (root); row 0 -> steps[7] (octave)
    shift = INSTRUMENT_SEMITONE_SHIFT.get(instrument, 0)
    return _C4_MIDI + semi + degree + shift


@dataclass(frozen=True)
class Note:
    pitch: int          # MIDI note number
    start_beats: float   # onset, in beats from bar start
    dur_beats: float     # duration, in beats
    velocity: int = 96


@dataclass
class Riff:
    notes: list[Note]
    tempo: float          # BPM
    key: str              # e.g. "C", "Am"
    instrument: str       # e.g. "piano"
    drum_style: str | None  # None when drums muted
    bar_beats: float = BEATS_PER_BAR


def parse_sequence(payload: dict) -> Riff:
    """Build a Riff from the Kid Sequencer payload.

    Expected shape (mirrors the app's saved state):
        {
          "riff": {"notes": [{"row":int,"start":int,"len":int}, ...]},
          "key": "C", "tempo": 120, "instrument": "piano",
          "drumStyle": "techhouse" | null   # null when drumsMuted
        }
    """
    key = str(payload.get("key", "C"))
    tempo = float(payload.get("tempo", 120))
    instrument = str(payload.get("instrument", "piano"))
    drum_style = payload.get("drumStyle") or None
    if drum_style == "funk":  # legacy key for UK Garage (renamed 2026-07-10)
        drum_style = "garage"

    raw = (payload.get("riff") or {}).get("notes", [])
    notes: list[Note] = []
    for n in raw:
        row = int(n["row"])
        start = int(n["start"])
        length = int(n["len"])
        if not (0 <= row < ROWS) or start < 0 or length <= 0:
            continue
        notes.append(
            Note(
                pitch=row_to_midi(row, key, instrument),
                start_beats=start / STEPS_PER_BEAT,
                dur_beats=length / STEPS_PER_BEAT,
                velocity=int(n.get("velocity", 96)),
            )
        )
    notes.sort(key=lambda x: (x.start_beats, x.pitch))
    return Riff(notes=notes, tempo=tempo, key=key, instrument=instrument, drum_style=drum_style)


def to_midi_bytes(riff: Riff, ticks_per_beat: int = 480) -> bytes:
    """Serialize the riff to a standard MIDI file (single track)."""
    import io

    import mido

    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(riff.tempo), time=0))

    # Build absolute-time on/off events, then convert to delta times.
    events: list[tuple[int, int, int, int]] = []  # (tick, kind 1=on/0=off, pitch, vel)
    for n in riff.notes:
        on = round(n.start_beats * ticks_per_beat)
        off = round((n.start_beats + n.dur_beats) * ticks_per_beat)
        events.append((on, 1, n.pitch, n.velocity))
        events.append((max(off, on + 1), 0, n.pitch, 0))
    events.sort(key=lambda e: (e[0], e[1]))  # offs before ons at same tick

    prev = 0
    for tick, kind, pitch, vel in events:
        delta = tick - prev
        prev = tick
        msg = "note_on" if kind == 1 else "note_off"
        track.append(mido.Message(msg, note=pitch, velocity=vel, time=delta))

    buf = io.BytesIO()
    mid.save(file=buf)
    return buf.getvalue()
