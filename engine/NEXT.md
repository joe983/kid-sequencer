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
