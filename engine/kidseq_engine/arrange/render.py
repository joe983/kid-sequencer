"""Render a SongPlan into full-length mono layers for master().

Each section is rendered separately (riff variant / drum subset / bass / pads) and
overlap-ADDED into the song buffers at its bar offset — renders carry an 0.8s
release tail that must bleed into the next section rather than be cut (clicks).

Layer renderers reuse the riff dispatchers, so every layer gets the same
premium-first fallback chain (sfz/vst > SF2 > numpy) with zero new audio code:
  riff  -> riff_audio(riff.instrument)      looped per bar (drops = verbatim notes)
  bass  -> riff_audio("bass")               one-shot span (bars=1, bar_beats=span)
  pads  -> vst 'pad' patch, else SF2 "pads" GM preset
"""

from __future__ import annotations

from dataclasses import dataclass, replace as dc_replace

import numpy as np

from ..audio import SR, as_stereo, seconds_per_beat
from ..sequence import Riff
from . import (Section, bass_feel_for, bass_notes, choose_progression,
               chord_pcs_for_bar, develop_phrase, drone_notes, pad_notes,
               pad_rhythm_for, plan_song, resolve_clashes, riff_variant,
               soften_clashes)
from .style import LEAD_STACKS, LEAD_VOICES, PAD_ROLES, _sub_rng, choose_style

# phrase-treatment draw weights: statements anchor (~1/3), the rest develop
_TREATMENT_W = {"statement": 0.34, "vary_end": 0.26, "octave_up": 0.12,
                "call_response": 0.15, "sparse_breath": 0.13}
# percussive mode: rhythm-led development — more rests/end-rewrites, fewer
# melodic transforms (the pattern is a groove, not a tune)
_TREATMENT_W_PERC = {"statement": 0.30, "vary_end": 0.30, "octave_up": 0.10,
                     "call_response": 0.10, "sparse_breath": 0.20}


def _phrase_treatment(seed: int, sec_name: str, pi: int, prev: str,
                      weights: dict | None = None) -> str:
    """Seeded per-phrase treatment; the same development never runs twice in a
    row (a repeated statement is fine — that's the anchor)."""
    w_map = weights or _TREATMENT_W
    rng = _sub_rng(seed, f"phrase:{sec_name}:{pi}")
    opts = list(w_map)
    w = np.asarray([w_map[o] for o in opts])
    t = opts[int(rng.choice(len(opts), p=w / w.sum()))]
    return "statement" if (t == prev and t != "statement") else t
from ..render import fx, riff_audio
from ..render.sf_render import default_soundfont, render_riff_sf
from ..render import vst_render
from ..mixmaster import kick_onsets_from_pattern

# voices that keep playing in "lite" drum sections (no kick/snare/sub weight)
_LITE_VOICES = {"hatC", "hatO", "shaker", "rim", "cowbell"}


@dataclass(frozen=True)
class FxFlags:
    """Arrangement-FX switches. Each one null-tests bit-identical when off.
    `throw` None = auto-decide per track via fx.throw_fits(riff)."""
    fx: bool = True           # risers / impacts / crashes / downlifters
    fills: bool = True        # drum fill in the last bar of each build
    automation: bool = True   # filter sweeps (intro/builds/breaks; drops never)
    gap: bool = True          # the pre-drop silence gap
    throw: bool | None = None # riff delay-echo into breaks
    earcandy: bool = True     # phrase-boundary events inside drops (R11)
    beds: bool = True         # rumble bed + odd perc loop in drops (R12)

    @property
    def any_on(self) -> bool:
        return (self.fx or self.fills or self.automation or self.gap
                or self.earcandy or self.beds or self.throw is not False)


def _lite_pattern(pattern: dict) -> dict:
    return {k: v for k, v in pattern.items() if k in _LITE_VOICES}


def _render_pads(notes, tempo: float, span_beats: float, sr: int,
                 pad_role: str = "supersaw") -> np.ndarray:
    """Render the pads layer with the style's genre role: Surge patches for
    synth-family roles, GM presets for keys-family (organ/e-piano/pizz).
    Cross-fallbacks keep SOME pad when a renderer is missing."""
    kind, name = PAD_ROLES.get(pad_role, ("vst", "pad"))
    if kind == "vst" and vst_render.SURGE_VST3.exists():
        return as_stereo(vst_render.render_patch(notes, tempo, name, 1, span_beats, sr))
    if kind == "sf" and default_soundfont():
        return as_stereo(render_riff_sf(notes, tempo, name, 1, span_beats, sr))
    if vst_render.SURGE_VST3.exists():
        return as_stereo(vst_render.render_patch(notes, tempo, "pad", 1, span_beats, sr))
    if default_soundfont():
        return as_stereo(render_riff_sf(notes, tempo, "pads", 1, span_beats, sr))
    return np.zeros((0, 2), dtype=np.float32)  # no pad fallback worth hearing


def _render_texture(kind: str, dur_s: float, sr: int, seed: int, riff) -> np.ndarray:
    """Genre texture bed for one section (the mix calibrates the layer to
    -30 LUFS — subliminal flavour, never a feature)."""
    if kind == "crackle":
        ticks = 4.0 if riff.drum_style == "garage" else 8.0  # garage runs dustier-lighter
        return fx.vinyl_crackle(dur_s, sr, seed + 300, ticks_per_s=ticks)
    if kind == "wash":
        return fx.noise_wash(dur_s, sr, seed + 301)
    if kind == "drone":
        from ..sequence import _scale_steps
        semi, _ = _scale_steps(riff.key)
        root_hz = 440.0 * 2.0 ** ((36 + semi - 69) / 12.0)  # tonic around C2
        return fx.dark_drone(dur_s, sr, seed + 302, root_hz=root_hz)
    if kind == "metal":
        from ..sequence import _scale_steps
        semi, _ = _scale_steps(riff.key)
        root_hz = 440.0 * 2.0 ** ((36 + semi - 69) / 12.0)  # tonic around C2
        return fx.metal_drone(dur_s, sr, seed + 303, root_hz=root_hz)
    return np.zeros((0, 2), dtype=np.float32)


