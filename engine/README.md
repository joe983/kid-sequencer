# Kid Sequencer — riff-anchored track engine

Turns a Kid Sequencer riff into a full produced instrumental, with the user's hook
**preserved exactly**. Replaces the old Stable-Audio-2.5 audio-to-audio call (which
lost the riff). See `../docs/` / the project plan for the full design.

## Why the riff is always preserved
The riff is **rendered deterministically from MIDI**, never inferred by a model.
Stages B/C/D only add layers *under and around* it, so they cannot change its
pitches or timing. (`sequence.py` is the exact pitch/timing model, mirrored from
`public/index.html`.)

## Pipeline (build order)
| Stage | Module | Status |
|---|---|---|
| Sequence → exact MIDI notes | `kidseq_engine/sequence.py` | ✅ done + tested |
| A. Render riff stem | `kidseq_engine/render/sf_render.py` | ✅ real samples (GeneralUser GS); numpy synth fallback |
| Drums from app patterns | `kidseq_engine/render/sf_render.py` | ✅ real GM drum kit; numpy fallback |
| B. Arrangement (chords/bass/pads/structure) | `kidseq_engine/arrange/` | ⬜ step 3 |
| D. Mix + master | `kidseq_engine/mixmaster/` | ✅ pedalboard chain: per-layer EQ/comp/space + sidechain pump + glue + loudness master (LUFS target) + MP3 |
| C. Generative texture (Modal GPU) | `kidseq_engine/texture/` | ⬜ step 5 |
| Async wiring (Firebase + Modal) | `infra/` | ⬜ step 6 |

## Setup
```bash
cd engine
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.txt
./.venv/Scripts/python scripts/fetch_soundfonts.py   # downloads sample libs (not committed)
```

## Run
```bash
./.venv/Scripts/python tests/test_sequence.py   # riff-fidelity contract
./.venv/Scripts/python tests/test_master.py     # mix/master numeric gates (loudness, true-peak, pump)
./.venv/Scripts/python smoke_step1.py           # → out/{riff_stem,drums,mix}.wav + riff.mid (raw layers)
./.venv/Scripts/python smoke_track.py           # → out/track_master.wav + track.mp3 (mixed + mastered)
```
`smoke_track.py` prints integrated loudness (target ~-10 LUFS) and true peak (≤-1 dBTP);
A/B `out/track.mp3` against a reference commercial kids-EDM track by ear.

## Sounds — current state & upgrade path
Rendering uses real sample libraries via `tinysoundfont` (SF2), with a per-instrument
registry in `render/sf_render.py` (`INSTRUMENT_SF`) so each instrument upgrades
independently. `render/synth.py` + `render/drums.py` remain as a numpy fallback if no
soundfont is present.

| Instrument | Library now | License |
|---|---|---|
| piano | **Salamander Grand V3** (real Yamaha C5, multi-velocity) | CC-BY 3.0 |
| synth | **FreePats SynthSquare** (matches the app's square lead) | CC0 |
| bass | **FreePats Lately Bass** (punchy FM EDM bass) | CC0 |
| trumpet / strings / bells | GeneralUser GS (GM) — see note | GeneralUser v2.0 (commercial OK) |
| drums | GeneralUser GS GM kit — **placeholder; → Splice kits later** | GeneralUser v2.0 |

**trumpet/strings/bells are still GM**: no clean commercially-licensed *SF2* exists for
them. The premium path is **VSCO 2 CE via the `sfizz` engine on the Modal/Linux build**
(VSCO is SFZ-only; sfizz installs cleanly on Linux, awkwardly on Windows). Local preview
stays on SF2 for zero native deps. See `LICENSES.md` for the full rationale.
