# Where we are / next session

## ⛔ PRODUCER PASSES FROZEN (owner decision 2026-07-20) — do NOT start new genres

The genre-by-genre producer passes (`docs/PRODUCER_PLAYBOOK.md` §7) are
**deliberately paused**, not abandoned. Rationale: R1–R32 already clears the
bar the real audience judges ("my kid's melody as a real song, doesn't sound
cheap"); further per-genre producer distinctness is below the perceptibility
threshold of a parent hearing a handful of tracks/month, while NONE of R1–R32
has shipped (not modal-deployed, Stripe still TEST mode, Pro not discoverable).

**In-flight garage pass:** the owner ENGAGED with the R34c listening set on
2026-07-20 (element notes: boinkpop drums great / others not; lead layering +
variations disjointed or off key; hats washed out AND too intense, worst in
coldbass) → **R34d built + Modal-verified the same day** (see the R34d section
below; garage branch now merged to main via `claude/sess-f9466434`). The R34d
signatures set is in the main checkout
`engine/out/showcase/PRODUCERS/garage/signatures/` (sig_*_v7059–8091) —
WAITING ON OWNER EARS. The freeze on NEW genres (dnb/hiphop/drill/reggaeton)
still stands until the owner explicitly reopens the playbook.

## R34d: garage owner-notes pass (2026-07-20, Modal-verified, awaiting ears)

All three R34c notes diagnosed with audio-level evidence, then fixed:

- **Hats "washed out + too intense, esp. coldbass"** → measured: coldbass hatC
  was `909 OPCL4` = an open→closed sample with **512 ms t90** ringing across
  five 16th steps at 1.35 kit gain; coldbass+stabriddim hatO was an 857 ms
  cymbal; sincere hatC 176 ms. boinkpop (the strain the owner liked) was the
  ONLY strain crisp in both hat rows (43/156 ms). Fixes: 4 in-list pick swaps
  (coldbass `LC_CNTRL_Hat_09` + `LCHZ_Triangle_01` icy ping, sincere
  `LC_CNTRL_Hat_34` soft, stabriddim `LC_CNTRL_OpenHat_04`); manifest
  `trims_ms` hatC 140 / hatO 320 for the five non-boinkpop strains (mechanical
  guard — no future pick can wash); hatC kit gain 1.35→1.25 non-boinkpop;
  coldbass `_PRODUCER_DRUMV` [0,1]→[4,1] (was the only strain never thinning
  its hats; "icy minimal" now rides the skip-hat-pair row half its takes);
  crewdark kick → `GS_Kick_08` (old pick was pure sub, centroid 76 Hz —
  kicks PUNCH never boom). Verified in the pack: every strain t90 ≤ 100 ms;
  boinkpop drums byte-identical. Delivered-audio check: coldbass 6–12 kHz
  sustained floor (p50/p95 of band envelope) 0.51 → 0.13.
- **"Lead variations off key"** → measured: 3 of 6 baked `root_hz` were wrong
  (crewdark −4.0 st, sincere +4.4, coldbass −2.1; stabriddim's "stab" was an
  ARP SLICE, root +17 st) — the old single-window detector mis-rooted sung
  melisma; held notes then exposed the phrases' internal pitch slides. Fixes
  in `tools/install_producer_kits.py`: `_frame_f0` frame-median root detector
  with octave guard (global-max lag, halve while half-lag ≥ 0.90 — NOTE: a
  "prefer longer lag" guard is a SUBHARMONIC MAGNET, first build rooted
  crewdark at half pitch) + `_steady_head_ms` per-chop trim (cut at first
  sustained >1 st departure from root, floor 350 ms — a held grid note now
  decays instead of singing the melisma). Pick swaps: stabriddim →
  `Synth_Chords_Fm_02` steady 130.5 Hz chord stab (parallel-chord riddim
  idiom; the tempting `SynthBass_E` candidates are REAL E1 subs at 41 Hz —
  never use as lead, the fold would bury the lead in sub range), coldbass →
  `LCHZ_140_Vox_05`, sincere → `LC_CNTRL_Vox_Fx_01`. Verified in the pack:
  all six chops hold their baked root (chord stab reads multi-pitch to a
  single-f0 tracker — expected).
- **"Lead layering disjointed"** → root cause: `fold_rate` folded the smp chop
  into ±6 st of its root while clean co-layers traced the full written
  contour — two melodic shapes at once. Fix in `_render_lead_stack`
  (arrange/render.py): when a stack leads with an smp voice, ALL layers' notes
  fold into the chop's octave band up front (octave-only moves; pitch classes
  + clash fixes untouched). Plus `resolve_clashes(strict=)` (arrange/
  __init__.py): garage-producer takes additionally snap sustained beat-start
  non-chord tones to the nearest chord tone (develop_phrase's diatonic
  call_response/vary_end shifts passed the semitone-only rule and read as
  off-key variations). Null contract: strict only fires when
  `drum_style=="garage" and producer_style is not None`; the fold only fires
  for stacks with a resolvable smp root (garage strains only today) — other
  genres byte-unchanged.

Modal: all 11 suites green; garage gate matrix moved (closest pair now
partybounce/sincere 2.44, gate 2.0) proving the volume audio changed
(`populate_assets` re-run from the WORKTREE — running it from the main
checkout silently validates the wrong engine); techhouse 3.58 unchanged.
Levers if the owner still hears intensity: hatC kit gains (sample_kit.KITS),
base hatC velocity row (drums.py garage), `_LAYER_LUFS["drums"]`
K-weighting note — coldbass's deep kick under-reads LUFS so calibration
lifts its hats hotter than boinkpop's at equal gains.

Priority order is now: **deploy R1–R32 (or R1–R34c if the garage branch merges
first) → Rhythm Trail merge → Stripe live → tier-flow discoverability → let
real-user feedback decide whether producer passes resume** (if users report
sameness, resume per the playbook with the banked push-button machinery — one
genre ≈ one session). Plan:
`~/.claude/plans/have-i-lost-focus-vivid-quiche.md`. Do not auto-continue the
playbook in a future session without the owner re-opening it.

## NEW — R32: producer SOUND pass, techhouse (2026-07-16, NOT deployed)
Answers the owner's R31 rejection ("they all sound the same"). R31 varied
per-press *decisions* but every producer shared one drum kit, one Surge synth
family and identically-synthesized FX. R32 puts REAL distinct sound SOURCES
into each producer at every layer, and adds an automated gate so the failure
can't recur silently. **Standing lesson baked in: producer variety is proven
with audio-level evidence (spectral distinctness + ears), never a `producer=`
log line.** Plan: `~/.claude/plans/ok-now-back-to-bubbly-allen.md`.

**8 increments (R32a–g built + Modal-verified; R32h = these docs):**
- **R32a** — `docs/producer_recipes.md` (per producer: DRUMS/SAMPLER/SYNTH+
  POST/FX/MIX → verified source folder + FINAL PICK + target). `tools/
  audition_producer_kits.py` + `tools/producer_candidates.json` (picks chosen
  by spectral triage — "rank, not hear"). 49 contact sheets in main-repo
  `engine/out/audition/<producer>/`.
- **R32b** — six `KITS["techhouse:<producer>"]` drum kits +
  `kit_key(genre, producer)` + `kick_slot_hz` producer fallback; threaded
  through the 6 AUDIO drum calls in `build_song` (symbolic pump/pattern stay on
  `riff.drum_style`) + `master(kit_key=)` slot. Picks de-duped so producers
  sharing a bank get DISTINCT files (byte-verified).
- **R32c** — `render/smp_render.py` repitch one-shot sampler (vocal chops/
  stabs/chants; playback rate octave-folded ±6 semis — the vocal-chop idiom).
  6 `LEAD_VOICES` smp voices; `_render_lead_stack` smp-first branch with synth
  fallback; producer signature stacks re-pointed to lead with the real chop.
- **R32d** — `VOICE_POST` generalizes `PAD_POST`: per-(producer,slot,voice)
  pedalboard chains (bassled Erosion grit, lofi tape-wobble, discofunk Chic
  phaser, latin slap-delay, bigroom saturation). felt_piano byte-compat via
  `*:pad:felt_piano`. New Surge patches `bass_moog`/`lead_futurerave` +
  `bass_wobble` v2 (proven params only; character lives in VOICE_POST, so the
  probe was unnecessary).
- **R32e** — `render/fx_samples.py` sampled ear-candy one-shots per producer
  (bassled slide/rev, discofunk tom-zap, latin crowd/perk, lofi reverse-swell,
  bigroom riser/impact/slide). Candy scheduler routes `smp_*` kinds via
  `fx_shot`, remaps to synth candy without assets. Scoped to the candy layer
  (fixed-length at phrase boundaries) — deliberately NOT the build-length synth
  riser (duration-fitting risk, little gain).
- **R32f** — per-producer mix seasoning (≤2 dB): `_PRODUCER_SEND_DELTA`/
  `_ROOM_SIZE`/`_NY_DB`/`_DRUM_CLIP_K` off the producer parsed from `kit_key`.
  None/non-producer misses every table = bit-identical null contract.
- **R32g** — `tests/test_producer_sound.py`: renders the base pattern through
  each producer kit → 24-band mean-subtracted spectral fingerprint → asserts
  all six distinct from base + each other. **Modal matrix (dB/band): closest
  pair bassled/bigroom 3.58, all-vs-base 2.83–4.52** (thresholds T_DRUMS 2.0 /
  T_BASE 1.5). The automated "they all sound the same" catcher.

