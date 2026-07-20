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
| trumpet, strings, bells (Modal/Linux build) | **VSCO 2 CE** (sgossner/VSCO-2-CE) via sfizz | **CC0 1.0** | ✅ public domain; AI/automated use OK |
| trumpet, strings, bells (local fallback) | GeneralUser GS v1.471 | **GeneralUser GS License v2.0** | ✅ explicitly allows commercial use + use in software projects |
| drums (electronic: kick/sub/snare/clap/hats) | **Boochi44/free-drum-samples** | **CC0 1.0** | ✅ public domain, no restriction; AI/automated use OK |
| drums (aux perc: cowbell/shaker/woodblock/conga/bongo) | **VCSL** (sgossner/VCSL) | **CC0 1.0** | ✅ public domain, no restriction; AI/automated use OK |
| drums (acoustic breakbeat kit for DnB: kick/snare/rim/hats) | **Virtuosity Drums** (sfzinstruments/virtuosity_drums) | **CC0 1.0** | ✅ public domain; AI/automated use OK |
| drums (GM kit) | GeneralUser GS (GM kit) | GeneralUser GS License v2.0 | ✅ fallback only (used when sample kits not fetched) |

Attribution required: **Salamander (CC-BY)** — credit in app credits/about.
GeneralUser license asks you to **host your own copy** (don't hot-link the author's
server) — satisfied by our downloaded copy.

