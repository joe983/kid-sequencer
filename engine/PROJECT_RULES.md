# Engine — project rules

These are project constraints, not preferences. Any future work on the track engine
must honour them.

## 1. Sample licensing is the owner's call (revised 2026-07-02)
The owner decides which sample packs and libraries are used, including in local
builds and development — that choice is not a build gate and is not relitigated
per task. `LICENSES.md` remains the factual record of each pack's known license
terms so the information is in one place whenever a shipping or distribution
decision is being made; keep it updated when new packs are added, but it is a
record, not a blocker.

Two standing mechanics that fall out of this (engineering, not policy):
- Sample audio binaries are never committed to git and never uploaded by hosting
  deploys (`public/samples/` is gitignored and in `firebase.json` hosting ignore).
  Local installs are scripted (`install_app_kits.py` / `fetch_drumkits.py`) so any
  machine can rebuild the folders from the recorded sources.
- The app must always work without the sample folders present — every sample
  voice falls back to its synthesized counterpart.

*(Superseded rev: rule 1 previously required explicit AI/automated-use licensing
before any pack could be touched. Removed at the owner's direction, 2026-07-02.)*

## 2. No stems
The engine **does not produce or distribute stems.** Output is a finished, mixed-down
track (MP3) only. (This also removes the sample-redistribution concern, and means we do
**not** need Demucs — we compose from internal layers and only ever export the final mix.)

## 3. Riff fidelity
The user's riff is rendered from exact MIDI and mixed in unaltered. Generative/AI steps
never touch the riff's pitches or timing — only add texture/production around it.
