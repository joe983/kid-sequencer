# Research Report: Front-end + Signal-Processing Pipeline for "Hum/Play -> Musical Seed -> AI Generation"

Scope: how a web app captures a short musical idea (hummed/sung/played melody or chord
progression) and turns it into a structured seed (MIDI / note sequence / chord symbols /
tempo / key) to condition an AI music-generation backend. Recommendation is a **hybrid
in-browser + server** pipeline.

---

## 0. Recommended pipeline (executive summary)

```
[Browser]                                          [Server]
getUserMedia -> AudioWorklet capture (Float32 PCM @48k)
   |-> (optional) live pitch monitor: Pitchy/pitchfinder for UI feedback
   |-> encode/keep raw PCM -> upload WAV/WebM
                                                   -> resample 22.05k
   monophonic hum/sing  ----------------------->   CREPE (or Basic Pitch) -> F0
   polyphonic / chords  ----------------------->   Basic Pitch -> note events + pitch bend
                                                   madmom / Chordino -> chord labels
                                                   Essentia / librosa -> tempo + key
                                                   QBH quantizer -> note segmentation + grid snap
                                                   -> assemble SEED (MIDI + chord symbols + tempo/key JSON)
                                                   -> condition generator (REMI / chroma / audio ref)
[Browser] <- seed preview (VexFlow notation + Tone.js playback) <-
```

Why hybrid: in-browser ML (TF.js/WASM) is good enough for **live UI feedback and simple
monophonic capture**, but the highest-accuracy transcription (especially polyphonic and
chords) and the heavier models (CREPE-full, madmom, Essentia extractors, MT3) are more
reliable, version-stable, and CPU-cheap to run server-side. Run a cheap in-browser
detector for instant feedback; run the authoritative transcription server-side.

---

## 1. Browser audio capture (Web Audio API / MediaRecorder / getUserMedia)

Key facts and best practices:

- Three-stage model: **capture** with `getUserMedia()`, optionally **process** with Web
  Audio nodes, then **encode** with `MediaRecorder`. Web Audio is only needed when you
  must analyze/transform before recording (visualization, custom DSP via AudioWorklet).
- `getUserMedia()` requires a **secure context (HTTPS or localhost)** and explicit mic
  permission.
- Always probe `MediaRecorder.isTypeSupported()` before recording. **WebM/Opus** is the
  best default on Chrome/Firefox; **Safari prefers `audio/mp4`**. Use a fallback list.
- Stop tracks when done: `stream.getTracks().forEach(t => t.stop())` or the mic indicator
  stays on.

Recommendations specific to this app:

- For **analysis-quality** capture (transcription downstream), do **not** rely on Opus
  round-trips. Capture raw **Float32 PCM via an `AudioWorklet`** (`AudioWorkletProcessor`)
  and assemble a WAV (or send PCM frames). Opus is lossy and adds latency; for pitch/onset
  accuracy you want the cleanest signal. Keep MediaRecorder/Opus only if you also want a
  small uploadable artifact for archival.
- Request constraints deliberately. For **singing/humming**, disabling browser voice
  processing usually improves transcription: `getUserMedia({ audio: { echoCancellation:
  false, noiseSuppression: false, autoGainControl: false } })`. Those features are tuned
  for speech telephony and distort musical pitch/dynamics. (Verify per-browser; some
  ignore the constraints.)
- AudioWorklet runs on the audio render thread -> low-latency, glitch-free; ScriptProcessor
  is deprecated. Use AudioWorklet for both capture and any live pitch meter.
- Sample rate: capture at the device native rate (often 48 kHz); resample to the model's
  expected rate (Basic Pitch -> 22.05 kHz; CREPE -> 16 kHz) at the analysis stage.

Sources:
- https://developer.mozilla.org/en-US/docs/Web/API/MediaStream_Recording_API/Using_the_MediaStream_Recording_API
- https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder
- https://web.dev/media-recording-audio/
- https://developer.chrome.com/blog/mediarecorder
- https://blog.openreplay.com/record-audio-browser-web-audio-api/
- https://medium.com/@tihomir.manushev/how-browsers-handle-audio-streams-mediarecorder-vs-web-audio-api-72553933a3a2

---

## 2. Melody transcription / pitch detection

### Monophonic (hum / sing / single-line play)