**Drum sample kits (CC0, AI-use OK), verified 2026-06-30** — fetched by
`scripts/fetch_drumkits.py`, curated flat into `assets/drums/`:
- **Boochi44/free-drum-samples** (https://github.com/Boochi44/free-drum-samples) — repo
  states *"All samples in this repository are released under the Creative Commons Zero
  (CC0 1.0) license."* 3 flavours (hard-trap / bounce / soulful-vintage). Many one-shots
  derive from the CC0 **tidalcycles/sounds-tr808-fischer** TR-808 set (E. Loveall).
- **VCSL** (https://github.com/sgossner/VCSL) — Versilian Studios, **CC0 1.0** public-domain
  dedication. We take 5 aux-percussion one-shots (cowbell, large shaker, woodblock,
  open conga `Conga_HitN_v2_rr1_Sum.wav`, high bongo `BongoH_Hit1_v2_rr1_Mid.wav` —
  the last two added R31 for the techhouse producer-style latin/disco seasoning).
- **Virtuosity Drums** (https://github.com/sfzinstruments/virtuosity_drums) — **CC0-1.0**
  (repo LICENSE, verified 2026-07-02). Real acoustic kit performed by drummer Austin McMahon,
  recorded by Versilian Studios / Karoryfer Samples (KVRDC'21). We take 6 top-velocity
  one-shots (kick snares-off/on, snare centre, rimshot, closed/open hat) for the
  breakbeat-DNA genres. Original performance — no copyrighted break recordings involved.
- **Rejected: `yaxu/clean-breaks`** — repo has **no license** → fails hard rule #1 despite
  the "clean" name. Classic breaks themselves (Amen/Think/Apache) are uncleared copyrighted
  recordings — never use them or derivatives of them.

## Reference-only packs (user-owned, NOT engine assets)
- **Jay Cactus — The Vault 2.0** (Greeze UK Drill / Trap Lordz / Candy / The Source), local at
  `~/Documents/MyMusic/Samples/Drill Samples/`. Terms (jaycactus.com, checked 2026-07-02)
  **prohibit use in "App Contents (Mobile or otherwise)" / competitive products**, require
  sounds to be embedded in a mixed musical piece, and are not fully royalty-free (publishing
  clauses). → **NEVER wire into KITS / the engine.** Fine as the user's own beats and as the
  A/B tuning reference for what the licensed kits should sound like.
- **Deliberately NOT used:** the full `tidalcycles/Dirt-Samples` (mixed per-folder
  licensing — only dedicated CC0 `sounds-*` repos are safe) and Freesound per-file
  one-shots (the Feb-2026 Gen-AI uploader-preference flag is non-binding but adds
  ambiguity; the CC0 GitHub kits are cleaner for an AI-generation product).

## Owner-provided commercial packs (bundled at the owner's direction)
Per PROJECT_RULES.md rule 1 (revised): sample choice is the owner's call and
this file is a record, not a gate. The owner owns these commercial packs and
directed their curated one-shots be bundled into the committed engine packs.
- **engine_extras.pack** (R17, 2026-07-14) — the owner's DnB library: 4 alt
  snares + 1 hat + 4 breakbeat fills. `tools/install_engine_extras.py`.
- **producer_techhouse.pack** (R32, 2026-07-16) — per-producer techhouse
  drums / smp chops / fx one-shots curated from the owner's packs:
  **AA Vengeance Essential House Vol.1** (VEH1 kicks/claps/hats/bongo/rim/
  shaker/perc/tom/cutted-vocal-chops/reverse/slides), **Roland TR-909**
  (pianohouse hats/clap/kick), **[VB] Hyperfunk** (discofunk funk-stab),
  **musicradar carnival-rave** (latin vox-chant/perks/reverse),
  **musicradar-rave** (bigroom stabs/crowd/impact), **musicradar-dnb-fx**
  (bigroom riser), **Madeon Adventure Machine v2** (bigroom rave-shot),
  **GarageSessions Vol.3** (lofi foley top). Owner-provided; bundled as
  conditioned one-shots inside the committed pack (no full library shipped).
  Rebuild `tools/install_producer_kits.py`.
- **producer_garage.pack** (R33/R33b, 2026-07-16) — six UK Garage producer
  strains from the owner's packs: **GarageSessions Vol.3** (drum core + UKG fx),
  **LCHZ** garage/bassline one-shots, **Roland TR-909/TR-808**, **AA Vengeance
  Essential House Vol.1** (clap-snare + House Rimshots), **[VB] Hyperfunk**
  (keys stab), **Cymatics Orchid/Infinity** sung-vocal loops + **GS/LCHZ vox
  loops** (sliced into one-shot chops by `tools/extract_chops.py`).
  Owner-provided; conditioned one-shots only, no full library shipped.
  Rebuild `tools/install_producer_kits.py --genre garage`.

**VSCO 2 CE (CC0, AI-use OK), verified 2026-07-09** — the premium orchestral path,
live on the Modal/Linux build. Repo LICENSE = **CC0 1.0 Universal**
(https://github.com/sgossner/VSCO-2-CE, same author as VCSL). `scripts/fetch_vsco.py`
sparse-clones 3 folders (Trumpet susvib, Violin Section susVib, Glock) and GENERATES
our own .sfz mappings (no maintained SFZ port exists); rendered by `sfizz_render`
(BSD-2-Clause, built from source in the Modal image — we bundle nothing).

## Software instruments (server-side only, never distributed)
- **Surge XT 1.3.4** (https://surge-synthesizer.github.io) — **GPL-3.0**. Runs ONLY on the
  Modal/Linux build (installed from the official .deb into the container image), hosted
  headless via pedalboard; we ship **rendered audio output**, never the synthesizer
  binary, so GPL obligations don't attach to the app or the MP3s. Patches are our own
  param dicts in `render/vst_render.py` (Surge factory patches unused).
- **sfizz** (https://github.com/sfztools/sfizz) — **BSD-2-Clause**, built from source in
  the Modal image; same server-side-only posture.

### Not used (and why)
- **Sonatina** — CC Sampling Plus (restrictive). VSCO 2 CE covers the need as pure CC0.
- **FreePats GM set** — GPL-v3-with-exception; the exception covers *output*, but
  bundling the GPL .sf2 file in a closed app is a gray area. Avoided.

## Python deps
tinysoundfont (MIT), numpy (BSD), mido (MIT), py7zr (LGPL — used as a tool, not linked).
Later: pedalboard (MIT), pyloudnorm (MIT), Matchering (GPL — run as a separate process).

## Renderer caveat
tinysoundfont does not fully implement SF2 modulators. We therefore keep modulator-heavy
GM synth/bass presets OFF (using the CC0 FreePats banks instead); the GM presets we do use
(trumpet/strings/bells) are straightforward sample zones that render correctly.
