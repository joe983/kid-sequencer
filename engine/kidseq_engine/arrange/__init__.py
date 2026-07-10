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
from .style import StructureStyle, choose_structure

# ---------------------------------------------------------------------------
# Progressions (0-based scale degrees, 4 chords = a 4-bar loop)
# ---------------------------------------------------------------------------

# Every entry contains degree 0 — tonic-anchored riffs always get a tonic
# chord by construction (the tonic-present test relies on this).
_MAJOR_BANK: list[list[int]] = [
    [0, 4, 5, 3],  # I–V–vi–IV   (the pop axis)
    [5, 3, 0, 4],  # vi–IV–I–V
    [0, 3, 5, 4],  # I–IV–vi–V
    [0, 5, 3, 4],  # I–vi–IV–V   (doo-wop)
    [0, 5, 1, 4],  # I–vi–ii–V   (rhythm changes A)
    [0, 3, 0, 4],  # I–IV–I–V    (three-chord anthem)
    [0, 2, 5, 3],  # I–iii–vi–IV (descending thirds)
]
_MINOR_BANK: list[list[int]] = [
    [0, 5, 2, 6],  # i–VI–III–VII (the minor axis)
    [0, 6, 5, 6],  # i–VII–VI–VII
    [0, 3, 5, 6],  # i–iv–VI–VII
    [0, 5, 3, 6],  # i–VI–iv–VII
    [0, 3, 4, 0],  # i–iv–v–i    (the classic cadence loop)
    [0, 2, 6, 5],  # i–III–VII–VI (epic descent)
    [0, 4, 5, 6],  # i–v–VI–VII
]


def _triad_pcs(degree: int, steps: list[int]) -> tuple[int, int, int]:
    """Pitch-class offsets (relative to the tonic) of the triad on a scale degree."""
    return tuple(steps[(degree + i) % 7] % 12 for i in (0, 2, 4))


def choose_progression(riff: Riff, variation: int = 0,
                       pick: int | None = None) -> list[int]:
    """Pick a bank progression whose chords cover the riff's notes well.

    Notes are weighted by duration (+1 for on-beat starts); the first chord is
    weighted double because it sits under the riff's strongest statement (bar 1
    of every drop). Deterministic: ties break by bank order.

    A QUALITY FLOOR keeps variety honest: the candidates are every progression
    scoring >= 0.8x the best (min 2, max 4) — all of them cover the riff well,
    they just colour it differently. `pick` (ArrangeStyle.prog_pick) indexes
    the candidates; without it the legacy `variation % 2` alternation applies."""
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
    best = score(ranked[0])
    candidates = [p for p in ranked if score(p) >= 0.8 * best][:4]
    if len(candidates) < 2:
        candidates = ranked[:2]
    idx = (variation % 2) if pick is None else pick
    return candidates[idx % len(candidates)]


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


# intro character -> (riff_variant, drums, pads) for the opening section
_INTRO_CHARACTER: dict[str, tuple[str, str | None, bool]] = {
    "sparse": ("sparse", "lite", False),      # the classic filtered tease
    "pad_open": ("verbatim", None, True),     # full riff over open pads, no kit
    "low": ("sparse_low", "lite", False),     # sub-octave murmur
}

# drop_bias -> (lo, hi) clamps for the drop bar count
_DROP_CLAMP: dict[str, tuple[int, int]] = {
    "short": (8, 24), "normal": (8, 32), "long": (12, 40),
}


