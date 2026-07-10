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
    "fragment": ("fragment", None, True),     # the riff's opening question, on pads
    "high": ("sparse_high", "lite", False),   # octave-up music-box tease
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


# ---------------------------------------------------------------------------
# Riff ornaments — tasteful per-bar embellishments for LATER sections. The
# first drop always states the hook PURE VERBATIM; from drop 2 (and long
# builds) phrase-end bars may carry one of these. Octave/velocity transforms
# only — pitch classes never leave the riff's own set (± an octave).
# ---------------------------------------------------------------------------


def ornament_riff(notes: list[Note], kind: str) -> list[Note]:
    """One ornamented BAR of the riff. Deterministic; octave/velocity only."""
    if not notes or kind == "none":
        return notes
    if kind == "echo":
        # the bar's last note answered an octave up in the gap after it
        last = max(notes, key=lambda n: n.start_beats + n.dur_beats)
        at = last.start_beats + last.dur_beats
        if at < 3.6:
            echo = replace(last, start_beats=at, pitch=last.pitch + 12,
                           dur_beats=min(last.dur_beats, 4.0 - at),
                           velocity=max(1, int(last.velocity * 0.55)))
            return notes + [echo]
        return notes
    if kind == "octave_pop":
        # the bar's highest note doubled an octave up — a sparkle on top
        hi = max(notes, key=lambda n: n.pitch)
        pop = replace(hi, pitch=hi.pitch + 12,
                      velocity=max(1, int(hi.velocity * 0.5)))
        return notes + [pop]
    if kind == "push":
        # gentle velocity phrasing: swell across the bar (0.88 -> 1.06)
        return [replace(n, velocity=max(1, min(127, int(
            n.velocity * (0.88 + 0.18 * min(n.start_beats, 4.0) / 4.0)))))
            for n in notes]
    if kind == "cadence":
        # end-of-bar pickup: the last note repeated as a quiet 8th leading into
        # the next bar — only when the bar end is actually free
        last = max(notes, key=lambda n: n.start_beats + n.dur_beats)
        if last.start_beats + last.dur_beats <= 3.4:
            pick = replace(last, start_beats=3.5, dur_beats=0.45,
                           velocity=max(1, int(last.velocity * 0.6)))
            return notes + [pick]
        return notes
    raise ValueError(f"unknown ornament {kind!r}")


def _scale_ladder(key: str, around: int) -> list[int]:
    """All in-scale MIDI pitches within +-2 octaves of `around`, sorted."""
    semi, steps = _scale_steps(key)
    pcs = {(semi + s) % 12 for s in steps}
    return [p for p in range(max(0, around - 24), min(128, around + 25))
            if p % 12 in pcs]


def _diatonic_shift(pitch: int, key: str, degrees: int) -> int:
    """Move a pitch by scale DEGREES (snapping into the key first)."""
    ladder = _scale_ladder(key, pitch)
    if not ladder:
        return pitch
    idx = min(range(len(ladder)), key=lambda i: abs(ladder[i] - pitch))
    return ladder[max(0, min(len(ladder) - 1, idx + degrees))]


