"""R32g — automated producer distinctness gate.

The R31 failure ("they all sound the same") must FAIL CI, not pass silently.
This renders the base techhouse drum pattern through each of the six producer
kits and asserts they are spectrally distinct from EACH OTHER and from the base
techhouse kit. The fingerprint is pure numpy (host-stable, unlike the Surge/
soundfont full-mix path), mean-subtracted so it compares spectral SHAPE not
level. Assets-gated: executes on Modal where the producer pack is unpacked;
skips on a clean checkout. Prints the distance matrix as audio-level evidence
(the standing lesson: verify producer variety with audio, not decision logs).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kidseq_engine.audio import SR  # noqa: E402
from kidseq_engine.render import sample_kit  # noqa: E402
from kidseq_engine.render.drums import DRUM_PATTERNS  # noqa: E402

_N_BANDS = 24
_F_LO, _F_HI = 40.0, 14000.0
PRODUCERS = ("bassled", "discofunk", "latin", "pianohouse", "lofi", "bigroom")

# min pairwise mean-abs band distance (dB/band). Observed on Modal: closest
# producer pair 3.58, closest-to-base 2.83 (deterministic numpy fingerprint,
# host-stable). Thresholds set below those with margin — strict enough to catch
# a producer drifting halfway back toward similarity, loose enough never to
# false-fail. "They all sound the same" would score ~0 and FAIL the gate.
T_DRUMS = 2.0   # between any two producers  (observed min 3.58)
T_BASE = 1.5    # each producer vs the base techhouse kit  (observed min 2.83)


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


def test_producer_drum_kits_are_spectrally_distinct():
    keys = [f"techhouse:{p}" for p in PRODUCERS]
    if not (sample_kit.kit_available("techhouse")
            and all(sample_kit.kit_available(k) for k in keys)):
        print("  (skipped: producer/techhouse assets not fetched)")
        return
    pat = DRUM_PATTERNS["techhouse"]
    base = _fingerprint(sample_kit.render_drums_samples("techhouse", 124, 4, SR,
                                                        pattern=pat))
    fps = {p: _fingerprint(sample_kit.render_drums_samples(k, 124, 4, SR,
                                                           pattern=pat))
           for p, k in zip(PRODUCERS, keys)}

    labels = ["base"] + list(PRODUCERS)
    allfp = [base] + [fps[p] for p in PRODUCERS]
    print("\n  producer drum-kit spectral distance (dB/band):")
    print("         " + "".join(f"{lbl[:6]:>7}" for lbl in labels))
    for i, li in enumerate(labels):
        row = "".join(f"{_dist(allfp[i], allfp[j]):7.2f}" for j in range(len(labels)))
        print(f"  {li[:7]:>7} {row}")

    for p in PRODUCERS:
        d = _dist(fps[p], base)
        assert d > T_BASE, f"{p} too close to base techhouse kit ({d:.2f} dB/band)"
    pairs = [(a, b, _dist(fps[a], fps[b]))
             for i, a in enumerate(PRODUCERS) for b in PRODUCERS[i + 1:]]
    a, b, mind = min(pairs, key=lambda t: t[2])
    print(f"  closest producer pair: {a} / {b} = {mind:.2f} dB/band "
          f"(gate {T_DRUMS})")
    assert mind > T_DRUMS, f"{a}/{b} too similar ({mind:.2f} dB/band < {T_DRUMS})"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
    print("all producer-sound tests passed")
