"""Stage B: arrangement — progression, bass, pads, song structure.

Rule-based (docs/PLAN.md section B): a curated diatonic progression bank scored by
riff chord-tone coverage (in-key by construction, can't clash with the riff), a
genre-feel bassline locked to the progression, sustained pad voicings, and a
fixed EDM structure sized by tempo. The DROP sections always use the user's riff
notes VERBATIM — that is the engine's whole fidelity guarantee, enforced here
symbolically (the drop's note list IS riff.notes, not a copy-with-edits).

music21 was planned but deliberately not used: for diatonic triads in a known key
the engine's own tested pitch model (sequence.py) covers it without a heavyweight
dependency; revisit only if real voice-leading lands on the roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..sequence import _C4_MIDI, Note, Riff, _scale_steps

# ---------------------------------------------------------------------------
# Progressions (0-based scale degrees, 4 chords = a 4-bar loop)
# ---------------------------------------------------------------------------

_MAJOR_BANK: list[list[int]] = [
    [0, 4, 5, 3],  # I–V–vi–IV   (the pop axis)
    [5, 3, 0, 4],  # vi–IV–I–V
    [0, 3, 5, 4],  # I–IV–vi–V
    [0, 5, 3, 4],  # I–vi–IV–V   (doo-wop)
]
_MINOR_BANK: list[list[int]] = [
    [0, 5, 2, 6],  # i–VI–III–VII (the minor axis)
    [0, 6, 5, 6],  # i–VII–VI–VII
    [0, 3, 5, 6],  # i–iv–VI–VII
    [0, 5, 3, 6],  # i–VI–iv–VII
]


def _triad_pcs(degree: int, steps: list[int]) -> tuple[int, int, int]:
    """Pitch-class offsets (relative to the tonic) of the triad on a scale degree."""
    return tuple(steps[(degree + i) % 7] % 12 for i in (0, 2, 4))


def choose_progression(riff: Riff, variation: int = 0) -> list[int]:
    """Pick a bank progression whose chords cover the riff's notes well.

    Notes are weighted by duration (+1 for on-beat starts); the first chord is
    weighted double because it sits under the riff's strongest statement (bar 1
    of every drop). Deterministic: ties break by bank order. `variation`
    alternates between the two BEST-scoring progressions (both cover the riff;
    which harmonic colour you get varies per press)."""
    semi, steps = _scale_steps(riff.key)
    bank = _MINOR_BANK if riff.key.endswith("m") else _MAJOR_BANK
    tonic = _C4_MIDI + semi

    weights: dict[int, float] = {}
    for n in riff.notes:
        pc = (n.pitch - tonic) % 12
        w = n.dur_beats + (1.0 if float(n.start_beats).is_integer() else 0.0)
        weights[pc] = weights.get(pc, 0.0) + w

    def score(prog: list[int]) -> float:
        total = 0.0
        for i, degree in enumerate(prog):
            chord = _triad_pcs(degree, steps)
            cover = sum(w for pc, w in weights.items() if pc in chord)
            total += cover * (2.0 if i == 0 else 1.0)
        return total

    ranked = sorted(bank, key=score, reverse=True)
    return ranked[variation % 2]


# ---------------------------------------------------------------------------
# Song structure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Section:
    name: str
    bars: int
    riff_variant: str | None  # "verbatim" | "sparse" | "sparse_low" | None
    drums: str | None         # "full" | "lite" | None
    bass: bool
    pads: bool


_TARGET_S = 190.0          # aim; hard window is 180–240 s (kids-attention + ≥3 min)
_BARS_PER_CYCLE = 44       # ≈ one build+drop+break; sets how many cycles a tempo needs


def _r4(x: float, lo: int, hi: int) -> int:
    """Round to the nearest multiple of 4, clamped to [lo, hi] (bar counts stay
    phrase-aligned so sections line up on 4-bar boundaries)."""
    return max(lo, min(hi, round(x / 4.0) * 4))


def plan_song(tempo: float, variation: int = 0) -> list[Section]:
    """Arrange N build→drop cycles so the song lands ≥3:00 (target ~190 s) at ANY
    tempo in the app's 40–200 BPM range.

    Rather than stretch one drop to fill time (unmusical), the cycle COUNT scales
    with tempo: slow tempos need 1 cycle, typical 2, very fast 3–4. Each cycle's
    build/drop bar counts are then sized to hit the duration target, phrase-aligned.
    Structure: intro → (build → drop → break)×(C-1) → build → drop → outro. Every
    drop keeps the verbatim riff + full kit (the fidelity guarantee).

    `variation` shifts the build:drop split (longer builds vs longer drops) —
    total bars stay the same, so the duration window holds for every nonce."""
    bar_s = 4.0 * 60.0 / tempo
    target_bars = round(_TARGET_S / bar_s / 4.0) * 4          # nearest 4 bars
    cycles = max(1, min(4, round(target_bars / _BARS_PER_CYCLE)))

    intro_bars = outro_bars = 4
    break_bars = 8
    overhead = intro_bars + outro_bars + (cycles - 1) * break_bars
    per_cycle = max(4.0, (target_bars - overhead) / cycles)   # bars per build+drop
    build_frac = (1 / 3.0, 1 / 4.0, 2 / 5.0)[variation % 3]   # per-press feel
    build_bars = _r4(per_cycle * build_frac, 4, 16)
    drop_bars = _r4(per_cycle * (1.0 - build_frac), 8, 32)

    sections = [Section("intro", intro_bars, "sparse", "lite", bass=False, pads=False)]
    for c in range(1, cycles + 1):
        sfx = "" if c == 1 else str(c)
        sections.append(Section(f"build{sfx}", build_bars, "verbatim", "lite", bass=True, pads=True))
        sections.append(Section(f"drop{sfx}", drop_bars, "verbatim", "full", bass=True, pads=True))
        if c < cycles:  # a break bridges cycles, never trails the final drop
            sections.append(Section(f"break{sfx}", break_bars, "sparse_low", None, bass=False, pads=True))
    sections.append(Section("outro", outro_bars, "sparse", "lite", bass=False, pads=True))
    return sections


def riff_variant(notes: list[Note], variant: str) -> list[Note]:
    """Deterministic riff transforms for non-drop sections. DROPS use riff.notes
    untouched — never route a drop through this function."""
    if variant == "verbatim":
        return notes
    if variant == "sparse":
        picked = [n for n in notes if float(n.start_beats).is_integer()]
        return picked or notes[:1]
    if variant == "sparse_low":
        return [replace(n, pitch=n.pitch - 12) for n in riff_variant(notes, "sparse")]
    raise ValueError(f"unknown riff variant {variant!r}")


# ---------------------------------------------------------------------------
# Bass + pads note builders (one chord per bar, progression loops every 4 bars)
# ---------------------------------------------------------------------------

# genres with a four-on-the-floor feel get offbeat 8ths; the rest get long roots
_OFFBEAT_GENRES = {"techhouse", "funk", "reggaeton"}


def _chord_for_bar(bar: int, prog: list[int]) -> int:
    return prog[bar % len(prog)]


def _fold(pitch: int, lo: int, hi: int) -> int:
    while pitch < lo:
        pitch += 12
    while pitch > hi:
        pitch -= 12
    return pitch


def bass_notes(riff: Riff, prog: list[int], bars: int) -> list[Note]:
    """Chord roots around C2–B2 in a genre feel. Pitches are absolute (no -24
    shift downstream — these are not grid notes)."""
    semi, steps = _scale_steps(riff.key)
    out: list[Note] = []
    for b in range(bars):
        root_pc = (semi + steps[_chord_for_bar(b, prog)]) % 12
        pitch = _fold(36 + root_pc, 36, 47)  # C2..B2
        bar0 = b * 4.0
        if riff.drum_style in _OFFBEAT_GENRES:
            for beat in (0.5, 1.5, 2.5, 3.5):  # classic house offbeat 8ths
                out.append(Note(pitch=pitch, velocity=104, start_beats=bar0 + beat,
                                dur_beats=0.45))
        elif riff.drum_style == "dnb":
            out.append(Note(pitch=pitch, velocity=106, start_beats=bar0, dur_beats=1.5))
            out.append(Note(pitch=pitch, velocity=100, start_beats=bar0 + 2.5, dur_beats=1.0))
        else:  # drill / hiphop / unknown: long sub roots
            out.append(Note(pitch=pitch, velocity=106, start_beats=bar0, dur_beats=3.0))
            out.append(Note(pitch=pitch, velocity=98, start_beats=bar0 + 3.0, dur_beats=1.0))
    return out


def pad_notes(riff: Riff, prog: list[int], bars: int) -> list[Note]:
    """Whole-bar triad voicings around C4–B4 (root position, folded into range)."""
    semi, steps = _scale_steps(riff.key)
    out: list[Note] = []
    for b in range(bars):
        degree = _chord_for_bar(b, prog)
        root_pc, third_pc, fifth_pc = _triad_pcs(degree, steps)
        root = _fold(60 + (semi + root_pc) % 12, 60, 71)
        third = _fold(60 + (semi + third_pc) % 12, root, root + 11)
        fifth = _fold(60 + (semi + fifth_pc) % 12, third, third + 11)
        for pitch in (root, third, fifth):
            out.append(Note(pitch=pitch, velocity=88, start_beats=b * 4.0, dur_beats=4.0))
    return out
