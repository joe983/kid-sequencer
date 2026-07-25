"""Tests for tonal-centre detection (major vs relative minor).

The Kid Sequencer grid is scale-locked, so a melody that "suits minor" arrives
in a MAJOR key made of the relative minor's exact pitches. detect_key() decides
whether to re-harmonise around the relative minor — WITHOUT changing any note.
These pin the contract: it flips only natural major keys, only to their relative
minor, only on clear evidence, and never touches an explicit minor choice.

C-major grid row -> pitch (row 7 = root at bottom):
  row7=C row6=D row5=E row4=F row3=G row2=A row1=B row0=C'
So the relative-minor tonic A sits at row 2; the major tonic C at row 7/0.
"""

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.arrange import (  # noqa: E402
    _MAJOR_BANK,
    _MINOR_BANK,
    choose_progression,
)
from kidseq_engine.arrange.tonal import detect_key  # noqa: E402
from kidseq_engine.sequence import parse_sequence  # noqa: E402

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _payload(rows, key="C", instr="piano"):
    """rows = list of (row, start, len) in 16th-note steps."""
    return {
        "riff": {"notes": [{"row": r, "start": s, "len": l} for r, s, l in rows]},
        "key": key, "tempo": 120, "instrument": instr, "drumStyle": "techhouse",
    }


def _detect(rows, key="C", instr="piano"):
    return detect_key(parse_sequence(_payload(rows, key, instr)))


# --- Null contract: an explicit choice is never second-guessed ---------------

def test_explicit_minor_never_flips():
    # Every natural minor key stays put, whatever the notes look like.
    for mk in ("Am", "Bm", "Cm", "Dm", "Em", "Fm", "Gm"):
        rows = [(2, 0, 2), (0, 2, 2), (5, 4, 2), (2, 12, 4)]  # A-minor-ish shape
        assert _detect(rows, key=mk) == mk, mk


def test_major_without_natural_relative_minor_stays():
    # A/E/B major relate to F#m/C#m/G#m, which are not in the app's key set.
    for mk in ("A", "E", "B"):
        rows = [(2, 0, 2), (0, 2, 2), (5, 4, 2), (2, 6, 2), (2, 12, 4)]
        assert _detect(rows, key=mk) == mk, mk


def test_too_few_notes_stays():
    assert _detect([(2, 0, 2)]) == "C"          # single note has no centre
    assert _detect([]) == "C"                    # empty riff


# --- Clear flips (melody genuinely orbits the relative-minor tonic) ----------

def test_clear_a_minor_flips_from_c():
    # A-C-E orbit, starts and ends on A -> A minor.
    rows = [(2, 0, 2), (0, 2, 2), (5, 4, 2), (2, 6, 2), (6, 8, 2), (7, 10, 2), (2, 12, 4)]
    assert _detect(rows, key="C") == "Am"


def test_clear_flip_g_to_em():
    # In G, orbit the E-minor triad (E/G/B), rest on E.
    rows = [(2, 0, 2), (7, 2, 2), (1, 4, 2), (2, 6, 2), (0, 8, 2), (2, 12, 4)]
    assert _detect(rows, key="G") == "Em"


def test_clear_flip_f_to_dm():
    # In F, orbit the D-minor triad (D/F/A), start and rest on D (row2 in F).
    rows = [(2, 0, 2), (7, 2, 2), (4, 4, 2), (2, 6, 2), (6, 8, 2), (2, 12, 4)]
    assert _detect(rows, key="F") == "Dm"


# --- Must STAY major (conservative bias; these are the real false-positives) --

def test_clear_c_major_stays():
    # C-E-G orbit, starts and ends on C.
    rows = [(7, 0, 2), (5, 2, 2), (3, 4, 2), (7, 6, 2), (6, 8, 2), (3, 10, 2), (7, 12, 4)]
    assert _detect(rows, key="C") == "C"


def test_c_centred_melody_with_minor_tones_stays():
    # Regression: "C C C C E A E C" scores high on the A-minor profile too
    # (uses A and E), but it starts, ends AND bottoms on C -> stays C major.
    rows = [(7, 0, 1), (7, 1, 1), (7, 2, 1), (7, 3, 1), (5, 4, 2), (2, 6, 2), (5, 8, 2), (7, 10, 2)]
    assert _detect(rows, key="C") == "C"


