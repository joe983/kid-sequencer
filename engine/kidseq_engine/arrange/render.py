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

    @property
    def any_on(self) -> bool:
        return self.fx or self.fills or self.automation or self.gap or self.throw is not False


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


def _render_bass(notes, tempo: float, span_beats: float, sr: int,
                 bass_patch: str = "bass") -> np.ndarray:
    """Render the bass LAYER with the style's genre patch (Surge). Falls back
    to the grid-voice chain (SF2 Lately Bass / numpy synth) without Surge —
    the kid's own 'bass' grid instrument is untouched by this."""
    if vst_render.SURGE_VST3.exists() and bass_patch in vst_render.PATCHES:
        return as_stereo(vst_render.render_patch(notes, tempo, bass_patch, 1,
                                                 span_beats, sr))
    return riff_audio(notes, tempo, "bass", 1, span_beats, sr)


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
    2 = hat-roll landing on the backbeat. The final 16th ALWAYS stays EMPTY
    (it butts into the Gap). Techhouse's backbeat voice is the CLAP — its kit
    has no snare (rolling a missing voice rendered silence)."""
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
    return {lead: ramp8 + ramp16}


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


def _apply_gap(layers: dict, drop_starts: list[int], sr: int, sixteenth_s: float) -> None:
    """THE GAP: everything cuts to silence for ~half a 16th before each drop —
    the classic pre-drop breath. 3 ms cosine edges (no clicks), hard back in
    exactly at the drop sample."""
    edge = max(2, int(0.003 * sr))
    for d in drop_starts:
        g0 = d - int(0.6 * sixteenth_s * sr)
        if g0 <= edge:
            continue
        for buf in layers.values():
            if buf.shape[0] < d:
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
        # Photek move: no chord movement under a non-harmonic pattern —
        # everything sits on the key root (bass pedals, drone instead of pads)
        prog = [0, 0, 0, 0]
    spb = seconds_per_beat(riff.tempo)
    bar_s = riff.bar_beats * spb
    seed = fx.song_seed(riff, variation)

    total_bars = sum(s.bars for s in plan)
    n = int((total_bars * bar_s + 1.0) * sr)
    layers = {name: np.zeros((n, 2), dtype=np.float32)
              for name in ("riff", "drums", "bass", "pads", "texture", "fx")}
    kick_onsets: list[int] = []

    from ..render.drums import pattern_for
    pattern = pattern_for(riff.drum_style, style.drum_variant) if riff.drum_style else None

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

        if sec.drums and pattern:
            base_pat = pattern
            if percussive and sec.name.startswith("drop"):
                # drum-led evolution: each drop rotates to a different
                # seasoning overlay (the kit does the developing)
                base_pat = pattern_for(riff.drum_style,
                                       style.drum_variant + (drop_seen - 1))
            pat = base_pat if sec.drums == "full" else _lite_pattern(base_pat)
            if pat:
                from ..render import drums_audio_pattern
                sig = drums_audio_pattern(riff.drum_style, pat, riff.tempo, sec.bars, sr)
                _add_at(layers["drums"], sig, at)
            if sec.drums == "full":
                kick_onsets += [at + o for o in
                                kick_onsets_from_pattern(pattern, riff.tempo, sec.bars, sr,
                                                          style=riff.drum_style)]

        if sec.bass:
            feel = bass_feel_for(riff.drum_style, style.bass_feel)
            notes = bass_notes(riff, prog, sec.bars, feel=feel)
            sig = _render_bass(notes, riff.tempo, span_beats, sr, style.bass_patch)
            _add_at(layers["bass"], sig, at)

        if sec.pads:
            if percussive:
                # open-fifth drone (no third — nothing for a discordant riff
                # to clash with), on a dark sustained role
                notes = drone_notes(riff, sec.bars)
                sig = _render_pads(notes, riff.tempo, span_beats, sr, "dark")
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
        tex_names = ("build", "drop", "intro", "outro") if percussive \
            else ("build", "drop")
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

    if flags.fx:
        for k, (idx, sec, a, e) in enumerate(drops):
            later = k >= 1  # drop2 onwards escalates
            prev = bounds[idx - 1] if idx > 0 else None
            if pal.riser_on and prev and prev[0].name.startswith("build"):
                b_sec, b_a, b_e = prev
                if pal.riser_kind == "spinback":
                    # vinyl brake into the drop — short, ends AT the downbeat
                    sig = fx.spinback(min(2.0, 2 * bar_s), sr, seed + idx)
                else:
                    riser_bars = min(pal.riser_bars, b_sec.bars)
                    dur = riser_bars * bar_s
                    depth = min(0.85, pal.gate_depth + (0.2 if later else 0.0))
                    sig = fx.riser(dur, sr, seed + idx, gate_hz=4.0 / spb,
                                   gate_depth=depth,
                                   f0=pal.riser_f0, f1=pal.riser_f1)
                _add_at(layers["fx"], sig * fx_g, a - sig.shape[0])
            cr = fx.crash(sr, seed + 100 + idx)
            _add_at(layers["fx"], cr * fx_g, a)
            if pal.reverse_crash_on:
                _add_at(layers["fx"], fx.reverse_crash(cr, sr), a - cr.shape[0])
            imp = fx.impact(sr, peak_db=pal.impact_db,
                            f0=pal.impact_f0, f1=pal.impact_f1)
            _add_at(layers["fx"], imp, a)
            if later:  # doubled impact on later drops
                _add_at(layers["fx"], imp * 0.5, a + int(0.010 * sr))
            nxt = bounds[idx + 1] if idx + 1 < len(bounds) else None
            if pal.downlifter_on and nxt and nxt[0].name.startswith("break"):
                _add_at(layers["fx"], fx.downlifter(2 * bar_s, sr), nxt[1])
        for sec, a, e in breaks:
            _add_at(layers["fx"], fx.crash(sr, seed + 200) * fx_g, a)

    if flags.fills and pattern:
        from ..render import drums_audio_pattern
        for i, (b_sec, b_a, b_e) in builds.items():
            fill_at = b_e - int(bar_s * sr)
            sig = drums_audio_pattern(riff.drum_style,
                                      _fill_pattern(riff.drum_style, pal.fill_shape),
                                      riff.tempo, 1, sr)
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
            if sec.pads and style.structure.escalation == "full":
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

    if flags.gap:
        _apply_gap(layers, [a for _, _, a, _ in drops], sr, spb / 4.0)

    layers = {k: v for k, v in layers.items() if float(np.max(np.abs(v))) > 1e-6}
    return layers, kick_onsets, plan, prog
