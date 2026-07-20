"""Per-genre producer manifest — the single source of truth for a genre's
R32 producer SOUND pass.

Each genre that gets the producer treatment has ONE manifest at
``engine/producers/<genre>.json`` holding every genre-specific literal the
mechanical tooling needs: the producer keys + reference legend, the pack
filename, the build maps (drum/melodic/fx voice -> candidate section), the
per-(producer,voice) trims, gate thresholds, the listening-battery input ->
producer pairs, and a ``recipe`` block that drives the triage front-half.

This replaces the literals that used to be hardcoded in five places
(``tools/install_producer_kits.py`` maps + genre prefix + pack name,
``test_producer_sound.py`` producers/genre/tempo/thresholds,
``modal_app.py::battery2`` pairs + ``_PRODUCER_LEGEND``). Add a genre by
dropping in a manifest + its assets; no tool edits.

WHY it lives under ``engine/``: only ``engine/`` rides into the Modal image
(``infra/modal_app.py`` ignores ``tools/``/``assets/``/``out/``), and the
distinctness gate runs remotely, so the manifest it reads must be here. The
``candidates_file`` points into ``tools/`` (repo root) and is only ever
dereferenced by the LOCAL build/audition/triage tools — never on Modal.

Pure stdlib so both the engine package (``kidseq_engine.producer_manifest``)
and the standalone-ish tools can import it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# engine/ (parents[1] of kidseq_engine/producer_manifest.py) and the repo root.
_ENGINE_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _ENGINE_ROOT.parent
_MANIFEST_DIR = _ENGINE_ROOT / "producers"

# Build-conditioning defaults (overridable per manifest under "build").
_DEFAULT_MELODIC_TRIM_MS = 1400
_DEFAULT_FX_PEAK_DBFS = -18.0
_DEFAULT_FX_TRIM_MS = 1600


@dataclass(frozen=True)
class Manifest:
    """One genre's producer-pass configuration (see module docstring)."""

    genre: str
    tempo: int
    pack: str                       # pack filename, e.g. "producer_garage.pack"
    candidates_file: str            # repo-root-relative, e.g. "tools/producer_candidates.json"
    producers: list[str]
    legend: dict[str, str]
    build: dict
    gate: dict
    battery: dict
    recipe: dict = field(default_factory=dict)
    path: Path = _MANIFEST_DIR      # the manifest file (set by load_manifest)

    # ---- assets / paths ----------------------------------------------------
    @property
    def pack_path(self) -> Path:
        return _ENGINE_ROOT / "packs" / self.pack

    @property
    def candidates_path(self) -> Path:
        """Absolute path to the candidate spreads (under tools/). NOT checked
        for existence here — it is absent on Modal by design."""
        return _REPO_ROOT / self.candidates_file

    def candidates(self) -> dict:
        """The ``{producer: {section: [relpath, ...]}}`` map (local tools only)."""
        doc = json.loads(self.candidates_path.read_text(encoding="utf-8"))
        return doc["candidates"]

    # ---- build maps (used by install) --------------------------------------
    @property
    def drum_map(self) -> dict[str, dict[str, str]]:
        return self.build.get("drum_map", {})

    @property
    def melodic_map(self) -> dict[str, dict[str, str]]:
        return self.build.get("melodic_map", {})

    @property
    def fx_map(self) -> dict[str, dict[str, str]]:
        return self.build.get("fx_map", {})

    @property
    def trims_ms(self) -> dict[tuple[str, str], int]:
        """JSON has no tuple keys, so trims are stored as ``"producer:voice"``
        strings; parse them back into the tuple keys install indexes by."""
        out: dict[tuple[str, str], int] = {}
        for k, v in self.build.get("trims_ms", {}).items():
            producer, _, voice = k.partition(":")
            out[(producer, voice)] = int(v)
        return out

    @property
    def melodic_trim_ms(self) -> int:
        return int(self.build.get("melodic_trim_ms", _DEFAULT_MELODIC_TRIM_MS))

    @property
    def fx_peak_dbfs(self) -> float:
        return float(self.build.get("fx_peak_dbfs", _DEFAULT_FX_PEAK_DBFS))

    @property
    def fx_trim_ms(self) -> int:
        return int(self.build.get("fx_trim_ms", _DEFAULT_FX_TRIM_MS))

    # ---- gate (used by test_producer_sound) --------------------------------
    @property
    def gate_tempo(self) -> int:
        return int(self.gate.get("tempo", self.tempo))

    @property
    def t_drums(self) -> float:
        return float(self.gate["t_drums"])

    @property
    def t_base(self) -> float:
        return float(self.gate["t_base"])

    # ---- battery (used by modal_app::battery2) -----------------------------
    @property
    def battery_base(self) -> int:
        return int(self.battery.get("base", 3000))

    @property
    def battery_pairs(self) -> list[tuple[str, str]]:
        """[(engine-relative input json, producer key), ...]."""
        return [(p["input"], p["producer"]) for p in self.battery.get("pairs", [])]

    # ---- producer kit keys -------------------------------------------------
    def kit_keys(self) -> list[str]:
        """``["<genre>:<producer>", ...]`` — the KITS / pack header keys."""
        return [f"{self.genre}:{p}" for p in self.producers]


