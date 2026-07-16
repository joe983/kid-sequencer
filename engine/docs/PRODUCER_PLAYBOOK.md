# Producer-style playbook — repeating R31 for the other genres

R31 built the machinery generically: `producer_style` is a per-genre axis and
everything below is a content-only pass. Remaining genres: **dnb, garage,
hiphop, drill, reggaeton** (owner decides order and timing). Sammy Virji is
the pre-banked anchor pick for garage.

## 1. Research (per genre, ~1 session)
6-angle web sweep → shortlist ~10 → deep-dive sonic signatures → pick 6
maximizing MUTUAL DISTINCTNESS (rhythm engine / lead identity / texture /
mood should partition, not cluster). Constraints:
- Hits 2022–2026, prefer still-peaking; chart or festival-mainstage scale,
  never underground/abrasive (kids app — instrumental palettes only).
- Every pick must be expressible inside the genre's PINNED backbone (the
  Virji lesson: a pick whose rhythm identity belongs to ANOTHER app genre
  gets banked for that genre instead).
- **Owner approves the six before any code.**

## 2. Signatures file
Save the deep-dives to `docs/producer_signatures_<genre>.md` (rename the
techhouse one from `producer_signatures.md` when a second genre lands).
Detailed enough that a palette can be programmed from it: kick/hats/swing,
bass sound + rhythm feel, chord instruments/voicings, hook carrier, FX/
textures, BPM, mood arc, the one-bar identifier.

## 3. Code pass (content-only, in `kidseq_engine/arrange/style.py`)
Add a `"<genre>"` entry to `_PRODUCER_MENU` (uniform weights) + a row per
producer in EVERY `_PRODUCER_*` table (`PAD_MENU`, `RHYTHM`, `BASS`, `FEEL`,
`GATE`, `PUMP`, `RUMBLE`, `SWING`, `DRUMV`, `LEAD_NONE`/`PADS_ON` and the FX
tables `RISER_ON`/`RISER_DB`/`FILL`/`SWELL`/`CANDY` where the producer needs
non-defaults) + `LEAD_STACKS["<genre>:<key>"]` banks (3 stacks each; layers
obey `semi ∈ {-12,0,12}`, `gain ≤ -8`). Add genre-specific `_BASS_FEELS` /
`_PAD_RHYTHMS` rows in `arrange/__init__.py` and `DRUM_VARIANTS` seasoning
rows in `render/drums.py` as needed. New patches/roles ONLY where the
palette genuinely needs them (Surge → `vst_render.PATCHES`; soundfont →
`sf_render.INSTRUMENT_SF` + fallback map; kit voices → `fetch_drumkits.py`
+ `sample_kit.KITS` + `_SEASONING_VOICES` + `_GM_DRUM_NOTE` + numpy
`_voice` fallback + LICENSES.md). No schema changes, no new plumbing —
`producer_style`, `drum_swing`, `_choose_fx_palette(producer=)` and the
showcase scanner already handle any genre.

## 4. Guardrails
- Producer treatments strip/colour TOPS only — never the genre's pinned
  backbone (dembow snare, dnb two-step snare mains, boom-bap kick/snare,
  4-floor + clap). Swing moves odd 16ths only, so even-step backbones are
  structurally safe.
- Genre FX disciplines OUTRANK producer menus (the riser order in
  `_choose_fx_palette`: hiphop-never → percussive-R30 → producer).
- "wash" texture stays banned; R28 sweep caps apply unchanged.
- Existing genre contract tests must stay green untouched.

## 5. Tests
`test_r31_producer_styles` iterates every genre in `_PRODUCER_MENU` — the
new genre is covered by adding its rows (extend the per-producer identity
pins for the new keys). Update that genre's `want` sets in
`test_style_fields_are_decorrelated_across_nonces` to the producer-menu
unions (the R21→R31 precedent), plus any genre assertions in the r10/r11/
r19 fx/bass tests that hard-code the old menus.

## 6. Verify + ear-check
- `python -m modal run infra/modal_app.py::run_tests` — all suites green.
- Null A/B: `::baseline --tag pre` BEFORE the change, `--tag post` after —
  every OTHER genre's SHA256 must be identical (cross-process; see the
  NEXT.md determinism caveat). If a hash differs, DON'T panic-bisect:
  some renders flip between two stable values across Modal hosts (CPU
  float variance, discovered R31). Re-render both revisions (`--tag
  post2`, and `--tag preflip` from a pre-revision worktree); a divergent
  hash the other revision also produces is environmental, not yours.
  The style layer can be compared exactly: diff `choose_style` output
  across revisions for the fixtures (pure Python, runs locally).
- `::producers --riff-file examples/<battery riff> --genre <genre> --tempo
  <genre tempo>` → `out/showcase/PRODUCERS/<genre>/` (+ a percussive-input
  run with the battery child riff). Copy to the MAIN repo checkout for the
  owner (worktree paths are invisible to them).
- Standing A–D batteries are NEVER re-cut as part of a producer pass.