| Method | Type | Runs in browser? | Notes |
|---|---|---|---|
| **CREPE** | CNN on raw waveform | Not officially; Python/TF only. TF.js requires self-conversion of the model | State of the art monophonic F0; "outperforms pYIN and SWIPE." Model sizes tiny->full trade speed vs accuracy. Best run **server-side**. |
| **pYIN** | DSP + probabilistic (HMM) voicing | No JS port (lives in librosa / Vamp/Sonic Annotator) | ~91% raw pitch accuracy on iKala vs CREPE ~90.5% - comparable. Strong, deterministic, no GPU. Good **server** default. |
| **SPICE** | Self-supervised CNN (Google) | Yes - published as a **TF.js / TF Hub** model | Matches CREPE accuracy with no labeled training; relative-pitch model. Viable **in-browser** option. |
| **Pitchy** | Autocorrelation/McLeod (MPM) | Yes, pure JS, tiny | Great for **real-time UI pitch meter**; not a full transcriber. |
| **pitchfinder** | YIN, AMDF, dynamic wavelet, etc. | Yes, pure JS | YIN = best accuracy/speed balance in JS; fewer octave errors than raw autocorrelation. |
| **SwiftF0** | Newer fast CNN | (emerging) | Recent "fast and accurate monophonic" model worth tracking. |

YIN improves on autocorrelation via a difference function + cumulative mean normalization
+ parabolic interpolation -> higher accuracy at low pitches, fewer octave errors. WASM
pitch DSP runs ~8x faster than pure JS.

**Humming accuracy reality check:** humming is monophonic and pitch-trackable, but humans
hum off-pitch, with unstable onsets, scoops, and drift. Raw F0 is the easy part; the hard
part is **note segmentation + quantization** (section 5). All of CREPE/pYIN/SPICE produce a
continuous F0 contour, not notes. You still need onset detection + quantization to get a
clean melody.

### Polyphonic / audio-to-MIDI

| Method | Runs in browser? | Notes |
|---|---|---|
| **Spotify Basic Pitch** | **Yes** - `@spotify/basic-pitch` (TS, TF.js) runs fully in-browser; also Python `basic-pitch`. Model ~900 KB-1 MB, caches after first load; uses Web Audio for decode, resamples to 22.05 kHz; WebGPU/CPU backend | Instrument-agnostic, polyphonic, with **pitch-bend** detection; onset/offset detectors on top of CREPE-style pitch. "Works best on one instrument at a time." The standout choice for browser audio->MIDI. |
| **MT3** (Google) | No - large T5 seq2seq, **server/GPU** | Multi-task multitrack transcription, MIDI token output. Highest ceiling for multi-instrument, heavy. YourMT3/MR-MT3 are training/robustness variants. |
| **Omnizart** | No - Python toolkit, **server** | Piano/ensemble/percussion/vocal + chord + beat models via CLI. Good when you need many content types. |

**Choice:** Use **Basic Pitch** as the primary transcriber for both the polyphonic/played
case and as a solid monophonic fallback - it's the only production-grade audio->MIDI that
runs in-browser *and* server-side from the same model family, which simplifies the
architecture. Reserve MT3/Omnizart for a future "high quality, server-only" mode.

Sources:
- https://github.com/spotify/basic-pitch and https://github.com/spotify/basic-pitch-ts
- https://basicpitch.spotify.com/about , https://engineering.atspotify.com/2022/6/meet-basic-pitch
- https://arxiv.org/abs/1802.06182 (CREPE), https://github.com/marl/crepe
- https://research.google/blog/spice-self-supervised-pitch-estimation/ , https://arxiv.org/pdf/1910.11664 (SPICE)
- https://github.com/ianprime0509/pitchy , https://www.npmjs.com/package/pitchy
- https://github.com/peterkhayes/pitchfinder
- https://arxiv.org/pdf/2508.18440 (SwiftF0)
- https://arxiv.org/abs/2111.03017 (MT3), https://arxiv.org/abs/2106.00497 (Omnizart)
- https://www.musicalboard.com/blog/2026-05-05-pitch-detection/ (WASM speedups)

---

## 3. Chord recognition / chord progression from audio

| Tool | Stack | Output | Notes |
|---|---|---|---|
| **Chordino** (NNLS-Chroma Vamp plugin) | C++ Vamp; wrap with `chord-extractor` (Python) | Time-stamped chord labels | Classic, robust, widely used baseline. |
| **chord-extractor** | Python, wraps Chordino, extensible | Chord sequence from many file formats | Easiest Python entry point; designed to add other methods. |
| **autochord** | Python; NNLS-Chroma -> Bi-LSTM-CRF (TF) | 25 classes (12 maj, 12 min, N) | ISMIR 2021; major/minor triads only - limited vocabulary. |
| **madmom** | Python; deep chroma -> CRF (`DeepChromaChordRecognitionProcessor`) | Major/minor chords | Strong DL chroma; also gives beats/downbeats/onsets - useful for tempo too. |

