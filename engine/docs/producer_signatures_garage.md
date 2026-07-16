# UK Garage producer signatures (R33 garage pass)

The six garage producer strains (owner-approved 2026-07-16). Each `### heading`
is the reference producer; the parenthesised code is the internal `producer_style`
key (globally unique vs the techhouse set). Every strain recolours drums, bass,
chords, the hook, FX and mix **within garage's PINNED backbone** — 2-step, kick
1 & 3-ish, snare/clap on 2 & 4, syncopated offbeat open hats, heavy swing
(~0.16), ~130–135 BPM. We borrow only the instrumental/production signature,
never lyrics. Web-verified current (the 2023–2025 UKG resurgence): Sammy Virji =
DJ Mag Best Producer 2025; Interplanetary Criminal = DJ Mag Best DJ 2025; MPH,
Silva Bumpa, Conducta top the 2024–25 UKG/bassline charts.

Format per entry (programmable into the `_PRODUCER_*` tables + manifest recipe):
BPM · DRUMS · BASS · CHORDS/PADS · LEAD/HOOK · FX/TEXTURE · MOOD · HOOK-ID.

The six PARTITION across four axes (rhythm feel / bass sound+role / chord+hook
carrier / texture+mood) — no two occupy the same cell. Two near-neighbour pairs
and how they're separated are noted at the end.

---

### Sammy Virji  (`virji`) — the banked anchor
- **BPM:** 130–138 · app target **133**
- **DRUMS:** Punchy skippy 2-step; tight kick, crisp clap on 2 & 4, rubbery offbeat open hats; heavy garage swing (~0.16).
- **BASS:** **Organ bass** (rounded, rubbery) — melodic, bouncy syncopated 8ths/16ths; the bass IS the hook, walks with the vocal.
- **CHORDS/PADS:** Rave organ stabs, warm major-leaning; occasional detuned supersaw chord.
- **LEAD/HOOK:** Chopped diva/rave vocal stabs over the organ-bass riff.
- **FX/TEXTURE:** Rave air-horn hits, reverse-cymbal lifts, vocal-shout stabs, light vinyl.
- **MOOD:** Party, hype, warm, feel-good rave energy.
- **HOOK-ID:** Rubbery organ bassline bouncing under a chopped diva chant.

### Interplanetary Criminal  (`breakz`)
- **BPM:** 130–135 · app target **132**
- **DRUMS:** Broken 2-step hybrid — re-pitched breakbeat fills spliced into the 2-step, shuffled ghost snares, dusty hats; swing present but rawer/looser.
- **BASS:** Deep sub / raw reese, minimal and dark; few notes, more felt than melodic.
- **CHORDS/PADS:** Sparse — a single filtered stab or dub chord, lots of space.
- **LEAD/HOOK:** Minimal — a lone re-pitched vocal snippet, or the break itself carries it.
- **FX/TEXTURE:** Cassette/DIY lo-fi — tape hiss, bit-crush, dub-delay throws, vinyl crackle.
- **MOOD:** Raw, underground, hypnotic, club-dark.
- **HOOK-ID:** Stripped lo-fi 2-step, chopped breakbeat and a deep dark sub, almost no melody.

### Conducta  (`sunny`)
- **BPM:** 130–135 · app target **130**
- **DRUMS:** Skippy, light, bright 2-step; crisp rimshots, sparkly shakers, airy; medium-heavy swing.
- **BASS:** Warm bouncy sub — melodic and springy, bright not heavy.
- **CHORDS/PADS:** Colourful rave stabs + plucked/organ chords, major, uplifting, top-end shimmer.
- **LEAD/HOOK:** Sugary chopped vocal confetti (Todd-Edwards micro-slices) + bright bell/pluck.
- **FX/TEXTURE:** Dub sirens, riser sweeps, sunny reverse-vocals, hand-claps, festival whistles.
- **MOOD:** Sunshine, serotonin, joyful, colourful — the most kid-bright strain.
- **HOOK-ID:** A dub siren + sugary vocal-chop confetti over springy sub.

