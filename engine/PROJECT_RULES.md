# Engine — hard rules (non-negotiable)

These are project constraints, not preferences. Any future work on the track engine
must honour them.

## 1. Samples must be licensed for AI / automated-generation use
Every sample pack, soundfont, or sound library baked into this engine **must have a
license that explicitly permits use in an automated / AI music-generation product**
(not just "royalty-free for your own music productions"). Before adding any paid or
free pack:
- Read its EULA for AI / automated-generation / software-product clauses.
- Prefer packs offering a **developer / multimedia / broadcast license** that names
  product/app use, or **CC0** (no restriction).
- Record the pack + its exact license + the AI-use permission in `LICENSES.md`.
- If a pack's license is silent or ambiguous on AI/automated use, **do not use it.**

## 2. No stems
The engine **does not produce or distribute stems.** Output is a finished, mixed-down
track (MP3) only. (This also removes the sample-redistribution concern, and means we do
**not** need Demucs — we compose from internal layers and only ever export the final mix.)

## 3. Riff fidelity
The user's riff is rendered from exact MIDI and mixed in unaltered. Generative/AI steps
never touch the riff's pitches or timing — only add texture/production around it.
