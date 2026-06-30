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

## Next step — YOUR ears on the 6 genre tracks
1. **Audition `out/genre_<style>.mp3`** (6 of them). For each genre tell me: drums punchy enough?
   right flavour (e.g. is drill's 808 sub doing the job, is funk's kit too lofi)? Then I tune the
   per-voice `_GAIN`/layer mapping in `sample_kit.py` and, if a flavour is wrong, repoint that
   genre's kit. **Per-voice LAYERING** (stack sub+click under a kick for punch) is the main quality
   lever now that the infra supports it — say the word and I'll layer the weak voices.
2. **THEN** the original A/B mix-tune step finally makes sense (real drums feeding the mix): tune
   `master.py:GENRE_PRESETS` against a reference kids-EDM track.

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