def test_ending_on_minor_tonic_alone_does_not_flip():
    # A strongly major body (C/E/G) that merely ENDS on A must not flip.
    rows = [(7, 0, 3), (3, 3, 3), (5, 6, 3), (7, 9, 3), (2, 12, 1)]
    assert _detect(rows, key="C") == "C"


def test_diatonic_scale_reads_major():
    # A plain 8-note diatonic run is the ambiguous default -> major.
    rows = [(7, 0, 1), (6, 1, 1), (5, 2, 1), (4, 3, 1), (3, 4, 1), (2, 5, 1), (1, 6, 1), (0, 7, 1)]
    assert _detect(rows, key="C") == "C"


def test_discordant_noise_stays():
    # Two short scattered notes correlate with NEITHER profile -> no flip.
    assert _detect([(6, 0, 1), (1, 4, 1)], key="C") == "C"


def test_do_la_resting_on_tonic_stays_major():
    # Regression (adversarial review): a sparse tonic+submediant tune ("C A A C")
    # that STARTS, ENDS and BOTTOMS on the major tonic must stay major, even
    # though the K-S minor profile shape-correlates highly with do+la. Reproduces
    # in every supported key.
    do_la = [(7, 0, 2), (2, 3, 2), (2, 12, 1), (7, 14, 2)]  # tonic hi/lo pattern
    assert _detect(do_la, key="C") == "C"
    assert _detect(do_la, key="G") == "G"
    assert _detect(do_la, key="D") == "D"
    assert _detect(do_la, key="F") == "F"


def test_major_tonic_outweighs_minor_tonic_stays():
    # If the major tonic carries strictly more weight than the relative-minor
    # tonic, the major tonic is the tonal centre -> no flip.
    rows = [(7, 0, 4), (7, 4, 2), (2, 6, 2), (5, 8, 2), (7, 10, 2)]  # do-dominant
    assert _detect(rows, key="C") == "C"


# --- Determinism -------------------------------------------------------------

def test_deterministic():
    rows = [(2, 0, 2), (0, 2, 2), (5, 4, 2), (2, 6, 2), (2, 12, 4)]
    a = _detect(rows, key="C")
    b = _detect(rows, key="C")
    assert a == b == "Am"


# --- Battery examples: explicit-minor inputs must round-trip unchanged --------

def test_battery_minor_examples_unchanged():
    for f in sorted(EXAMPLES.glob("*_minor.json")):
        import json
        riff = parse_sequence(json.load(open(f)))
        assert not riff.key.endswith("m") or detect_key(riff) == riff.key, f.name


# --- End-to-end: a flip actually drives the MINOR progression bank -----------

def test_flip_drives_minor_bank_and_chords():
    from kidseq_engine.arrange import _triad_pcs
    from kidseq_engine.sequence import _MINOR_STEPS, _ROOT_SEMITONES

    minor_lean = parse_sequence(_payload(
        [(2, 0, 2), (0, 2, 2), (5, 4, 2), (2, 6, 2), (6, 8, 2), (7, 10, 2), (2, 12, 4)]))
    det = detect_key(minor_lean)
    assert det == "Am"
    riff = replace(minor_lean, key=det)
    prog = choose_progression(riff, 0)
    assert prog in _MINOR_BANK and prog not in _MAJOR_BANK
    # tonic chord is a genuine A-minor triad {A, C, E}
    semi = _ROOT_SEMITONES["A"]
    triad = {(semi + pc) % 12 for pc in _triad_pcs(prog[0], _MINOR_STEPS)}
    assert triad == {9, 0, 4}, triad  # A, C, E


def test_no_flip_keeps_major_bank():
    major_lean = parse_sequence(_payload(
        [(7, 0, 2), (5, 2, 2), (3, 4, 2), (7, 6, 2), (6, 8, 2), (3, 10, 2), (7, 12, 4)]))
    assert detect_key(major_lean) == "C"
    prog = choose_progression(major_lean, 0)
    assert prog in _MAJOR_BANK and prog not in _MINOR_BANK


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all tonal tests passed")