def vary_bar(notes: list[Note], kind: str, key: str,
             target_pitch: int | None = None) -> list[Note]:
    """One VARIATION BAR of the riff — a real change to the pattern, the way a
    musician varies a repeated phrase. Bar-end focused; always in key; at
    least the bar's opening notes survive so the riff stays recognisable.

    Light kinds (echo/octave_pop/push/cadence) delegate to ornament_riff.
    Bold kinds:
      ending_fill  final beat replaced by a stepwise scale run toward the next
                   bar's first note (the classic turnaround fill)
      rest_gap     final-beat notes dropped — a breath before the next bar
      retrigger    the last note re-struck as a quick double at the bar end
      answer       the bar's second half re-pitched a diatonic third down
                   (call unchanged, response answers lower)"""
    if not notes or kind == "none":
        return notes
    if kind in ("echo", "octave_pop", "push", "cadence"):
        return ornament_riff(notes, kind)
    if kind == "rest_gap":
        kept = [n for n in notes if n.start_beats < 3.0]
        return kept or notes
    if kind == "retrigger":
        last = max(notes, key=lambda n: n.start_beats + n.dur_beats)
        if last.start_beats + last.dur_beats <= 3.0:
            # room after the phrase: ratatat into the next bar
            return notes + [
                replace(last, start_beats=3.0, dur_beats=0.22,
                        velocity=max(1, int(last.velocity * 0.82))),
                replace(last, start_beats=3.5, dur_beats=0.4,
                        velocity=max(1, int(last.velocity * 0.95)))]
        # bar end occupied: split the last note into a quick double
        rest = [n for n in notes if n is not last]
        half = last.dur_beats / 2.0
        return rest + [
            replace(last, dur_beats=max(0.15, half * 0.9),
                    velocity=max(1, int(last.velocity * 0.8))),
            replace(last, start_beats=last.start_beats + half,
                    dur_beats=last.dur_beats - half)]
    if kind == "ending_fill":
        head = [n for n in notes if n.start_beats < 3.0]
        if not head:
            return notes
        cur = max(head, key=lambda n: n.start_beats + n.dur_beats).pitch
        target = target_pitch if target_pitch is not None else cur
        step = 1 if target >= cur else -1
        vel = max(1, int(max(n.velocity for n in head) * 0.9))
        run = []
        p = cur
        for i, beat in enumerate((3.0, 3.5)):
            p = _diatonic_shift(p, key, step)
            run.append(Note(pitch=p, velocity=vel, start_beats=beat,
                            dur_beats=0.45))
        return head + run
    if kind == "answer":
        call = [n for n in notes if n.start_beats < 2.0]
        resp = [replace(n, pitch=_diatonic_shift(n.pitch, key, -2))
                for n in notes if n.start_beats >= 2.0]
        return (call + resp) if resp else notes
    raise ValueError(f"unknown variation {kind!r}")


#: phrase treatments — how a 4-bar phrase develops the motif
PHRASE_TREATMENTS = ("statement", "vary_end", "octave_up",
                     "call_response", "sparse_breath")