def _render_lead_stack(notes, tempo: float, bars: int, bar_beats: float,
                       sr: int, genre: str | None, stack_i: int) -> np.ndarray:
    """The genre's lead-texture stack: LEAD_STACKS layers summed at their
    per-layer gains, rendered UNDER the main riff voice (which stays untouched
    and dominant — every layer sits >=9 dB down). Each voice routes Surge or
    GM per LEAD_VOICES; a missing renderer just drops that layer."""
    stacks = LEAD_STACKS.get(genre or "")
    if not stacks:
        return np.zeros((0, 2), dtype=np.float32)
    stack = stacks[stack_i % len(stacks)]
    out: np.ndarray | None = None
    for voice, semi, gain_db in stack:
        kind, name = LEAD_VOICES[voice]
        shifted = [dc_replace(n, pitch=min(127, max(0, n.pitch + semi)))
                   for n in notes]
        if kind == "vst" and vst_render.SURGE_VST3.exists():
            sig = as_stereo(vst_render.render_patch(shifted, tempo, name, bars,
                                                    bar_beats, sr))
        elif default_soundfont():
            sf_name = name if kind == "sf" else "pads"
            sig = as_stereo(render_riff_sf(shifted, tempo, sf_name, bars,
                                           bar_beats, sr))
        else:
            continue
        sig = sig * np.float32(10.0 ** (gain_db / 20.0))
        if out is None:
            out = sig.copy()
        else:
            if sig.shape[0] > out.shape[0]:
                out = np.pad(out, ((0, sig.shape[0] - out.shape[0]), (0, 0)))
            out[: sig.shape[0]] += sig
    return out if out is not None else np.zeros((0, 2), dtype=np.float32)


def _sine_sub(notes, tempo: float, span_beats: float, sr: int) -> np.ndarray:
    """A plain sine layer following the bass notes — the Architechs rule:
    garage bass is never one raw patch. The static deep layer under the
    plucky mid (Todd Edwards' Juno square-sub instinct, sine-simplified)."""
    spb = seconds_per_beat(tempo)
    n = int(span_beats * spb * sr) + int(0.1 * sr)
    out = np.zeros(n, dtype=np.float64)
    for nt in notes:
        f = 440.0 * 2.0 ** ((nt.pitch - 69) / 12.0)
        s0 = int(nt.start_beats * spb * sr)
        e0 = min(n, s0 + max(4, int(nt.dur_beats * spb * sr)))
        if s0 < 0 or s0 >= e0:
            continue
        t = np.arange(e0 - s0) / sr
        seg = np.sin(2 * np.pi * f * t)
        atk = min(len(seg), max(2, int(0.008 * sr)))
        seg[:atk] *= np.linspace(0.0, 1.0, atk)
        rel = min(len(seg), max(2, int(0.030 * sr)))
        seg[-rel:] *= np.linspace(1.0, 0.0, rel)
        out[s0:e0] += seg
    return np.stack([out, out], axis=1).astype(np.float32)


def _render_bass(notes, tempo: float, span_beats: float, sr: int,
                 bass_patch: str = "bass",
                 sub_double_db: float | None = None) -> np.ndarray:
    """Render the bass LAYER with the style's genre patch (Surge). Falls back
    to the grid-voice chain (SF2 Lately Bass / numpy synth) without Surge —
    the kid's own 'bass' grid instrument is untouched by this.
    `sub_double_db` layers a sine sub under the patch at that level relative
    to the patch's peak (garage: never raw bass)."""
    if vst_render.SURGE_VST3.exists() and bass_patch in vst_render.PATCHES:
        sig = as_stereo(vst_render.render_patch(notes, tempo, bass_patch, 1,
                                                span_beats, sr))
    else:
        sig = riff_audio(notes, tempo, "bass", 1, span_beats, sr)
    if sub_double_db is not None and sig.size:
        sub = _sine_sub(notes, tempo, span_beats, sr)
        peak_sig = float(np.max(np.abs(sig)))
        peak_sub = float(np.max(np.abs(sub)))
        if peak_sig > 1e-9 and peak_sub > 1e-9:
            sub = sub * np.float32(peak_sig * 10.0 ** (sub_double_db / 20.0)
                                   / peak_sub)
            out = sig.copy()
            m = min(out.shape[0], sub.shape[0])
            out[:m] += sub[:m]
            return out
    return sig


def _add_at(buf: np.ndarray, sig: np.ndarray, start: int) -> None:
    # buf and sig are both (N, 2); slicing on axis 0 overlap-adds correctly.
    if start < 0:  # e.g. a reverse-crash into a cold-open drop at sample 0
        sig = sig[-start:]
        start = 0
    end = min(len(buf), start + len(sig))
    if end > start:
        buf[start:end] += sig[: end - start]


def _fill_pattern(style: str | None, shape: int | None = None) -> dict:
    """Build-tail fill (last bar of a build), by shape: 0 = backbeat roll
    (8ths → 16ths, ramping velocity), 1 = rim-led landing on the backbeat,
    2 = hat-roll landing on the backbeat, 4 = rug-pull 16th roll that stops
    dead at beat 3 (the silence IS the tension — Adam Douglas). Shape 3 (the
    2-bar subdivision-doubling roll) lives in _fill_bars. The final 16th
    ALWAYS stays EMPTY (it butts into the Gap). Techhouse's backbeat voice is
    the CLAP — its kit has no snare (rolling a missing voice rendered
    silence)."""
    ramp8 = [0.45, 0, 0.52, 0, 0.60, 0, 0.68, 0]
    ramp16 = [0.72, 0.76, 0.81, 0.85, 0.90, 0.94, 0.98, 0.0]
    lead = "clap" if style == "techhouse" else "snare"
    if shape is None:  # legacy auto-shape
        shape = 1 if style in ("drill", "hiphop") else 0
    if shape == 1:
        return {"rim": ramp8 + [0.0] * 8, lead: [0.0] * 8 + ramp16}
    if shape == 2:
        return {"hatC": [.50, .55, .60, .65, .70, .75, .80, .85,
                         .88, .90, .92, .94, .96, .98, 1.0, 0.0],
                lead: [0.0] * 12 + [0.85, 0.90, 0.95, 0.0]}
    if shape == 4:
        return {lead: [0.50, 0.55, 0.60, 0.64, 0.68, 0.72, 0.76, 0.80,
                       0.84, 0.88, 0.92, 0.95, 0.0, 0.0, 0.0, 0.0]}
    return {lead: ramp8 + ramp16}


