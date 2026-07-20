"""Push-button driver for a genre's producer SOUND pass.

Two one-command phases around the mandatory human LISTENING checkpoint (the two
ear-in-the-loop points — picking candidates, and signing off the final battery —
cannot be automated):

  python tools/run_producer_pass.py --genre <g> --phase audition
      triage (rank owner banks -> candidates) -> audition (contact sheets)
      -> STOP: owner listens + reorders picks.

  python tools/run_producer_pass.py --genre <g> --phase build
      install (build producer_<g>.pack) -> fetch (unpack locally) -> local gate
      -> STOP: deploy to Modal + owner ears the battery.

Each sub-step is CONTENT-verified (candidate de-dup, sheet counts, pack header +
SHA, gate matrix) — the driver ABORTS on a failed check rather than trusting an
exit code (standing owner lesson: verify artifacts by content). Prereqs for a
NEW genre (hand-authored, not push-button): engine/producers/<g>.json (with a
'recipe' block), the style.py _PRODUCER_* rows, KITS/smp/master rows, and the
6 examples/showcase_<g>_p*.json inputs. See engine/docs/PRODUCER_PLAYBOOK.md §7.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ENGINE = ROOT / "engine"
PY = sys.executable

sys.path.insert(0, str(ENGINE))
from kidseq_engine.producer_manifest import load_manifest  # noqa: E402


class Abort(SystemExit):
    pass


def _step(desc: str, *cmd: str) -> None:
    """Run a sub-tool, streaming its output; abort the pass if it fails."""
    print(f"\n{'='*70}\n[{desc}] $ {' '.join(str(c) for c in cmd)}\n{'='*70}")
    r = subprocess.run([str(c) for c in cmd])
    if r.returncode != 0:
        raise Abort(f"ABORT: [{desc}] exited {r.returncode}")


def _verify_candidates(genre: str) -> None:
    man = load_manifest(genre)
    doc = json.loads(man.candidates_path.read_text(encoding="utf-8"))
    cand = doc["candidates"]
    empties, slot0 = [], {}
    print("\n  candidate pick matrix (producer / section -> slot-0):")
    for producer in man.producers:
        for section, rels in cand.get(producer, {}).items():
            if not rels:
                empties.append(f"{producer}/{section}")
                continue
            name = Path(rels[0]).name
            print(f"    {producer:12s} {section:10s} -> {name}")
            slot0.setdefault(rels[0], []).append(f"{producer}/{section}")
    if empties:
        raise Abort(f"ABORT: empty candidate sections {empties} — check recipe banks globs")
    dupes = {f: locs for f, locs in slot0.items() if len(locs) > 1}
    if dupes:
        raise Abort(f"ABORT: slot-0 pick reused across producers (de-dup broke): {dupes}")
    print(f"  OK: {len(slot0)} sections, all slot-0 picks distinct (de-dup holds)")


def _verify_sheets(genre: str) -> None:
    out = ENGINE / "out" / "audition"
    man = load_manifest(genre)
    total = 0
    for producer in man.producers:
        mp3s = list((out / producer).glob(f"{producer}__*.mp3")) if (out / producer).is_dir() else []
        bad = [p for p in mp3s if p.stat().st_size == 0]
        if bad:
            raise Abort(f"ABORT: zero-byte contact sheets: {[p.name for p in bad]}")
        total += len(mp3s)
    if total == 0:
        raise Abort("ABORT: no contact sheets rendered")
    print(f"\n  OK: {total} non-empty contact sheets under {out}")


def _verify_pack(genre: str) -> None:
    man = load_manifest(genre)
    pack = man.pack_path
    if not pack.exists():
        raise Abort(f"ABORT: pack not written ({pack})")
    b = pack.read_bytes()
    hlen = struct.unpack("<I", b[:4])[0]
    header = json.loads(b[4:4 + hlen].decode("utf-8"))
    nd = sum(len(v) for v in header.get("drums", {}).values())
    nm = sum(len(v) for v in header.get("melodic", {}).values())
    nf = sum(len(v) for v in header.get("fx", {}).values())
    missing = [k for k in man.kit_keys() if k not in header.get("drums", {})]
    if missing:
        raise Abort(f"ABORT: pack header missing drum kits for {missing}")
    print(f"\n  OK: {pack.name}  {len(b):,} bytes  sha256={hashlib.sha256(b).hexdigest()[:16]}…")
    print(f"      voices: {nd} drum + {nm} melodic + {nf} fx")


def phase_audition(genre: str) -> None:
    _step("triage", PY, HERE / "producer_triage.py", "--genre", genre)
    _verify_candidates(genre)
    _step("audition", PY, HERE / "audition_producer_kits.py", "--genre", genre)
    _verify_sheets(genre)
    print(f"""
{'*'*70}
LISTEN, THEN PICK — phase 1 done for '{genre}'.
  1. Listen to engine/out/audition/<producer>/<producer>__<section>.mp3
     (each candidate is a numbered slot behind a rising pitch pip; the .txt
      sidecar maps slot -> filename).
  2. For any section, put the file you prefer FIRST in
     tools/producer_candidates/{genre}.json (slot 0 = the locked pick).
  3. Then run:  python tools/run_producer_pass.py --genre {genre} --phase build
{'*'*70}""")


def phase_build(genre: str) -> None:
    _step("install", PY, HERE / "install_producer_kits.py", "--genre", genre)
    _verify_pack(genre)
    _step("fetch", PY, ENGINE / "scripts" / "fetch_producer_kits.py", "--force")
    # local gate — informative; SKIPS if base kits aren't fetched locally (the
    # authoritative gate runs on Modal where every asset is present).
    print(f"\n{'='*70}\n[gate] local distinctness check (authoritative gate = Modal run_tests)\n{'='*70}")
    r = subprocess.run([PY, str(ENGINE / "tests" / "test_producer_sound.py")],
                       capture_output=True, text=True)
    print(r.stdout + r.stderr)
    if r.returncode != 0:
        raise Abort("ABORT: local distinctness gate FAILED (producers too similar)")
    if "skipped" in (r.stdout + r.stderr):
        print("  NOTE: gate skipped locally (base kits not fetched here) — the "
              "distinctness matrix is proven on Modal via run_tests.")
    print(f"""
{'*'*70}
BUILT — phase 2 done for '{genre}'. Now verify on Modal + ears (from engine/):
  python -m modal run infra/modal_app.py::populate_assets
  python -m modal run infra/modal_app.py::run_tests            # {genre} gate prints the distance matrix
  python -m modal run infra/modal_app.py::battery2 --genre {genre}
  python -m modal run infra/modal_app.py::producers --genre {genre} --tempo {load_manifest(genre).tempo}
Then: pin gate.t_drums/t_base in engine/producers/{genre}.json below the first
observed matrix minima, re-run run_tests, owner ears the battery -> sign-off,
commit the pack. (Does NOT deploy — ships with the next `modal deploy`.)
{'*'*70}""")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--genre", required=True)
    ap.add_argument("--phase", required=True, choices=["audition", "build"])
    args = ap.parse_args()
    load_manifest(args.genre)  # fail fast if the manifest is missing/malformed
    (phase_audition if args.phase == "audition" else phase_build)(args.genre)


if __name__ == "__main__":
    main()
