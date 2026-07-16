"""R32g — automated producer distinctness gate (config-driven, per genre).

The R31 failure ("they all sound the same") must FAIL CI, not pass silently.
For EACH genre that has a producer manifest (engine/producers/<genre>.json),
this renders that genre's base drum pattern through each of its producer kits
and asserts they are spectrally distinct from EACH OTHER and from the base
genre kit. The fingerprint is pure numpy (host-stable, unlike the Surge/
soundfont full-mix path), mean-subtracted so it compares spectral SHAPE not
level. Assets-gated PER GENRE: a genre executes on Modal where its producer
pack is unpacked, and skips on a clean checkout (or before its pack is built).
Prints the distance matrix as audio-level evidence (the standing lesson: verify
producer variety with audio, not decision logs).

Add a genre by dropping in its manifest + pack — the producers, base tempo and
thresholds come from the manifest, so this file never needs a per-genre edit.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.audio import SR  # noqa: E402
from kidseq_engine.producer_manifest import (  # noqa: E402
    assert_producer_keys_globally_unique, available_genres, load_manifest)
from kidseq_engine.render import sample_kit  # noqa: E402
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402

_N_BANDS = 24
_F_LO, _F_HI = 40.0, 14000.0


def _fingerprint(stereo: np.ndarray) -> np.ndarray:
    x = stereo.mean(axis=1).astype(np.float64)
    n = 1 << int(np.ceil(np.log2(max(256, len(x)))))
    mag = np.abs(np.fft.rfft(x, n))
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    edges = np.logspace(np.log10(_F_LO), np.log10(_F_HI), _N_BANDS + 1)
    fp = np.full(_N_BANDS, -180.0)
    for i in range(_N_BANDS):
        band = mag[(freqs >= edges[i]) & (freqs < edges[i + 1])]
        if band.size:
            fp[i] = 20.0 * np.log10(np.sqrt(np.mean(band ** 2)) + 1e-9)
    return fp - fp.mean()   # compare spectral SHAPE, not overall level


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a - b)))


def _check_genre(genre: str) -> bool:
    """Render + assert distinctness for one genre. Returns True if it ran,
    False if skipped (assets not fetched). Thresholds/tempo/producers come
    from the manifest."""
    man = load_manifest(genre)
    producers = man.producers
    keys = man.kit_keys()
    if not (sample_kit.kit_available(genre)
            and all(sample_kit.kit_available(k) for k in keys)):
        print(f"  ({genre}: skipped — producer/base assets not fetched)")
        return False
    pat = DRUM_PATTERNS[genre]
    tempo = man.gate_tempo
    base = _fingerprint(sample_kit.render_drums_samples(genre, tempo, 4, SR,
                                                        pattern=pat))
    fps = {p: _fingerprint(sample_kit.render_drums_samples(k, tempo, 4, SR,
                                                           pattern=pat))
           for p, k in zip(producers, keys)}

    labels = ["base"] + list(producers)
    allfp = [base] + [fps[p] for p in producers]
    print(f"\n  [{genre}] producer drum-kit spectral distance (dB/band):")
    print("         " + "".join(f"{lbl[:6]:>7}" for lbl in labels))
    for i, li in enumerate(labels):
        row = "".join(f"{_dist(allfp[i], allfp[j]):7.2f}" for j in range(len(labels)))
        print(f"  {li[:7]:>7} {row}")

    t_base, t_drums = man.t_base, man.t_drums
    for p in producers:
        d = _dist(fps[p], base)
        assert d > t_base, (f"[{genre}] {p} too close to base kit "
                            f"({d:.2f} dB/band < {t_base})")
    pairs = [(a, b, _dist(fps[a], fps[b]))
             for i, a in enumerate(producers) for b in producers[i + 1:]]
    a, b, mind = min(pairs, key=lambda t: t[2])
    print(f"  [{genre}] closest producer pair: {a} / {b} = {mind:.2f} dB/band "
          f"(gate {t_drums})")
    assert mind > t_drums, (f"[{genre}] {a}/{b} too similar "
                            f"({mind:.2f} dB/band < {t_drums})")
    return True


def test_producer_drum_kits_are_spectrally_distinct():
    genres = available_genres()
    if not genres:
        print("  (no producer manifests found)")
        return
    ran = [g for g in genres if _check_genre(g)]
    if not ran:
        print("  (all genres skipped: producer assets not fetched)")


def test_producer_keys_globally_unique():
    # bare producer names key the style.py _PRODUCER_* tables; a name reused
    # across two genres would collide. Asset-free structural check.
    assert_producer_keys_globally_unique()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all producer-sound tests passed")