def manifest_path(genre: str) -> Path:
    return _MANIFEST_DIR / f"{genre}.json"


def available_genres() -> list[str]:
    """Every genre with a manifest on disk (sorted)."""
    if not _MANIFEST_DIR.is_dir():
        return []
    return sorted(p.stem for p in _MANIFEST_DIR.glob("*.json"))


def load_manifest(genre: str) -> Manifest:
    """Load + validate one genre's manifest. Raises on a malformed file."""
    path = manifest_path(genre)
    if not path.exists():
        raise FileNotFoundError(
            f"no producer manifest for genre {genre!r} at {path} "
            f"(have: {available_genres()})")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("genre") != genre:
        raise ValueError(f"{path}: genre field {doc.get('genre')!r} != {genre!r}")
    for key in ("tempo", "pack", "candidates_file", "producers", "gate"):
        if key not in doc:
            raise ValueError(f"{path}: missing required key {key!r}")
    m = Manifest(
        genre=genre,
        tempo=int(doc["tempo"]),
        pack=str(doc["pack"]),
        candidates_file=str(doc["candidates_file"]),
        producers=list(doc["producers"]),
        legend=dict(doc.get("legend", {})),
        build=dict(doc.get("build", {})),
        gate=dict(doc["gate"]),
        battery=dict(doc.get("battery", {})),
        recipe=dict(doc.get("recipe", {})),
        path=path,
    )
    _validate(m)
    return m


def _validate(m: Manifest) -> None:
    if len(set(m.producers)) != len(m.producers):
        raise ValueError(f"{m.path}: duplicate producer keys in {m.producers}")
    # every producer must have a drum kit row (drums are the distinctness floor)
    missing = [p for p in m.producers if p not in m.drum_map]
    if missing:
        raise ValueError(f"{m.path}: producers {missing} have no drum_map row")
    for key in ("t_drums", "t_base"):
        if key not in m.gate:
            raise ValueError(f"{m.path}: gate missing {key!r}")


def assert_producer_keys_globally_unique() -> None:
    """The style.py ``_PRODUCER_*`` tables key off the BARE producer name while
    KITS/LEAD_STACKS use ``<genre>:<producer>``. So a producer key reused across
    two genres would collide in those bare-keyed tables. Enforce global
    uniqueness across all manifests (call from a test / the orchestrator)."""
    seen: dict[str, str] = {}
    for genre in available_genres():
        for p in load_manifest(genre).producers:
            if p in seen:
                raise ValueError(
                    f"producer key {p!r} used by both {seen[p]!r} and {genre!r} "
                    f"— bare-keyed _PRODUCER_* tables would collide; rename one")
            seen[p] = genre
