# Where we are / next session

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
