# Plan: Riff-Anchored Track Engine for Kid Sequencer

## Context

**What this is.** Kid Sequencer (`C:\Users\Joe_C\Documents\kid-sequencer-repo`) is a near-finished
kids' music web app (vanilla JS on Firebase Hosting; Firebase Functions Node 20 / Firestore /
Cloud Storage; Stripe £4.99/mo Pro = 10 AI tracks/mo + top-ups). Its "Make an AI track" feature
is the last major piece before release. The magic it promises: *"my exact little tune became a
real produced song."*

**The problem.** The current feature renders the sequence to a WAV seed and calls **Stable Audio
2.5 audio-to-audio at `strength: 0.75`** (`functions/index.js:54`, `:182 generateAiTrack`). The
code comment is explicit that this *deliberately* sacrifices the riff for production polish — and
that's the user's exact complaint: the hook comes back unrecognisable. This is **not a tunable
bug**: audio-to-audio diffusion reinterprets audio by design. Low strength keeps the riff but
sounds like the raw seed; high strength sounds produced but loses the riff. No single value gives
both. Tuning `strength` is a dead end.

**The unlock.** The input isn't a messy hum — it's **exact symbolic data** (an 8-row × 16-step,
1-bar grid: `{row, start, len}` + key + tempo + instrument + drumStyle). So the riff never has to
be *generated* at all. We render it verbatim and have the engine build the production *around* it.

**Decisions made (with the user):**
- **Hybrid, riff-anchored engine** — exact riff stem + algorithmic arrangement (musical bones) +
  generative AI for texture/realism layers only.
- **Drop Stable Audio entirely** — replace the audio-to-audio call with this engine.
- **Fold into Kid Sequencer** — it's already an integrated feature, not a new product. The new
  engine lives in the Kid Sequencer repo and is called from the existing `generateAiTrack`.

**Outcome.** Same UX and billing; `generateAiTrack` stays the orchestrator (auth, quota,
refund-on-failure, storage save). Inside it, Stable Audio is replaced by a new async engine that
**guarantees** riff fidelity (the riff is rendered, not inferred) and produces a believable
kids-EDM/pop track.

> Supersedes the earlier "hum → MusicGen-melody" scaffolding in
> `C:\Users\Joe_C\Documents\gitHub_repos\music_production_repo` (built on the wrong input
> assumption). Salvage from it: the `master/` chain scope, the seed-as-contract idea, the Modal
> spike conventions, and `LICENSES.md`. That standalone repo can be archived once those move in.

---

## Architecture — riff-anchored, 4 stages

The exact-riff guarantee is **structural**: stage A renders the user's MIDI deterministically and
it is summed into the final mix untouched. B/C/D only add layers under/around it — nothing can
alter its pitches or timing.

```
Browser (Kid Sequencer)
  └─ NEW: export riff MIDI from notesByRow + key + tempo  (+ controls: instrument, drumStyle, tempo, key)
  └─ call generateAiTrack({ riffMidiB64, meta })   ← replaces WAV-seed upload at index.html:1229-1249

Firebase  generateAiTrack (europe-west1)        ← keep as orchestrator
  1. auth + quota (existing)
  2. POST Modal /jobs  → returns {jobId}; write jobs/{jobId}={status:queued} to Firestore
  3. return {jobId} immediately (ASYNC — callable 280s timeout can't hold a multi-min render)
  4. Modal webhook → small HTTPS fn copies MP3/stems to users/{uid}/tracks, sets job doc done|failed
  5. client listens to jobs/{jobId} via Firestore realtime; refund-on-failure stays

Modal app "kidseq-engine"
  A. render_riff (CPU)  riff MIDI → EXACT riff stem WAV     [sfizz/FluidSynth + CC0/CC-BY samples]
  B. arrange     (CPU)  riff+key → chords/bass/pads/drums + song structure  [music21 + rules + one-shots]
  C. texture     (GPU)  short in-key pads/risers/impacts    [Stable Audio Open 1.x]  (parallel w/ A+B)
  D. mix_master  (CPU)  stems → genre preset + sidechain + master → MP3 (+stems)  [pedalboard/Matchering/ffmpeg]
```

**Engine code home:** `kid-sequencer-repo/engine/` (Python + Modal), with subfolders
`render/ arrange/ texture/ mixmaster/` and `infra/` (Modal app defs). One repo, one deploy story.

---

## Tooling (concrete picks)