### Silva Bumpa  (`niche`) — MPH is the alt anchor
- **BPM:** 133–140 · app target **135**
- **DRUMS:** Swung, but kick leans toward driving 4x4/Niche push (backbone intact: offbeat hats + clap on 2 & 4, energy heavier); tight, system-tuned.
- **BASS:** **Wobble / growl / talkbox mid-bass** (Sheffield bassline weight) over a deep sub — the aggressive bass-lead.
- **CHORDS/PADS:** Minimal, dark-warm stabs; the bass is the harmony.
- **LEAD/HOOK:** The wobble-bass riff IS the hook, call-and-response with a vocal shout.
- **FX/TEXTURE:** Sub drops, gated FX, impact booms, filtered build sweeps.
- **MOOD:** Heavy, driving, rave-powerful, muscular.
- **HOOK-ID:** A wobbling/growling Niche bassline as the lead melody over a driving swung kick.

### MJ Cole  (`sincere`)
- **BPM:** 130–134 · app target **130**
- **DRUMS:** Smooth, immaculate 2-step; soft kick, brushed/tight snare, silky offbeat hats; understated swing.
- **BASS:** Soft round sub / fingered bass — musical, walking, jazzy.
- **CHORDS/PADS:** **Rhodes / grand piano** — lush jazzy 7th/9th chords, the centrepiece.
- **LEAD/HOOK:** Soulful chopped vocal + piano/Rhodes riff, sung-melodic and warm.
- **FX/TEXTURE:** Tasteful reverb wash, vinyl warmth, string swell, subtle sidechain breathing.
- **MOOD:** Smooth, soulful, sophisticated, romantic-calm.
- **HOOK-ID:** A Rhodes/piano progression over a soft swung 2-step — the "Sincere" lineage.

### salute  (`dusk`)
- **BPM:** 130–135 · app target **132**
- **DRUMS:** Rolling 2-step (backbone pinned) with atmospheric fills; softened transients, reverb-tailed snares, washed hats.
- **BASS:** Deep rolling sub — continuous, hypnotic, warm and enveloping.
- **CHORDS/PADS:** Big washed / filtered pads, French-house filter swells — euphoric, evolving.
- **LEAD/HOOK:** Pitched/formant-shifted vocal float in reverb, or a lone euphoric synth line.
- **FX/TEXTURE:** Long reverb/delay washes, filter automation, misty risers, filtered-disco shimmer.
- **MOOD:** Euphoric-atmospheric, uplifting-emotional, "sunrise" festival lift — the orthogonal mood axis.
- **HOOK-ID:** A filtered euphoric pad + reverb-drenched vocal float over a deep rolling sub.
- *Anchor note:* salute (Ninja Tune, festival-scale) replaces Overmono for this slot — garage-native, so zero backbone risk while keeping the atmospheric/euphoric mood no other strain touches.

---

## Distinctness partition

| key | rhythm feel | bass sound + role | chord + hook carrier | texture + mood |
|---|---|---|---|---|
| `virji` | bouncy skippy 2-step | organ bass, melodic lead | rave organ stabs + diva chop | party / warm rave |
| `breakz` | broken 2-step + breaks | dark sub/raw reese, minimal | sparse stab + the break | lo-fi / underground-dark |
| `sunny` | light airy skippy 2-step | springy warm sub | rave stabs + vocal confetti | sunshine / dub sirens |
| `niche` | 4x4-driving swung | wobble/growl mid-bass = lead | bass-as-harmony, dark stab | heavy / muscular |
| `sincere` | smooth understated 2-step | soft round jazzy sub | Rhodes/piano + soul vocal | soulful / romantic |
| `dusk` | rolling atmospheric 2-step | deep rolling continuous sub | filtered washed pads + vocal float | euphoric-atmospheric |

**Near-neighbour separations:**
- `virji` vs `sunny` (both bright, organ/rave stabs, vocal chops): separate on **bass weight + role** — `virji` bassline-weighted (organ *bass* drives, party-hype), `sunny` top-end-weighted (springy light sub, brighter stabs + dub sirens, more FX). Program `virji` rounder/louder bass, `sunny` brighter tops.
- `niche` vs `dusk` (both heavy low-end): separate on **bass behaviour + mood** — `niche` aggressive wobble/growl mid-bass as the lead riff (driving/muscular); `dusk` smooth continuous rolling sub under filtered pads (euphoric-atmospheric). Opposite energy arcs.