def _fill_bars(style: str | None, shape: int, build_bars: int) -> list[dict]:
    """Fill as a list of 1-bar patterns placed back-to-back ending at the
    build end. Shape 3 = the 2-bar subdivision-doubling roll (quarters →
    8ths in bar one, 8ths → 16ths in bar two, velocity ramping straight
    through — Adam Douglas' build mechanics); degrades to shape 0 when the
    build is only 1 bar."""
    if shape == 3:
        if build_bars >= 2:
            lead = "clap" if style == "techhouse" else "snare"
            bar_a = {lead: [0.45, 0, 0, 0, 0.52, 0, 0, 0,
                            0.58, 0, 0.62, 0, 0.66, 0, 0.70, 0]}
            bar_b = {lead: [0.72, 0, 0.75, 0, 0.78, 0, 0.81, 0,
                            0.84, 0.86, 0.89, 0.91, 0.93, 0.95, 0.98, 0.0]}
            return [bar_a, bar_b]
        shape = 0
    return [_fill_pattern(style, shape)]


# R18 drummer scheduler: gesture cadence per personality (bars)
_DRUMMER_EVERY = {"busy": 4, "regular": 8, "sparse": 16}


def _candy_bar_set(sec_bars: int, drop_index: int, every: int) -> set[int]:
    """The phrase-boundary bars _candy_slots would use for one drop section —
    the drummer scheduler stays out of their way. Computed from the palette
    (NOT FxFlags) so gesture placement never depends on flag configs."""
    if not every:
        return set()
    return {b for b in range(every, sec_bars, every)
            if not (drop_index == 1 and b < 8) and b <= sec_bars - 2}


def _drummer_gestures(seed: int, sec_name: str, sec_bars: int, drummer: str,
                      drop_index: int, candy_bars: set[int],
                      genre: str | None) -> dict[int, str]:
    """bar_index -> gesture for one drop section (R18 — owner: fills/changes
    every 2/4/8/16 bars like a real drummer, but not every tune). The gesture
    occupies the bar LEADING INTO each phrase boundary (a drummer fills into
    the next phrase). Hook protection mirrors _candy_slots: drop 1's first 8
    bars stay pure. Deterministic per (seed, section, bar)."""
    every = _DRUMMER_EVERY.get(drummer)
    if not every:
        return {}
    menu = ["minifill", "overlay_swap", "hat_lift", "ghost_add", "none"]
    w = [0.28, 0.24, 0.18, 0.15, 0.15]
    if genre != "techhouse":   # never break the four-on-floor
        menu = menu + ["kick_skip"]
        w = [0.26, 0.22, 0.16, 0.12, 0.12, 0.12]
    wa = np.asarray(w) / sum(w)
    out: dict[int, str] = {}
    for b in range(every, sec_bars + 1, every):
        if drop_index == 1 and b <= 8:
            continue
        if b in candy_bars:
            continue
        gb = b - 1
        if gb <= 0:
            continue
        rng = _sub_rng(seed, f"drummer:{sec_name}:{b}")
        g = menu[int(rng.choice(len(menu), p=wa))]
        if g != "none":
            out[gb] = g
    return out


def _gesture_pattern(base: dict, gesture: str, style: str | None,
                     swapped: dict | None,
                     fill_shape: int) -> dict:
    """One bar's pattern with a drummer gesture applied. All transforms stay
    inside the genre's own vocabulary — reduced-velocity fill rows, a one-bar
    seasoning swap, a hat lift, ghost-snare chatter, or a dropped back-half
    kick. Pure: never mutates `base`."""
    lead = "clap" if style == "techhouse" else "snare"
    if gesture == "hat_lift":
        return {k: v for k, v in base.items()
                if k in ("kick", "snare", "clap", "sub")}
    if gesture == "overlay_swap" and swapped is not None:
        return swapped
    if gesture == "ghost_add":
        merged = dict(base)
        row = list(merged.get(lead) or [0.0] * 16)
        for i, v in ((6, 0.18), (9, 0.22), (14, 0.18)):
            row[i] = max(row[i], v)
        merged[lead] = row
        return merged
    if gesture == "kick_skip":
        merged = dict(base)
        row = list(merged.get("kick") or [0.0] * 16)
        for i in range(8, 16):
            row[i] = 0.0
        merged["kick"] = row
        return merged
    if gesture == "minifill":
        merged = dict(base)
        for voice, steps in _fill_pattern(style, fill_shape).items():
            row = list(merged.get(voice) or [0.0] * 16)
            merged[voice] = [max(a, b * 0.65) for a, b in zip(row, steps)]
        return merged
    return base


def _lpf_sweep(seg: np.ndarray, sr: int, f0: float, f1: float) -> np.ndarray:
    """LadderFilter LPF12 sweep f0→f1 (exp) across the segment, 1024-sample
    hops with carried state. f0 == f1 gives a fixed filter."""
    from pedalboard import LadderFilter

    filt = LadderFilter(mode=LadderFilter.Mode.LPF12, cutoff_hz=f0, resonance=0.15)
    n = seg.shape[0]
    out = np.empty_like(seg)
    hop = 1024
    for s in range(0, n, hop):
        e = min(n, s + hop)
        frac = (s + hop * 0.5) / n
        filt.cutoff_hz = float(f0 * (f1 / f0) ** min(frac, 1.0))
        out[s:e] = filt.process(seg[s:e], sr, reset=False)
    return out.astype(np.float32)


