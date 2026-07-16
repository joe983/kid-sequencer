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

## 7. SOUND pass — REQUIRED (R32 lesson: decisions ≠ sound)

R31 varied per-press *decisions* but every producer shared one drum kit, one
Surge family and identically-synthesized FX → the owner heard "they all sound
the same." A producer axis is not done until each producer has REAL distinct
sound SOURCES. The R32 techhouse pass is the template (`docs/producer_recipes.md`
+ `~/.claude/plans/can-you-remember-i-woolly-horizon.md`).

### The push button (mechanical — one file + two commands)

Everything genre-specific lives in ONE manifest, **`engine/producers/<genre>.json`**
(schema loaded by `kidseq_engine/producer_manifest.py`): the producer keys +
reference `legend`, `tempo`, the `pack` filename, the `build` maps (drum/melodic/
fx voice → candidate section + trims), `gate` thresholds, the `battery`
input→producer pairs, and a `recipe` block (bank globs + spectral target per
producer/section) that drives triage. It lives under `engine/` because only
`engine/` rides into the Modal image and the gate reads it there.

The mechanical steps are then a driver, `tools/run_producer_pass.py`, with the
mandatory human listening checkpoint in the middle:

```
python tools/run_producer_pass.py --genre <g> --phase audition
    triage (rank owner banks -> tools/producer_candidates/<g>.json)
    -> audition (contact sheets)   [STOP: owner listens + reorders picks]

python tools/run_producer_pass.py --genre <g> --phase build
    install (build engine/packs/producer_<g>.pack) -> fetch (unpack) -> local gate
    [STOP: modal run populate_assets/run_tests/battery2/producers -> owner ears]
```

Each sub-step is content-verified (candidate de-dup, sheet counts, pack header +
SHA, gate matrix); the driver aborts on a failed check. The four tools
(`producer_triage`, `audition_producer_kits`, `install_producer_kits`,
`fetch_producer_kits`) and `test_producer_sound.py` + `modal_app::battery2` are
ALL genre-parameterized off the manifest — **adding a genre is dropping in a
manifest + assets, not editing a tool.**

### What's hand-authored per genre (musical, NOT push-button)

Sections 1–6 above (research → signatures → the `_PRODUCER_*` decision rows +
`LEAD_STACKS` + `KITS`/`SMP_VOICES`/master seasoning rows) plus the manifest's
`build` maps, the `recipe`, the 6 `examples/showcase_<genre>_p*.json` battery
inputs, and pinning `gate.t_drums`/`t_base` below the first observed matrix.

### The seven sound layers (what the mechanical steps produce)

1. **Recipes + triage** — the manifest `recipe` maps each producer's signature to
   bank globs + a spectral target. `tools/producer_triage.py --genre <g>` ranks
   the banks (decay/centroid/band-energy/tonalness), **de-dups so producers
   sharing a bank get DISTINCT slot-0 picks**, and writes
   `tools/producer_candidates/<g>.json`. Audition (`--phase audition`) → owner.
   (Triage is a reconstruction of the original scratchpad ranker — a proposal
   the owner corrects by ear.)
2. **Drum kits** — `KITS["<genre>:<producer>"]` + `kit_key()`; `install` packs the
   picks from the manifest `build.drum_map` → `producer_<g>.pack`; thread
   `drum_kit` through the AUDIO drum calls + `master(kit_key=)` slot.
3. **smp chops** — the producer's real vocal/stab/chant hook via
   `render/smp_render.py` (octave-fold ±6 semis); `build.melodic_map`.
4. **VOICE_POST** — pedalboard colour per (producer, slot, voice) — the safe
   place for character. New Surge patches use only proven param names.
5. **Sampled FX** — `render/fx_samples.py` candy one-shots per producer;
   `build.fx_map` + `_PRODUCER_CANDY` menus + `FX_FALLBACK`.
6. **Mix seasoning** — ≤2 dB per-producer deltas off `kit_key` in master.py.
7. **DISTINCTNESS GATE** — `tests/test_producer_sound.py` is now config-driven: it
   discovers every `engine/producers/*.json`, renders each genre's base pattern
   through its kits, and asserts all distinct at that manifest's thresholds. A
   new genre is covered by its manifest (+ pinned thresholds) — **no test edit**.
   This is what makes "they all sound the same" fail CI.

Every increment: `run_tests` green (asset-gated sound tests EXECUTE on Modal) +
commit. The null contract holds by construction (non-producer ⇒ producer_style
None ⇒ every producer hook is bypassed). Success is claimed with the
distinctness matrix + the content-verified battery, NOT decision logs.
