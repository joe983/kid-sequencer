"""Tonal-centre detection: decide major vs relative minor from the notes.

The Kid Sequencer grid is **scale-locked** — every row is a degree of the
selected key, so a default-key melody can only contain the 7 notes of C major,
which are the *same 7 pitches* as A minor (its relative minor). What makes one
read major and the other minor is purely which note is heard as "home" and the
chords placed underneath. So detecting that a melody "suits minor" means:

    decide whether the tonal centre is the major tonic (C) or its relative
    minor (A), and re-harmonise around that — WITHOUT changing a single note.

`detect_key(riff)` returns the key string the arranger should use. It only ever
reinterprets a MAJOR key as its **relative minor** (the one reinterpretation that
keeps every note in-key — flipping to the *parallel* minor would flatten the
3rd/6th/7th and shove the child's notes out of key). It is deliberately
one-directional and conservative:

  * An explicitly-chosen minor key is returned unchanged (a deliberate choice is
    never second-guessed).
  * A major key whose relative minor is not in the app's natural-key vocabulary
    (A/E/B major → F#m/C#m/G#m) is returned unchanged.
  * Where it does apply (C/G/D/F major → Am/Em/Bm/Dm), it flips to minor only on
    CLEAR evidence — a happy major tune wrongly turned minor is a worse error
    than leaving an ambiguous one alone.

Method: Krumhansl-Kessler key-profile correlation (the validated standard).
Because both candidates share the identical 7-note collection, the decision
reduces to "does the duration-weighted pitch distribution look more like the
major profile anchored on the major tonic, or the minor profile anchored on the
relative-minor tonic". A cadential tie-break (final / lowest note) settles the
dead-band. Pure function of the notes → deterministic; when the key is not
flipped it returns the original string verbatim, so the arrangement is
byte-identical to before (null contract).
"""

from __future__ import annotations

from .. import sequence as _seq
from ..sequence import Riff

# Krumhansl-Kessler (1982) probe-tone key profiles, index 0 = tonic.
_KK_MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
_KK_MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)

# Semitone name lookup (natural roots only, mirrors sequence._ROOT_SEMITONES).
_SEMI_TO_ROOT = {v: k for k, v in _seq._ROOT_SEMITONES.items()}

# The relative minor must win the cadence-adjusted K-S comparison by at least
# this margin before we flip — a deliberate bias toward the selected (major)
# reading. Tuned so the tonic-anchored patterns kids usually make stay major,
# and only melodies that genuinely orbit the relative-minor tonic flip. See
# tests/test_tonal.py.
_FLIP_MARGIN = 0.06
# The minor reading must also be a genuinely good fit in absolute terms: a melody
# that resembles NEITHER profile (discordant / percussive noise, or one centred
# on a non-tonic) has no real minor case, so we leave it on the selected key.
_MIN_FLOOR = 0.20
# Cadence weights folded into the comparison. K-S is a positionless bag of
# pitch-classes; where a melody actually starts/rests is strong tonal-centre
# evidence it ignores. The final note is the strongest cue, then the lowest.
_CAD_FINAL = 0.10
_CAD_LOW = 0.06


def _pc_weights(riff: Riff) -> list[float]:
    """Duration-weighted pitch-class histogram (12 bins), on-beat starts nudged.

    Mirrors choose_progression's weighting so the two stages agree on what the
    riff emphasises: +dur per note, +1 when the onset lands on a beat.
    """
    w = [0.0] * 12
    for n in riff.notes:
        pc = n.pitch % 12
        weight = n.dur_beats + (1.0 if float(n.start_beats).is_integer() else 0.0)
        w[pc] += weight
    return w


def _pearson(a, b) -> float:
    """Pearson correlation of two equal-length sequences (0.0 if degenerate)."""
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    da = [x - ma for x in a]
    db = [x - mb for x in b]
    num = sum(x * y for x, y in zip(da, db))
    den = (sum(x * x for x in da) * sum(y * y for y in db)) ** 0.5
    return num / den if den else 0.0


def _rotated(profile, tonic_pc: int) -> list[float]:
    """Profile with index 0 (tonic) rotated onto pitch-class `tonic_pc`."""
    return [profile[(p - tonic_pc) % 12] for p in range(12)]


def _last_and_low_pc(riff: Riff) -> tuple[int | None, int | None]:
    """Pitch class of the note the melody RESTS on and of the lowest note — the
    two strongest cadential cues for a tonal centre. "Rests on" = the note that
    stops sounding last (latest offset), tie-broken by latest onset then lowest
    pitch, so a long held tonic isn't overridden by a short late blip."""
    if not riff.notes:
        return None, None
    final = max(riff.notes,
                key=lambda x: (x.start_beats + x.dur_beats, x.start_beats, -x.pitch))
    low = min(riff.notes, key=lambda x: x.pitch)
    return final.pitch % 12, low.pitch % 12


def detect_key(riff: Riff) -> str:
    """Return the key the arranger should use (see module docstring).

    Only ever flips a natural MAJOR key to its relative minor, on clear
    evidence; otherwise returns ``riff.key`` unchanged (verbatim string, so the
    null cases stay byte-identical downstream)."""
    key = riff.key
    # Respect an explicit minor choice; only naturals have a relative in-vocab.
    if key.endswith("m") or key not in _seq._ROOT_SEMITONES:
        return key
    if len(riff.notes) < 2:
        return key  # a single note has no tonal centre to weigh

    major_pc = _seq._ROOT_SEMITONES[key]
    minor_pc = (major_pc - 3) % 12  # relative minor = major tonic down a m3
    minor_root = _SEMI_TO_ROOT.get(minor_pc)
    if minor_root is None:
        return key  # A/E/B major → F#m/C#m/G#m, not in the app's key set

    hist = _pc_weights(riff)
    if sum(hist) <= 0:
        return key

    # Two structural vetoes that a positionless K-S histogram can't see. Both
    # guard the conservative contract against sparse do+la patterns, where the
    # minor profile's shape (it likes the major tonic as its own m3) over-rewards
    # the relative-minor reading even when the tune plainly rests on the major
    # tonic:
    final_pc, low_pc = _last_and_low_pc(riff)
    #  (a) a melody that ENDS on and BOTTOMS on the major tonic rests there — it
    #      is heard as major whatever the histogram shape.
    if final_pc == major_pc and low_pc == major_pc:
        return key
    #  (b) the relative-minor tonic must carry at least as much weight as the
    #      major tonic; otherwise the major tonic is the tonal centre. A genuine
    #      minor tune leans on its tonic (la); a major tune leaning on do does not.
    if hist[minor_pc] < hist[major_pc]:
        return key

    score_major = _pearson(hist, _rotated(_KK_MAJOR, major_pc))
    score_minor = _pearson(hist, _rotated(_KK_MINOR, minor_pc))

    # Cadence-adjust the K-S lean: resting on the minor tonic is minor evidence;
    # resting on the major tonic is major evidence (finer control in the zone the
    # vetoes let through, e.g. when la and do are equally weighted).
    adj = score_minor - score_major
    for pc, wt in ((final_pc, _CAD_FINAL), (low_pc, _CAD_LOW)):
        if pc == minor_pc:
            adj += wt
        elif pc == major_pc:
            adj -= wt

    flip = score_minor >= _MIN_FLOOR and adj >= _FLIP_MARGIN
    return f"{minor_root}m" if flip else key