All are **Python/C++ -> server-side**. No production browser chord recognizer; Essentia.js
exposes chroma/HPCP and an extractor but full chord decoding is best done server-side.

**Recommendation:** server-side **madmom** (or Chordino via chord-extractor) for chord
labels. Note the common limitation: most off-the-shelf recognizers only emit maj/min
triads (no 7ths/extensions/inversions). If you need richer harmony, plan to post-process
chroma or accept triad-level seeds.

Sources:
- https://github.com/ohollo/chord-extractor , https://pypi.org/project/chord-extractor/
- https://github.com/cjbayron/autochord , https://archives.ismir.net/ismir2021/latebreaking/000008.pdf
- https://madmom.readthedocs.io/en/v0.16/modules/features/chords.html , https://github.com/CPJKU/madmom
- https://arxiv.org/pdf/1612.05065 (Deep Chroma Extractor)

---

## 4. Tempo & key detection

- **librosa** (Python): `beat_track`/`tempo`, key via chroma + Krumhansl-Schmuckler. Server.
- **Essentia** (C++): production MIR algorithms - `RhythmExtractor2013`, `KeyExtractor`,
  `PercivalBpmEstimator`, predominant melody, etc. Server or via bindings.
- **Essentia.js** (WASM): the **browser** path. Same Essentia algorithms compiled via
  Emscripten with a JS/TS API and the `essentia.js-extractor` add-on computing **BPM, beat
  positions, key, chords, chroma, MFCC, pitch, melody**. Integrates directly with Web
  Audio. Real-world demo: BPMKeyFinder runs tempo+key entirely in-browser on Essentia.js.

**Recommendation:** For a short clip, run **Essentia.js in-browser** for instant tempo/key
estimates to show the user immediately; **re-confirm server-side** with Essentia/librosa on
the uploaded audio for the authoritative seed value (browsers vary in throughput and you
want determinism). Tempo from a free hum is unreliable - prefer a **metronome/count-in or
a tap-tempo control** in the UI rather than trusting onset-based BPM from humming.

Sources:
- https://mtg.github.io/essentia.js/ , https://github.com/mtg/essentia.js/
- https://program.ismir2020.net/static/final_papers/260.pdf , https://transactions.ismir.net/articles/10.5334/tismir.111
- https://essentia.upf.edu/ , https://essentia.upf.edu/demos.html
- https://aistage.net/tool/bpmkeyfinder

---

## 5. Humming-to-melody specifically (query-by-humming style cleanup)

This is the crux: turning a rough, off-pitch hum into a usable melody. QBH research gives
the recipe:

1. **F0 extraction** -> continuous pitch contour (CREPE/pYIN/SPICE), convert Hz -> semitones.
2. **Note onset/segmentation** -> cut the contour into discrete notes using amplitude
   envelope and/or high-frequency content (spectral flux) onset detection.
3. **Pitch quantization** -> snap each note's median/robust pitch to the nearest semitone;
   optionally a **pitch fine-tuning** pass to remove quantization error / drift.
4. **Key-aware correction** -> detect key (section 4), then snap to the nearest **in-scale**
   degree to fix wrong notes the singer produced (configurable strength so you don't
   destroy intended chromaticism).
5. **Rhythm quantization** -> snap onsets/durations to a tempo grid (needs tempo from a
   count-in or tap-tempo; grid resolution e.g. 1/8 or 1/16).
6. Emit MIDI / note sequence.

Practical notes: pitch drift in unaccompanied singing is well documented; allow per-note
robust statistics (median over the stable middle of the note, ignore onset scoops). Expose
correction strength to the user (raw -> semitone-snap -> scale-snap -> rhythm-snap) so they
can dial how much the system "fixes." This whole stage is custom code on top of an F0
tracker - there isn't a turnkey JS library; implement it server-side alongside CREPE/Basic
Pitch output, or on top of Basic Pitch's note events (which already do onset/offset).

Sources:
- https://www.researchgate.net/publication/280237859 (pitch quantization & note segmentation in audio QBH)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC3943253/ (QBH melody matching pipeline)
- https://arxiv.org/pdf/2204.01009 (pitch drift in solo singing)
- https://grokipedia.com/page/query_by_humming

---

## 6. Useful JS/TS music libraries

- **Tone.js** - Web Audio framework: scheduling, synths, transport/tempo grid, playback of
  the seed for preview. Core of the front-end audio engine.
- **@tonejs/midi** - parse/serialize MIDI <-> JS-friendly JSON. Use to build the seed MIDI
  in the browser and to read MIDI returned by the generator.
- **Magenta.js** (`@magenta/music`) - TF.js music models (MelodyRNN, MusicVAE, etc.),
  `NoteSequence` data type, quantization helpers. Useful both for optional in-browser
  generation/continuation and for its symbolic representation utilities.
