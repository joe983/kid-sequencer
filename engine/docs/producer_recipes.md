# Producer SOUND recipes — techhouse R32

The **sound-source** layer under the R31 `producer_style` axis. R31 varied
per-press *decisions*; every producer still shared one drum kit, one Surge
synth family and identically-synthesized FX, so the owner heard "they all
sound the same." R32 puts REAL distinct sources into each producer.

**Standing lesson (why this file exists): decision logs are NOT sound.**
Producer variety is proven with audio-level evidence (spectral distinctness +
ears), never a `producer=` log line.

This doc is the bridge from the R31 sonic signatures
(`producer_signatures.md`, the arrangement level) to the actual files on the
owner's disk (the source level). Each producer has five subsections:

| section | R32 increment that consumes it |
|---|---|
| **DRUMS** | R32b — `sample_kit.KITS["techhouse:<producer>"]` in `producer_techhouse.pack` |
| **SAMPLER** | R32c — `smp_render.py` repitch one-shots (vocal chops / stabs / chants) |
| **SYNTH+POST** | R32d — Surge patch v2 + `VOICE_POST` pedalboard chain |
| **FX** | R32e — `fx_samples.py` sampled one-shots (riser / impact / swell) |
| **MIX** | R32f — ≤2 dB per-producer seasoning on the genre mix tables |

## Sources (owner-provided commercial packs, on the owner's disk)

All under `C:\Users\Joe_C\Documents\MyMusic\Samples`. Committed into
`engine/packs/producer_techhouse.pack` at R32b; `LICENSES.md` records
owner-provided + date (R32h).

- **VEH1** = `AA VENGEANCE ESSENTIAL HOUSE VOL.1` — the techhouse workhorse:
  Hard Kicks (379), Soft Kicks (185), Snares & Claps (465), Closed Hihat
  (140), Open Hihat (232), Bongo (86), House Rimshots (92), Tom (49), Shakers
  (46), Percussive (116), **Cutted Sounds (396) = vocal/synth chops**, FX
  Reverse (75) / Slides (48) / Hallkicks (18).
- **TR-909** = `Roland-TR-909` (211) — MK's 909 hats/clap (filename decode:
  `HHCD*`=closed hat, `HHOD*`/`HHOA*`=open hat, `HANDCLP*`=clap, `BTAA*`=kick).
- **Hyperfunk** = `[VB] Hyperfunk\[VB] Hyperfunk` — funk bass one-shots
  (`Oneshots (if you don't have Serum)\Bass 11\BA *.wav`).
- **Carnival** = `musicradar-carnival-rave-samples` — HUGEL chants
  (`Vox slices\Zena Kitt vox slices-*.wav`), Assorted perks, Revers-a-perk,
  Mental noises.
- **Rave** = `musicradar-rave-samples` — bigroom `DrumHits` + `FX`
  (Crowd/Riser/Lazer/Delay_Boom).
- **Madeon** = `Madeon Adventure Machine Samples v2` — bigroom `sounds.*`/
  `bass.*` synth stabs.
- **dnb-fx** = `musicradar-dnb-fx-samples` — bigroom/latin risers & sweeps.
- **GarageSessions** = `GarageSessionsVol3...\...\Foley Percussion` + **WuTang**
  = `WuTang_DRUMS_ BREAKS` — Fred's found-sound / dusty top texture.

## Method — how the FINAL PICKs were chosen

I can rank by spectral feature, not hear. `scratchpad/triage.py` extracts
decay, spectral centroid, low/mid/hi energy and tonalness for every candidate
and, per section, returns (a) a target-sorted top pick and (b) a diverse
spread. `tools/audition_producer_kits.py` renders those into contact-sheet
MP3s → `engine/out/audition/<producer>/` (each candidate in a numbered slot
behind a rising pitch-ladder marker; slot→file in the `.txt` sidecar).

**FINAL PICK below = the triage top pick = slot 1 of each contact sheet.**
It is a *proposal*. After the owner listens, swap any pick to the slot they
prefer (edit `tools/producer_candidates.json` — put the chosen file first —
then rebuild the pack: one command). Alternates already sit in the sheet.

---

## bassled — Dom Dolla  (≈126 BPM)

One-bar ID: rubbery filter-wobble bass interlocked with a pitch-shifted
"talkbox-alien" vocal phrase over a clean punchy 4/4; dry, sparse, bass IS the
melody. Overall colour: **clean + dry + punchy**, space left for the bass hook.

- **DRUMS** — clean punchy round house kick (tight, never distorted), crisp
  16th closed hats + offbeat open, dry snappy clap on 2 & 4.
  - kick → `VEH1 Hard Kicks\VEH1 Hard Kick - 047.wav` (decay 74 ms, low-heavy, tight)
  - clap → `VEH1 Snares und Claps\VEH1 Snares & Claps - 135.wav` (bright, dry, snappy)
  - hatC → `VEH1 Closed Hihat - 78.wav` · hatO → `VEH1 Open Hihat - 094.wav`