def develop_phrase(notes: list[Note], treatment: str, key: str,
                   vary_kind: str = "ending_fill",
                   target_pitch: int | None = None,
                   phrase_bars: int = 4) -> list[list[Note]]:
    """Per-bar note lists for ONE PHRASE of the riff — motif development, the
    way a producer keeps a 1-bar motif interesting for 3 minutes. The motif
    always stays recognisable: statements anchor, developments transform.

      statement      the pure riff, every bar
      vary_end       bars 1..n-1 pure, final bar rewritten (vary_bar kind)
      octave_up      the whole phrase an octave up — same motif, new register
      call_response  first half states, second half answers a diatonic third
                     down
      sparse_breath  bars 2 and n thinned at the tail — space and groove
    """
    if treatment == "statement":
        return [list(notes) for _ in range(phrase_bars)]
    if treatment == "vary_end":
        bars = [list(notes) for _ in range(phrase_bars)]
        bars[-1] = vary_bar(notes, vary_kind, key, target_pitch=target_pitch)
        return bars
    if treatment == "octave_up":
        up = [replace(n, pitch=min(115, n.pitch + 12)) for n in notes]
        return [list(up) for _ in range(phrase_bars)]
    if treatment == "call_response":
        resp = [replace(n, pitch=_diatonic_shift(n.pitch, key, -2)) for n in notes]
        half = max(1, phrase_bars // 2)
        return [list(notes) for _ in range(half)] + \
               [list(resp) for _ in range(phrase_bars - half)]
    if treatment == "sparse_breath":
        gap = vary_bar(notes, "rest_gap", key)
        bars = [list(notes) for _ in range(phrase_bars)]
        bars[-1] = list(gap)
        if phrase_bars >= 3:
            bars[1] = list(gap)
        return bars
    raise ValueError(f"unknown treatment {treatment!r}")


def resolve_clashes(notes: list[Note], chord_pcs: set[int]) -> list[Note]:
    """On VARIATION bars: notes a semitone against a chord tone are SNAPPED to
    that chord tone (+-1 semitone) — makes discordant riffs work with the
    progression. Only ever a semitone move, only on clash notes."""
    out: list[Note] = []
    for n in notes:
        pc = n.pitch % 12
        if pc not in chord_pcs:
            for d in (1, -1):
                if (pc + d) % 12 in chord_pcs:
                    out.append(replace(n, pitch=n.pitch + d))
                    break
            else:
                out.append(n)
        else:
            out.append(n)
    return out


def chord_pcs_for_bar(riff: Riff, prog: list[int], bar: int) -> set[int]:
    """Absolute pitch classes of the chord under a (section-local) bar."""
    semi, steps = _scale_steps(riff.key)
    return {(semi + pc) % 12 for pc in _triad_pcs(_chord_for_bar(bar, prog), steps)}


def soften_clashes(notes: list[Note], chord_pcs: set[int],
                   amount: float = 0.85) -> list[Note]:
    """Chord-aware shading: notes a semitone against a chord tone get their
    velocity eased (x amount) so discordant riffs sit better against the
    progression. Velocity ONLY — pitches and timing are never touched, and
    the riff stays the prominent voice."""
    out: list[Note] = []
    for n in notes:
        pc = n.pitch % 12
        rub = pc not in chord_pcs and any(
            (pc - c) % 12 in (1, 11) for c in chord_pcs)
        out.append(replace(n, velocity=max(1, int(n.velocity * amount)))
                   if rub else n)
    return out


def riff_variant(notes: list[Note], variant: str) -> list[Note]:
    """Deterministic riff transforms for non-drop sections. DROPS use riff.notes
    untouched — never route a drop through this function. All transforms are
    octave / timing / velocity ONLY (never off-octave re-pitching), so every
    variant stays inside the riff's own harmony."""
    if variant == "verbatim":
        return notes
    if variant == "sparse":
        picked = [n for n in notes if float(n.start_beats).is_integer()]
        return picked or notes[:1]
    if variant == "sparse_low":
        return [replace(n, pitch=n.pitch - 12) for n in riff_variant(notes, "sparse")]
    if variant == "sparse_high":
        return [replace(n, pitch=n.pitch + 12) for n in riff_variant(notes, "sparse")]
    if variant == "fragment":
        # just the riff's opening half — a question the drop answers
        picked = [n for n in notes if n.start_beats < 2.0]
        return picked or notes[:1]
    if variant == "octave_echo":
        # sparse statement answered two beats later, an octave up and softer
        base = riff_variant(notes, "sparse")
        echo = [replace(n, start_beats=n.start_beats + 2.0, pitch=n.pitch + 12,
                        velocity=max(1, int(n.velocity * 0.6)))
                for n in base if n.start_beats + 2.0 < 4.0]
        return base + echo
    if variant == "call_response":
        # first half of the bar verbatim, answered an octave down and softer
        call = [n for n in notes if n.start_beats < 2.0]
        resp = [replace(n, start_beats=n.start_beats + 2.0, pitch=n.pitch - 12,
                        velocity=max(1, int(n.velocity * 0.75)))
                for n in call if n.start_beats + 2.0 < 4.0]
        return (call + resp) or notes[:1]
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


# Legacy per-genre-bucket feels (variant 0 keeps today's exact behaviour)
_FEEL_OFFBEAT = [(0.5, 0.45, 104), (1.5, 0.45, 104), (2.5, 0.45, 104), (3.5, 0.45, 104)]
_FEEL_DNB_TWOSTEP = [(0.0, 1.5, 106), (2.5, 1.0, 100)]
_FEEL_LONG_SUB = [(0.0, 3.0, 106), (3.0, 1.0, 98)]

# Per-genre bass FEELS: list of variants, each a list of (start, dur, vel)
# root hits within one bar. Variant 0 = the genre's current signature.
_BASS_FEELS: dict[str, list[list[tuple[float, float, int]]]] = {
    "techhouse": [
        _FEEL_OFFBEAT,
        # rolling 8th-pairs, alternating accents
        [(0.5, 0.2, 104), (0.75, 0.2, 86), (1.5, 0.2, 104), (1.75, 0.2, 86),
         (2.5, 0.2, 104), (2.75, 0.2, 86), (3.5, 0.2, 104), (3.75, 0.2, 86)],
        # offbeats answering an octave up (4th tuple slot = octave shift)
        [(0.5, 0.45, 104, 0), (1.5, 0.45, 100, 12),
         (2.5, 0.45, 104, 0), (3.5, 0.45, 100, 12)],
    ],
    "garage": [
        _FEEL_OFFBEAT,
        # 2-step bounce: long-short pairing around the swung skip
        [(0.0, 0.9, 106), (1.75, 0.45, 98), (2.5, 0.9, 104), (3.5, 0.45, 98)],
        # 2-step with octave pops on the skips
        [(0.0, 0.9, 106, 0), (1.75, 0.45, 98, 12),
         (2.5, 0.9, 104, 0), (3.5, 0.45, 98, 12)],
    ],
    "reggaeton": [
        _FEEL_OFFBEAT,
        # tresillo — the dembow's 3+3+2 pulse
        [(0.0, 1.4, 106), (1.5, 1.4, 100), (3.0, 0.9, 98)],
        # tresillo with the last push answered an octave up
        [(0.0, 1.4, 106, 0), (1.5, 1.4, 100, 0), (3.0, 0.9, 98, 12)],
    ],
    "dnb": [
        _FEEL_DNB_TWOSTEP,
        # roller: three pushes across the bar
        [(0.0, 1.4, 106), (2.0, 0.9, 102), (3.0, 0.9, 98)],
        # whole-bar reese drone
        [(0.0, 3.9, 104)],
        # two-step with the answer an octave up
        [(0.0, 1.5, 106, 0), (2.5, 1.0, 100, 12)],
    ],
    "drill": [
        _FEEL_LONG_SUB,
        # kick-locked 808s (mirrors the drill kick placement)
        [(0.0, 1.4, 106), (1.5, 1.4, 102), (3.0, 0.7, 100), (3.75, 0.25, 96)],
    ],
    "hiphop": [
        _FEEL_LONG_SUB,
        # kick-locked boom-bap roots
        [(0.0, 2.4, 106), (2.5, 1.4, 100)],
    ],
}


def _default_feel(genre: str | None) -> list[tuple[float, float, int]]:
    if genre in _OFFBEAT_GENRES:
        return _FEEL_OFFBEAT
    if genre == "dnb":
        return _FEEL_DNB_TWOSTEP
    return _FEEL_LONG_SUB


def bass_feel_for(genre: str | None, variant: int = 0) -> list[tuple[float, float, int]]:
    variants = _BASS_FEELS.get(genre or "")
    if not variants:
        return _default_feel(genre)
    return variants[variant % len(variants)]


def bass_notes(riff: Riff, prog: list[int], bars: int,
               feel: list[tuple] | None = None) -> list[Note]:
    """Chord roots around C2–B2 in a genre feel — `feel` is a list of
    (start_beat, dur, vel[, octave_shift]) hits per bar (default: the genre's
    legacy bucket). The optional 4th element lifts a hit an octave (C3–B3 —
    the classic octave-pop bassline move); the pitch CLASS is always the chord
    root (the root-pc test relies on it). Pitches are absolute (no -24 shift
    downstream — these are not grid notes)."""
    feel = feel if feel is not None else _default_feel(riff.drum_style)
    semi, steps = _scale_steps(riff.key)
    out: list[Note] = []
    for b in range(bars):
        root_pc = (semi + steps[_chord_for_bar(b, prog)]) % 12
        pitch = _fold(36 + root_pc, 36, 47)  # C2..B2
        bar0 = b * 4.0
        for hit in feel:
            start, dur, vel = hit[0], hit[1], hit[2]
            shift = hit[3] if len(hit) > 3 else 0
            out.append(Note(pitch=pitch + shift, velocity=vel,
                            start_beats=bar0 + start, dur_beats=dur))
    return out


# Per-genre pad RHYTHMS: list of variants, each a list of (start_beat, dur)
# chord onsets within one bar. Variant 0 = the genre's signature comping;
# style.pad_rhythm picks. Sustained genres keep the whole-bar wash.
_PAD_RHYTHMS: dict[str, list[list[tuple[float, float]]]] = {
    "garage": [  # organ skank: offbeat 8th stabs / 2-step displaced comping
        [(0.5, 0.4), (1.5, 0.4), (2.5, 0.4), (3.5, 0.4)],
        [(0.5, 0.4), (2.0, 0.3), (2.75, 0.4), (3.75, 0.25)],
    ],
    "techhouse": [  # pluck stabs on the &s / 16th-push comping
        [(1.5, 0.35), (3.5, 0.35)],
        [(0.75, 0.3), (1.5, 0.3), (2.75, 0.3), (3.5, 0.3)],
    ],
    "drill": [  # dark sustain / re-struck tail
        [(0.0, 4.0)],
        [(0.0, 3.0), (3.0, 1.0)],
    ],
    "hiphop": [  # e-piano comping
        [(0.0, 1.75), (2.5, 1.25)],
        [(0.0, 1.0), (1.75, 0.75), (2.5, 1.25)],
    ],
    "reggaeton": [  # dembow-accent plucks / warm wash
        [(0.0, 0.75), (0.75, 0.5), (2.0, 0.75), (2.75, 0.5)],
        [(0.0, 4.0)],
    ],
    "dnb": [  # supersaw wash / half-bar swells
        [(0.0, 4.0)],
        [(0.0, 2.0), (2.0, 2.0)],
    ],
}
_PAD_RHYTHM_DEFAULT: list[tuple[float, float]] = [(0.0, 4.0)]


def pad_rhythm_for(genre: str | None, variant: int = 0) -> list[tuple[float, float]]:
    variants = _PAD_RHYTHMS.get(genre or "", [_PAD_RHYTHM_DEFAULT])
    return variants[variant % len(variants)]


def pad_notes(riff: Riff, prog: list[int], bars: int,
              rhythm: list[tuple[float, float]] | None = None,
              voicing: str = "close") -> list[Note]:
    """Diatonic triad voicings around C4–B5, comped per `rhythm` — a list of
    (start_beat, dur) chord onsets within one bar (default: one whole-bar
    wash). Short stabs hit slightly harder.

    `voicing`: "close" = root position (legacy); "first_inv" = root lifted an
    octave (brighter colour, same pitch classes); "alt" = alternate the two
    per bar (harmonic movement without leaving the triad). All voicings stay
    inside MIDI 60–83."""
    rhythm = rhythm if rhythm is not None else _PAD_RHYTHM_DEFAULT
    semi, steps = _scale_steps(riff.key)
    out: list[Note] = []
    for b in range(bars):
        degree = _chord_for_bar(b, prog)
        root_pc, third_pc, fifth_pc = _triad_pcs(degree, steps)
        root = _fold(60 + (semi + root_pc) % 12, 60, 71)
        third = _fold(60 + (semi + third_pc) % 12, root, root + 11)
        fifth = _fold(60 + (semi + fifth_pc) % 12, third, third + 11)
        invert = voicing == "first_inv" or (voicing == "alt" and b % 2 == 1)
        chord = (root + 12, third, fifth) if invert else (root, third, fifth)
        for start, dur in rhythm:
            vel = 96 if dur < 1.0 else 88
            for pitch in chord:
                out.append(Note(pitch=pitch, velocity=vel,
                                start_beats=b * 4.0 + start, dur_beats=dur))
    return out
