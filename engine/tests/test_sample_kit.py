"""Tests for the CC0 sample-kit drum renderer.

read_wav is tested with a synthesised WAV (no assets needed). The render tests are
skipped when the kits haven't been fetched (CI without assets/), so they never fail
on a clean checkout — run scripts/fetch_drumkits.py first to exercise them.
"""

import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.audio import SR, read_wav, seconds_per_beat, write_wav  # noqa: E402
from kidseq_engine.render import sample_kit  # noqa: E402
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402


def test_read_wav_roundtrip_mono():
    t = np.arange(SR // 10) / SR
    sig = (np.sin(2 * np.pi * 220 * t) * 0.5).astype(np.float32)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "tone.wav"
        write_wav(p, sig, SR)            # writes 16-bit stereo
        got = read_wav(p, SR)            # downmixes back to mono
    assert got.ndim == 1
    assert abs(got.shape[0] - sig.shape[0]) <= 1
    n = min(got.shape[0], sig.shape[0])
    assert float(np.max(np.abs(got[:n] - sig[:n]))) < 0.01  # within 16-bit quantisation


def test_read_wav_resamples_to_target():
    # a 22050 Hz file read at SR=44100 should roughly double in length
    half = SR // 2
    t = np.arange(half // 5) / half
    sig = (np.sin(2 * np.pi * 100 * t) * 0.4).astype(np.float32)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "low.wav"
        write_wav(p, sig, half)
        got = read_wav(p, SR)
    assert abs(got.shape[0] - sig.shape[0] * 2) <= 2


def test_every_genre_kit_covers_its_pattern_voices():
    # the registry must define a sample for every voice each genre actually
    # triggers — INCLUDING every seasoning-variant overlay and every base-beat
    # skeleton — else those hits render silent. Static check, no assets.
    from kidseq_engine.render.drums import (DRUM_SKELETONS, DRUM_VARIANTS,
                                            pattern_for)

    from kidseq_engine.render.drums import PERC_SKELETAL

    for style, pat in DRUM_PATTERNS.items():
        kit = sample_kit.KITS.get(style)
        assert kit is not None, f"no sample kit defined for genre {style!r}"
        n_variants = 1 + len(DRUM_VARIANTS.get(style, []))
        n_skels = 1 + len(DRUM_SKELETONS.get(style, []))
        for variant in range(n_variants):
            for skel in range(n_skels):
                p = pattern_for(style, variant, skel)
                missing = [v for v in p if v not in kit]
                assert not missing, (style, variant, skel, missing)
        # R24 skeletal percussive patterns hit real voices too
        for i, sk in enumerate(PERC_SKELETAL.get(style, [])):
            missing = [v for v in sk if v not in kit]
            assert not missing, (style, f"skeletal:{i}", missing)


def test_drum_variants_never_touch_the_genre_skeleton():
    # overlays are seasoning: hats/rim/shaker/cowbell only. kick/snare/clap/sub
    # ARE the genre — replacing them would break authenticity (and the pump).
    from kidseq_engine.render.drums import DRUM_VARIANTS, pattern_for

    skeleton = {"kick", "snare", "clap", "sub"}
    for style, variants in DRUM_VARIANTS.items():
        base = DRUM_PATTERNS[style]
        for i, overlay in enumerate(variants):
            assert not (set(overlay) & skeleton), (style, i, sorted(overlay))
            merged = pattern_for(style, i + 1)
            for voice in skeleton & set(base):
                assert merged[voice] == base[voice], (style, i, voice)
            for voice, steps in overlay.items():
                assert len(steps) == 16, (style, i, voice)
    # variant 0 is the base object untouched
    for style in DRUM_PATTERNS:
        assert pattern_for(style, 0) is DRUM_PATTERNS[style]


def test_drum_skeletons_are_curated_and_only_touch_skeleton_voices():
    # R17: base-beat variety comes from a CURATED hand-written menu — the old
    # "skeleton untouchable" rule is now "skeleton ∈ DRUM_SKELETONS". Skeleton
    # overlays may ONLY replace kick/snare/clap/sub (hats stay on the
    # seasoning system), rows are 16 steps, and (variant 0, skeleton 0) is
    # still the base pattern object untouched.
    from kidseq_engine.render.drums import (DRUM_SKELETONS, DRUM_VARIANTS,
                                            _SKELETON_VOICES, pattern_for)

    for style, skels in DRUM_SKELETONS.items():
        base = DRUM_PATTERNS[style]
        for i, skel in enumerate(skels):
            assert set(skel) <= _SKELETON_VOICES, (style, i, sorted(skel))
            for voice, steps in skel.items():
                assert len(steps) == 16, (style, i, voice)
            merged = pattern_for(style, 0, skeleton=i + 1)
            # replaced rows come from the skeleton; others from the base
            for voice in merged:
                want = skel.get(voice, base.get(voice))
                assert merged[voice] == want, (style, i, voice)
            # skeleton x seasoning compose: seasoning rows win their voices,
            # skeleton rows survive underneath
            for vi in range(len(DRUM_VARIANTS.get(style, []))):
                both = pattern_for(style, vi + 1, skeleton=i + 1)
                for voice in skel:
                    if voice not in DRUM_VARIANTS[style][vi]:
                        assert both[voice] == skel[voice], (style, i, vi, voice)
    for style in DRUM_PATTERNS:
        assert pattern_for(style, 0, skeleton=0) is DRUM_PATTERNS[style]


def test_kit_alts_and_fills_are_well_formed():
    # static registry checks (no assets needed): alt voices exist in the base
    # KITS entry; fill metadata is sane. With assets present, alternates must
    # actually swap the rendered one-shot.
    for style, alts in sample_kit.KIT_ALTS.items():
        kit = sample_kit.KITS[style]
        for voice, takes in alts.items():
            assert voice in kit, (style, voice)
            assert takes, (style, voice)
    for style, fills in sample_kit.KIT_FILLS.items():
        for rel, bpm, beats in fills:
            assert 60.0 <= bpm <= 200.0, (style, rel, bpm)
            assert 0.5 <= beats <= 4.0, (style, rel, beats)
    # takes resolution: take 0 == default; missing files fall back to default
    layers = sample_kit._voice_layers("dnb", "snare", None)
    assert layers is sample_kit.KITS["dnb"]["snare"]
    layers = sample_kit._voice_layers("dnb", "snare", {"snare": 0})
    assert layers is sample_kit.KITS["dnb"]["snare"]


def test_alt_takes_and_sampled_fills_when_assets_present():
    # needs only the dnb snare + extras files (not the full kit — the CC0
    # perc/shaker is a separate network fetch this test doesn't touch)
    style = "dnb"
    needed = [rel for rel, _ in sample_kit.KITS[style]["snare"]]
    needed += [rel for rel, _ in sample_kit.KIT_ALTS[style]["snare"][0]]
    needed += [sample_kit.KIT_FILLS[style][0][0]]
    if not all((sample_kit.DRUM_DIR / rel).exists() for rel in needed):
        print("  (skipped: dnb snare/extras assets not fetched)")
        return
    pat = {"snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]}
    a = sample_kit.render_drums_samples(style, 170, 1, SR, pattern=pat)
    b = sample_kit.render_drums_samples(style, 170, 1, SR, pattern=pat,
                                        takes={"snare": 1})
    assert a.shape == b.shape
    assert not np.array_equal(a, b)          # the alternate really swaps in
    # same take twice = identical bytes (per-press determinism)
    b2 = sample_kit.render_drums_samples(style, 170, 1, SR, pattern=pat,
                                         takes={"snare": 1})
    assert np.array_equal(b, b2)
    # sampled fill: near-native tempo renders; the stretch guard refuses far
    got = sample_kit.render_fill_sample(style, 1, 172.0, SR)
    assert got is not None
    sig, beats = got
    assert sig.ndim == 2 and sig.shape[1] == 2
    assert float(np.max(np.abs(sig))) > 0.05
    assert 0.5 <= beats <= 4.0
    assert sample_kit.render_fill_sample(style, 1, 100.0, SR) is None
    # determinism: same call = identical bytes
    sig2, _ = sample_kit.render_fill_sample(style, 1, 172.0, SR)
    assert np.array_equal(sig, sig2)


def test_render_is_non_silent_and_right_length_when_assets_present():
    style = "drill"
    if not sample_kit.kit_available(style):
        print("  (skipped: drum assets not fetched)")
        return
    tempo, bars = 120, 4
    buf = sample_kit.render_drums_samples(style, tempo, bars, SR)
    expected = int(bars * 4 * seconds_per_beat(tempo) * SR)
    assert buf.ndim == 2 and buf.shape[1] == 2  # stereo, constant-power panned
    assert abs(buf.shape[0] - expected) < SR  # within the tail allowance
    assert float(np.max(np.abs(buf))) > 0.05  # real hits, not silence


def test_garage_drums_render_mono_others_keep_stereo():
    # R34e: garage (incl. producer strains) renders drums MONO — owner: era
    # garage was mixed mono for mono club systems; the L/R hat spread read as
    # confusing. Null contract: other genres keep their stereo pan image.
    for style in ("garage", "garage:boinkpop", "garage:coldbass"):
        if not sample_kit.kit_available(style):
            print(f"  (skipped {style}: drum assets not fetched)")
            continue
        buf = sample_kit.render_drums_samples(style, 134, 2, SR)
        assert np.array_equal(buf[:, 0], buf[:, 1]), f"{style} not mono"
    for style in ("techhouse", "drill"):
        if not sample_kit.kit_available(style):
            print(f"  (skipped {style}: drum assets not fetched)")
            continue
        buf = sample_kit.render_drums_samples(style, 128, 2, SR)
        assert not np.array_equal(buf[:, 0], buf[:, 1]), f"{style} lost stereo"


def test_producer_kits_static():
    # R32b: the six techhouse producer kits each exist, cover the FULL techhouse
    # voice set (so kit_available/kit render never leave a pattern voice silent),
    # carry valid layer specs, and resolve via kit_key. Static, no assets.
    from kidseq_engine.render.sample_kit import KITS, PRODUCER_KEYS, kit_key
    base = set(KITS["techhouse"])
    for p in PRODUCER_KEYS:
        key = f"techhouse:{p}"
        assert key in KITS, p
        assert set(KITS[key]) == base, (p, set(KITS[key]) ^ base)
        for voice, layers in KITS[key].items():
            assert layers and all(isinstance(r, str) and r and 0.0 < g <= 1.5
                                  for r, g in layers), (p, voice)
        assert kit_key("techhouse", p) == key
    assert kit_key("techhouse", "nope") == "techhouse"   # unknown producer
    assert kit_key("dnb", None) == "dnb"                  # non-producer genre
    assert kit_key("dnb", "bassled") == "dnb"             # no dnb producer kit
    assert kit_key(None, None) == ""


def test_producer_kick_slot_falls_back_without_assets():
    # R32b: a producer key with no pack on disk slots around the BASE genre kick
    # (not the raw 55 Hz default). With assets, kick_slot_hz FFT-detects the
    # producer kick — the render test below covers the present-assets path.
    from kidseq_engine.render.sample_kit import kick_slot_hz, kit_available
    if kit_available("techhouse:bassled"):
        print("  (skipped: producer assets present)")
        return
    assert kick_slot_hz("techhouse:bassled") == kick_slot_hz("techhouse")


def test_producer_render_differs_from_base_and_peers_when_assets_present():
    # R32b core (the R31 fix, at the SOUND level): with the producer pack
    # unpacked, each producer kit renders a DIFFERENT drum sound from the base
    # techhouse kit AND from the other producers, for the same pattern — and is
    # deterministic per (kit, pattern).
    from kidseq_engine.render.sample_kit import kit_available
    prods = [f"techhouse:{p}"
             for p in ("bassled", "discofunk", "latin", "pianohouse",
                       "lofi", "bigroom")]
    if not (kit_available("techhouse") and all(kit_available(k) for k in prods)):
        print("  (skipped: producer/techhouse assets not fetched)")
        return
    pat = DRUM_PATTERNS["techhouse"]
    base = sample_kit.render_drums_samples("techhouse", 124, 2, SR, pattern=pat)
    outs = {k: sample_kit.render_drums_samples(k, 124, 2, SR, pattern=pat)
            for k in prods}
    for k, o in outs.items():
        assert o.shape == base.shape, k
        assert not np.array_equal(o, base), f"{k} identical to base techhouse"
        o2 = sample_kit.render_drums_samples(k, 124, 2, SR, pattern=pat)
        assert np.array_equal(o, o2), f"{k} not deterministic"
    keys = list(outs)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            assert not np.array_equal(outs[keys[i]], outs[keys[j]]), \
                (keys[i], keys[j])


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all sample-kit tests passed")
