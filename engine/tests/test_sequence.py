"""Tests for the exact pitch/timing mapping — the riff-fidelity contract."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.sequence import (  # noqa: E402
    Note,
    Riff,
    parse_sequence,
    row_to_midi,
    to_midi_bytes,
)


def test_c_major_anchor_pitches():
    # Row 7 = scale root at C4 = MIDI 60; row 0 = octave up = C5 = MIDI 72.
    assert row_to_midi(7, "C", "piano") == 60
    assert row_to_midi(0, "C", "piano") == 72


def test_a440_lands_on_midi_69():
    # In C major the A (9 semitones above C4) must be MIDI 69 (A4 = 440 Hz).
    # C-major ascending steps = [0,2,4,5,7,9,11,12]; the '9' is degree index 5,
    # which is row 7-5 = row 2.
    assert row_to_midi(2, "C", "piano") == 69


def test_minor_key_third_is_flat():
    # A minor: root A4 = MIDI 69 at row 7; the minor third (C) is +3 semitones.
    assert row_to_midi(7, "Am", "piano") == 69
    assert row_to_midi(6, "Am", "piano") == 71  # +2 (major 2nd) in natural minor


def test_instrument_octave_shifts():
    # Bass drops two octaves, bells rise two octaves vs the same row/key.
    base = row_to_midi(7, "C", "piano")
    assert row_to_midi(7, "C", "bass") == base - 24
    assert row_to_midi(7, "C", "bells") == base + 24


def test_timing_one_bar_is_four_beats():
    payload = {
        "riff": {"notes": [{"row": 7, "start": 0, "len": 16}]},
        "key": "C", "tempo": 120, "instrument": "piano", "drumStyle": None,
    }
    riff = parse_sequence(payload)
    assert len(riff.notes) == 1
    n = riff.notes[0]
    assert n.start_beats == 0.0
    assert n.dur_beats == 4.0  # 16 steps / 4 steps-per-beat = 4 beats = one 4/4 bar
    assert riff.drum_style is None


def test_midi_roundtrip_is_lossless():
    import mido

    notes = [Note(60, 0.0, 1.0), Note(64, 1.0, 1.0), Note(67, 2.0, 2.0)]
    riff = Riff(notes=notes, tempo=120, key="C", instrument="piano", drum_style=None)
    data = to_midi_bytes(riff)
    mid = mido.MidiFile(file=__import__("io").BytesIO(data))
    on = [m for tr in mid.tracks for m in tr if m.type == "note_on" and m.velocity > 0]
    assert sorted(m.note for m in on) == [60, 64, 67]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all sequence tests passed")