**Pack `engine/packs/producer_techhouse.pack`** (committed, ~3 MB): 29 drum +
6 melodic (smp chops, root_hz baked) + 10 fx voices. Container schema v1
`{"drums"/"melodic"/"fx": {"techhouse:<producer>": {...}}}`. Rebuild:
`tools/install_producer_kits.py` (reads `tools/producer_candidates.json` — put
a different file first to swap a pick, rebuild = one command). Unpack:
`scripts/fetch_producer_kits.py` (wired into `populate_assets`).

**Verification:** all 11 remote suites green each increment (drum/smp/fx
assets-gated tests EXECUTE on Modal). Null contract for non-techhouse is
structural (producer_style None ⇒ drum_kit==genre, no VOICE_POST, no producer
candy, no smp, kit_key None → master seasons nothing) + backed by the passing
null-contract tests; a full cross-revision `::baseline` A/B is the remaining
belt-and-suspenders (host-variance caveat applies — see R31 note below).

**Owner-listen (open):** 49 R32a contact sheets + the R32g producer battery
(`out/showcase/PRODUCERS/techhouse/`, base 1500). Any pick swap = reorder
`producer_candidates.json` + rebuild.

**Tuning levers:** picks in `producer_candidates.json`; kit gains/sub-lanes in
`sample_kit.KITS`; smp octave-fold + `SMP_VOICES` fallbacks; `VOICE_POST`
chains; `_PRODUCER_CANDY` menus + `FX_FALLBACK`; `_PRODUCER_*` mix deltas in
master.py; gate thresholds in `test_producer_sound.py`.

**Known pick swaps to consider after listening:** bigroom `rave_shot` root
auto-detected 1520 Hz (bright); latin `smp_crowd` + bigroom `smp_impact`
grabbed rave sweeps rather than a crowd/boom (rave_fx bank sorted
long-sweep-first).

**Deploy gate unchanged:** `modal deploy engine/infra/modal_app.py` ships
R1–R32 together after owner ears. Endpoint URL + app/functions unchanged.

## NEW — R31: producer-style axis, techhouse (2026-07-15, NOT deployed)
The genre-by-genre variety pass begins. Answers "a second press sounds like
the same track": a 6-value **producer style** drawn per press recolours the
whole techhouse take. Each value is a coherent palette modeled on a modern
chart producer (owner-approved after a web-verified research pass; Sammy
Virji was banked for the future Garage pass — 2-step belongs to that genre):

| key | reference | palette core |
|---|---|---|
| `bassled` | Dom Dolla | `bass_wobble` + kick call-response 16ths, `lead_talkbox` hook, sparse pluck/piano pads, dry |
| `discofunk` | Purple Disco Machine | `bass_funk` octave-pop 8ths (feel 5), clav chuck (rhythm 3), `string_machine`/`lead_italo`, disco perc row 5 |
| `pianohouse` | MK | `bass_organ` bounce, piano/organ skank (rhythm 4), `stab_vocal` chop lead, swing 0.13 |
| `latin` | HUGEL | conga/bongo rows 4/7 (never bare), accordion/brass/marimba hooks, tumbao feel 6 |
| `lofi` | Fred again.. | felt_piano (PAD_POST LPF) + pinned crackle + pinned pads, held roots feel 8, pump 0.62, reverse swell |
| `bigroom` | Guetta | R21 bigroom assets (supersaw_chord, whole-bar pads), rolling 8ths, riser PINNED ON, roll fills, swing 0.02 |

- **Mechanics**: `producer_style` (generic per-genre `_PRODUCER_MENU` — other
  genres add entries later, no schema change) REPLACES R21 `house_style`
  (`_HOUSE_*` tables deleted; bigroom carries the reusable assets forward).
  Uniform 6-way draw, fresh stream name, both production modes; percussive
  and hiphop FX disciplines still outrank producer FX menus (riser order:
  hiphop→never, percussive→R30, then producer).
- **New assets**: Surge `lead_talkbox`/`stab_vocal`/`bass_wobble`/
  `bass_organ`/`lead_italo` (probed on Modal: all render, BP 24 dB valid);
  SF `pad_accordion` (GM 21); VCSL conga+bongo → `perc/{conga,bongo}.wav`
  (on the volume); DRUM_VARIANTS["techhouse"] rows 4–7; _BASS_FEELS 5–8;
  _PAD_RHYTHMS 3–4; felt piano = Salamander through `PAD_POST` LPF 2.8k.
- **Per-press swing**: `ArrangeStyle.drum_swing` threads a `swing=` override
  through `swung_step_offset` → all three drum renderers + `drums_audio_
  pattern` + `kick_onsets_from_pattern` (pump stays locked). Odd-16th-only,
  so the pinned even-step kick/clap backbone can never move. None = legacy.
- **Ear-check**: `python -m modal run infra/modal_app.py::producers`
  (--riff-file/--genre/--tempo/--base) — scans nonces until all 6 keys hit,
  renders → `out/showcase/PRODUCERS/<genre>/producer_<key>_v<N>.mp3` (real
  reproducible variation numbers; resumable, skips existing files).
  Null A/B fixtures: `::baseline --tag <pre|post>` → out/baseline/<tag>/
  SHA256SUMS (other genres must stay byte-identical, cross-process).
  ⚠️ NULL A/B CAVEAT (discovered verifying R31): some fixture renders flip
  between TWO stable hash values across Modal runs REGARDLESS of code
  revision (dnb/hiphop flipped; each divergent hash was reproduced exactly
  by the other revision, and choose_style output diffed empty) — host CPU
  variance in the synth float paths, pre-existing, NOT a regression. If a
  hash differs, re-render BOTH revisions before concluding anything: a
  value the other revision also produces = environmental. This also
  refines the determinism note below: same (sequence, variation) = same
  track holds per machine-type, not across Modal's host fleet.
- **Repeat-press math**: P(same producer twice) = 1/6; with per-producer
  sub-draws still varying, "feels the same" ≈ 4–6% of consecutive pairs.
- Levers: every `_PRODUCER_*` table in style.py (menus/weights/pins),
  `_PRODUCER_SWING` values, PAD_POST felt-piano (LPF Hz, vel scale),
  producer stack banks `LEAD_STACKS["techhouse:<key>"]`, DRUM_VARIANTS rows.
- Playbook for the other five genres: `docs/PRODUCER_PLAYBOOK.md`; producer
  sonic signatures: `docs/producer_signatures.md`.

## NEW — R30: percussive backbones + swoosh purge (2026-07-14, NOT deployed)
Owner on battery three (percussive focus; "apply to all"): half-tempo dnb
too long + wrong there; swooshes as continuous background AGAIN
(drill/garage/reggaeton "all the way through — sounds crap"); reggaeton
dembow missing = unrecognisable; hiphop disjointed; dnb main snares must be
equal; techhouse percussive too dubbed out; echo risks warping the note.
NEXT SESSION (owner): close this session out, then go GENRE BY GENRE adding
a little more variety to each separately.

- **PERC_SKELETAL principle: strip TOPS, never the backbone.** Reggaeton
  keeps the full dembow; dnb always full-tempo two-step, snare mains EQUAL
  at steps 4+12 (half-feel lives ONLY in the melodic ≤8-bar switch-up);
  hiphop keeps boom-bap kick/snare; techhouse keeps 4-floor + CLAP; garage
  mains equalised; drill untouched. R30 contract test pins all of this.
- **"wash" texture BANNED everywhere** (melodic + percussive menus + the
  R23 exclusion fallback → crackle): a filtered-noise bed IS a continuous
  swoosh. Percussive riser_on 0.50 → 0.25.
- **riff_echo subtler**: feedback 0.35, target −29 LUFS.
- Levers: PERC_SKELETAL rows; _PERC_TEXTURE weights; percussive riser
  menu; riff_echo feedback/LUFS.

## NEW — R29 + battery THREE (2026-07-14, NOT deployed)
Owner confirmed the R26 half-feel switch-up is what they meant, lifted the
Modal spend limit, and asked for a fresh listening set: ALL base melodies
swapped, and each battery's percussive slot = a different NON-MUSICAL
child-experiment pattern, from very sparse to far too busy.

- **R29 routing**: `riff_tonality` returns 0.30 (percussive) for 1–2 note
  patterns (was 1.0/melodic) — a single programmed note now gets the R24
  sparse/atmospheric treatment. test_style's melodic fixture grew to 4
  triad-anchored notes.
- **Battery THREE inputs** (`examples/{a2,b2,c2,d2}_*.json`, _BATTERIES
  bases/steps/tempos unchanged): 8 new melodies across piano/synth/trumpet/
  strings/bells/bass + child patterns A = TWO touches, B = 4 pokes w/ a
  finger rub, C = 18-note splatter, D = 32-note wall mash over held lows.
  All 12 verified routing correctly; extremes smoke-rendered clean.
- Battery cut on the R24–R29 engine, verified by content (96 files, 24
  percussive/72 melodic, both perc_low + note_style modes live, 16 dry_echo
  takes carry the riff_echo layer) → copied to MAIN repo
  `engine/out/showcase/` — **this is the owner's current listening set**.