def plan_song(tempo: float, variation: int = 0,
              structure: StructureStyle | None = None) -> list[Section]:
    """Arrange the song so it lands ≥3:00 (target ~190 s) at ANY tempo in the
    app's 40–200 BPM range. Every drop keeps the verbatim riff + full kit (the
    fidelity guarantee) — no shape or bias ever touches that.

    The cycle COUNT scales with tempo (slow 1 … very fast 4); the SKELETON
    comes from a `StructureStyle` (derived from `variation` alone — never the
    riff — so the same nonce gives the same skeleton for any tune):

      classic     intro → [build→drop→break]×(C−1) → build→drop → outro
      cold_open   drop FIRST (instant payoff) → break → [build→drop→break]… → outro
      double_drop cycle 1's drop is followed back-to-back by a second, shorter
                  drop (escalated), then the break (needs ≥2 cycles, else classic)
      late_break  no mid-cycle breaks; ONE break just before the final cycle

    Section lengths vary per press too: build_frac (1/5…1/2), drop_bias
    clamps (short/normal/long), intro/break/outro at 4 or 8 bars. A corrective
    loop then trims/grows drops (and builds) so the 180–240 s window holds for
    EVERY shape × length combination at every tempo."""
    st = structure if structure is not None else choose_structure(variation)
    bar_s = 4.0 * 60.0 / tempo
    target_bars = round(_TARGET_S / bar_s / 4.0) * 4          # nearest 4 bars
    cycles = max(1, min(4, round(target_bars / _BARS_PER_CYCLE)))

    shape = st.song_shape
    if shape == "double_drop" and cycles < 2:
        shape = "classic"                                     # needs two drops' room

    intro_bars, outro_bars, break_bars = st.intro_bars, st.outro_bars, st.break_bars
    n_breaks = max(0, cycles - 1) if shape != "late_break" else (1 if cycles > 1 else 0)
    overhead = intro_bars + outro_bars + n_breaks * break_bars
    if shape == "cold_open":
        overhead += break_bars - intro_bars                   # opening drop + its break
    per_cycle = max(4.0, (target_bars - overhead) / cycles)   # bars per build+drop
    d_lo, d_hi = _DROP_CLAMP[st.drop_bias]
    build_bars = _r4(per_cycle * st.build_frac, 4, 16)
    drop_bars = _r4(per_cycle * (1.0 - st.build_frac), d_lo, d_hi)

    iv, idr, ipads = _INTRO_CHARACTER[st.intro_character]
    sections: list[Section] = []
    drop_i = 1

    def _drop(bars: int) -> Section:
        nonlocal drop_i
        sfx = "" if drop_i == 1 else str(drop_i)
        drop_i += 1
        return Section(f"drop{sfx}", bars, "verbatim", "full", bass=True, pads=True)

    if shape == "cold_open":
        # straight in on the full riff + kit, then breathe
        sections.append(_drop(drop_bars))
        sections.append(Section("break", break_bars, "sparse_low", None, bass=False, pads=True))
    else:
        sections.append(Section("intro", intro_bars, iv, idr, bass=False, pads=ipads))

    for c in range(1, cycles + 1):
        sfx = "" if c == 1 else str(c)
        sections.append(Section(f"build{sfx}", build_bars, "verbatim", "lite", bass=True, pads=True))
        sections.append(_drop(drop_bars))
        if shape == "double_drop" and c == 1:
            # the payoff doubles down before the first breath
            sections.append(_drop(max(8, _r4(drop_bars * 0.5, 8, 16))))
        want_break = (c < cycles) if shape != "late_break" else (c == cycles - 1)
        if want_break:
            bname = f"break{sfx}" if shape != "cold_open" else f"break{c + 1}"
            sections.append(Section(bname, break_bars, "sparse_low", None, bass=False, pads=True))
    sections.append(Section("outro", outro_bars, "sparse", "lite", bass=False, pads=True))
    return _fit_window(sections, bar_s)


def _fit_window(sections: list[Section], bar_s: float,
                lo_s: float = 180.0, hi_s: float = 240.0) -> list[Section]:
    """Deterministic corrective loop: trim the longest drop (floor 8), then
    builds (floor 4), then breaks (floor 4) while over the window; grow drops
    (cap 40) then builds (cap 16) while under it. Makes the duration window
    structural for every shape/length combination."""
    secs = list(sections)

    def dur() -> float:
        return sum(s.bars for s in secs) * bar_s

    def adjust(pred, delta: int, lo: int, hi: int, prefer_longest: bool) -> bool:
        idxs = [i for i, s in enumerate(secs)
                if pred(s) and lo <= s.bars + delta <= hi]
        if not idxs:
            return False
        i = max(idxs, key=lambda j: secs[j].bars) if prefer_longest else \
            min(idxs, key=lambda j: secs[j].bars)
        secs[i] = replace(secs[i], bars=secs[i].bars + delta)
        return True

    for _ in range(64):
        if dur() <= hi_s:
            break
        if not (adjust(lambda s: s.name.startswith("drop"), -4, 8, 99, True)
                or adjust(lambda s: s.name.startswith("build"), -4, 4, 99, True)
                or adjust(lambda s: s.name.startswith("break"), -4, 4, 99, True)):
            break
    for _ in range(64):
        if dur() >= lo_s:
            break
        if not (adjust(lambda s: s.name.startswith("drop"), 4, 8, 40, False)
                or adjust(lambda s: s.name.startswith("build"), 4, 4, 16, False)):
            break
    return secs


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
_OFFBEAT_GENRES = {"techhouse", "garage", "reggaeton"}


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
