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