- **SAMPLER** (smp `chop_alien`) — formant/talkbox vocal chop, pitched down.
  - → `VEH1 Cutted Sounds - 023.wav` (tonal, vowel-y; alt: 175 / 067 in sheet)
- **SYNTH+POST** (R32d) — `bass_wobble` v2 (deeper res/env) through a
  **HPF + Distortion wet-blend** VOICE_POST chain = the Ableton-Erosion grit
  that makes the sub cut on small speakers. This is the identity element.
- **FX** — restrained filter sweeps (`VEH1 Slides - 12/09`) + reverse-vocal
  swell (`VEH1 Reverse - 04/10`). No impacts.
- **MIX** — dry (pads −2 dB drier via `_PRODUCER_SEND_DELTA`), prominent
  sidechain pump; small room.

## discofunk — Purple Disco Machine  (≈121 BPM)

One-bar ID: octave-popping funk bass (low-HIGH-low-HIGH 8ths) locked with
Chic-style chucked guitar and Italo string/synth stabs; live disco percussion
bed. Overall colour: **live, warm, busy-but-light**.

- **DRUMS** — tight round moderate kick, 8th closed hats + offbeat open, soft
  clap + reverb-tail on 2 & 4, **live perc bed** (shaker 16ths, disco tom
  pitch-drop zaps as fills).
  - kick → `VEH1 Soft Kicks\VEH1 Soft Kick - 096.wav` (round, warm) — or 100 (punchier)
  - clap → `VEH1 Snares & Claps - 025.wav` (softer, mid) · hatC → `VEH1 Closed Hihat - 05.wav`
  - shaker → `VEH1 Shaker - 11.wav` · tom_zap (fill) → `VEH1 Tom - 13.wav` (pitch-drop)
  - perc → `VEH1 Percussive - 51.wav`
- **SAMPLER** (smp `funk_stab`) — Hyperfunk funk-bass/synth one-shot as a
  chuck stab. → `[VB] Hyperfunk\...\Oneshots (if you don't have Serum)\Bass 11\BA Talking Yoi [VB].wav`
  (bright, funky; alts BA Lime / BA Distorted Synth Layer in sheet).
- **SYNTH+POST** (R32d) — `bass_moog` springy octave-pop pluck (replaces
  bass_funk as the discofunk signature) + a **phaser** VOICE_POST on the
  clav/stab (Chic chuck colour). Italo lead = R31 `lead_italo`/`string_machine`.
- **FX** — disco-tom zap fills (from DRUMS), tape-echo throws.
- **MIX** — warm; light NY comp; percussion sits up.

## latin — HUGEL  (≈124 BPM)

One-bar ID: a 1-2 bar cumbia chant hook riding a rolling syncopated bass with
live congas/timbales/shakers over a tight 4/4; timbale-roll into a
percussion-plus-hook drop-out. Overall colour: **carnival-festive, never bare**.

- **DRUMS** — punchy round kick, offbeat open hats + 16th shakers, clap + rim
  on 2 & 4, **live Latin hand-perc on top** (bongo, conga tumbao, rimshot).
  - kick → `VEH1 Soft Kick - 096.wav` (round) · clap → `VEH1 Snares & Claps - 025.wav`
  - hatO → `VEH1 Open Hihat - 094.wav` · bongo → `VEH1 Bongo - 19.wav`
  - rim → `VEH1 House Rimshot - 38.wav` · shaker → `VEH1 Shaker - 11.wav`
  - perc → `VEH1 Percussive - 51.wav` (seasoning; congas/timbale flavour)
- **SAMPLER** (smp `chant_v`) — carnival vocal chant slice.
  → `Carnival\Vox slices\Zena Kitt vox slices-22.wav` (tonal chant; alts 52/95 in sheet).
- **SYNTH+POST** (R32d) — R31 `pad_accordion` (cumbia accordion) + a **slap
  delay** VOICE_POST on the chant. Marimba/brass hooks from GM.
- **FX** — reverse-perk swell (`Carnival\Revers-a-perk\Bungle stylee.wav`),
  latin perk seasoning (`Carnival\Assorted perks\*`), crowd "hey" from
  `Rave\FX\Crowd01/02.wav`, timbale-roll build (dnb-fx riser stand-in).
- **MIX** — bright, festive; percussion prominent; no dark textures.

## pianohouse — MK  (≈126 BPM)

One-bar ID: pitched, chopped vocal-sample stabs as the LEAD over warm 90s
piano/organ stabs and a round syncopated deep-house bass with double-swung
909 hats. Overall colour: **warm, soulful, sunny-with-longing; 909-swung**.

- **DRUMS** — clean round house kick, **TR-909 hats (two swung lines)** +
  909 clap on 2 & 4, house rimshot garnish.
  - kick → `TR-909\BTAA0DA.WAV` (round 909) — or VEH1 round (`Soft Kick - 096`, `kick_veh` sheet)
  - hatC → `TR-909\HHCD0.WAV` · hatO → `TR-909\HHODA.WAV` · clap → `TR-909\HANDCLP2.WAV`
  - rim → `VEH1 House Rimshot - 38.wav`
