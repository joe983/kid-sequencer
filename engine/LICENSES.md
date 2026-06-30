# Engine asset & dependency licensing

> **Hard rules: see [PROJECT_RULES.md](PROJECT_RULES.md).** Every sample/soundfont MUST be
> licensed for **AI / automated-generation** use (not just "royalty-free for your own
> music"). No stems are produced or distributed.

Source of truth for what's safe to ship in the (paid) Kid Sequencer app. Soundfonts
are downloaded by `scripts/fetch_soundfonts.py`, not committed. For each pack, record its
exact license **and** its AI/automated-use permission below.

## Sample libraries (rendered audio + bundled files)

| Instrument | Library | License | Commercial / bundling |
|---|---|---|---|
| piano | Salamander Grand Piano V3 | **CC-BY 3.0** | ✅ commercial OK; attribute S. Christian Collins / Alexander Holm |
| synth | FreePats **SynthSquare** | **CC0 1.0** | ✅ public domain, no restriction |
| bass | FreePats **Lately Bass** | **CC0 1.0** | ✅ public domain, no restriction |
| trumpet, strings, bells | GeneralUser GS v1.471 | **GeneralUser GS License v2.0** | ✅ explicitly allows commercial use + use in software projects |
| drums | GeneralUser GS (GM kit) | GeneralUser GS License v2.0 | ✅ (placeholder — Splice kits planned) |

Attribution required: **Salamander (CC-BY)** — credit in app credits/about.
GeneralUser license asks you to **host your own copy** (don't hot-link the author's
server) — satisfied by our downloaded copy.

### Not used (and why)
- **VSCO 2 CE / Sonatina** — SFZ-only (needs `sfizz`, not our SF2 renderer) and/or
  CC Sampling Plus (restrictive). Reserved for the Modal/sfizz production build as the
  premium upgrade path for trumpet/strings/bells.
- **FreePats GM set** — GPL-v3-with-exception; the exception covers *output*, but
  bundling the GPL .sf2 file in a closed app is a gray area. Avoided.

## Python deps
tinysoundfont (MIT), numpy (BSD), mido (MIT), py7zr (LGPL — used as a tool, not linked).
Later: pedalboard (MIT), pyloudnorm (MIT), Matchering (GPL — run as a separate process).

## Renderer caveat
tinysoundfont does not fully implement SF2 modulators. We therefore keep modulator-heavy
GM synth/bass presets OFF (using the CC0 FreePats banks instead); the GM presets we do use
(trumpet/strings/bells) are straightforward sample zones that render correctly.