def _candy_slots(bounds, every: int, bar_s: float, sr: int) -> list[tuple[int, str, int]]:
    """Phrase-boundary ear-candy slots inside drop sections (Camo & Krooked:
    a small event every 4-8 bars). HOOK PROTECTION: never inside drop 1's
    first 8 bars (the pure hook statement stays clean), never within one bar
    of a section boundary (transition FX own those). Returns
    (sample_pos, section_name, bar_index) — deterministic, pure."""
    if not every:
        return []
    slots = []
    drop_i = 0
    for sec, a, e in bounds:
        if not sec.name.startswith("drop"):
            continue
        drop_i += 1
        for b in range(every, sec.bars, every):
            if drop_i == 1 and b < 8:
                continue
            if b > sec.bars - 2:
                continue
            slots.append((a + int(b * bar_s * sr), sec.name, b))
    return slots


def _gap_samples(gap_beats: float, spb: float, sr: int) -> int:
    """Pre-drop gap length in samples: the palette's beat count, clamped to
    1.1 s so a 2-beat cut at tempo 40 doesn't read as 3 s of dead air."""
    return int(min(gap_beats * spb, 1.1) * sr)


def _apply_gap(layers: dict, drop_starts: list[int], sr: int, spb: float,
               gap_beats: float, exempt: tuple = ()) -> None:
    """THE GAP: everything cuts to silence before each drop — the pre-drop
    breath. The pros cut a REAL one (up to 2 beats, Attack's 'Good Life'
    analysis); the palette picks the length per press. 3 ms cosine edges (no
    clicks), hard back in exactly at the drop sample. Layers named in
    `exempt` keep running through the silence (KSHMR: carry one element)."""
    edge = max(2, int(0.003 * sr))
    gap_n = _gap_samples(gap_beats, spb, sr)
    for d in drop_starts:
        g0 = d - gap_n
        if g0 <= edge:
            continue
        for name, buf in layers.items():
            if name in exempt or buf.shape[0] < d:
                continue
            t = np.linspace(0.0, np.pi, edge)
            buf[g0 - edge:g0] *= ((1.0 + np.cos(t)) * 0.5)[:, None]  # fade out
            buf[g0:d] = 0.0