## NEW — Rounds 24–28: battery-two ear feedback ("nearly there for launch") (2026-07-14, NOT deployed)
Owner on the R17–R23 battery: drill + reggaeton nailed bar minor fx tweaks;
standouts B/garage_minor, B/drill_major_a, B/hiphop_percussive,
B/reggaeton_major_a+b, C/hiphop_major_b. Remaining: techhouse mixes boomy;
dnb half-tempo skeleton wrong song-level; hiphop shouldn't build/drop;
PERCUSSIVE STILL MUDDY (all genres — "the main thing that lets the engine
down"); drum variety ≥ every 16 bars; swooshes never up-down repeatedly.
Owner Q&A on the sparse concept: drums SKELETAL + SPACIOUS (kid's note =
loudest event); low end = kick+sub-accents OR short stabs (never
sustained); note treatment ALTERNATES per track (dry+echo-tail vs washed);
references = early Photek/Source Direct + Burial + Rhythm & Sound.

- **R24 percussive/sparse rework**: `PERC_SKELETAL` stripped patterns
  REPLACE the full groove in percussive mode (2-3/genre, drops rotate
  variants; dnb+techhouse kits gained a woodblock rim). `perc_bass_notes`:
  "stabs" (0.3-beat subs on the skeletal kick) | "accents" (no bassline,
  one phrase-end 0.75-beat accent) — sustained pedal GONE; pump follows the
  skeletal kick. `perc_note_style`: "dry_echo" = new `riff_echo` layer
  (wet-only delay ghost, HP300, −27 LUFS, un-pumped) | "washed" =
  whole-track riff wet span. `_PERC_TEXTURE` reference flavours
  (dnb/drill=metal-led, garage/hiphop=crackle-led, techhouse/reggaeton=
  drone-led). percussive_pads 60/40 pad-FREE. Mix: riff +1 dB, drums −1 dB
  in percussive (`_PERC_LUFS_DROP`).
- **R25 techhouse punch**: kit sub lane 1.0→0.55; techhouse drums board
  90 Hz low-shelf −1.5 (transient carries, boom doesn't).
- **R26**: dnb half-feel OUT of the song-level menu (`DNB_HALF_SKELETON`);
  `half_switch` (35% melodic dnb) opens drop 2 on it then snaps back.
  "static" drummer REMOVED everywhere — sparse(16) is the floor; dnb leans
  busy/regular [0.40/0.40/0.20].
- **R27 hiphop flat arc**: riser menu ([False],None), no build LPF climb,
  `_IMPACT` −12, reverse-crash 0.40, escalation off at render.
- **R28 swoosh discipline**: sweep candy never consecutive + ≤2/track
  (remaps to non-sweeps); downlifter 0.8→0.5, 0.35 on riser-led takes.
- Tuning levers: `PERC_SKELETAL` rows; perc_low/note_style weights;
  `_PERC_TEXTURE`; riff_echo delay/feedback + `_LAYER_LUFS["riff_echo"]`;
  techhouse sub-lane gain + shelf; `half_switch` weight; `_DRUMMER_MENU`;
  hiphop `_IMPACT`/crash menu; sweep cap + downlifter menus.

## NEW — Rounds 17–23: owner ear-feedback epic on the A–D batteries (2026-07-14, NOT deployed)
Owner listened to the 96-track A–D grid. Garage + hiphop good (menus left
alone), drill great except muddy percussive mixes, and: DnB stuck on reese +
identical beat every song + unused library fills + boxey drum reverb; bass
everywhere too sustained/synthesised/dry/similar; variety only at
breakdowns; techhouse cheesy-90s (wants Avicii/Guetta/SHM × Berlin minimal ×
Detroit); reggaeton amateur; not every song needs pads/long sounds.

- **R17 drums+space**: `DRUM_SKELETONS` — hand-curated base-beat variants
  per genre (dnb ×3: shuffled two-step/roller/half-feel; drill ×2; others
  ×1; skeleton 0 = legacy; `pattern_for(style, variant, skeleton)`
  composes). The old "skeleton untouchable" rule is now "skeleton ∈ curated
  menu" (test_sample_kit pins it; reggaeton dembow snare still untouchable
  across ALL combos — R22 test). **engine_extras.pack** (committed,
  `tools/install_engine_extras.py` → `scripts/fetch_extras.py` in
  populate_assets): the owner's 4 alt dnb snares + alt hat + 4 REAL
  breakbeat fills. `sample_kit.KIT_ALTS/KIT_FILLS` + per-press
  `snare_take`/`hat_take`/`fill_take`; sampled fills REPLACE the synth fill
  at build tails (kit cut for the fill span; >15% tempo stretch falls back).
  De-box: `_ROOM_GAIN_DB` −4 dB, room bus drive 12→6 dB + LP 6k→8k,
  `_ROOM_SIZE` garage/reggaeton .50→.44, drums shared-return send −22→−20.
- **R18 drummer**: `ArrangeStyle.drummer` static/sparse/regular/busy
  (= never/16/8/4-bar gesture cadence; drill/hiphop lean static). In-drop
  gestures on the bar INTO each phrase boundary: minifill / one-bar
  seasoning swap / hat lift / ghost adds / kick_skip (never techhouse).
  Hook + candy-slot discipline; gesture sections render drums PER BAR with
  per-bar kick onsets (kick_skip never ducks against silence); bass answers
  minifill bars with an octave pop.
- **R19 bass**: patches `bass_pizz` (true zero-sustain pluck), `bass_funk`,
  `bass_sub_roll` (clean non-reese dnb). `bass_gate` [1.0/0.6/0.35]
  duration lever (drill/hiphop keep tails). New short feels (funk 16th
  sync, on-beat quarters, rolling-sub 8ths, stab bass, staccato tresillo).
  Explicit weights: dnb reese 0.35, reese-drone feel 0.10; techhouse
  offbeat ~0.45 total. Mix: harmonics-only bass send into the shared reverb
  (`_BASS_SEND_DB` −18, split 150 Hz, sub dry+mono). `master(pump_depth=)`
  per-press override (techhouse [preset/.35/.22]).
- **R20 sparse**: `lead_stack` None (~25–30%), `pads_on` 80/20 (drill
  70/30); guard: never both out unless texture carries.
- **R21 techhouse**: `house_style` classic .25 / bigroom .30 / minimal .25
  / detroit .20. New patches `supersaw_chord`/`dub_chord`/`string_machine`
  + `pad_piano` (real Salamander). Per-sub-style pad menus, pad rhythm
  (bigroom whole-bar holds = _PAD_RHYTHMS index 2), LEAD_STACKS banks
  (`techhouse:bigroom|minimal|detroit` via `lead_stack_key`), pump feel,
  rumble weighting, minimal lead-None 45%. Classic demoted rave_stab/acid
  to 0.15 each (`_STACK_W`).
- **R22 reggaeton**: `_IMPACT` entry (70/32/−7), crackle texture, conga rim
  tumbao overlay (variant 5), odd_loop shaker cell 40%.
- **R23 percussive mud**: drone pads exclude drone/metal textures (one dark
  bed at a time; metal stays the pad-free signature); `percussive_pedal`
  [0,1,2] with moving shapes leading (new alternating root/fifth walk);
  `master(percussive=)` — beds −2 dB (`_PERC_LUFS_DROP`), 280 Hz mud cut
  −1.5→−2.5, drill drums 85 Hz shelf −1.5 (percussive only; flag off =
  bit-identical legacy path).
- smoke_song decision log now prints all of it: `drums: skeleton= variant=
  drummer= snare_take= hat_take= fill_take= bass_gate= pump= lead_stack=
  pads_on= house=`.
- Tuning levers: `_SKELETON_MENU`/`_SNARE_TAKES`/`_FILL_TAKES` weights;
  `_DRUMMER_MENU` + gesture menu weights in `_drummer_gestures`;
  `_BASS_PATCH_W`/`_BASS_FEEL_W`/`_BASS_GATE`/`_PUMP_MENU`/`_BASS_SEND_DB`;
  `_LEAD_NONE_W`/`_PADS_ON`; `_HOUSE_*` menus + `_STACK_W`; room-bus
  constants; `_PERC_LUFS_DROP` + pedal weights. New samples: edit
  `tools/install_engine_extras.py` → re-run → commit the pack → re-run
  `modal run infra/modal_app.py::populate_assets`.

## NEW — Round 16: Photek percussive + A-D showcase batteries (2026-07-12, NOT deployed)
Owner: (1) restructure the showcase into folders — A = the existing battery,
B/C/D = the same 24-track grid on COMPLETELY different sequencer melodies,
each folder as far from the others as the engine can reach; (2) swooshes are
still not mandatory — takes without any riser must be a real outcome; (3) the
TRUE Photek percussive treatment was never achieved: no pads/synth long notes
at all — just hits and a dark industrial space.

- **Pad-free percussive takes**: `ArrangeStyle.percussive_pads` ("drone" 55%
  | "none" 45%). "none" renders NO pads layer in percussive mode — drums +
  riff-as-percussion + bass pedal + texture bed carry the track.
- **`fx.metal_drone`** — the industrial bed: inharmonic plate partials
  (1/1.53/2.27/3.19/4.41) on the tonic, per-partial slow breathing,
  alternate partials leaning L/R, faint shimmer, LP 1800. Joined the
  percussive texture menu (drone/wash/metal + genre's own). -26 dBFS,
  texture layer calibrates to -30 LUFS as ever.
- **Riser restraint at the on/off level**: melodic default riser_on
  0.85→0.70 (30% of takes have NO riser — reverse crash + fills carry the
  transition); percussive takes 50/50; hiphop unchanged (mostly off).
- **Batteries** (`infra/modal_app.py::_BATTERIES`): showcase() now renders
  into out/showcase/<LETTER>/ — A = original riffs (base 1, step 7, standard
  tempos), B = syncopated offbeat synth hook / falling piano lament /
  two-row machine stabs (base 211, step 13), C = 5-note sparse
  question-answer piano / wall-to-wall 16th strings arps / long overlapped
  bass seconds (base 421, step 17), D = trumpet scalar climb into holds /
  synth octave pendulum / sparse irregular piano hits (base 631, step 19).
  Per-battery genre tempos differ too. Riff files: examples/{b,c,d}_*.json —
  all 9 verified: clusters riff_tonality 0.000 (always percussive), the
  rest firmly melodic. `modal run infra/modal_app.py::showcase` renders
  B,C,D by default; `--batteries A,B,C,D` re-cuts everything.
- Tuning levers: percussive_pads weights + riser_on menus in
  _choose_fx_palette/choose_style; metal_drone partials/level in fx.py;
  battery bases/steps/tempos in _BATTERIES.

## NEW — Round 15: owner ear-feedback on the R10-14 battery (2026-07-11, NOT deployed)
Owner listened to the showcase: risers samey / too prominent / not pro, no
audible shepard, gaps overused (hiphop never needs one; one take stacked a
big gap on starvation), dnb bass reads cheap, dnb swooshes amateur. Fixes:
- **Riser level**: new `riser_db` palette field (-17 signature / -14 / -20)
  replaces the fixed -12 — risers now sit UNDER the mix and vary per press.
- **Riser colour**: `riser_color` smooth/textured/airy (fx._RISER_COLORS —
  q, tanh drive, band shift). Sangiuliano: organic/textured, never shiny.
  drill/hiphop lean textured. riser_bars menu widened [8,4,2].
- **TRUE cyclic shepard** rebuild: 3 layers climbing a 3-octave span and
  wrapping (raised-cosine loudness over position, silent at wrap), two full
  handovers per riser, tonal partials riding the cycle — the old crossfade
  version was 60% identical to a classic sweep, which is why it was never
  heard. Pinned: first half must already carry energy.
- **Gap discipline**: hiphop menu = [0.15] only (micro-breath); drill leans
  micro [0.65/0.35]; default demotes the 2-beat cut to 25% (was 50%).
  EXCLUSION: gap>=2 beats forces starve=0; gap>=1 caps starve at 1 —
  the too-much take was exactly that stack.
- **DnB bass**: new Surge patch `bass_reese` (4-voice 0.52-detune saw over
  clean sine sub, SLOW filter env ride, chorus) leads the dnb menu; plus
  mix-stage `_bass_band_sat` on every genre's bass (Noisia: sub band clean,
  mids tanh-thickened, RMS-matched — _BASS_SAT_WET, dnb hottest 0.35).
- **Downlifter rework**: noise-led composite (falling band-noise + soft tanh
  sine bed) at -18, seeded — the pure falling sine read plastic. Removed
  mini_downlifter from dnb candy (menu now rev_swell_delay/siren/sweep_down).
Tuning levers: _RISER_DB_MENU/_RISER_COLOR/_GAP_BEATS/_BASS_SAT_WET/
_BASS_SAT_DRIVE, fx._RISER_COLORS table, bass_reese patch params.

## NEW — Rounds 10–13: PRO POLISH epic (2026-07-11, NOT deployed)
Owner: tracks need the professional finish of top-tier DnB/techno records —
more (tasteful, modern) swooshes/rises/sirens/SFX, richer layering, better
mix/master. Method: 119 adversarially-verified techniques from NAMED master
producers/engineers (Noisia, Sub Focus, Rødhåd, Tom Hades, KiNK, MJ Cole,
Todd Edwards, Wookie, 808Melo, M1OnTheBeat, Ghosty, Premier, Young Guru,
MixedByAli, Tainy, Ovy on the Drums, Pretolesi, Stuart Hawkes, Beau Thomas,
Bob Katz…) — every finding source-fetched and quote-checked. Full research +
design doc: `~/.claude/plans/having-listened-to-the-witty-ritchie.md`.

- **R10 transition core**: REAL pre-drop gap (gap_beats 2.0/1.0/0.15 per
  press, 1.1 s clamp; gap_carry can keep the texture running); into-boundary
  FX now END AT GAP START (never chopped); Noisia bass starvation (HP180 on
  the build's last 1-2 bars); KSHMR riser restraint (one prominent riser —
  later drops half/reverse-only/none); fx.shepard_riser (octave-staggered
  endless rise); FX layer finally WET (_SEND_DB fx -16); fill shapes 3
  (2-bar subdivision-doubling roll) + 4 (rug-pull stop at beat 3).
- **R11 ear candy**: _candy_slots scheduler — breath-level events (Tumay:
  -18..-30 dBFS, the written law of the layer) every 4-8 bars inside drops,
  hook-protected (never drop 1's first 8 bars). fx.bomb (break-entry sub
  impact → new mono fx_sub layer), dub_siren, scratch (ONE per track,
  hiphop), reverse_swell (from the track's OWN riff audio — 808Melo),
  candy_blip kinds incl. the recurring sig_chirp. Genre placements: garage
  drop_open (pads out 2 bars) + kick_fill; reggaeton drum_stop (riff keeps
  singing; muted kicks leave the pump list); drill/dnb/garage riff-swells.
- **R12 beds/width**: fx.rumble_bed + 'rumble' layer (-31 LUFS, mono,
  pump 1.25 — Hades' sidechained kick-tail return), drum 'room' bus
  (Noisia overheads: HP250→dist→wet room→LP6k under the kit; drill/hiphop
  OFF), dnb+reggaeton texture menus (wash), hiphop crackle EDGE-TO-EDGE
  (Premier), per-section reverb-send rides (master(section_spans=…): +4 dB
  breaks/build_tail, -2 dB drops), _haas_sides width on pads/texture (mono
  sum unchanged BY CONSTRUCTION — answers the "melodic pipeline is mono"
  flag), KiNK 3-beat odd loop, garage sine-sub bass double (never raw).
- **R13 mix/master**: multiband bass duck (only <170 Hz ducks fully —
  Pretolesi), low-mono fold 120→250 Hz, drum-bus clipper (Sub Focus),
  Hawkes master EQ (30 Hz HP, dnb 65 Hz shelf, TWO cascaded top shelves),
  6-9 kHz dynamic guard band pre-clip (Beau Thomas), +0.5 dB drop push
  (DJ Swivel), PLR floor alarm (Katz) guarded on pre-limiter PLR.
- **Null A/B: flags-off byte-identical to R9** (verified cross-process,
  same assets, per layer). Flags-ON cross-process deterministic (3 genres).
  NB: tinysoundfont is NOT bit-deterministic WITHIN one process (~1e-5
  drift, like the Surge unison caveat) — determinism tests must be
  cross-process; prod renders one song per process, so the same-(riff,
  variation)-same-track guarantee is unaffected.
- **Tuning levers**: gap/starve/riser/candy/swell/bomb menus + tables in
  style.py (_GAP_BEATS/_STARVE_BARS/_RISER_STYLE/_CANDY_MENU/_CANDY_EVERY/
  _SWELL/_BOMB); breath levels in fx.CANDY_LEVELS + generator peak_db;
  master: _ROOM_GAIN_DB, _DRUM_CLIP_K, _HAAS_SIDE_DB, _SEND_RIDE_DB,
  _DROP_PUSH_DB, _PLR_FLOOR, guard band params in _dynamic_guard.
- **Research VALIDATED (do not churn)**: tiered pump depths ≈ Reznikov;
  return ducking = Sub Focus; NY comp + HP120 = Ali/Guru; riser+sweep
  already simultaneous; reverse-crash already end-aligned; garage swing
  already Roger-Linn-correct; lead stacks ≥8 dB = Alchemist "felt not
  heard"; skeleton/dembow untouchable = Tainy; pattern-derived kick onsets
  BEAT a synthetic pulse (swing-aware, no pumping in kickless breaks).
- **Deliberately NOT applied**: Todd Edwards vocal chops (samples/license),
  convolution reverb (no IRs), kit re-layering (app-pack parity), Colton's
  limiter recipe (JUCE make-up-gain trap), 2nd serial master GR stage,
  garage bass-solo drops that mute the riff. Deferred R15 candidates:
  per-voice pad lanes (Playford), shared character bus (Dense & Pika),
  one-LFO-many-destinations (Sub Focus), Just Blaze lead-keyed pad duck.
- Showcase battery coverage verified: across the standing 24 combos the new
  vocabulary all fires (gap≥1 beat ×21, starve ×18, shepard ×7, swell ×7,
  bomb ×8, scratch ×1, drop_open ×3, rumble ×4, odd_loop ×3, candy ×14).
  smoke_song now prints the fx palette line per render (ears ↔ decisions).

## NEW — Round 9: percussive de-reciped + battery re-cut (2026-07-10, NOT deployed)
Owner: fixed per-category recipes would converge. Audit: minor never was one
(it's the kid's key); percussive had two — fixed drone voice + static pedal.
Now variation-driven: drone role per genre (_DRONE_ROLES), drone voicing ×3
(drone_notes voicing=), pedal static-root vs root→fifth (percussive_pedal),
percussive texture = genre's + drone/wash. 12 presses → 10 distinct
percussive configs. Showcase uses per-genre variation numbers (1+i*7 etc.)
— columns no longer share structures. Battery re-rendered: 24/24 distinct,
23 changed vs R8 (1 same-draw = determinism), percussive spread visible in
MODE lines. All 9 suites green. Ears: engine/out/showcase/.

## NEW — Round 8: tonality fix + SHOWCASE battery (2026-07-10 late night, NOT deployed)
Owner caught percussive_dnb rendering with chord pads (tonality 0.579 =
borderline; v3 tipped melodic; mode never printed in logs). Fixes:
- riff_tonality now MULTIPLICATIVE (explain × (1−cluster)²) — cluster riff
  0.58→0.21, percussive at ALL variation numbers, pinned by a regression
  test on the SHIPPED examples/cluster_riff.json. Thresholds 0.45/0.60.
- smoke_song prints MODE=… (verify renders by log, never assume).
- **SHOWCASE battery** (owner: Suno-style variety demos): `modal run
  infra/modal_app.py::showcase` renders 24 MP3s in parallel — per genre:
  major_a(v1)/major_b(v5)/minor(Am riff, v2)/percussive(cluster riff, v4)
  → main-repo engine/out/showcase/. All 24 hash-distinct; 6 percussive
  MODE lines confirmed in logs. Extend by adding rows to the plan in
  `showcase()` — this is the standing demo battery for future changes.
- Known cosmetic: same variation number ⇒ same structure across genres
  (structure derives from variation only) — use different numbers per genre
  if the battery should show structural spread per column.
- Say "variation number", not "nonce" (owner).

## NEW — Round 7: percussive production mode (2026-07-10 night, NOT deployed)
Owner: discordant user patterns (early-Photek ref) shouldn't get chords
forced under them; intros too samey; asked what "nonce" means (say
"variation number"!).
- `riff_tonality(riff)` 0..1 = 0.6×chord-explainability + 0.4×(1−cluster
  fraction of overlapping 2nds/7ths). <0.55 → PERCUSSIVE mode; 0.55–0.65
  variation-number-tipped; else melodic. Same tune ⇒ same character family.
- PERCUSSIVE (`style.production_mode`): prog=[0,0,0,0] root pedal; pads →
  open-FIFTH drone (no third) on the dark role; chord soften/snap skipped;
  rhythm-led treatment weights (_TREATMENT_W_PERC); each drop rotates drum
  seasoning overlay; texture forced on + rendered edge-to-edge.
- Intros: 7 characters (menu widened in THIS commit — that re-picks intros
  for existing variation numbers; harmless, audited: v2 flipped high→low,
  divergence confined to intro+build tail; techhouse v1/dnb v4/var_4 renders
  byte-identical R6→R7 = determinism working).
- examples/cluster_riff.json + ::song --args/--name for arbitrary-riff
  auditions. EAR FILE: engine/out/percussive_dnb_170.mp3 (cluster riff, dnb
  170 — the Photek check) + re-rendered var_0..5 + song_<genre>.
- All 9 suites green on Modal. Tuning: tonality thresholds in choose_style,
  _TREATMENT_W_PERC, drone_notes voicing.

## NEW — Round 6: palette explosion + discordance fix (2026-07-10 night, NOT deployed)
Owner: intros samey; garage variation discordant; wants LOADS more sounds
(twinkles/rave synths) per genre; asked re render-time UX + per-genre
similarity risk.
- **BUG FIX (the discordance)**: lead stack rendered the ORIGINAL riff looped
  while the main voice played DEVELOPED phrases — two melodies at once. Stack
  now renders the same developed span.
- Intros: 5 characters (+fragment = opening question over pads; +high =
  octave-up tease) × intro LPF nonce-varied {1500,2500,4000,open}.
- Palette: +16 GM voices (celesta/musicbox/vibes/marimba/kalimba/harp/clav/
  nylon/brass/choir/fmep/tubular + square/saw/calliope/fifths leads),
  +7 Surge patches (lead_hoover, lead_acid, stab_rave, pad_glass, bell_glass,
  bass_acid, bass_fm). LEAD_STACKS = 4/genre; pad roles 3-4/genre; bass 2-4/
  genre; drum seasoning 3rd overlays (909 cowbell techhouse, shaker garage/
  hiphop, woodblock reggaeton) + KITS aux voices.
- **Render time measured**: 99 s wall incl CLI overhead (~75-85 s actual) vs
  ~139 s pre-variety baseline — UX unchanged; async-jobs plan stays parked.
- Diversity: 40 nonces → 31-37 distinct (pad,bass,stack,intro) combos/genre
  on 4 of ~15 axes. All 9 suites green; 12 ear files hash-fresh delivered.

## NEW — Round 5: phrase-level motif DEVELOPMENT (2026-07-10 late, NOT deployed)
Owner: R4 still read as one tiny variation / 16 bars; wants it REALLY
interesting, motif intact. Root cause: variation was an exception (one bar
per cadence). Now `develop_phrase` treats EVERY 4-bar phrase: statement
(~1/3, pure anchor) / vary_end (final-bar rewrite) / octave_up (whole phrase
+12) / call_response (2nd half a diatonic 3rd down) / sparse_breath (bars
2+4 thinned). Seeded per-phrase sequence (`_phrase_treatment`, no repeated
developments back-to-back); drop 1 opens with 2 forced pure phrases;
`ornament_every` removed. Tuning: `_TREATMENT_W` in arrange/render.py +
pure_phrases count. All 9 suites green; 12 ear files hash-fresh in main-repo
engine/out/. Deploy gated on owner ears.

## NEW — Round 4: REAL riff variations (2026-07-10 late, NOT yet deployed)
Owner (3rd riff complaint): R2/R3 "ornaments" only added quiet notes/velocity
— inaudible. R4 rewrites the bar on the cadence (`vary_bar`): ending_fill
(scale run into next bar), answer (2nd half diatonic 3rd down), retrigger,
rest_gap + light kinds. TWO kinds per track alternate across variation bars;
"none" removed; every ∈ {4,8,16} favouring 4/8. Clash notes SNAP to chord
tones on variation bars (`resolve_clashes`); velocity softening elsewhere.
Drop 1 pure for its FIRST 8 BARS only (was whole drop). Proven at note level
+ all 9 suites green on Modal. Ear files (all hash-fresh, watch for stale
copies — one variations run died on network mid-save and nearly shipped R3
files): var_0..5 + song_<genre> in main-repo engine/out/. Deploy gated on
owner ears.

## NEW — Round 3: the LEAD is the fix (2026-07-10 eve, NOT yet deployed)
Owner on round 2: genre songs still sound alike. Diagnosis (probe): the riff/
lead is the LOUDEST melodic layer (−4.8 dBFS peak vs pads −12.7) and was
identical across genres + unlayered — round 2's variety sat 6–13 dB under it.
Also the ::songs demo rendered every genre at variation 0 (each genre's
plainest take). Round 3:
- **LEAD_STACKS (always-on)**: per-genre lead texture UNDER the kid's
  untouched instrument (techhouse rave-unison+shimmer, dnb unison/strings,
  garage shimmer+keys, drill dark-body−12+string-whisper, hiphop Rhodes,
  reggaeton shimmer+keys; 2 recipes/genre nonce-picked; every layer ≥8 dB
  down — pinned; riff LUFS calibration keeps composite level).
- **Ornament cadence** (owner spec): `ornament_every` ∈ {4,8,16} bars, fires
  at phrase-end bars in builds AND drop 2+; new "cadence" pickup ornament.
  **soften_clashes**: chord-aware velocity ×0.85 on semitone-rub notes in
  post-hook sections (helps discordant riffs; velocity only). Drop 1 pure.
- **::songs fixed**: per-genre nonces 1,4,7,10,13,16 (sizes now differ —
  different skeletons visible). Fresh ear files in main-repo engine/out/
  (all 12 hash-new): var_0..5 + song_<genre>.
All 9 suites green on Modal. Deploy still gated on owner ears.

## NEW — Round 2 after owner ears (2026-07-10 pm, NOT yet deployed)
Owner verdict on round 1: good but palettes converge across genres, riff too
static, lead too plain. Round 2 (4 commits, all suites green local+Modal):
- **Riff ornaments** (`ornament_riff`): echo / octave_pop / push on PHRASE-END
  bars of drop 2+ only; **drop 1 always pure verbatim** (the hook rule).
  Octave/velocity only; melody notes never removed/re-timed (pinned).
- **Lead layering** (`LEAD_LAYERS`): sparkle (+12 pluck −11 dB) / shadow
  (dark unison −15 dB) under the riff in full-riff sections; drill/hiphop
  shadow-only. GM fallbacks.
- **Palette spread**: pad voicings close/first_inv/alt; new roles strings_pad
  (GM 49 — drill string-loop DNA)/newage (GM 88); bass_round patch; octave-pop
  bass feels (4-tuple feel slots; register test now 36–59).
- **Swoosh character**: riser f0/f1 bands per genre (drill/hiphop dark
  200-2500, dnb 400-12k); NEW `fx.spinback` vinyl brake (garage/hiphop menus).
- Fresh ear files in main-repo engine/out/ (all 12 re-rendered, hashes differ
  from round 1): var_0..5.mp3 + song_<genre>.mp3.

## NEW — Genre authenticity + per-press variety (2026-07-10, 7 increments, NOT yet deployed)
Full plan: `~/.claude/plans/sounds-graet-now-we-delightful-tarjan.md`. All on
`claude/sess-67239ccc`; all 9 suites pass remotely; **ears pending** on:
main-repo `engine/out/`: `var_0..5.mp3` (same riff × 6 nonces — the variety
check), `song_<genre>.mp3` × 6 (authenticity check), `dnb_drums_172.mp3` vs
`dnb_drums_virtuosity_172.mp3` (kit A/B) + drill/hiphop/reggaeton/techhouse
drums. **`modal deploy` NOT run — prod still serves the old engine until the
owner signs off.**
- **style.py = the ONE place the nonce is spent** (`choose_style` → frozen
  `ArrangeStyle`; named decorrelated sub-streams; per-genre `_GENRE_MENU`,
  signature-first ~50%). Structure fields derive from variation ONLY.
- **Song shapes**: classic / cold_open (drop first) / double_drop /
  late_break + build_frac {1/5..1/2} + drop_bias clamps + intro/break/outro
  4|8 + intro character (sparse/pad_open/low) + escalation modes.
  `_fit_window` corrective loop = 180–240 s structural (exhaustive test).
- **Drums = app pack for ALL genres** (fetch_appkit all-genre + layered dnb
  kick + baked trimMs; techhouse hybrid keeps bounce kick/sub). Seasoning
  overlays `DRUM_VARIANTS`/`pattern_for` (hats/rim/shaker only — skeleton
  pinned by test). Fill shapes ×3 (techhouse fills were silently missing a
  snare voice — now roll the CLAP).
- **Pads per genre**: garage=organ skank, techhouse=pluck stabs, drill=dark,
  hiphop=epiano, reggaeton=pizz, dnb=supersaw; `_PAD_RHYTHMS` comping ×2.
  **Bass per genre**: bass_pluck / bass_sub808 / reese + `_BASS_FEELS`
  (2-step bounce, kick-locked 808s, tresillo, roller…), variant 0 = legacy.
- **Textures** (−30 LUFS slot): hiphop/garage crackle, techhouse wash,
  drill tonic drone; dnb/reggaeton none. **FX palette** seeded per genre
  (hiphop risers default OFF; impact f0/f1 per genre; downlifter/
  reverse-crash/throw nonce-gated). Riff break variants octave_echo /
  call_response (octave-only transforms).
- **Progressions**: banks 4→7/mode (all contain degree 0), quality floor
  ≥0.8×best (2–4 candidates), seeded pick.
- Determinism fix: synth-drum `_noise` was unseeded (broke same-nonce⇒same-
  track on the no-assets fallback path).
- Tuning levers: menu weights in `style.py` (`_pick` signature-first 50%),
  `_IMPACT`/`_FILL_MENU`, `_PAD_RHYTHMS`/`_BASS_FEELS` tables, overlay rows
  in `DRUM_VARIANTS`, texture levels in fx.py generators.

## Mental model (important)
The HTML app stays the front-end. The track engine is a **back-end service** the app calls —
exactly like the current "Make AI track" already calls a Firebase Function → Stable Audio.
We're swapping the engine inside that call. "Local" = dev/testing only; production runs on
**Modal** (cloud). Gigabyte sample libraries + mixing + AI never run in the browser.

Flow:  Browser (HTML)  →  server engine  →  finished MP3  →  browser plays it

## Hard rules (see PROJECT_RULES.md)
1. **Samples MUST be licensed for AI / automated-generation use** (not just royalty-free for your
   own music). Record license + AI-use permission in LICENSES.md before adding any pack.
2. **No stems** produced or distributed — final mixed MP3 only. (So **no Demucs**.)
3. Riff rendered from exact MIDI, never altered by AI.

## Decisions made this session
- **Add a software-synth engine** (Vital/Surge XT via pedalboard VST hosting) for the EDM melodic
  slots — lead/bass/pads — because synth *movement* (filter env, detune, LFO) is what reads as
  "produced." Keep sampled libs for acoustic (piano). Synths are GPL → fine server-side (we serve
  audio output, not the software).
- **Drums = real one-shot samples**, NOT synthesis (pro 808s are processed samples). Use packs
  licensed for AI use (CC0, or a developer/multimedia license). Splice rejected as the default
  (subscription license not written for automated products).
- "Pro pop" is achievable with MIDI+samples+production; riff fidelity does NOT force a robotic
  sound (humanize timing/velocity; reharmonize the same lead per section, etc.).

## Done & verified (engine/)
- `kidseq_engine/sequence.py` — exact sequence→MIDI mapping (6 tests pass). Riff-fidelity guarantee.
- `render/` — riff + drums render end-to-end → `out/{riff_stem,drums,mix}.wav`.
- Real dedicated samples: **piano**=Salamander (CC-BY), **synth**=FreePats SynthSquare (CC0),
  **bass**=FreePats Lately Bass (CC0). trumpet/strings/bells = GeneralUser GM (placeholder).
- `scripts/fetch_soundfonts.py` re-downloads soundfonts (gitignored). `LICENSES.md` current.
- **NEW — `kidseq_engine/mixmaster/` (stage D = mix + master) — built & verified (2026-06-30).**
  Pedalboard chain on the rendered layers: per-layer EQ/comp/space (riff = EQ + reverb ONLY, never
  pitch/time), a **musical sidechain pump** (ducks melodic layers to the kick — onsets read from the
  symbolic drum pattern, not audio detection; the EDM "pump"), per-genre gain preset, bus glue
  compressor, then a **loudness master** that lands exactly on the LUFS target with the true peak
  kept under the ceiling, exported to **MP3** (lameenc, no ffmpeg). Per-genre presets for all 6
  styles in `master.py:GENRE_PRESETS`. `smoke_track.py` → `out/track_master.wav` + `out/track.mp3`,
  prints loudness/TP. Verified: every genre masters to **-10.00 LUFS**, TP safely under -1 dBTP;
  pump ducks to (1-depth); 8 master tests pass.

Run: `./.venv/Scripts/python smoke_track.py` (full mastered track) ·
`./.venv/Scripts/python smoke_step1.py` (raw layers) ·
`./.venv/Scripts/python tests/test_sequence.py` · `./.venv/Scripts/python tests/test_master.py`

## Parked
- sfizz/VSCO for trumpet/strings/bells — no clean SF2; needs sfizz (Linux/Modal easy, Windows
  painful). Leaning: do it on the Modal build, not locally.
- **Soft synth (Vital/Surge via pedalboard VST hosting)** — pedalboard CAN host VST3, but it needs
  the plugin binary installed and is awkward to run/verify headless on Windows. Natural home is the
  **Modal/Linux build** (same call as sfizz). Deferred there, not attempted blindly this session.
- **True peak runs conservative (~-2 to -4 dBTP, ceiling -1).** Loudness is exact; peaks sit below
  the ceiling because loudness is the *last* (downward) gain stage. Fine for v1; to get peaks nearer
  the ceiling, drive the limiter harder before the loudness trim.

## NEW — Real CC0 drum kits (stage = "right sounds: drums") — built & verified (2026-06-30)
User decision: get the *right sounds* before A/B mix-tuning (no point tuning a mix on placeholder
GM drums). Per-genre kits chosen (**Option B**). Drums now render from real CC0 one-shots, NOT the
GM soundfont.
- **Sources (both CC0 1.0, AI-use OK — see LICENSES.md):** Boochi44/free-drum-samples (electronic
  kick/sub/snare/clap/hats, 3 flavours) + VCSL (cowbell/shaker/woodblock aux perc).
- **`scripts/fetch_drumkits.py`** clones Boochi (shallow) + downloads 3 VCSL raw files, curating a
  flat layout `assets/drums/{hard-trap,bounce,soulful}/<voice>.wav` + `assets/drums/perc/<perc>.wav`
  (gitignored, like soundfonts).
- **`kidseq_engine/render/sample_kit.py`** — `KITS` maps each genre→voice→[(relpath, gain)] **layers**
  (v1 = one layer/voice; the list is the hook for per-voice layering later). Per-genre mapping:
  techhouse/hiphop/reggaeton→Bounce, dnb/drill→Hard Trap (+808 sub), funk→Soulful Vintage; rim←VCSL
  woodblock, cowbell/shaker←VCSL. `read_wav` added to audio.py (8/16/24/32-bit, stereo→mono, resample).
- **`render/__init__.py`** drum priority is now: **sample-kit > GM soundfont > numpy synth.**
  `drum_source(style)` reports which path fires.
- **Verified:** `render_all_genres.py` → `out/genre_<style>.mp3` for all 6, every one `drums=sample-kit`,
  all master to -10.00 LUFS, TP under ceiling. `tests/test_sample_kit.py` (4 tests) + existing
  sequence/master suites all pass.

Run: `./.venv/Scripts/python scripts/fetch_drumkits.py` (once) ·
`./.venv/Scripts/python render_all_genres.py` (audition all 6) ·
`./.venv/Scripts/python tests/test_sample_kit.py`

## Audition verdict (user ears, 2026-07-02) — first Boochi/VCSL pass
Only **techhouse works**. The rest: **dnb** = electro snares (wrong — needs breakbeat DNA);
**drill** = 808 bass where the kick should be; **hiphop/funk** = too lofi. Genre-by-genre fix
plan, **dnb first** (user pick). Note: genre-appropriate tempo matters for a fair listen — the
first audition ran everything at 120.

## NEW — DnB rebuilt on a real acoustic kit (2026-07-02)
User requirements: samples actually used in DnB (breakbeat DNA, not random one-shots), audition
at **170 BPM**, **drums only** (no piano riff).
- **Source: Virtuosity Drums** (sfzinstruments/virtuosity_drums, **CC0-1.0** verified) — real
  drummer-played jazz/club kit (Versilian/Karoryfer). This is the legit stand-in for classic
  breaks: Amen/Think themselves are uncleared copyrighted recordings (hard rule #1 bans them;
  `yaxu/clean-breaks` rejected — no license).
- `fetch_drumkits.py` gains `fetch_virtuosity()`: 6 top-velocity one-shots, FLAC→WAV via
  pedalboard (48k→44.1k handled by read_wav) → `assets/drums/virtuosity/`.
  Both kicks fetched: `kick.wav` (snares-off, tight — mapped) + `kick-live.wav` (wire rattle, swap candidate).
- `sample_kit.py` dnb kit repointed: kick=virtuosity, **snare = centre hit + rimshot layered**
  (first real use of the layering hook — the DnB crack), hats=virtuosity.
- `render_dnb_audition.py [bpm]` → `out/dnb_drums_170.mp3` — 8 bars @ 170, drums-only through
  the real dnb master chain (silent riff layer satisfies master()'s riff requirement).
- Verified: renders sample-kit, -10.26 LUFS, -1.00 dBTP; all 3 test suites pass.

## NEW — App plays SAMPLE drum kits (2026-07-02)
The sequencer's drum engine now prefers real one-shot samples over synthesis, per voice.
- `public/index.html`: `loadDrumSampleKits()` fetches `samples/drums/manifest.json` +
  decodes layered WAVs (per-voice gain + trimMs); `playDrumsAtStep`'s generic dispatch
  tries the sample kit first, falls back to the synth voice — app fully works without
  the folder. Kits route through `drumBus` (fader/comp/swing/tempo-ramp all apply).
- `public/samples/` is **gitignored** + in firebase.json hosting **ignore** (binaries
  stay out of git and deploys); install locally with scratchpad `install_app_kits.py`
  (28 samples, 6 genres: dnb=user pack, drill=Greeze, techhouse=TR-909, hiphop=The
  Source, funk=Hyperfunk+808CB, reggaeton=dancehall KitC).
- PROJECT_RULES.md rule 1 revised at owner's direction: licensing = owner's decision,
  LICENSES.md is a record not a gate.
- Verified live: all 6 genres play samples in the app, tempo ridden 120→180→80 during
  playback, zero console errors; prod (no samples folder) falls back to synth.
- **Prod sample delivery SHIPPED (2026-07-04):** all kits packed into a single
  `public/samples/drums.pack` (`[4B LE headerLen][JSON header][concatenated wavs]`;
  header carries per-layer o/n/g/trimMs/room). App loader tries pack → dev folder →
  synth. Pack is committed + hosting-served (raw `samples/drums/` folder stays
  gitignored + hosting-ignored). Rebuild with `tools/install_app_kits.py`. Prod now
  plays the real kits.

## Next step — ears on out/dnb_drums_170.mp3
1. User listens to the 170 BPM DnB drum track. Tuning levers ready: swap kick→kick-live.wav,
   rim layer gain (0.55), hat balance in `_GAIN`, or go shopping for a different snare
   articulation (Virtuosity has 11: stickshot, flam, buzz, halfopen…).
2. When dnb passes: same treatment for **drill** — user hears "808 bass instead of kick".
   Drill's pattern fires kick+sub on the SAME steps; likely the 808 sub swamps a weak kick
   (`hard-trap/kick.wav` = hard-kick-01.wav — audition it solo to confirm before swapping).
   Then de-lofi **hiphop/funk** (several Boochi picks were the lofi variants — check
   `fetch_drumkits.py` prefs; Virtuosity may serve funk directly).
3. THEN the A/B mix-tune of `master.py:GENRE_PRESETS` against reference tracks, genre by genre.

## NEW — Modal/Linux build STOOD UP (2026-07-09)
The engine now runs end-to-end on Modal (workspace `joe983`, app `kidseq-engine`).
`infra/modal_app.py`: debian_slim image (+git +portaudio19-dev — pyaudio builds from
source on Linux) + persistent Volume `kidseq-assets` (31 files, populated once by the
fetch scripts; functions symlink `engine/assets` → the volume so relative paths work).
- **Verified:** all 18 tests pass remotely (sequence/master/sample-kit);
  `smoke` renders in the cloud → `out/modal_track.mp3` locally (-10.00 LUFS, -2.09 dBTP).
- Run (from `engine/`, `PYTHONUTF8=1` needed on Windows — Modal CLI prints ✓):
  `python -m modal run infra/modal_app.py::{populate_assets|run_tests|smoke}`
- Auth: `~/.modal.toml` (this laptop linked via `modal token new`).
- **Unblocked:** the parked sfizz/VSCO orchestral + VST soft-synth work now has its
  Linux home — extend the image (apt sfizz / synth binaries) in `infra/modal_app.py`.

## NEW — trumpet/strings/bells = real VSCO 2 CE via sfizz (2026-07-09, Modal)
GM placeholders replaced on the Modal build. No Debian sfizz package and no maintained
VSCO SFZ port exist, so both halves are built ourselves:
- **`sfizz_render` compiled from source** in the Modal image (cmake layer, cached;
  JACK/LV2/VST all OFF). No sfizz on Windows — local dev keeps the SF2/GM fallback.
- **`scripts/fetch_vsco.py`** sparse-clones 3 folders of sgossner/VSCO-2-CE (**CC0
  verified** from repo LICENSE) and **generates .sfz files**: Trumpet susvib +
  Violin Section susVib (11 pitches × v1/v2 velocity takes), Glock (6 pitches).
  **Root detection is mode-split** — autocorrelation for the harmonic sustains
  (uniform +1-octave offset vs filenames, drift <25 cents, octave sanity-snap to the
  filename prior) but **FFT-peak-near-named for the glock** (bell partials are
  inharmonic; autocorr octave-errors badly; glock filenames ARE at sounding pitch).
  An FFT octave-picker for the harmonic voices was tried and REVERTED — strong 2nd
  harmonics flip it an octave up on random takes. `--force` regenerates.
- **`render/sfz_render.py`** — looped-riff MIDI (mido) → `sfizz_render` CLI → WAV →
  mono float32, same length contract as sf_render. `riff_audio` priority:
  **sfz > SF2 > numpy synth** (`riff_source()` logs which fires).
- **Verified:** 23/23 tests remotely (tests/test_sfz.py new, 5 tests — render tests
  auto-skip where sfizz is absent); `render_orchestral_audition.py` on Modal →
  `out/orch_{trumpet,strings,bells}.mp3` all "sfz(VSCO 2 CE …)", −10 LUFS, TP ≤ −1.
  `modal run infra/modal_app.py::orchestral` pulls them local. **Ears still pending**
  (user). Volume now 84 asset files.
- Known limitation: the engine pipeline is mono end-to-end, so the violin *section*
  will read narrower than the app's dual-take stereo strings — a mix-stage question
  (stereo layers), not a sample-quality one.

## NEW — Surge XT soft synth for synth/bass (+pad) (2026-07-09, Modal)
The second half of "right sounds part 2": synth-family voices now render through a
REAL soft synth (filter envelopes / unison detune / chorus = the "produced" movement).
- **Surge XT 1.3.4 (GPL, server-side only)** installed from the official .deb into the
  Modal image; **hosted headless by pedalboard** — works with NO display/xvfb once
  `libasound2` is present (that was the sole missing runtime dep; pedalboard's
  "scan failure" error means a missing shared lib — `ldd | grep "not found"` it).
- **`render/vst_render.py`** — patches are param dicts (`PATCHES`): `synth` = 5-voice
  detuned-saw rave lead w/ LP24 sweep + chorus; `bass` = reese (2-voice detune) +
  sine sub, vintage ladder; `pad` = 7-voice supersaw, slow attack (for the arrangement
  stage — not a grid voice). Envelope times via `_env(seconds)` (Surge's normalized
  log2 scale). `.fxp` factory patches are NOT loadable via pedalboard — param dicts
  are deliberate (deterministic + reviewable). Full patch re-applied every render.
  NB bass notes arrive already −24 from sequence.py — do NOT transpose again.
- **`riff_audio` priority:** sfz (trumpet/strings/bells) / vst (synth/bass) > SF2 >
  numpy. `riff_source()` says which fired.
- **Verified:** 28/28 tests remotely (test_vst.py new; render tests auto-skip w/o the
  VST3); audition now covers all 5 upgraded voices → `out/orch_{trumpet,strings,bells,
  synth,bass}.mp3`, all −10 LUFS, TP ≤ −1. **Ears pending** (user) — patch tuning
  levers live in `PATCHES` (cutoff/resonance/detune/env times per voice).
- LICENSES.md: Surge GPL-3 note (server-side render only, nothing distributed).

## NEW — Arrangement stage (PLAN step 3) BUILT (2026-07-09)
`kidseq_engine/arrange/` — riff → full ~2-minute arranged song. First render verified
on Modal: sample riff (C, 120, techhouse) → I–V–vi–IV, 64 bars ≈ 128 s,
`out/modal_song.mp3` at −10.52 LUFS / −1.00 dBTP. **Ears pending.**
- **Progression:** curated diatonic bank (4 major + 4 minor, 4-chord loops) scored by
  riff chord-tone coverage (duration-weighted, on-beat bonus, chord 1 ×2) — in-key by
  construction. Deterministic. **music21 deliberately NOT used** — sequence.py's tested
  pitch model covers diatonic triads; revisit only for real voice-leading.
- **Structure:** `plan_song(tempo)` = intro→build→drop→break→build2→drop2→outro; drop/
  build bars sized by tempo tier so total lands ~1:40–2:30. **Drops use riff.notes
  VERBATIM by construction** (`riff_variant` never sees them — the fidelity guarantee,
  asserted in tests). Other sections: `sparse` (on-beat notes) / `sparse_low` (−12).
- **Bass:** chord roots C2–B2; offbeat 8ths (techhouse/funk/reggaeton), 2-step (dnb),
  long subs (drill/hiphop). **Pads:** whole-bar triads C4-region, rendered by the Surge
  `pad` patch on Modal, GM Synth Strings (`INSTRUMENT_SF["pads"]`) fallback locally.
- **Rendering:** `arrange/render.py::build_song` overlap-ADDS per-section renders into
  full-song layers (release tails bleed across boundaries — never truncate). One-shot
  spans use the `bars=1, bar_beats=span` trick on the existing riff renderers, so every
  layer inherits the sfz/vst > SF2 > synth chain. Drum sections: `full` vs `lite`
  (hats/rim/shaker/cowbell only) via new `drums_audio_pattern` (+ `pattern=` overrides
  in sample_kit/drums). **Pump kicks only from `full` sections** — breaks don't duck.
- Run: `python smoke_song.py` · Modal: `python -m modal run infra/modal_app.py::song`
  → `out/modal_song.mp3`. Tests: `tests/test_arrange.py` (6, pure theory — run locally
  too); 34/34 total on Modal.
- Tuning levers when ears arrive: section bars in `plan_song`, bass feels in
  `bass_notes`, pad voicing/register in `pad_notes`, lite-section voice set
  `_LITE_VOICES`, per-layer gains stay in `master.py:GENRE_PRESETS`.

## NEW — 3-minute songs + professional mix/master (2026-07-09, 6 increments)
Full plan: `~/.claude/plans/the-modal-song-sounds-enchanted-lobster.md` (approved).
All merged to main; every increment gated by `tests/test_master_gates.py` (+ test_fx.py).
**Song length:** `plan_song` is cycle-based — build→drop cycle COUNT scales with tempo
(1 cycle @40bpm … 4 @200), lands 3:05–3:20 across the app's whole 40–200 clamp.
**Mix/master (was: dup-mono, no slotting, timid limiter):**
- (1) **Stereo end-to-end** — all renderers emit (N,2) (tsf de-interleaved, sfizz via
  `read_stereo`, Surge transposed); drum one-shots constant-power panned; bass hard-mono;
  mono-below-120 fold; gates: genuine-stereo / mono-compat / sub-mono.
- (2) **Master endgame** — DC → master EQ (HP24, genre low shelf, −280 mud, −3.2k
  anti-fatigue, +11k air) → windowed-LUFS calibration (−16) → tempo-synced glue →
  tanh clip → **drive-into-limiter LUFS convergence at 4x** → guards.
  **`_brickwall` is OURS**: pedalboard's `Limiter` is a JUCE limiter WITH make-up gain
  (ceiling ≠ threshold, measured +2.2 dBTP) — unusable. Ours: asymmetric max-filter +
  Hann FIR with a hard gain guarantee. **Two traps fixed:** resample_poly edge-ringing
  (pad/trim around the 4x sandwich) and content-dependent decimation ISP overshoot
  (final-ceiling trim INSIDE the loop, else masters land 0.3+ dB off target).
- (3) **Mix rebuild** — kick-slot FFT detection (`sample_kit.kick_slot_hz`); boards
  slot drums AT/bass AWAY-FROM the kick fundamental; pads inverse-EQ'd at 3k; per-layer
  LUFS calibration over ACTIVE regions (drums −18/riff −20/bass −21/pads −26 — genre
  gains are now small creative offsets); sidechain 2.0 (dip→hold→tempo-synced recovery,
  per-layer mults riff .5/pads 1.15, cap .65). **SWING is now in the engine**
  (`drums.swung_step_offset`, funk .16/techhouse .08) — renderers AND pump share it.
- (4) **Shared space** — ONE wet-only reverb return (HP300/LP7500, room .35–.50/genre,
  20ms predelay; sends riff −14/pads −9/drums −22; intro riff rides −7 = "distant open"
  via `riff_wet_spans`); parallel NY drum bus (−32dB 8:1 crush, LP8k, +6, −6..−10/genre).
- (5) **Arrangement FX** (`render/fx.py` + build_song flags, each null-tested off):
  riser/impact/crash/reverse-crash/downlifter (numpy-synthesized, seeded from the riff
  via `fx.song_seed`), pre-drop GAP, build drum fills (16th snare rolls, rim-led for
  drill/hiphop), LadderFilter automation (intro riff LP2.5k; builds sweep 900→18k
  ending AT the drop; breaks close pads; **drops never touched — riff-verbatim null
  test**), drop2+ escalation (kit/pads boost, pad octave-double, deeper gate, doubled
  impact), **riff delay-throw into breaks auto-decided per track** (`fx.throw_fits`:
  tail note + tempo ≤150 + ≤10 notes; owner chose per-track auto).
- **Surge determinism caveat:** unison phase RNG isn't reseeded by VST reset — renders
  are audibly identical but not bit-identical (retrigger enabled to minimize). Null
  tests pin the SF2/synth fallback via `KIDSEQ_SURGE_VST3=nonexistent`.
- Ear files in MAIN repo `engine/out/`: `modal_song_stereo/master2/mix3/mix4.mp3`
  (increment A/Bs) + `song_<genre>.mp3` × 6 (full sweep, `::songs` entrypoint).

## NEW — ENGINE IS LIVE IN PROD (2026-07-09, step 6 v1 synchronous)
**The AI button now calls the engine, not Stable Audio.** Wiring:
- **Modal endpoint** `infra/modal_app.py::render` — `POST {token, sequence, variation}`
  → audio/mpeg. Deployed persistently (`modal deploy infra/modal_app.py`) at
  `https://joe983--kidseq-engine-render.modal.run`. Auth = shared ENGINE_TOKEN
  (Modal Secret `kidseq-engine-auth` = Firebase Secret `ENGINE_TOKEN`, same value).
  Verified: 401 on bad token; real render HTTP 200, 7.7 MB in 139 s incl. cold start.
- **`generateAiTrack` rewritten** (functions/index.js): takes `{sequence, variation,
  name}` (the saved-state shape — parse_sequence's input), POSTs to the engine,
  saves the MP3 to `users/{uid}/tracks/` exactly as before. Quota/refund/auth
  UNCHANGED. `timeoutSeconds: 540`. Stability code/prompt deleted (git history);
  STABILITY_API_KEY secret no longer bound. `ENGINE_ENDPOINT` in .env.kid-sequencer.
- **Client** (`runAiGeneration`): sends the grid symbolically (flattened notes +
  key/tempo/instrument/drumStyle-audio-key) + `variation = Date.now()%1e6` — a fresh
  nonce per press. No WAV capture/upload (captureSequenceToWav now unused, kept).
  Callable timeout 540 s; spinner copy says "a few minutes".
- **Per-press VARIATION** (owner: "can't judge until we know the variation"):
  same (riff, nonce) = identical track; new nonce varies progression colour (top-2
  scoring), build:drop split (3 feels), and every FX seed (risers/crashes/throw).
  The riff itself NEVER varies.
- **Kick punch pass** (owner: "kicks punch, never boom"): NY crush path HP120
  (was amplifying kick tails), slot boost tightened +1.0/q1.4, drums HP35,
  dnb low shelf −2 dB @85 (acoustic kit sustain).
- **Rollback**: redeploy functions from the pre-wiring commit (Stable Audio path
  is in git); hosting rollback via Firebase console.
- **Next**: owner presses AI button in prod several times to judge variation +
  the mix; funk/reggaeton engine kits still need de-lofi rebuild (owner: "all
  over"); async job flow (Firestore jobs + webhook) if synchronous UX feels bad.

## Then — synths/orchestral ("right sounds", part 2, Modal build)
User: don't accept GM placeholders for trumpet/strings/bells or the EDM lead/bass/pads — do it AFTER
drums. This is the trigger to stand up the **Modal/Linux build** (soft synth via pedalboard VST
hosting + sfizz/VSCO orchestral — both parked below because they're painful on Windows, easy on Linux).

## Remaining build order (docs/PLAN.md)
- Step 3: music21 arrangement (progression bank + bass + pads + structure) — the mixmaster already
  takes `bass`/`pads`/`texture` layers + per-genre gains, so arrangement plugs straight in. (task #9)
- Step 5: generative texture (Stable Audio Open on Modal)  (task #10)
- Step 6: wire async engine into Firebase generateAiTrack + Firestore jobs  (task #11)
- Step 7: breadth (6 genres/instruments) + sfizz/VSCO upgrade for the 3 GM ones  (task #12)