**A. Riff render — "pro" is the sample set, not the synth.**
- **sfizz-render** (BSD, https://github.com/sfztools/sfizz-render) for SFZ (velocity layers,
  round-robins) — the marquee instruments. **FluidSynth** (LGPL, run as CLI subprocess) for SF2.
- Samples (commercial-clear): **VSCO 2 Community Edition** (CC0 — strings/brass/bells)
  https://vis.versilstudios.com/vsco-community.html ; **Salamander Grand** (CC-BY) piano;
  **FluidR3_GM** (MIT) GM fallback. Render 48k/24-bit, dry (space added in D), trim to exact bar.
- For kids-EDM, the riff is usually best rendered as synth-pluck/piano/bells; reserve VSCO
  strings/brass for when the child literally picked that instrument.

**B. Arrangement — rule-based with `music21` (BSD), `pretty_midi` (MIT). Not a learned model for v1.**
- Key is already known (app sends it). Per section, pick from a **curated diatonic progression
  bank** (major: I–V–vi–IV, vi–IV–I–V…; minor: i–VI–III–VII…) scored by riff chord-tone coverage
  → in-key by construction, can't clash with the riff.
- Bass locked to progression + genre feel (+ numpy sine sub for EDM weight). Pads = `music21`
  voicings. Structure = `intro→build→drop→breakdown→build→drop→outro`, bar counts sized to ~2:30.
- Develop the 1-bar riff across sections with deterministic transforms (octave/scale transpose,
  thinning, double-time fills, filter automation, call-response) — but the **drops keep the
  verbatim riff** as the anchor.
- Drums: reuse the app's existing per-genre 16-step `DRUM_PATTERNS` (`index.html:650-709`),
  rendered by placing one-shot WAVs (numpy sum). Kits: **Unison Free EDM Kit** (cleared) /
  **Splice** (royalty-free, cleanest for a paid app).
- Roadmap (not v1): **AccoMontage-3** as an optional "richer accompaniment" mode once our transform
  layer has expanded the 1 bar into a multi-bar lead sheet to feed it.

**C. Texture (GPU) — ear-candy only, never melody.**
- **Stable Audio Open 1.0/1.5** (Stability Community License, free under $1M revenue — the
  sanctioned commercial path) https://huggingface.co/stabilityai/stable-audio-open-1.0 . Strong at
  risers/sweeps/impacts/atmospheres (≤47s clips). Fits A10G/L4; ~$0.01–0.03/track.
- **Prefer non-pitched textures** (key-agnostic). For pitched pads, keep them quiet + blurred
  (band-limit + reverb + low mix) and let `music21` pads carry the harmony. Deterministic seed.
- Avoid CC-BY-NC MusicGen for commercial; treat Stable Audio 3.0 as opt-in pending license check.

**D. Mix/master (CPU).**
- **pedalboard** (Spotify, MIT) for per-layer + bus EQ/comp/reverb/limiter; **pyloudnorm** (MIT)
  LUFS; **Matchering** (GPL — run as isolated process) reference-match per genre; **ffmpeg** MP3 320k.
- Chain: per-layer EQ/comp (riff gets *only* gentle EQ + space, never pitch/time edits) →
  **sidechain duck bass/pads/texture to kick** (the EDM "pump") → genre mix preset → bus glue comp
  → Matchering → limiter → loudness ~-9 to -11 LUFS, -1 dBTP. **Output: final mixed MP3 only.**
- **No stems** (project rule, see engine/PROJECT_RULES.md): we compose from internal layers and
  export only the final mix → **Demucs is not used** (it separates a finished mix — unnecessary
  when we already hold the parts).
- **Melodic sounds use a synth engine** (Vital/Surge via pedalboard VST hosting) for EDM
  lead/bass/pads (movement = "produced"); sampled libraries for acoustic (piano). **Drums = real
  one-shot samples** (synthesis rejected — pro 808s are processed samples). All sample packs MUST
  be **licensed for AI/automated use** (project rule).

**E. Infra — async job, Modal + Firebase.**
- Modal FastAPI `POST /jobs` spawns the orchestrator, returns `{jobId}` (pattern:
  https://modal.com/docs/guide/webhook-timeouts). Orchestrator fans out A/B/C (GPU parallel to
  CPU) → joins at D. Write output straight to the **same GCS bucket** via a service-account key in
  a Modal Secret (avoids a second hop). On done, Modal calls a small Firebase HTTPS webhook →
  writes `jobs/{jobId}` → client gets it via Firestore realtime listener.