def build_song(riff: Riff, sr: int = SR, plan: list[Section] | None = None,
               flags: FxFlags | None = None, variation: int = 0):
    """Arrange + render the full song.

    Returns (layers, kick_onsets, plan, prog):
      layers = {"riff","drums","bass","pads"[,"fx"]} full-length stereo (N, 2)
      float32 (empty arrays dropped), kick_onsets = pump triggers only where a
      full kit plays. `plan` overrides plan_song (tests); `flags` gates the
      arrangement FX (all on by default; throw auto-decided from the riff).
      `variation` is the per-press nonce: progression colour, build:drop split
      and every FX seed vary with it — the riff itself NEVER does.
    """
    style = choose_style(riff, variation)
    pal = style.fx_palette
    plan = plan if plan is not None else plan_song(riff.tempo, variation,
                                                   structure=style.structure)
    # breaks take the style's riff transform (octave_echo / call_response /
    # sparse_low); drops are untouchable and intros keep their character
    plan = [dc_replace(s, riff_variant=style.riff_break_variant)
            if s.name.startswith("break") and s.riff_variant == "sparse_low" else s
            for s in plan]
    flags = flags if flags is not None else FxFlags()
    prog = choose_progression(riff, variation, pick=style.prog_pick)
    percussive = style.production_mode == "percussive"
    if percussive:
        # Photek move: no chord movement under a non-harmonic pattern — the
        # bass PEDALS (static root, or a root->fifth pedal shift for motion
        # without harmony; variation-picked), drone instead of chord pads
        prog = ([0, 0, 0, 0], [0, 0, 4, 4])[style.percussive_pedal % 2]
    spb = seconds_per_beat(riff.tempo)
    bar_s = riff.bar_beats * spb
    seed = fx.song_seed(riff, variation)

    total_bars = sum(s.bars for s in plan)
    n = int((total_bars * bar_s + 1.0) * sr)
    layers = {name: np.zeros((n, 2), dtype=np.float32)
              for name in ("riff", "drums", "bass", "pads", "texture", "fx",
                           "fx_sub", "rumble")}
    kick_onsets: list[int] = []

    from ..render.drums import pattern_for
    pattern = pattern_for(riff.drum_style, style.drum_variant,
                          style.drum_skeleton) if riff.drum_style else None
    takes = style.drum_takes   # per-press sample-take swaps (R17)

    # ---- base section renders + boundary map -------------------------------
    bounds: list[tuple[Section, int, int]] = []   # (section, start, end) samples
    bar = 0
    drop_seen = 0   # drop 1 = the pure verbatim hook statement (never ornamented)
    for sec in plan:
        at = int(bar * bar_s * sr)
        end = int((bar + sec.bars) * bar_s * sr)
        bounds.append((sec, at, end))
        span_beats = sec.bars * riff.bar_beats

        if sec.riff_variant:
            is_drop = sec.name.startswith("drop")
            if is_drop:
                drop_seen += 1
            if sec.riff_variant == "verbatim":
                # MOTIF DEVELOPMENT: the riff is developed PHRASE BY PHRASE
                # (4 bars), the way a producer keeps a 1-bar motif interesting
                # for 3 minutes — statements anchor (~1/3, and the first two
                # phrases of drop 1 are always pure: the hook), the rest
                # transform: varied endings, whole-phrase octave lifts,
                # call-and-response answers, breathing space. Rewritten bars
                # snap clash notes to chord tones; pure post-hook bars get
                # velocity-only shading. The motif is never lost.
                pure_phrases = 2 if (is_drop and drop_seen == 1) else 0
                target = min(riff.notes, key=lambda n: n.start_beats).pitch
                span_notes = []
                var_i = 0
                prev_t = ""
                for pi in range(max(1, sec.bars // 4)):
                    if pi < pure_phrases:
                        treatment = "statement"
                    else:
                        treatment = _phrase_treatment(
                            seed, sec.name, pi, prev_t,
                            _TREATMENT_W_PERC if percussive else None)
                    prev_t = treatment
                    if treatment == "vary_end":
                        kind = style.riff_ornament if var_i % 2 == 0 \
                            else style.riff_ornament_b
                        var_i += 1
                    else:
                        kind = style.riff_ornament
                    pbars = develop_phrase(riff.notes, treatment, riff.key,
                                           vary_kind=kind, target_pitch=target,
                                           phrase_bars=min(4, sec.bars - pi * 4))
                    for bi, bar_notes in enumerate(pbars):
                        b = pi * 4 + bi
                        # percussive mode: no chords to clash with — leave the
                        # pattern's own character alone
                        if b >= pure_phrases * 4 and not percussive:
                            pcs = chord_pcs_for_bar(riff, prog, b)
                            bar_notes = resolve_clashes(bar_notes, pcs) \
                                if bar_notes != riff.notes else \
                                soften_clashes(bar_notes, pcs)
                        span_notes += [dc_replace(nt, start_beats=nt.start_beats
                                                  + b * riff.bar_beats)
                                       for nt in bar_notes]
                sig = riff_audio(span_notes, riff.tempo, riff.instrument,
                                 1, span_beats, sr)
                _add_at(layers["riff"], sig, at)
                # the genre lead STACK: always-on texture layers under the
                # kid's instrument (>=9 dB down each — the riff stays on top).
                # CRITICAL: the stack renders the SAME developed span as the
                # main voice — doubling the original riff against a developed
                # phrase played two melodies at once (owner heard it as
                # discordance in the garage take).
                # R20: some takes carry NO stack — the kid's voice + rhythm
                # section stand alone (owner: not every song needs layers)
                if style.lead_stack is not None:
                    stk = _render_lead_stack(span_notes, riff.tempo, 1,
                                             span_beats, sr, riff.drum_style,
                                             style.lead_stack)
                    _add_at(layers["riff"], stk, at)
            else:
                notes = riff_variant(riff.notes, sec.riff_variant)
                if notes:
                    sig = riff_audio(notes, riff.tempo, riff.instrument,
                                     sec.bars, riff.bar_beats, sr)
                    _add_at(layers["riff"], sig, at)

        gestures: dict[int, str] = {}
        if sec.drums and pattern:
            variant_eff = style.drum_variant
            base_pat = pattern
            if percussive and sec.name.startswith("drop"):
                # drum-led evolution: each drop rotates to a different
                # seasoning overlay (the kit does the developing)
                variant_eff = style.drum_variant + (drop_seen - 1)
                base_pat = pattern_for(riff.drum_style, variant_eff,
                                       style.drum_skeleton)
            pat = base_pat if sec.drums == "full" else _lite_pattern(base_pat)
            if sec.drums == "full" and sec.name.startswith("drop"):
                # R18 drummer scheduler: per-press personality drops small
                # gestures on phrase boundaries INSIDE the drop
                gestures = _drummer_gestures(
                    seed, sec.name, sec.bars, style.drummer, drop_seen,
                    _candy_bar_set(sec.bars, drop_seen, pal.earcandy_every),
                    riff.drum_style)
            if pat and gestures:
                from ..render import drums_audio_pattern
                swapped = pattern_for(riff.drum_style, variant_eff + 1,
                                      style.drum_skeleton)
                for b in range(sec.bars):
                    bpat = pat
                    if b in gestures:
                        bpat = _gesture_pattern(pat, gestures[b],
                                                riff.drum_style, swapped,
                                                pal.fill_shape)
                    b_at = at + int(b * bar_s * sr)
                    sig = drums_audio_pattern(riff.drum_style, bpat,
                                              riff.tempo, 1, sr, takes=takes)
                    _add_at(layers["drums"], sig, b_at)
                    # pump triggers from the bar's ACTUAL kicks (kick_skip
                    # bars must not duck the mix against silence)
                    kick_onsets += [b_at + o for o in
                                    kick_onsets_from_pattern(
                                        bpat, riff.tempo, 1, sr,
                                        style=riff.drum_style)]
            elif pat:
                from ..render import drums_audio_pattern
                sig = drums_audio_pattern(riff.drum_style, pat, riff.tempo,
                                          sec.bars, sr, takes=takes)
                _add_at(layers["drums"], sig, at)
                if sec.drums == "full":
                    kick_onsets += [at + o for o in
                                    kick_onsets_from_pattern(pattern, riff.tempo, sec.bars, sr,
                                                              style=riff.drum_style)]

        if sec.bass:
            feel = bass_feel_for(riff.drum_style, style.bass_feel)
            notes = bass_notes(riff, prog, sec.bars, feel=feel,
                               gate=style.bass_gate)
            # R18: the bass answers the drummer's fill bars — the bar's final
            # note pops an octave (small, feel-aware; drums and bass move
            # together the way a live rhythm section does)
            for gb, g in sorted(gestures.items()):
                if g != "minifill":
                    continue
                lo, hi = gb * riff.bar_beats, (gb + 1) * riff.bar_beats
                idx = [i for i, nt in enumerate(notes)
                       if lo <= nt.start_beats < hi]
                if idx:
                    i = idx[-1]
                    notes[i] = dc_replace(notes[i],
                                          pitch=min(127, notes[i].pitch + 12))
            # garage bass is never raw (Architechs): plucky/FM patches get a
            # sine sub layered -12 dB underneath
            sub_db = -12.0 if (riff.drum_style == "garage"
                               and style.bass_patch in ("bass_pluck", "bass_fm")) \
                else None
            sig = _render_bass(notes, riff.tempo, span_beats, sr,
                               style.bass_patch, sub_double_db=sub_db)
            _add_at(layers["bass"], sig, at)

        if sec.pads:
            if percussive and style.percussive_pads == "none":
                # the TRUE Photek treatment (owner R16): NO pads, NO drones,
                # no synth long notes — just the hits, the bass pedal and the
                # texture bed carrying the dark space
                sig = np.zeros((0, 2), dtype=np.float32)
            elif percussive:
                # open-fifth drone (no third — nothing for a discordant riff
                # to clash with); role + voicing vary per press so percussive
                # tracks don't all share one drone sound
                notes = drone_notes(riff, sec.bars, voicing=style.pad_rhythm)
                sig = _render_pads(notes, riff.tempo, span_beats, sr,
                                   style.pad_role)
            elif not style.pads_on:
                # R20 sparse take: no pads/long sounds — riff + bass + drums
                # (+ texture, guaranteed by choose_style when the stack is
                # also out) carry the whole arrangement
                sig = np.zeros((0, 2), dtype=np.float32)
            else:
                rhythm = pad_rhythm_for(riff.drum_style, style.pad_rhythm)
                notes = pad_notes(riff, prog, sec.bars, rhythm=rhythm,
                                  voicing=style.pad_voicing)
                sig = _render_pads(notes, riff.tempo, span_beats, sr, style.pad_role)
            _add_at(layers["pads"], sig, at)

        bar += sec.bars

    # ---- genre texture bed (builds+drops; percussive mode runs it edge to
    # edge — intro/outro included — as the sound-development bed). The -30
    # LUFS layer calibration keeps it subliminal. --------------------------
    if style.texture:
        if percussive:
            tex_names = ("build", "drop", "intro", "outro")
        elif riff.drum_style == "hiphop" and style.texture == "crackle":
            # Premier: 'hip-hop is grimy and dirty, so keep it dirty' — the
            # crackle bed runs edge to edge, drops included
            tex_names = ("build", "drop", "intro", "outro", "break")
        else:
            tex_names = ("build", "drop")
        for s, a, e in bounds:
            if s.name.startswith(tex_names):
                sig = _render_texture(style.texture, (e - a) / sr, sr, seed, riff)
                _add_at(layers["texture"], sig, a)

    # ---- arrangement FX on top of the base ---------------------------------
    drops = [(i, s, a, e) for i, (s, a, e) in enumerate(bounds) if s.name.startswith("drop")]
    builds = {i: (s, a, e) for i, (s, a, e) in enumerate(bounds) if s.name.startswith("build")}
    breaks = [(s, a, e) for s, a, e in bounds if s.name.startswith("break")]
    quiet_fx_db = -5.0 if riff.drum_style in ("drill", "hiphop") else 0.0
    fx_g = 10.0 ** (quiet_fx_db / 20.0)

    # INTO-the-boundary FX (riser / spinback / reverse crash) end at the GAP
    # start, not the drop sample — a real gap chopping the crescendo peak
    # kills both the riser and the silence. AT-boundary FX stay on the drop.
    gap_n = _gap_samples(pal.gap_beats, spb, sr) if flags.gap else 0

    if flags.fx:
        for k, (idx, sec, a, e) in enumerate(drops):
            later = k >= 1  # drop2 onwards escalates
            prev = bounds[idx - 1] if idx > 0 else None
            if pal.riser_on and prev and prev[0].name.startswith("build"):
                b_sec, b_a, b_e = prev
                # KSHMR restraint: one prominent riser per track (the first
                # drop); later drops get a half riser, reverse-only, or none
                mode = "full"
                if later and pal.riser_restraint:
                    rng = _sub_rng(seed, f"riser_later:{idx}")
                    mode = ("half", "reverse_only", "none")[
                        int(rng.choice(3, p=[0.45, 0.35, 0.20]))]
                if mode in ("full", "half"):
                    if pal.riser_kind == "spinback":
                        # vinyl brake into the drop — short, ends at the gap
                        sig = fx.spinback(min(2.0, 2 * bar_s), sr, seed + idx)
                    else:
                        riser_bars = min(pal.riser_bars, b_sec.bars)
                        if mode == "half":
                            riser_bars = max(1, riser_bars // 2)
                        dur = riser_bars * bar_s
                        if pal.riser_style == "shepard" and mode == "full":
                            sig = fx.shepard_riser(dur, sr, seed + idx,
                                                   peak_db=pal.riser_db,
                                                   f0=pal.riser_f0,
                                                   f1=pal.riser_f1)
                        else:
                            depth = min(0.85, pal.gate_depth
                                        + (0.2 if later else 0.0))
                            sig = fx.riser(dur, sr, seed + idx,
                                           gate_hz=4.0 / spb, gate_depth=depth,
                                           peak_db=pal.riser_db,
                                           f0=pal.riser_f0, f1=pal.riser_f1,
                                           color=pal.riser_color)
                    if mode == "half":
                        sig = sig * np.float32(10.0 ** (-6.0 / 20.0))
                    _add_at(layers["fx"], sig * fx_g, a - gap_n - sig.shape[0])
            cr = fx.crash(sr, seed + 100 + idx)
            _add_at(layers["fx"], cr * fx_g, a)
            if pal.reverse_crash_on:
                _add_at(layers["fx"], fx.reverse_crash(cr, sr),
                        a - gap_n - cr.shape[0])
            imp = fx.impact(sr, peak_db=pal.impact_db,
                            f0=pal.impact_f0, f1=pal.impact_f1)
            _add_at(layers["fx"], imp, a)
            if later:  # doubled impact on later drops
                _add_at(layers["fx"], imp * 0.5, a + int(0.010 * sr))
            if later and pal.swell_kind:
                # reverse swell from the track's OWN riff (808Melo / Swivel):
                # the bar before the boundary, effect-printed backwards so the
                # tail crescendos INTO the drop. Ends at the gap start.
                b0 = max(0, (a - gap_n) - int(bar_s * sr))
                sw = fx.reverse_swell(layers["riff"][b0:a - gap_n].copy(), sr,
                                      pal.swell_kind, delay_s=0.25 * spb)
                if sw.size:
                    _add_at(layers["fx"], sw * fx_g, (a - gap_n) - sw.shape[0])
            nxt = bounds[idx + 1] if idx + 1 < len(bounds) else None
            if pal.downlifter_on and nxt and nxt[0].name.startswith("break"):
                _add_at(layers["fx"], fx.downlifter(2 * bar_s, sr, seed + 500 + idx),
                        nxt[1])
        if pal.scratch_on and len(drops) >= 2:
            # Premier's rule: ONE turntable gesture per record — entering the
            # second drop (the hook return), never repeated
            sc = fx.scratch(sr, seed + 555)
            _add_at(layers["fx"], sc * fx_g, drops[1][2] - gap_n - sc.shape[0])
        for sec, a, e in breaks:
            _add_at(layers["fx"], fx.crash(sr, seed + 200) * fx_g, a)
            if pal.bomb_on:
                # 'The Bomb' (Attack): energy-exit punctuation at the break
                # start; the sub path rides the dedicated fx_sub layer
                _add_at(layers["fx_sub"], fx.bomb(sr, seed + 400) * fx_g, a)
        if pal.drop_open == "no_pads":
            # the adapted 'Battle' opening (UKG): pads sit out of each drop's
            # first 2 bars — riff + bass + drums carry the entry
            for k, (idx, sec, a, e) in enumerate(drops):
                e0 = min(n, a + int(2 * bar_s * sr), e)
                if e0 <= a:
                    continue
                g = np.zeros(e0 - a, dtype=np.float32)
                ramp = max(2, min(int(0.050 * sr), e0 - a))
                g[-ramp:] = np.linspace(0.0, 1.0, ramp, dtype=np.float32)
                layers["pads"][a:e0] *= g[:, None]

    if flags.fills and pattern:
        from ..render import drums_audio_pattern
        from ..render.sample_kit import render_fill_sample
        # R17: a per-press take may swap the synthesized fill for one of the
        # owner's REAL breakbeat fills (dnb). The fill takes over — a real
        # drummer stops the groove to play it — so the kit is cut for the
        # fill's musical span; render_fill_sample returns None (→ legacy
        # synth fill) without assets or past the stretch guard.
        sampled = (render_fill_sample(riff.drum_style, pal.fill_take,
                                      riff.tempo, sr)
                   if pal.fill_take else None)
        for i, (b_sec, b_a, b_e) in builds.items():
            if sampled is not None:
                sig, beats = sampled
                f0 = max(b_a, b_e - int(beats * spb * sr))
                edge = max(2, int(0.003 * sr))
                if f0 > edge:
                    fade = ((1.0 + np.cos(np.linspace(0.0, np.pi, edge)))
                            * 0.5)[:, None]
                    layers["drums"][f0 - edge:f0] *= fade
                layers["drums"][f0:b_e] = 0.0
                _add_at(layers["drums"], sig, f0)
                continue
            bars = _fill_bars(riff.drum_style, pal.fill_shape, b_sec.bars)
            for bi, pat in enumerate(bars):
                fill_at = b_e - int((len(bars) - bi) * bar_s * sr)
                sig = drums_audio_pattern(riff.drum_style, pat, riff.tempo, 1,
                                          sr, takes=takes)
                _add_at(layers["drums"], sig, fill_at)

    if flags.automation:
        for sec, a, e in bounds:
            e2 = min(e, n)
            if sec.name == "intro" and pal.intro_lpf < 15000.0:
                layers["riff"][a:e2] = _lpf_sweep(layers["riff"][a:e2], sr,
                                                  pal.intro_lpf, pal.intro_lpf)
            elif sec.name.startswith("build"):
                for lname in ("riff", "pads"):
                    layers[lname][a:e2] = _lpf_sweep(layers[lname][a:e2], sr, 900.0, 18000.0)
                # Noisia low-end starvation: HP the bass for the build's final
                # bars so the drop's bass lands as pure contrast. 30 ms seam
                # crossfade in; the gap + drop impact mask the exit seam.
                if pal.bass_starve_bars:
                    s0 = max(a, e2 - int(pal.bass_starve_bars * bar_s * sr))
                    seg = layers["bass"][s0:e2]
                    if seg.shape[0] > int(0.060 * sr):
                        from pedalboard import HighpassFilter, Pedalboard
                        board = Pedalboard(
                            [HighpassFilter(cutoff_frequency_hz=180.0)])
                        wet = np.asarray(board(seg.astype(np.float32), sr),
                                         dtype=np.float32)
                        xf = max(2, int(0.030 * sr))
                        mix = np.ones(seg.shape[0], dtype=np.float32)
                        mix[:xf] = np.linspace(0.0, 1.0, xf, dtype=np.float32)
                        layers["bass"][s0:e2] = (seg * (1.0 - mix[:, None])
                                                 + wet * mix[:, None])
            elif sec.name.startswith("break"):
                two = min(e2, a + int(2 * bar_s * sr))
                layers["pads"][a:two] = _lpf_sweep(layers["pads"][a:two], sr, 18000.0, 4000.0)
                if two < e2:
                    layers["pads"][two:e2] = _lpf_sweep(layers["pads"][two:e2], sr, 4000.0, 4000.0)
            # drops + outro: never touched (riff-verbatim null test relies on it)

    # drop2+ escalation: hotter kit/pads + pad octave-double (pads are not the
    # riff). Mode from the style: "full" = both, "gain_only" = no octave
    # double, "off" = later drops stay level with the first.
    if style.structure.escalation != "off":
        for k, (idx, sec, a, e) in enumerate(drops):
            if k == 0:
                continue
            e2 = min(e, n)
            ramp = max(2, int(0.020 * sr))
            for lname, db in (("drums", 0.8), ("pads", 1.0)):
                g = np.full(e2 - a, 10.0 ** (db / 20.0), dtype=np.float32)
                g[:ramp] = np.linspace(1.0, g[-1], ramp)
                g[-ramp:] = np.linspace(g[-1], 1.0, ramp)
                layers[lname][a:e2] *= g[:, None]
            if sec.pads and style.structure.escalation == "full" and \
                    not (percussive and style.percussive_pads == "none") and \
                    (percussive or style.pads_on):
                # pad-free Photek takes stay pad-free through escalation too;
                # drone takes escalate with the DRONE an octave up (chord
                # doubles would break the no-chord-ops percussive doctrine)
                if percussive:
                    hi = [dc_replace(nt, pitch=nt.pitch + 12)
                          for nt in drone_notes(riff, sec.bars,
                                                voicing=style.pad_rhythm)]
                else:
                    rhythm = pad_rhythm_for(riff.drum_style, style.pad_rhythm)
                    hi = [dc_replace(nt, pitch=nt.pitch + 12)
                          for nt in pad_notes(riff, prog, sec.bars, rhythm=rhythm,
                                              voicing=style.pad_voicing)]
                sig = _render_pads(hi, riff.tempo, sec.bars * riff.bar_beats, sr,
                                   style.pad_role)
                _add_at(layers["pads"], sig * 0.5, a)

    # riff delay-throw into breaks — auto-decided per track unless forced.
    # flags.throw (tests) wins; then the palette may suppress an eligible throw
    if flags.throw is not None:
        do_throw = flags.throw
    elif pal.throw is False:
        do_throw = False
    else:
        do_throw = fx.throw_fits(riff)
    if do_throw and breaks:
        # the riff's final half-bar (beats 2..4), shifted to start at zero
        half_bar = riff.bar_beats / 2.0
        tail_notes = [dc_replace(nt, start_beats=max(0.0, nt.start_beats - half_bar))
                      for nt in riff.notes if nt.start_beats + nt.dur_beats > half_bar]
        if tail_notes:
            from pedalboard import Delay, HighpassFilter, Pedalboard
            half = riff_audio(tail_notes, riff.tempo, riff.instrument, 1, half_bar, sr)
            board = Pedalboard([Delay(delay_seconds=0.75 * spb, feedback=0.45, mix=1.0),
                                HighpassFilter(cutoff_frequency_hz=300.0)])
            wet = np.asarray(board(half.astype(np.float32), sr), dtype=np.float32)
            keep = min(wet.shape[0], int(2.5 * sr))
            wet = wet[:keep].copy()
            fade = max(2, int(0.2 * sr))
            wet[-fade:] *= np.linspace(1.0, 0.0, fade)[:, None]
            # ping-pong: first tap right of centre, next tap left, one tap later
            from ..audio import pan_stereo
            w_mono = wet.mean(axis=1)
            pp = pan_stereo(w_mono, 0.4)
            tap = int(0.75 * spb * sr)
            pp2 = pan_stereo(w_mono * 0.45, -0.4)
            for sec, a, e in breaks:
                _add_at(layers["fx"], pp * (10.0 ** (-10.0 / 20.0)), a)
                _add_at(layers["fx"], pp2 * (10.0 ** (-10.0 / 20.0)), a + tap)

    # ---- phrase-boundary ear candy inside drops (R11). Breath-level events
    # every 4-8 bars keep long drops alive without touching the riff. --------
    if flags.earcandy and pal.earcandy_every and pal.earcandy_menu:
        from ..render import drums_audio_pattern
        chirp_seed = seed + 777   # 808Melo signature: the SAME chirp each time
        for pos, sname, b in _candy_slots(bounds, pal.earcandy_every, bar_s, sr):
            rng = _sub_rng(seed, f"candy:{sname}:{b}")
            kind = pal.earcandy_menu[int(rng.choice(len(pal.earcandy_menu)))]
            if kind == "drum_stop":
                # Tainy: a 1-2 beat drum+bass stop 'so it doesn't get boring';
                # the riff keeps singing. Muted kicks leave the pump list too
                # (never duck the mix against silence).
                beats = (1, 2)[int(rng.choice(2))]
                s0, e0 = pos, min(n, pos + int(beats * spb * sr))
                edge = max(2, int(0.003 * sr))
                for lname in ("drums", "bass"):
                    fadeout = ((1.0 + np.cos(np.linspace(0.0, np.pi, edge)))
                               * 0.5)[:, None]
                    layers[lname][s0 - edge:s0] *= fadeout
                    layers[lname][s0:e0] = 0.0
                kick_onsets = [o for o in kick_onsets if not (s0 <= o < e0)]
                continue
            if kind == "kick_fill":
                # UKG vocabulary: a 2-beat kick pickup INTO the phrase boundary
                pat = {"kick": [0.0] * 8 + [0.55, 0, 0.65, 0, 0.75, 0, 0.85, 0]}
                sig = drums_audio_pattern(riff.drum_style, pat, riff.tempo, 1,
                                          sr, takes=takes)
                _add_at(layers["drums"], sig * 0.8, pos - int(bar_s * sr))
                continue
            if kind in ("rev_swell_riff", "rev_swell_delay"):
                b0 = max(0, pos - int(bar_s * sr))
                mode = "reverb" if kind == "rev_swell_riff" else "delay"
                sig = fx.reverse_swell(layers["riff"][b0:pos].copy(), sr, mode,
                                       delay_s=0.25 * spb, peak_db=-20.0)
                if sig.size:
                    _add_at(layers["fx"], sig, pos - sig.shape[0])
                continue
            sig = fx.candy_blip(kind, bar_s, sr,
                                chirp_seed if kind == "sig_chirp"
                                else seed + 900 + b)
            _add_at(layers["fx"], sig, pos)

    # ---- beds (R12): the fullness layers under the drop kit -----------------
    if flags.beds and (pal.rumble_on or pal.odd_loop_on) and pattern:
        from ..render.drums import render_odd_cell
        for k, (idx, sec, a, e) in enumerate(drops):
            dur = (e - a) / sr
            if pal.rumble_on:
                ons = kick_onsets_from_pattern(pattern, riff.tempo, sec.bars,
                                               sr, style=riff.drum_style)
                sig = fx.rumble_bed(dur, sr, seed + 600,
                                    [o / sr for o in ons], decay_s=1.5 * spb)
                _add_at(layers["rumble"], sig, a)
            if pal.odd_loop_on:
                cell = render_odd_cell(riff.drum_style, riff.tempo, dur, sr)
                # ~-20 dB under the kit: an added quiet lane, never a feature
                _add_at(layers["drums"], as_stereo(cell) * np.float32(0.35), a)

    if flags.gap:
        exempt = (pal.gap_carry,) if pal.gap_carry else ()
        _apply_gap(layers, [a for _, _, a, _ in drops], sr, spb,
                   pal.gap_beats, exempt)

    layers = {k: v for k, v in layers.items() if float(np.max(np.abs(v))) > 1e-6}
    return layers, kick_onsets, plan, prog