- **SAMPLER** (smp `chop_real`) — the MK-dub syllable: a re-pitched vowel
  cutted-sound stab. → `VEH1 Cutted Sounds - 023.wav` (or a shorter syllable,
  slots 2-4 in sheet). This is MK's whole identity — the lead IS the chop.
- **SYNTH+POST** (R32d) — R31 `bass_organ` (Korg M1 Organ-2 root+fifth) as the
  bounce bass; piano/organ stabs = Salamander `pad_piano`. 0.13 swing.
- **FX** — restrained: short delay throws + small riser on the chop only.
- **MIX** — warm, dry-ish, mono-centre rhythm; wide backing pads.

## lofi — Fred again..  (≈128 BPM)

One-bar ID: a chopped, pitch/formant-shifted "voice-note" fragment over warm
detuned felt-piano chords with deep sidechain pump and an ever-present
vinyl-crackle / foley bed. Overall colour: **soft, dusty, intimate, breathing**.

- **DRUMS** — soft dusty kick, quiet closed hats, soft wide clap, **found-sound
  foley top** instead of bright cymbals.
  - kick → `VEH1 Soft Kick - 096.wav` (dustiest/roundest) · clap → `VEH1 Snares & Claps - 025.wav`
  - hatC → `VEH1 Closed Hihat - 78.wav` (quiet in mix)
  - foley top → `GarageSessions\...\Foley Percussion\GS_GSV3_FoleyPerc_20.wav` (or WuTang `RZABR24.wav`, `wutang` sheet)
- **SAMPLER** (smp `chop_note`) — soft warm voice-note chop.
  → `VEH1 Cutted Sounds - 048.wav` (warm, sustained-ish; alts in sheet).
- **SYNTH+POST** (R32d) — R31 `felt_piano` (Salamander → PAD_POST LPF) with an
  added **tape-wobble chorus** VOICE_POST; warm round sub bass.
- **FX** — reverse-reverb swells (`VEH1 Reverse - 04/07`), **pinned vinyl
  crackle bed** + pinned pads (R31), tape-stop.
- **MIX** — lofi: riff/pads +2 dB wetter, room 0.46 (`_PRODUCER_*` deltas);
  0.62 pump.

## bigroom — David Guetta  (≈125 BPM)

One-bar ID: huge detuned-supersaw STAB RIFF singing a nostalgic melody over a
dead-straight 126 4/4, whole mix breathing to the kick, after a long filtered
build. Overall colour: **glossy, loud, festival, dead-straight**.

- **DRUMS** — punchy festival kick (short, controlled), crisp offbeat hats,
  layered clap + bright snare on 2 & 4, snare/clap rolls into drops.
  - kick → `VEH1 Hard Kick - 047.wav` (festival-tight) · clap → `VEH1 Snares & Claps - 135.wav` (bright)
  - hatC → `VEH1 Closed Hihat - 78.wav` · hatO → `VEH1 Open Hihat - 094.wav`
- **SAMPLER** (smp `rave_shot`) — supersaw/rave stab one-shot.
  → `Madeon\sounds.1.8.wav` (tonal synth stab) or `Rave\DrumHits\*` (`stab_rave` sheet).
- **SYNTH+POST** (R32d) — new `lead_futurerave` saturated supersaw stab
  (joins the bigroom stacks) + R21 `supersaw_chord` pads; **distortion**
  VOICE_POST on the lead. Rolling offbeat saw bass.
- **FX** — big riser (`dnb-fx\DNB_FX_11.wav` / `VEH1 Slides - 12`), reverb
  impact on the drop (`Rave\FX\Delay_Boom.wav` / `VEH1 Hallkicks`), roll fills.
  Riser PINNED ON (Guetta always builds).
- **MIX** — loud, glossy; drum clipper harder (`_PRODUCER_DRUM_CLIP_K` 1.5);
  less NY comp; +0.5 dB drop push.

---

## What R32b builds from the DRUMS rows

`producer_techhouse.pack` (committed) — container
`[4B LE headerLen][UTF-8 JSON][WAV bytes]`, header v1:

```
{"drums":   {"techhouse:<producer>": {voice: {o,n,g}}},
 "melodic": {"techhouse:<producer>": {name:  {o,n,g,root_hz}}},   # smp chops (R32c)
 "fx":      {"techhouse:<producer>": {kind:  {o,n,g,peak_dbfs}}}} # sampled FX (R32e)
```

Every techhouse pattern voice must be covered per producer (producer-specific
voice → producer file; the rest reuse the base techhouse relpaths). Sub-lane
policy (R25: sub = weight, never a 2nd kick): bassled 0.50, discofunk 0.45,
latin 0.55, pianohouse 0.55, lofi 0.45, bigroom 0.60.

## Owner-listen checkpoint 1

Contact sheets: `engine/out/audition/<producer>/<producer>__<section>.mp3`
(+ `.txt` slot index). Listen, note any slot you prefer over slot 1, tell me
"`<producer> <section>` → slot N". I lock picks in `producer_candidates.json`
+ the FINAL PICK cells above, then build the pack (R32b).
