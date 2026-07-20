"""Spectral triage — rank the owner's sample banks into a candidate list.

RECONSTRUCTION NOTE: the original `scratchpad/triage.py` that produced the
techhouse `tools/producer_candidates.json` was never committed. This is a
faithful REBUILD from its documented behaviour (engine/docs/producer_recipes.md
§Method: "extracts decay, spectral centroid, low/mid/hi energy and tonalness
for every candidate and, per section, returns (a) a target-sorted top pick and
(b) a diverse spread", de-duplicated so producers sharing a bank get DISTINCT
picks). It is NOT the original algorithm — but it only ever runs for a NEW
genre (techhouse candidates are locked), and its output is only a PROPOSAL that
the owner corrects by ear at the audition step, so ranking imperfection washes
out. It closes the "front half is not reproducible" gap in the push-button pass.

Reads the genre manifest's `recipe` block:
  recipe: { <producer>: { <section>: {
      "banks":  ["<glob relative to LIB>", ...],   # where to look
      "target": {"decay_ms": 90, "centroid_hz": 1400,
                 "band": "low"|"mid"|"hi", "tonalness": "low"|"high"},
      "count":  7                                    # candidates per sheet (default 7)
  }}}

Writes tools/producer_candidates/<genre>.json (same shape as the committed
techhouse file: {"candidates": {producer: {section: [relpath, ...]}}}, slot 0 =
the target-sorted top pick, slots 1.. = a farthest-point diverse spread). Then
`audition_producer_kits.py --genre <g>` renders those to contact sheets.

Standalone: numpy + pedalboard, NO engine imports (the recipe is read from the
manifest json directly, mirroring audition).

    python tools/producer_triage.py --genre garage
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
from pedalboard.io import AudioFile

LIB = Path(os.environ.get("KIDSEQ_SAMPLE_LIB",
                          r"C:\Users\Joe_C\Documents\MyMusic\Samples"))
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent / "producer_candidates"

_MAX_S = 3.0          # analyse at most the first 3 s (one-shots are short)
_DEFAULT_COUNT = 7
# band edges (Hz) for the low/mid/hi energy split
_BAND_EDGES = {"low": (0.0, 200.0), "mid": (200.0, 2000.0), "hi": (2000.0, 20000.0)}


# ---- feature extraction (documented set: decay, centroid, band energy, tonalness) ----
def _features(path: Path) -> dict | None:
    """Return {decay_ms, centroid_hz, low, mid, hi, tonalness} or None if unreadable."""
    try:
        with AudioFile(str(path)) as f:
            sr = int(f.samplerate)
            a = f.read(min(f.frames, int(sr * _MAX_S)))
    except Exception:  # noqa: BLE001
        return None
    x = a.mean(axis=0).astype(np.float64)  # mono
    if x.size < 64 or not np.any(x):
        return None
    peak = float(np.max(np.abs(x))) or 1.0
    x = x / peak

    # decay: peak -> first drop below -30 dB of peak, on a smoothed abs envelope
    env = np.abs(x)
    win = max(1, int(0.005 * sr))
    env = np.convolve(env, np.ones(win) / win, mode="same")
    pk = int(np.argmax(env))
    thr = 10.0 ** (-30.0 / 20.0)
    after = np.where(env[pk:] < thr)[0]
    decay_ms = (float(after[0]) / sr * 1000.0) if after.size else (len(x) - pk) / sr * 1000.0

    # spectrum
    n = 1 << int(np.ceil(np.log2(max(256, len(x)))))
    mag = np.abs(np.fft.rfft(x, n))
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    total = float(np.sum(mag)) or 1e-9
    centroid = float(np.sum(freqs * mag) / total)

    e = float(np.sum(mag ** 2)) or 1e-9
    band = {}
    for name, (lo, hi) in _BAND_EDGES.items():
        m = mag[(freqs >= lo) & (freqs < hi)]
        band[name] = float(np.sum(m ** 2)) / e

    # tonalness = 1 - spectral flatness (peaky/tonal -> ~1, noise -> ~0)
    m2 = mag ** 2 + 1e-12
    flatness = float(np.exp(np.mean(np.log(m2))) / np.mean(m2))
    tonalness = 1.0 - flatness

    return {"decay_ms": decay_ms, "centroid_hz": centroid,
            "low": band["low"], "mid": band["mid"], "hi": band["hi"],
            "tonalness": tonalness}


def _target_distance(feat: dict, target: dict) -> float:
    """Weighted distance of a candidate's features to the section's target."""
    d = 0.0
    if "decay_ms" in target:
        d += abs(np.log(max(1.0, feat["decay_ms"])) - np.log(max(1.0, target["decay_ms"])))
    if "centroid_hz" in target:
        d += abs(np.log(max(20.0, feat["centroid_hz"])) - np.log(max(20.0, target["centroid_hz"])))
    if "band" in target and target["band"] in _BAND_EDGES:
        d += 1.5 * (1.0 - feat[target["band"]])          # want energy IN the target band
    if "tonalness" in target:
        want = 1.0 if str(target["tonalness"]).startswith("h") else 0.0
        d += 1.0 * abs(feat["tonalness"] - want)
    return float(d)


def _zmatrix(feats: list[dict]) -> np.ndarray:
    """z-scored feature matrix for farthest-point diversity sampling."""
    cols = ["decay_ms", "centroid_hz", "low", "mid", "hi", "tonalness"]
    m = np.array([[np.log(max(1.0, f["decay_ms"])), np.log(max(20.0, f["centroid_hz"])),
                   f["low"], f["mid"], f["hi"], f["tonalness"]] for f in feats])
    mu, sd = m.mean(axis=0), m.std(axis=0)
    sd[sd == 0] = 1.0
    return (m - mu) / sd


def _diverse_spread(ranked_idx: list[int], z: np.ndarray, count: int) -> list[int]:
    """Slot 0 = the top pick; slots 1.. = farthest-point sampling for variety."""
    if not ranked_idx:
        return []
    chosen = [ranked_idx[0]]
    pool = ranked_idx[1:]
    while pool and len(chosen) < count:
        # pick the candidate maximizing min-distance to everything chosen so far
        best, best_d = None, -1.0
        for i in pool:
            dmin = min(float(np.linalg.norm(z[i] - z[c])) for c in chosen)
            if dmin > best_d:
                best, best_d = i, dmin
        chosen.append(best)
        pool.remove(best)
    return chosen


def _locked_elsewhere(genre: str) -> set[str]:
    """Slot-0 picks already LOCKED by other genres' producers. Never reuse them:
    a producer's sound must be its own, across genres as well as within one
    (techhouse's pianohouse chop and garage's breakz chop grabbing the same
    VEH1 file rendered byte-identical leads — the smp distinctness test caught
    it). Missing/unreadable candidate files are simply skipped."""
    taken: set[str] = set()
    for man_path in sorted((ROOT / "engine" / "producers").glob("*.json")):
        if man_path.stem == genre:
            continue
        try:
            other = json.loads(man_path.read_text(encoding="utf-8"))
            cf = ROOT / other["candidates_file"]
            cand = json.loads(cf.read_text(encoding="utf-8"))["candidates"]
        except Exception:  # noqa: BLE001
            continue
        for sections in cand.values():
            for rels in sections.values():
                if rels:
                    taken.add(rels[0])
    return taken


def triage(genre: str) -> Path:
    man = json.loads((ROOT / "engine" / "producers" / f"{genre}.json")
                     .read_text(encoding="utf-8"))
    recipe = man.get("recipe") or {}
    if not recipe:
        raise SystemExit(
            f"genre {genre!r} has no 'recipe' block in its manifest — nothing to "
            f"triage (techhouse candidates are locked; author a recipe for a new genre).")

    # rank every (producer, section) independently, then de-dup slot-0 picks so
    # no file is the FINAL PICK for two producers (the documented invariant).
    ranked: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for producer, sections in recipe.items():
        for section, spec in sections.items():
            files = _gather(spec.get("banks", []))
            scored = []
            for rel, path in files:
                feat = _features(path)
                if feat is not None:
                    scored.append((rel, feat, _target_distance(feat, spec.get("target", {}))))
            scored.sort(key=lambda t: t[2])
            ranked[(producer, section)] = [(rel, feat) for rel, feat, _ in scored]
            print(f"  {producer:12s} {section:10s}: {len(scored):3d} candidates"
                  f"{'' if scored else '  !! NONE — check banks globs'}")

    taken: set[str] = _locked_elsewhere(genre)
    if taken:
        print(f"  (cross-genre de-dup: {len(taken)} file(s) already locked by "
              f"other genres are excluded from slot-0)")
    candidates: dict[str, dict[str, list[str]]] = {}
    for (producer, section), items in ranked.items():
        if not items:
            candidates.setdefault(producer, {})[section] = []
            continue
        # slot 0 = best-ranked file not already a pick elsewhere (distinct picks)
        order = list(range(len(items)))
        top = next((i for i in order if items[i][0] not in taken), 0)
        taken.add(items[top][0])
        order.remove(top)
        order.insert(0, top)
        feats = [items[i][1] for i in order]
        z = _zmatrix(feats)
        count = int(recipe[producer][section].get("count", _DEFAULT_COUNT))
        picks = _diverse_spread(list(range(len(order))), z, count)
        # manifest "ensure" rules: guarantee named banks appear in the sheet.
        # Farthest-point diversity can drown a small NEW bank among hundreds of
        # older candidates (the owner bought Loop Cult and 7/12 kick+snare
        # sheets offered zero LC slots) — the owner can only pick what they can
        # hear. Replace tail picks (never slot 0, never an already-matching
        # slot) with the bank's best-ranked candidates until min is met.
        for rule in man.get("ensure", []):
            substr, need = rule["match"], int(rule.get("min", 1))
            def _m(i):
                return substr in items[order[i]][0]
            have = sum(1 for i in picks if _m(i))
            if have >= need:
                continue
            pool = [i for i in range(len(order)) if _m(i) and i not in picks]
            repl = [i for i in reversed(range(1, len(picks)))
                    if not _m(picks[i])]
            for i in repl:
                if have >= need or not pool:
                    break
                picks[i] = pool.pop(0)   # best-ranked bank candidate first
                have += 1
        rels = [items[order[i]][0] for i in picks]
        candidates.setdefault(producer, {})[section] = rels

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{genre}.json"
    doc = {
        "_README": (f"Triage candidates for the {genre} producers. Paths relative "
                    f"to LIB (KIDSEQ_SAMPLE_LIB / owner's sample library). First entry "
                    f"per section = the triage top pick (de-duplicated so producers "
                    f"get DISTINCT slot-0 picks); the rest are a farthest-point diverse "
                    f"spread to swap. Regenerate: python tools/producer_triage.py "
                    f"--genre {genre}  (reconstructed ranker — owner corrects by ear "
                    f"at the audition step)."),
        "candidates": candidates,
    }
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    n = sum(len(s) for s in candidates.values())
    print(f"\nwrote {out}  ({n} sections, {sum(len(v) for p in candidates.values() for v in p.values())} candidate paths)")
    return out


def _gather(globs: list[str]) -> list[tuple[str, Path]]:
    """Expand bank globs (relative to LIB) into (relpath, absolute path) pairs,
    de-duplicated and sorted for determinism."""
    seen: dict[str, Path] = {}
    for g in globs:
        for p in sorted(LIB.glob(g)):
            if p.is_file() and p.suffix.lower() in (".wav", ".aif", ".aiff", ".flac"):
                rel = str(p.relative_to(LIB)).replace("\\", "/")
                seen.setdefault(rel, p)
    return sorted(seen.items())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--genre", required=True,
                    help="which genre's manifest recipe to triage (engine/producers/<genre>.json)")
    triage(ap.parse_args().genre)