- **VexFlow** - render the extracted melody/chords as notation (SVG/Canvas) so the user can
  see and confirm the seed.
- **Pitchy / pitchfinder** - lightweight live pitch detection for UI feedback (section 2).
- **Essentia.js** - in-browser tempo/key/chroma (section 4).

Reference combo seen in the wild (Noteflow): VexFlow for notation + Tone.js for MIDI
playback + Magenta.js MelodyRNN for generation.

Sources:
- https://tonejs.github.io/Midi/ , https://github.com/Tonejs/Midi
- https://magenta.github.io/magenta-js/music/ , https://github.com/topics/magenta-js
- https://www.vexflow.com/ , https://github.com/vexflow/vexflow
- https://devpost.com/software/noteflow

---

## 7. Representing the seed to condition a generative model

Three conditioning modalities; pick per backend, and ideally store all three in the seed:

1. **Symbolic MIDI / token sequence (melody).**
   - **REMI** (Revamped MIDI): beat-based; each note = (position, pitch, velocity,
     duration) tokens, plus **bar / tempo / chord events**. The de-facto representation for
     transformer music models -> best fit if you control/finetune the generator.
   - Simpler triplet form per note: (pitch_name, duration, rest). Magenta `NoteSequence` is
     a clean interchange object.
   - This is the strongest, most controllable seed from a hum/played line.

2. **Symbolic chords (harmony).**
   - **Multi-hot chroma vectors** per time frame (12 pitch classes, multiple active) -
     exactly what **MusicGen-Chord** and **MusiConGen** consume for chord control. Or pass
     chord **symbols** (e.g. "Am F C G") if the backend accepts text/symbolic harmony.
   - Best fit when the input was a chord progression rather than a melody.

3. **Audio reference (melody/style).**
   - Some text-to-music models (MusicGen melody variants, MusiConGen) accept a **reference
     audio** clip and extract chroma/discrete bottleneck features internally. Cheapest path
     (skip transcription) but least precise/controllable.

**Recommendation:** Produce a structured seed JSON carrying: `midi` (note events, base64
or @tonejs/midi JSON), `chords` (symbol list + per-beat chroma), `tempo` (BPM), `key`,
plus the original `audioRef`. Feed MIDI/REMI + chord chroma when the backend is symbolic or
controllable; fall back to the audio reference for off-the-shelf text-to-music models. This
multi-representation seed keeps you backend-agnostic.

Sources:
- https://arxiv.org/html/2412.00325v1 (MusicGen-Chord, multi-hot chroma)
- https://arxiv.org/pdf/2407.15060 (MusiConGen, audio or symbolic chord/rhythm control)
- https://arxiv.org/pdf/2201.10936 (FIGARO controllable generation)
- https://arxiv.org/html/2407.12563v1 (audio conditioning via discrete bottleneck)
- https://arxiv.org/html/2409.20196v4 (melody-guided generation)
- REMI: https://arxiv.org/pdf/2201.10936 and MusicGen-Chord paper above

---

## In-browser vs server: decision table

| Task | In-browser | Server | Recommendation |
|---|---|---|---|
| Mic capture | Yes (AudioWorklet/getUserMedia) | n/a | Browser, raw PCM |
| Live pitch meter (UI) | Pitchy/pitchfinder | - | Browser |
| Monophonic F0 (authoritative) | SPICE (TF.js) possible | CREPE/pYIN | Server (CREPE/pYIN); SPICE if you must stay client-side |
| Polyphonic audio->MIDI | Basic Pitch (TF.js) | Basic Pitch / MT3 | Browser Basic Pitch for quick result; server for best quality |
| Chord recognition | (weak) | madmom/Chordino | Server |
| Tempo/key | Essentia.js (quick) | Essentia/librosa | Browser preview + server confirm; prefer count-in/tap-tempo |
| Hum cleanup (segment/quantize) | custom JS possible | custom | Server (on F0/Basic Pitch output) |
| Notation preview | VexFlow | - | Browser |
| Playback preview | Tone.js + @tonejs/midi | - | Browser |
| Seed assembly | @tonejs/midi | preferred | Server (canonical), mirror in browser |

**Bottom line:** capture and give instant feedback in the browser (AudioWorklet + Pitchy +
Essentia.js + Basic Pitch-TF.js); upload raw audio; do authoritative transcription, chord
recognition, tempo/key, and hum quantization server-side (Basic Pitch + CREPE/pYIN +
madmom + Essentia); emit a multi-representation seed (REMI/MIDI + chord chroma + tempo/key
+ audio ref); preview with VexFlow + Tone.js before sending to the generator.
