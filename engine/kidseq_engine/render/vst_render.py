"""Soft-synth rendering via Surge XT (VST3) hosted headless by pedalboard.

The "produced EDM" upgrade for the synth-family voices: real filter envelopes,
unison detune and chorus movement instead of static SF2 one-shots. Surge XT is
GPL-3 and runs server-side only — we ship rendered audio, never the synth.

Linux/Modal only (the .deb is installed in the Modal image; no local install is
attempted on Windows) — riff_audio() falls back to the SF2 registry elsewhere.

Patches are plain param dicts (deterministic + reviewable — Surge's .fxp factory
patches are not loadable through pedalboard's VST3 preset hook). Envelope times
use Surge's normalized log2-seconds scale via _env(). The plugin instance is
loaded once per process; every render re-applies the full patch, so renders are
order-independent.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np

from ..audio import SR, as_stereo, seconds_per_beat

_TAIL_S = 0.8  # matches sf_render / sfz_render total-length padding

SURGE_VST3 = Path(os.environ.get("KIDSEQ_SURGE_VST3", "/usr/lib/vst3/Surge XT.vst3"))

_plugin = None  # module cache — Surge takes ~1s to load


def _env(seconds: float) -> float:
    """Surge envelope param: normalized position on its log2-time scale (~2^-8..2^5 s)."""
    return min(1.0, max(0.0, (math.log2(max(seconds, 0.004)) + 8.0) / 13.0))


# engine role -> Surge param dict. Keys are pedalboard parameter names; plain
# values are set as display units (str for choices, float for Hz/%/dB); tuples
# ("raw", x) set the normalized raw value (unlabeled params: envelopes, detune).
PATCHES: dict[str, dict] = {
    # rave lead for the app's "synth" voice: detuned saw stack, snappy LP sweep, chorus
    "synth": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "5 voices",
        "a_osc_1_unison_detune": ("raw", 0.25),
        "a_filter_1_type": "LP 24 dB",
        "a_filter_1_cutoff": 1200.0,
        "a_filter_1_resonance": 22.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.72),
        "a_filter_eg_attack": ("raw", _env(0.004)),
        "a_filter_eg_decay": ("raw", _env(0.35)),
        "a_filter_eg_sustain": 30.0,
        "a_filter_eg_release": ("raw", _env(0.2)),
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(0.5)),
        "a_amp_eg_sustain": 80.0,
        "a_amp_eg_release": ("raw", _env(0.25)),
        "fx_a1_fx_type": "Chorus",
        "character": "Bright",
    },
    # reese/moog bass: 2-voice detuned saw + sine sub an octave down, ladder LP
    "bass": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "2 voices",
        "a_osc_1_unison_detune": ("raw", 0.35),
        "a_osc_2_mute": False,
        "a_osc_2_type": "Sine",
        "a_osc_2_retrigger": True,
        "a_osc_2_octave": -1.0,
        "a_osc_2_volume": -6.0,
        "a_filter_1_type": "LP Vintage Ladder",
        "a_filter_1_cutoff": 350.0,
        "a_filter_1_resonance": 32.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.68),
        "a_filter_eg_attack": ("raw", _env(0.004)),
        "a_filter_eg_decay": ("raw", _env(0.18)),
        "a_filter_eg_sustain": 15.0,
        "a_filter_eg_release": ("raw", _env(0.12)),
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_sustain": 100.0,
        "a_amp_eg_release": ("raw", _env(0.12)),
        "character": "Warm",
    },
    # PROPER DnB reese (R15 — owner: the old 2-voice "bass" read cheap in the
    # dnb take): a wide 4-voice detuned saw stack over a clean sine sub, with
    # a SLOW filter envelope so every held note visibly moves (the beating +
    # motion is what makes a reese professional), chorus width on the mids.
    # The mix stage keeps the sub band clean and saturates only the mids
    # (Noisia doctrine — see master._bass_band_sat).
    "bass_reese": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "4 voices",
        "a_osc_1_unison_detune": ("raw", 0.52),
        "a_osc_2_mute": False,
        "a_osc_2_type": "Sine",
        "a_osc_2_retrigger": True,
        "a_osc_2_octave": -1.0,
        "a_osc_2_volume": -4.0,
        "a_filter_1_type": "LP Vintage Ladder",
        "a_filter_1_cutoff": 480.0,
        "a_filter_1_resonance": 24.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.38),
        "a_filter_eg_attack": ("raw", _env(0.05)),
        "a_filter_eg_decay": ("raw", _env(0.9)),   # the slow open-close ride
        "a_filter_eg_sustain": 40.0,
        "a_filter_eg_release": ("raw", _env(0.2)),
        "a_amp_eg_attack": ("raw", _env(0.006)),
        "a_amp_eg_sustain": 100.0,
        "a_amp_eg_release": ("raw", _env(0.15)),
        "fx_a1_fx_type": "Chorus",
        "character": "Warm",
    },
    # supersaw pad — for the arrangement stage's pads layer (not a grid voice)
    "pad": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "7 voices",
        "a_osc_1_unison_detune": ("raw", 0.3),
        "a_filter_1_type": "LP 12 dB",
        "a_filter_1_cutoff": 2500.0,
        "a_filter_1_resonance": 10.0,
        "a_amp_eg_attack": ("raw", _env(0.6)),
        "a_amp_eg_sustain": 100.0,
        "a_amp_eg_release": ("raw", _env(1.2)),
        "fx_a1_fx_type": "Chorus",
        "character": "Neutral",
    },
    # plucky stab pad (techhouse/garage alternate) — short filter+amp envelopes,
    # zero sustain: chords hit and get out of the riff's way
    "pad_pluck": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "3 voices",
        "a_osc_1_unison_detune": ("raw", 0.18),
        "a_filter_1_type": "LP 24 dB",
        "a_filter_1_cutoff": 900.0,
        "a_filter_1_resonance": 18.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.55),
        "a_filter_eg_attack": ("raw", _env(0.004)),
        "a_filter_eg_decay": ("raw", _env(0.12)),
        "a_filter_eg_sustain": 0.0,
        "a_filter_eg_release": ("raw", _env(0.15)),
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(0.25)),
        "a_amp_eg_sustain": 0.0,
        "a_amp_eg_release": ("raw", _env(0.15)),
        "fx_a1_fx_type": "Chorus",
        "character": "Bright",
    },
    # rave hoover-ish lead: huge detuned stack, bright and snarling
    "lead_hoover": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,
        "a_osc_1_unison_voices": "7 voices",
        "a_osc_1_unison_detune": ("raw", 0.45),
        "a_filter_1_type": "LP 24 dB",
        "a_filter_1_cutoff": 3500.0,
        "a_filter_1_resonance": 15.0,
        "a_amp_eg_attack": ("raw", _env(0.01)),
        "a_amp_eg_sustain": 90.0,
        "a_amp_eg_release": ("raw", _env(0.2)),
        "fx_a1_fx_type": "Chorus",
        "character": "Bright",
    },
    # acid line: single saw through a squelchy resonant ladder
    "lead_acid": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,
        "a_filter_1_type": "LP Vintage Ladder",
        "a_filter_1_cutoff": 300.0,
        "a_filter_1_resonance": 55.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.85),
        "a_filter_eg_attack": ("raw", _env(0.004)),
        "a_filter_eg_decay": ("raw", _env(0.2)),
        "a_filter_eg_sustain": 5.0,
        "a_filter_eg_release": ("raw", _env(0.1)),
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_sustain": 85.0,
        "a_amp_eg_release": ("raw", _env(0.1)),
        "character": "Bright",
    },
    # rave stab: the classic chord-stab envelope on a detuned stack
    "stab_rave": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,
        "a_osc_1_unison_voices": "5 voices",
        "a_osc_1_unison_detune": ("raw", 0.3),
        "a_filter_1_type": "LP 24 dB",
        "a_filter_1_cutoff": 2200.0,
        "a_filter_1_resonance": 14.0,
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(0.3)),
        "a_amp_eg_sustain": 0.0,
        "a_amp_eg_release": ("raw", _env(0.2)),
        "fx_a1_fx_type": "Chorus",
        "character": "Bright",
    },
    # airy glass pad: light detune, wide-open LP12, slow bloom
    "pad_glass": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,
        "a_osc_1_unison_voices": "5 voices",
        "a_osc_1_unison_detune": ("raw", 0.12),
        "a_filter_1_type": "LP 12 dB",
        "a_filter_1_cutoff": 6000.0,
        "a_filter_1_resonance": 5.0,
        "a_amp_eg_attack": ("raw", _env(1.2)),
        "a_amp_eg_sustain": 100.0,
        "a_amp_eg_release": ("raw", _env(1.5)),
        "fx_a1_fx_type": "Chorus",
        "character": "Neutral",
    },
    # bell-glass: two sines an octave apart, fast decay, long shimmer release
    "bell_glass": {
        "a_osc_1_type": "Sine",
        "a_osc_1_retrigger": True,
        "a_osc_2_mute": False,
        "a_osc_2_type": "Sine",
        "a_osc_2_retrigger": True,
        "a_osc_2_octave": 1.0,
        "a_osc_2_volume": -8.0,
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(0.6)),
        "a_amp_eg_sustain": 0.0,
        "a_amp_eg_release": ("raw", _env(1.0)),
        "character": "Bright",
    },
    # acid bassline (register comes from the notes)
    "bass_acid": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,
        "a_filter_1_type": "LP Vintage Ladder",
        "a_filter_1_cutoff": 250.0,
        "a_filter_1_resonance": 48.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.75),
        "a_filter_eg_attack": ("raw", _env(0.004)),
        "a_filter_eg_decay": ("raw", _env(0.15)),
        "a_filter_eg_sustain": 8.0,
        "a_filter_eg_release": ("raw", _env(0.08)),
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_sustain": 70.0,
        "a_amp_eg_release": ("raw", _env(0.08)),
        "character": "Warm",
    },
    # FM-ish knock bass: sub sine + punchy octave sine, tight envelope
    "bass_fm": {
        "a_osc_1_type": "Sine",
        "a_osc_1_retrigger": True,
        "a_osc_2_mute": False,
        "a_osc_2_type": "Sine",
        "a_osc_2_retrigger": True,
        "a_osc_2_octave": 1.0,
        "a_osc_2_volume": -10.0,
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(0.45)),
        "a_amp_eg_sustain": 30.0,
        "a_amp_eg_release": ("raw", _env(0.1)),
        "character": "Warm",
    },
    # 808-style sub bass (drill/hiphop) — pure sine, long natural decay
    "bass_sub808": {
        "a_osc_1_type": "Sine",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(1.2)),
        "a_amp_eg_sustain": 60.0,
        "a_amp_eg_release": ("raw", _env(0.3)),
        "character": "Warm",
    },
    # round bass (hiphop alt) — sub sine + quiet octave-up sine for definition:
    # softer attack than the 808, more melodic presence than pure sub
    "bass_round": {
        "a_osc_1_type": "Sine",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_2_mute": False,
        "a_osc_2_type": "Sine",
        "a_osc_2_retrigger": True,
        "a_osc_2_octave": 1.0,
        "a_osc_2_volume": -14.0,
        "a_amp_eg_attack": ("raw", _env(0.008)),
        "a_amp_eg_decay": ("raw", _env(0.8)),
        "a_amp_eg_sustain": 70.0,
        "a_amp_eg_release": ("raw", _env(0.2)),
        "character": "Warm",
    },
    # plucky bassline (garage/techhouse/reggaeton) — single saw, tight filter
    # envelope, short release: the bouncing 8th-note bass that stays out of the
    # kick's way
    "bass_pluck": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_filter_1_type": "LP 24 dB",
        "a_filter_1_cutoff": 500.0,
        "a_filter_1_resonance": 20.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.5),
        "a_filter_eg_attack": ("raw", _env(0.004)),
        "a_filter_eg_decay": ("raw", _env(0.09)),
        "a_filter_eg_sustain": 10.0,
        "a_filter_eg_release": ("raw", _env(0.08)),
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(0.4)),
        "a_amp_eg_sustain": 40.0,
        "a_amp_eg_release": ("raw", _env(0.08)),
        "character": "Warm",
    },
    # R19 (owner: "never a real short sound like a pizzicato … like in some
    # funk tunes"): TRUE pizzicato-style bass — zero sustain, the filter
    # snaps shut in 60 ms, gone in a quarter second. The woody funk thump.
    "bass_pizz": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_filter_1_type": "LP 24 dB",
        "a_filter_1_cutoff": 420.0,
        "a_filter_1_resonance": 14.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.55),
        "a_filter_eg_attack": ("raw", _env(0.003)),
        "a_filter_eg_decay": ("raw", _env(0.06)),
        "a_filter_eg_sustain": 0.0,
        "a_filter_eg_release": ("raw", _env(0.04)),
        "a_amp_eg_attack": ("raw", _env(0.003)),
        "a_amp_eg_decay": ("raw", _env(0.12)),
        "a_amp_eg_sustain": 0.0,
        "a_amp_eg_release": ("raw", _env(0.05)),
        "character": "Warm",
    },
    # R19 funk finger-bass: short punchy envelope with a little squelch —
    # more body than the pizz, still percussive (syncopated 16th lines)
    "bass_funk": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_filter_1_type": "LP 24 dB",
        "a_filter_1_cutoff": 650.0,
        "a_filter_1_resonance": 26.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.60),
        "a_filter_eg_attack": ("raw", _env(0.003)),
        "a_filter_eg_decay": ("raw", _env(0.15)),
        "a_filter_eg_sustain": 5.0,
        "a_filter_eg_release": ("raw", _env(0.06)),
        "a_amp_eg_attack": ("raw", _env(0.003)),
        "a_amp_eg_decay": ("raw", _env(0.25)),
        "a_amp_eg_sustain": 15.0,
        "a_amp_eg_release": ("raw", _env(0.06)),
        "character": "Warm",
    },
    # R19 clean rolling dnb sub (owner: "stuck on reese every time") — the
    # authentic non-reese dnb colour: pure sine weight + a quiet saw edge for
    # definition, short release so rolling 8ths articulate
    "bass_sub_roll": {
        "a_osc_1_type": "Sine",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_2_mute": False,
        "a_osc_2_type": "Classic",
        "a_osc_2_retrigger": True,
        "a_osc_2_volume": -14.0,
        "a_filter_1_type": "LP Vintage Ladder",
        "a_filter_1_cutoff": 320.0,
        "a_filter_1_resonance": 8.0,
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(0.5)),
        "a_amp_eg_sustain": 85.0,
        "a_amp_eg_release": ("raw", _env(0.08)),
        "character": "Warm",
    },
    # R21 big-room supersaw chords (Avicii/Guetta/SHM): huge detune, wide-open
    # filter, chords that fill the frame — sidechain pump does the movement
    "supersaw_chord": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "7 voices",
        "a_osc_1_unison_detune": ("raw", 0.35),
        "a_filter_1_type": "LP 24 dB",
        "a_filter_1_cutoff": 4500.0,
        "a_filter_1_resonance": 8.0,
        "a_amp_eg_attack": ("raw", _env(0.02)),
        "a_amp_eg_sustain": 100.0,
        "a_amp_eg_release": ("raw", _env(0.3)),
        "fx_a1_fx_type": "Chorus",
        "character": "Bright",
    },
    # R21 Berlin dub-techno chord stab: dark filtered minor stab that decays
    # into space — Basic Channel vocabulary, not rave
    "dub_chord": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "3 voices",
        "a_osc_1_unison_detune": ("raw", 0.15),
        "a_filter_1_type": "LP 12 dB",
        "a_filter_1_cutoff": 900.0,
        "a_filter_1_resonance": 20.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.25),
        "a_filter_eg_attack": ("raw", _env(0.004)),
        "a_filter_eg_decay": ("raw", _env(0.5)),
        "a_filter_eg_sustain": 0.0,
        "a_filter_eg_release": ("raw", _env(0.5)),
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(0.8)),
        "a_amp_eg_sustain": 0.0,
        "a_amp_eg_release": ("raw", _env(0.6)),
        "fx_a1_fx_type": "Chorus",
        "character": "Warm",
    },
    # R21 Detroit string machine: ensemble-chorused saw strings, stabbed or
    # held — the Rhythim Is Rhythim colour
    "string_machine": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "5 voices",
        "a_osc_1_unison_detune": ("raw", 0.20),
        "a_filter_1_type": "LP 12 dB",
        "a_filter_1_cutoff": 3200.0,
        "a_filter_1_resonance": 6.0,
        "a_amp_eg_attack": ("raw", _env(0.15)),
        "a_amp_eg_sustain": 100.0,
        "a_amp_eg_release": ("raw", _env(0.8)),
        "fx_a1_fx_type": "Chorus",
        "character": "Neutral",
    },
    # R31 Dom Dolla talkbox lead: single saw through a high-resonance bandpass
    # with a medium filter-envelope sweep — every note "talks" a vowel-ish wah.
    # The instrumental stand-in for his pitched/formant vocal hooks.
    "lead_talkbox": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_filter_1_type": "BP 24 dB",
        "a_filter_1_cutoff": 800.0,
        "a_filter_1_resonance": 45.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.55),
        "a_filter_eg_attack": ("raw", _env(0.01)),
        "a_filter_eg_decay": ("raw", _env(0.25)),
        "a_filter_eg_sustain": 35.0,
        "a_filter_eg_release": ("raw", _env(0.15)),
        "a_amp_eg_attack": ("raw", _env(0.005)),
        "a_amp_eg_decay": ("raw", _env(0.4)),
        "a_amp_eg_sustain": 55.0,
        "a_amp_eg_release": ("raw", _env(0.12)),
        "character": "Warm",
    },
    # R31 MK/Fred vocal-chop stab: detuned pair through a brighter bandpass,
    # fast decay to silence — reads as a re-pitched SYLLABLE, not a talking
    # lead (deliberately differentiated from lead_talkbox).
    "stab_vocal": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "2 voices",
        "a_osc_1_unison_detune": ("raw", 0.2),
        "a_filter_1_type": "BP 24 dB",
        "a_filter_1_cutoff": 1400.0,
        "a_filter_1_resonance": 38.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.35),
        "a_filter_eg_attack": ("raw", _env(0.004)),
        "a_filter_eg_decay": ("raw", _env(0.14)),
        "a_filter_eg_sustain": 0.0,
        "a_filter_eg_release": ("raw", _env(0.1)),
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(0.18)),
        "a_amp_eg_sustain": 0.0,
        "a_amp_eg_release": ("raw", _env(0.1)),
        "fx_a1_fx_type": "Chorus",
        "character": "Bright",
    },
    # R31 Dom Dolla rubber-wobble bass: saw + sine sub with a slow-ish
    # high-mod filter envelope — each note does the filter "wobble" that
    # carries his bass-as-melody signature. Short release so syncopated
    # 16ths duck cleanly around the kick.
    # R32d v2: deeper resonance + feg so the wobble moves harder (the Erosion
    # grit that makes it Dom Dolla lives in VOICE_POST bassled:bass:bass_wobble)
    "bass_wobble": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_2_mute": False,
        "a_osc_2_type": "Sine",
        "a_osc_2_retrigger": True,
        "a_osc_2_octave": -1.0,
        "a_osc_2_volume": -5.0,
        "a_filter_1_type": "LP Vintage Ladder",
        "a_filter_1_cutoff": 300.0,
        "a_filter_1_resonance": 40.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.84),
        "a_filter_eg_attack": ("raw", _env(0.004)),
        "a_filter_eg_decay": ("raw", _env(0.3)),
        "a_filter_eg_sustain": 12.0,
        "a_filter_eg_release": ("raw", _env(0.08)),
        "a_amp_eg_attack": ("raw", _env(0.004)),
        "a_amp_eg_decay": ("raw", _env(0.5)),
        "a_amp_eg_sustain": 45.0,
        "a_amp_eg_release": ("raw", _env(0.08)),
        "character": "Warm",
    },
    # R31 MK organ bass (Korg M1 "Organ 2" lineage): sine + quiet octave-up
    # sine, instant attack, short release — round bouncy stabs that sit fat
    # under piano/organ comping. (A +7-semi fifth layer would be truer to the
    # M1 stack, but osc pitch-in-semitones isn't in the exposed param set —
    # the octave pair reads close.)
    "bass_organ": {
        "a_osc_1_type": "Sine",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_2_mute": False,
        "a_osc_2_type": "Sine",
        "a_osc_2_retrigger": True,
        "a_osc_2_octave": 1.0,
        "a_osc_2_volume": -8.0,
        "a_amp_eg_attack": ("raw", _env(0.003)),
        "a_amp_eg_decay": ("raw", _env(0.35)),
        "a_amp_eg_sustain": 85.0,
        "a_amp_eg_release": ("raw", _env(0.06)),
        "character": "Warm",
    },
    # R31 Purple Disco Machine Italo lead: lightly-detuned pair, open LP24,
    # medium decay + chorus — the sparkling 4-8-note earworm voice that
    # trades with string stabs over the octave funk bass.
    "lead_italo": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "2 voices",
        "a_osc_1_unison_detune": ("raw", 0.15),
        "a_filter_1_type": "LP 24 dB",
        "a_filter_1_cutoff": 3000.0,
        "a_filter_1_resonance": 10.0,
        "a_amp_eg_attack": ("raw", _env(0.005)),
        "a_amp_eg_decay": ("raw", _env(0.35)),
        "a_amp_eg_sustain": 60.0,
        "a_amp_eg_release": ("raw", _env(0.18)),
        "fx_a1_fx_type": "Chorus",
        "character": "Bright",
    },
    # R32d discofunk (PDM) octave-pop bass: springy Moog-style pluck — fast
    # attack, SHORT snappy decay so the low-HIGH octave pops bounce and don't
    # sustain. (Chic chuck colour is a VOICE_POST phaser on the funk stab.)
    "bass_moog": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_filter_1_type": "LP Vintage Ladder",
        "a_filter_1_cutoff": 550.0,
        "a_filter_1_resonance": 22.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.65),
        "a_filter_eg_attack": ("raw", _env(0.002)),
        "a_filter_eg_decay": ("raw", _env(0.10)),
        "a_filter_eg_sustain": 8.0,
        "a_filter_eg_release": ("raw", _env(0.05)),
        "a_amp_eg_attack": ("raw", _env(0.002)),
        "a_amp_eg_decay": ("raw", _env(0.16)),
        "a_amp_eg_sustain": 10.0,
        "a_amp_eg_release": ("raw", _env(0.05)),
        "character": "Warm",
    },
    # R32d bigroom (Guetta) future-rave stab: detuned saw stack, mid-open LP,
    # short punchy stab envelope. The saturation that makes it "future rave" is
    # a VOICE_POST distortion (bigroom:lead:lead_futurerave).
    "lead_futurerave": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "5 voices",
        "a_osc_1_unison_detune": ("raw", 0.30),
        "a_filter_1_type": "LP 24 dB",
        "a_filter_1_cutoff": 2600.0,
        "a_filter_1_resonance": 14.0,
        "a_filter_1_feg_mod_amount": ("raw", 0.40),
        "a_filter_eg_attack": ("raw", _env(0.003)),
        "a_filter_eg_decay": ("raw", _env(0.18)),
        "a_filter_eg_sustain": 25.0,
        "a_filter_eg_release": ("raw", _env(0.12)),
        "a_amp_eg_attack": ("raw", _env(0.003)),
        "a_amp_eg_decay": ("raw", _env(0.22)),
        "a_amp_eg_sustain": 40.0,
        "a_amp_eg_release": ("raw", _env(0.12)),
        "fx_a1_fx_type": "Chorus",
        "character": "Bright",
    },
    # dark sustained pad (drill) — closed-down LP12, slow bloom, warm
    "pad_dark": {
        "a_osc_1_type": "Classic",
        "a_osc_1_retrigger": True,  # phase-lock: renders must be deterministic
        "a_osc_1_unison_voices": "5 voices",
        "a_osc_1_unison_detune": ("raw", 0.22),
        "a_filter_1_type": "LP 12 dB",
        "a_filter_1_cutoff": 700.0,
        "a_filter_1_resonance": 10.0,
        "a_amp_eg_attack": ("raw", _env(0.8)),
        "a_amp_eg_sustain": 100.0,
        "a_amp_eg_release": ("raw", _env(1.5)),
        "fx_a1_fx_type": "Chorus",
        "character": "Warm",
    },
}

# grid instruments served by this renderer (pad is arrangement-only)
INSTRUMENT_PATCH = {"synth": "synth", "bass": "bass"}


def vst_available(instrument: str) -> bool:
    return instrument in INSTRUMENT_PATCH and SURGE_VST3.exists()


def _get_plugin():
    global _plugin
    if _plugin is None:
        from pedalboard import load_plugin
        _plugin = load_plugin(str(SURGE_VST3))
    return _plugin


def _apply_patch(plugin, patch: dict) -> None:
    params = plugin.parameters
    for name, value in patch.items():
        if isinstance(value, tuple) and value[0] == "raw":
            params[name].raw_value = float(value[1])
        else:
            setattr(plugin, name, value)


def render_patch(notes, tempo: float, patch_name: str, bars: int,
                 bar_beats: float = 4.0, sr: int = SR,
                 transpose: int = 0) -> np.ndarray:
    """Render the exact riff, looped across bars, with a named Surge patch."""
    from mido import Message

    plugin = _get_plugin()
    _apply_patch(plugin, PATCHES[patch_name])

    spb = seconds_per_beat(tempo)
    total_frames = int((bars * bar_beats * spb + _TAIL_S) * sr)

    msgs = []
    for b in range(bars):
        bar_off = b * bar_beats * spb
        for n in notes:
            pitch = min(127, max(0, n.pitch + transpose))
            on_t = bar_off + n.start_beats * spb
            off_t = bar_off + (n.start_beats + n.dur_beats) * spb
            msgs.append(Message("note_on", note=pitch, velocity=n.velocity, time=on_t))
            msgs.append(Message("note_off", note=pitch, time=max(off_t, on_t + 0.01)))

    audio = plugin(msgs, duration=total_frames / sr, sample_rate=sr)
    st = as_stereo(np.asarray(audio).T)  # plugin (channels, frames) -> (frames, 2)
    if len(st) < total_frames:
        st = np.pad(st, ((0, total_frames - len(st)), (0, 0)))
    return st[:total_frames].astype(np.float32)


def render_riff_vst(notes, tempo: float, instrument: str, bars: int,
                    bar_beats: float = 4.0, sr: int = SR) -> np.ndarray:
    patch = INSTRUMENT_PATCH.get(instrument)
    if patch is None or not SURGE_VST3.exists():
        raise RuntimeError(f"vst renderer unavailable for {instrument!r}")
    # NB: bass notes arrive already -24 from sequence.py's INSTRUMENT_SEMITONE_SHIFT
    return render_patch(notes, tempo, patch, bars, bar_beats, sr)


def library_name(instrument: str) -> str:
    return f"Surge XT patch '{INSTRUMENT_PATCH.get(instrument, '?')}'"