- ~60–120s wall-clock/track; all-in compute ~$0.03–0.08/track (CPU-dominant) — trivial vs £4.99.

---

## Key integration points in the existing app

- **MIDI export (new, client):** convert `notesByRow` + `currentKey` + `tempo` → standard MIDI.
  Use the existing pitch model — `SCALES`/`pitchFor` (`index.html:506-534`): row 7 = root (C4/MIDI
  60), row 0 = octave up (MIDI 72), `_MAJOR_STEPS`/`_MINOR_STEPS` step tables; apply the
  `playInstrument` octave shifts (bass ×0.25 = −24, bells ×4 = +24, `index.html:3376-3385`).
  step→ticks from tempo, `len`→note duration. The user will add this to the sequencer.
- **Client trigger (modify):** `index.html:1229-1249` — replace `captureSequenceToWav()` + WAV
  upload with the MIDI export + `generateAiTrack({ riffMidiB64, meta })`; switch the result handling
  to a Firestore `jobs/{jobId}` listener. `_seedProduce` (`:529`) and `captureSequenceToWav`
  (`:3689`) become dead and can be removed.
- **`generateAiTrack` (rewrite body):** `functions/index.js:182` — keep auth/quota/refund/save/return
  shape; replace the Stability block (`:234-284`) with the Modal `/jobs` call + Firestore job doc.
  Remove `STABILITY_*`/`buildPrompt`/`AI_STRENGTH` (`:48-86`), drop the `STABILITY_API_KEY` secret.
- **New Firebase fn:** the Modal completion webhook (HTTPS) that finalizes the job doc + copies the
  MP3/stems into `users/{uid}/tracks/`.

---

## Build order (steps 1–4 = a convincing track with ZERO AI/GPU)

1. **Riff stem render** — sfizz/FluidSynth + Salamander/VSCO; prove the exact riff sounds real. (½d)
2. **Drums** — render one existing pattern (techno) with the Unison kit under the riff at tempo;
   now it "sounds like a track." (½d)
3. **`music21` progression + bass + pads** — one structure, one genre. (1d)
4. **Mix/master** — pedalboard + sidechain + loudness → MP3. **First convincing track, no GPU.** (1d)
5. **Texture layer** — Stable Audio Open on Modal: a riser into the drop + one impact. (1d)
6. **Wire async** — MIDI export client-side, `generateAiTrack` → Modal `/jobs`, Firestore job doc +
   listener, completion webhook, refund path. (1–2d)
7. **Breadth** — all 6 genres + 6 instruments; tune per-genre presets against reference tracks.

---

## Licensing
- Commercial-safe: sfizz/FluidSynth, VSCO 2 CE (CC0), Salamander (CC-BY, attribute), FluidR3_GM
  (MIT), music21/pretty_midi/pedalboard/pyloudnorm (permissive), Stable Audio Open (<$1M revenue),
  Unison/Splice samples (cleared/royalty-free).
- Run **Matchering** (GPL) as a separate process. Confirm **Stable Audio 3.0** terms before using.
- Keep `LICENSES.md` (moved into `kid-sequencer-repo/engine/`) as source of truth.

## Verification
1. **Riff-fidelity gate (the whole point):** export a known riff → run engine → the riff stem is a
   bit-exact render of the MIDI, and it's clearly audible/recognisable in the final mix. A/B the
   isolated riff stem vs the in-mix riff — pitches/timing identical.
2. **Sound quality:** A/B the master against a reference commercial kids-EDM track; check LUFS
   (~-9 to -11) and true-peak (≤-1 dBTP) with pyloudnorm.
3. **End-to-end:** in the app, sequence → Make AI track → Firestore job flips queued→done → MP3
   plays + downloads; quota decrements; failure path refunds.
4. **Per-genre/instrument:** smoke-test all 6 drum styles and 6 instruments for clashes/off-key
   textures.
5. **Cost/latency:** confirm ~60–120s/track and ~$0.03–0.08 compute on Modal.

## Top risks
1. **"Pro sound" rests on samples + mix presets, not architecture.** Invest first effort in VSCO
   CE + Splice kit curation + tuned per-genre pedalboard presets; A/B against a reference.
2. **Musicality from 1 bar** — curated progression bank + section variation + fills/risers; keep
   sections short/energetic (kids-EDM forgives repetition); iterate by ear.
3. **Texture clash / license drift** — prefer non-pitched textures, keep pitched ones quiet+blurred,
   pin to Stable Audio Open 1.x.
