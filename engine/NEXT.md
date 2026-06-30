# Where we are / next session

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

## Next build step (user pick was "tune the current sounds first")
Pedalboard half of that pick is **done** (above). Remaining sound-tuning, both needing YOUR ears:
1. **A/B `out/track.mp3` against a reference** kids-EDM track — tell me what's missing (too dry?
   pump too deep/shallow? drums weak? riff buried?) so I can tune the presets in `master.py`.
2. **Real AI-licensed drum kit** — current drums are the GM placeholder. Hard rule #1: a kit must be
   licensed for AI/automated use (CC0 ideal) and recorded in LICENSES.md *before* use. Pick a source
   (or I propose CC0 candidates) → I'll add a one-shot-sample drum renderer.
The soft synth is parked to the Modal build (see Parked).

## Remaining build order (docs/PLAN.md)
- Step 3: music21 arrangement (progression bank + bass + pads + structure) — the mixmaster already
  takes `bass`/`pads`/`texture` layers + per-genre gains, so arrangement plugs straight in. (task #9)
- Step 5: generative texture (Stable Audio Open on Modal)  (task #10)
- Step 6: wire async engine into Firebase generateAiTrack + Firestore jobs  (task #11)
- Step 7: breadth (6 genres/instruments) + sfizz/VSCO upgrade for the 3 GM ones  (task #12)
