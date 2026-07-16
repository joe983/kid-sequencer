# Rhythm Trail — Note-Length Lesson Course: Full Design (synthesized 2026-07-17)

Produced by a 3-designer / 3-judge / synthesis workflow over a 6-dimension research sweep.
The executable plan lives at ~/.claude/plans/using-the-3-scaffolding-melodic-scroll.md.

---

# Note-Length Course for Kid Sequencer — Final Design ("Rhythm Trail")

**Skeleton call:** the pedagogy-first design wins as the spine (highest pedagogy score, second on kid-UX; the curriculum and micro-arc were judged strongest) with leverage-first's engineering discipline and ux-first's delivery-channel fixes grafted throughout. Every judge graft is incorporated; every concern is resolved inline and marked **[FIX]**.

## 0. Design stance — five hard rules from the research

1. **Sound before symbol** (Kodály/Gordon/Pestalozzi consensus): no stave glyph until the child has made and heard that duration on the grid. Never name a concept before the behaviour exists (DragonBox staging).
2. **No fraction math, ever**: long notes are "stretched tas" felt against a pulse. Whole note **late** (Kodály Gr4), ta+ti-ti **first**, rests **immediately** (Gr1). Never "a half note is half a whole note."
3. **No graded live tapping below ~7** (tapping CV ~0.2 at 5–6, −81 ms negative asynchrony): assessment = untimed grid placement + Gordon-PMMA same/different listening (validated at age 5, motor-free, machine-gradable).
4. **No text below ~8, no audio-only either** (Hiniker/NN-g): every instruction = spoken clip + synchronized demonstration on the real grid, replayable. Pulsing a cell alone demonstrably does not teach.
5. **No loss states** (Deci/Koestner/Ryan; anti-IXL; 5Rights): no streaks, timers, lives, leaderboards. Misses only escalate help. The reward is the child's own bar played back with a full groove (intrinsic integration, anti-Prodigy).

**Standing over-build watch-list** (graft, both judges): no meta-game economy, no separate app/framework, no mic or tap-timing assessment before C4, no bespoke stave renderer, no circular meter views, no per-lesson illustrations. Any feature on this list needs explicit owner sign-off.

---

## 1. Curriculum spine

Three bands map NN/g age bands onto PYP phases; ~19 lessons in 7 units, ordered by the Wichita State Kodály grade sequence — **not** the whole→quarter fraction pyramid. Lessons: 2–5 min (Band A) to 8–10 min (Band C).

**Grid semantics (one resolution, leverage-first's reuse move):** the existing 8-col `stepDiv:2` learning grid — one column = one eighth. Existing ♩ tool (2-col, one attack) *is* ta; existing ♫ *is* ti-ti. Half = new len-4 token, whole = new len-8 token. All length comes from **pre-sized palette tokens, tap-only** — no drag before Band C, if ever (drag succeeds for ~30% of 7–8s).

### Band A — "Sound Makers" (PYP 1–2, ages 5–7, pre-readers)
1–2 rows, 8 cols, tempo locked 90, blobs not glyphs, syllables only (ta/ti-ti — defers the UK/US crotchet/quarter fork). `techlearn` drum loop = Gordon's macrobeat layer.

| # | Lesson | Concept | Entry → Exit |
|---|---|---|---|
| A1 | The Heartbeat | Steady beat ≠ rhythm; pulsing heartbeat row; freeze game (ungraded) | none → feels/points at pulse |
| A2 | Walking Notes (ta) | 1-beat note placed on beats | A1 → builds a 4-ta bar |
| A3 | Running Notes (ti-ti) | Eighth pair = two sounds in one beat (existing `kind:"eighth"`) | A2 → ear-discriminates ta vs ti-ti; builds mixed bars |
| A4 | The Quiet Beat | Empty cell = performed silence; freeze gesture as playhead crosses | A3 → deliberate rests; passes keep-the-rest check |
| A5 | Pattern Play | Unit review: echo, same/different, fix, free-create; ends with the Groovy-Music stave reveal on the child's OWN pattern — "you wrote real music" | A2–4 → 75%+ mixed check |

*Why this order:* ta+ti-ti is the universal Gr1 entry (walk/run locomotion, Dalcroze); rest at Gr1 as performed silence; beat/rhythm separation is the #1 conceptual failure point and the sequencer isolates the layers (drum pulse vs child's row) as no classroom can.

### Band B — "Note Stretchers" (PYP 3, ages 7–9)
1–3 rows, 8–16 cols; stick-notation glyphs drawn ON blocks; one-line rhythm stave; note names arrive here (Kodály Gr2) via UK/US terminology toggle (name-bearing clips atomic and few).

| # | Lesson | Concept |
|---|---|---|
| B1 | The Long Note (ta-a) | Half note = one attack ringing across 2 pulsing heartbeats — sustain IS the concept (piano sample decay carries it) |
| B2 | Long Quiet | Half rest, paired with its note value (Rhythm Swing pattern) |
| B3 | Real Names + Sticks | "Musicians call ta a crotchet"; stick glyphs revealed on blocks the child already uses; one-line stave debuts |
| B4 | Reading Rhythms | Stave→grid builds — the anti-Synthesia move (watching lights = recognition, not reading) |
| B5 | Fast Notes (tika-tika) | Sixteenths. **[FIX B5 touch targets]** introduced through listening/discrimination first (PMMA items need no building); building happens on a **zoomed half-bar** — 8 visible columns of a 16-col bar with a bar-half toggle — so cells never drop below the ~2 cm child minimum. Full-16-col building only if the iPhone-Safari canary passes it |
| B6 | Rhythm Detective | Unit review: interleaved discrimination juxtaposing nearest confusables (Kornell & Bjork discriminative contrast; Stambaugh) + colourless-glyph checkpoint (Rogers 1996: colour gains don't transfer alone) |

### Band C — "Composers" (PYP 4–5, ages 9–11, visibly older styling)
Full 5-line treble stave (Faber pre-staff → one line → five lines). Drag-to-stretch unlocks here only.

| # | Lesson | Concept |
|---|---|---|
| C1 | The Whole Bar | Semibreve fills the bar — taught LAST of plain values (Kodály Gr4: hardest to feel). Whole rest paired |
| C2 | Three-Beat Notes | Dotted half = "a note lasting three beats" (Heart Chart token), never dot arithmetic; re-grid to 6 cols/3-4 (Song Maker re-gridding) |
| C3 | Joined Notes | Ties only where the grid forces it: span crossing the barline = one grid block, two arced stave notes (tie rendering stave-only) |
| C4 | Off-Beat Tricks | Syncopation + tam-ti. Optional tap-along vs woodblock (±15% beat window, early-biased, shift-detection first). **[FIX]** Strictly **formative and non-gating** — never blocks path progression; results logged to validate window widths before they ever count |
| C5 | Capstone: Teach It | PYP Phase-4 verbatim: compose 2 bars, see real notation, print worksheet + QR for a younger child to scan and play (existing SHEET_GEOMETRY/print) |

**Placement (kid-UX graft — replaces any adult-facing picker):** no test. The path map opens with three door-sized band entrances, spoken + iconic ("I'm new to music" / "I know ta and ti-ti" / "I read some music"). Repeated failure drops to the prior band's variant (Khan Kids adaptive drop-down); fast success skips ahead.

**Spaced review [FIX dosage]:** review nodes are data-level path entries placed AHEAD (Duolingo reframe = spaced retrieval as forward progress), scheduled so **every duration value is retrieved in at least two later units** (ta resurfaces in U5 and U9 reviews; ta-a in B6 and C1; etc. — Vlach & Sandhofer). Every session opens with a 60-second retrieval warm-up.

---

## 2. Lesson micro-arc

One repeatable loop = Gordon's skill sequence fused with Renkl/Atkinson worked-example fading, plus the grafted do-first opener:

**START → TOUCH → HEAR/ECHO → EAR-CHECK → DO → NAME → CREATE → CELEBRATE**

1. **START** — one big tappable button: resumes AudioContext, runs the silent-mp3 unmute trick (iOS hardware silent switch mutes WebAudio; `<audio>` narration is immune), plays clip 1. **In MVP, not v2** (feasibility graft — the on-device kid test is exactly where a silently-muted iPhone produces a false negative).
2. **TOUCH** (do-first, ~20 s; ux-first graft) — lesson opens on a *preloaded playing pattern*, never a blank grid (Ableton "modify a working example"). **[FIX tap-only prompts]** every do-first prompt uses an action the current palette supports in one tap: "add a running note," "take one note away," "swap this walking note for two running notes" — never "make this note longer," which implies drag Band A doesn't have.
3. **HEAR/ECHO** — ghost demonstration performs the target while the mascot chants **duration-voiced syllables** ("ta-a-a" physically held for its length — feasibility graft: these ship as chant-type clips in the narration sprite, so cutting mascot art never cuts the chant, the channel that actually teaches duration). Child chants back (honour-system) and replays via play button.
4. **EAR-CHECK [FIX audiation probe]** — every Band A lesson places one **which-one** (Gordon PMMA same/different: two mini-grids, a pattern plays, tap the match) immediately after ECHO, so at least one motor-free check confirms the sound is internalized before building begins.
5. **DO** — 2–4 exercises, varied verbs:

| Type | Mechanic | Completion |
|---|---|---|
| copy | target heard (+ ghost demo), child rebuilds | set-equals target; 3 correct, non-consecutive |
| fill-the-gap | bar pre-placed minus 1–2 notes; **preset notes locked/undeletable** (leverage graft — a child can't wreck the scaffold into an accidental free-build) | set-equals; fade adaptively (Belland: contingent beats scheduled) |
| fix-the-pattern | one note wrong length; hear target vs broken, repair | set-equals |
| keep-the-rest (leverage graft) | target has deliberate empty beats; **filling a rest cell IS the error** — rest-as-performed-silence becomes directly assessable | set-equals |
| which-one / puppet check | PMMA 2AFC; or mascot taps on/off the beat, child judges (cBAT) | correct choice, 2 of 3 |
| read-and-build (B+) | stave shown, no audio until built and played | set-equals |
| free-create | constrained palette | ≥N notes of target len; cannot fail |
| hold (v2, B+) | touch-and-hold a big pad for the note's length, quantized to cells | **[FIX]** beat-proportional generous windows, feedback in heartbeats never ms, **optional enrichment — never gates progression** |

6. **NAME** — ≤20 s (kid-UX graft). **[FIX Band-A contradiction]** In Band A this step is **syllable-naming only — voice, no glyph, no stave** (Kodály's extended preparation period; the stave first appears at the A5 reveal). From B3 onward: stave panel slides up (existing slide-up sheet), the symbol pulses in sync with its grid block, narration names it once.
7. **CREATE** — Orff endpoint: "make your own using two long notes." Constrained palette so everything sounds good (PhET implicit scaffolding: constraint IS the instruction).
8. **CELEBRATE** — see the proportionality spec in §3.

**Feedback.** Every placement sounds instantly (intrinsic; Kulik). A wrong build never gets an X: target then attempt play back-to-back with the playhead sweeping — the mistake is *heard as consequence* (ST Math/JiJi), replayable. Success copy names the object — "You made a looong note — two heartbeats!" (Harvard Reach Every Reader RCT: concept-naming beat dings and generic praise). Periodic no-hint checks in unit reviews prevent guidance dependency.

**Hint ladder** (Sesame Workshop spec, system-initiated only — self-serve hint buttons get abused):
- ~7 s idle → sparkle the relevant control (existing idle-nudge pattern) + one ≤10-word clip.
- Miss 1 → warm "not quite — try again!" + target replays.
- Miss 2 → goal restated + demo finger re-demonstrates.
- Miss 3 → ghost outlines pulse on the exact cells and wait.
- Persistent → **demo finger places it, names it, celebrate anyway, move on** (kid-UX graft: the child who never solves it still gets celebration and forward motion — the complete no-dead-end guarantee). Repeated failure across a lesson additionally swaps in a **simpler grid variant of the same concept** (feasibility graft: Khan Kids drop-down; the `LEARN_LEVELS` variant machinery makes this nearly free), never the identical task again.
- Shifted-but-correct patterns get their own rung: "Right pattern — try starting on the first heartbeat!" (see `matchShifted`, §5).

---

## 3. UX / UI

**Lesson shell** (fixed 1600×900 stage; `learning-mode` already hides drums UI, instruments, pots, save/print — Mayer coherence for free):
- **Top strip:** mascot head (tap = replay instruction, always visible — NN/g: distracted children lose audio permanently), progress, exit door.
- **Progress = a bar of music filling note-by-note** (kid-UX graft: domain-native, countable by a 6-year-old; wins over abstract beads; never bare numbers — "What does this 2 mean? It's annoying!"). Stars (max 3/lesson) only ever fill.
- **Exit door [FIX fat-finger]:** forgiving, not confirming — leaving and re-entering resumes the *exact step with grid state intact*, no progress lost, no dialog a pre-reader can't read. State snapshot via `cloneState`.
- **Heartbeat row** beneath the grid: hearts pulsing per beat, driven from the `movePlayheadToStep` tick hook. This is the Kodály beat chart and the scaffold Bamberger requires: children read rhythm figurally; "how many heartbeats does it last?" constructs the metric mapping the grid otherwise assumes.
- **Mascot + demo finger (judge disagreement — the call):** keep ONE mascot (a round metronome-creature), but **its hand IS the demo finger, implemented leverage-first's way** — an absolutely-positioned sprite that moves to real cell coordinates (trivial: fixed-geometry stage) and **drives the actual `onCellClick` path**, so demonstrations use the real UI with the real `.placing` animation, truthful to what the child will do. Behavioural contract (kid-UX graft): appears only at instruction/hint/payoff moments, leaves during doing-time, reacts playfully when poked. MVP ships a minimal SVG creature (~4 poses); personality lives in the voice.
- **Instruction delivery:** recorded human UK voice, one action per clip, ≤10 words, verb last ("to add a running note, *tap here!*" — Sesame formula), always paired with the synchronized demo. Zero reading in Band A; one 14 pt line allowed in Band C.
- **[FIX phone-density collapse order]** on the smallest viewport, the shell degrades in this order before cells ever shrink below ~2 cm: (1) heartbeat row and stave are **never co-visible in Band A/B** — stave opening hides hearts; (2) progress bar compresses to a thin strip; (3) mascot shrinks to a head-icon; (4) only then may cell size flex. Band A caps at 8 cols × 2 rows. Every band gates on the iPhone-Safari canary.

**Navigation:** full-screen **path map** (multi-view modal — the call over leverage-first's slide-up sheet, whose documented 330 px/5-row cap can't hold the course; the modal scrolls) — one Duolingo-style linear path through three visually distinct band zones (Band A rounded/bright, Band C flatter/cooler — one register fails both ends). Unit anatomy as **data-level path structure** (feasibility graft): intro node → 3–5 exercise nodes → review node placed ahead. Node states: done ⭐ / current (idle-nudge pulse) / locked = **hidden**, not greyed (owner preference; dormant `.level-locked` treatment). MVP uses linear "next lesson" chaining; the map lands in v2.

**Celebration proportionality spec [FIX inventory]:**
- *Step complete:* sparkle only (`.placing` spring + toast), <1 s.
- *Lesson complete:* ≤2 s confetti burst → **full-groove playback of the child's bar** (the real reward), star fills on the path.
- *Unit complete:* unlock reveal — a new instrument/drum style for lesson free-play (the app's existing unlock vocabulary; intrinsically integrated).
All non-blocking (Hirsh-Pasek: embellishment measurably reduces comprehension). No coins, pets, or variable rewards. Completed creations accrue on a "song shelf." No upgrade modal can ever fire inside lesson flow (Toca Boca no-interruption rule); the dormant `requiresTier`/`enforceLevelEntitlement` gate stays wired but off.

---

## 4. Stave integration

One data model, per-band renderings (MusicFirst three-skin ladder), evolving:

- **Band A:** stave hidden A1–A4 (NAME is voice-only — see §2 fix). A5 = the Groovy-Music reveal on the child's own pattern, un-taught. Blocks are blobs; heartbeat row is the only "notation."
- **Band B:** **glyph-on-block** — stick-notation symbol drawn directly on the note block spanning its cells, so the symbol *physically occupies its duration* (gorhyme fused-object — the most direct "this symbol = this length" device; one small addition to `createNoteBlock`). Stave panel = **one-line rhythm staff** (a `renderStave` param suppressing four lines + clef; Faber pre-staff / percussion convention), **proportionally spaced so every notehead sits vertically above its grid column**, chunked per beat (the one spacing manipulation with measured positive effect). A separate stick-notation renderer is cut (leverage): glyph-on-block → one-line → five-line covers the bridge with parameters.
- **Band C:** full 5-line treble stave — existing `renderStave` already does coloured heads, beamed pairs, chords, rests. New: half/whole noteheads + rests (see line budget). Colour fade plan: value-coloured in A–B, **monochrome checkpoints** before any value counts as mastered (Rogers 1991/1996). The stave stays strictly standard — invent on the grid side only (Duolingo's octave-arrow mistake).

**Stave playhead sync (new):** tag each rendered note with `data-start`; `tick()` adds the existing `.playing` swell class to the SVG element at the current step — grid cell, sound, and symbol pulse as one perceptual event (Mayer signaling; the app's structural advantage over every worksheet). Lightweight class toggle, not a re-render. Rest glyphs pulse as the playhead crosses silence, introduced one per paired note value (Rhythm Swing). Post-attempt in Band C: SmartMusic-style green/red noteheads, red nudged for early/late.

**Reverse direction is mandatory** from B4: stave→grid construction every unit — grid-following alone teaches "following lights" (Synthesia transfer failure; DragonBox's documented weakness).

---

## 5. Tech architecture

**Config — extend the `LEARN_LEVEL` pure-data pattern:**

```js
LESSONS['a2'] = {
  band:'A', unit:1, title:'Walking Notes',
  level: _mkLearnLevel(1,[261.6],['#e05555'],36),  // reuse verbatim
  palette:['quarter'],            // adds 'half'(len4),'whole'(len8) later
  skin:'blob',                    // blob|glyph  (glyph-on-block from Band B)
  stave:'none',                   // none|reveal|line1|full|mono
  tempo:90,                       // per-lesson (long-note lessons may lock ~70 — owner Q6)
  drums:'techlearn', pulseRow:true,
  requiresTier:'guest',           // dormant gate, unchanged
  steps:[
    {type:'touch',  narr:'a2_0', preset:[…], prompt:'addNote'},
    {type:'demo',   narr:'a2_1', chant:'a2_c1', pattern:[{row:0,start:0,len:2},…]},
    {type:'which',  narr:'a2_2', options:[[…],[…]], answer:0, n:2},   // mandatory ear-check
    {type:'copy',   narr:'a2_3', target:[…], n:3, pass:{kind:'match'}},
    {type:'gap',    narr:'a2_4', preset:[…], locked:[…], target:[…], n:2},
    {type:'create', narr:'a2_5', mustUse:{len:2,count:2}},
  ],
  reward:{unlock:'trumpet'},
};
```

**Completion detection:** serialize `notesByRow` → sorted `"row:start:len:kind"` strings; set equality = pass (~30 lines; `cloneState` proves grid state is cheaply snapshotable). The per-cell diff (missing/extra/wrong-len) feeds the hint ladder and compare-playback. **`matchShifted` is a named pass mode in config, not a risk-list aspiration** (feasibility graft): a constant-offset match of the whole pattern triggers "right pattern — try starting on the first heartbeat" (Toussaint shift-detection; Bamberger's figural-stage kids preserve shape, not anchor — the predicted #1 unfair-grading case). `matchLoose` ignores row for rhythm-only steps. Detection hooks the `redrawRowNotes()` funnel (every grid mutation already flows through it), debounced; `copy/gap/fix` auto-pass only when the child presses play (hearing the answer is part of the answer). No timing machinery before C4.

**`playOnce()` primitive [FIX timer invariants]:** target auditions and 2AFC playbacks need a stop-at-bar-wrap. It **wraps `stop()` at the wrap boundary inside the existing tick — never forks the tick loop or touches the self-correcting `setTimeout` origin or the tempo-ramp re-anchor block** (both carry do-not-touch invariants). On-device check that the final step's audio (scheduled `AUDIO_AHEAD_S` ahead) isn't clipped by the stop.

**Narration:** `lessons.pack` — per-band mono MP3 sprite + JSON offset map, the exact `drums.pack` container philosophy; build script mirrors `install_app_kits.py`. Played through an **`<audio>` element** (silent-switch immunity), seeked by offset, ≥300 ms gaps. Clips ≤10 words, ~120 wpm; **duration-voiced chant clips are a first-class clip type**. Band A ≈ 50–70 clips ≈ 1.5–2 MB; course total ~100–120 clips ≈ 3–5 MB. Human UK voice for ship (measured TTS comprehension deficit for 5–8s); name-bearing clips atomic, duplicated only for the UK/US toggle if wanted.

**[FIX MVP test validity — both judges]:** MVP ships **TTS placeholders behind the sprite-loader interface with the final clip-key contract** (feasibility graft), *but* the **~15 load-bearing Band A clips are recorded as scratch human voice before any kid test** — otherwise a failed test indicts the placeholder, not the design; TTS-round results are directional only.

**Lesson runner placement:** inside the IIFE (needs `notesByRow`, `redrawRowNotes`, `startSequencer`, `pushUndo` — the documented cross-scope wall). `LESSONS` data + sprite offsets externalized to `js/lessons-data.js` to bound index.html growth.

**Line budget [FIX honesty]:** **1,200–1,600 lines JS + ~300 CSS**, not 500–700. New len-4/len-8 note kinds touch `tick()`'s trigger scan (which has the eighth-pair special case), `createNoteBlock`, the `occ[]` span logic, and `renderStave` (half/whole noteheads and rests don't exist in the renderer today) — each a documented chokepoint, each budgeted.

**URL scheme [FIX entry composition]:** `?level=1|2|3` untouched (printed QR worksheets + `SHEET_GEOMETRY` keep working, aliased to Band A sandbox entry — owner Q5). New `?lesson=<id>` derives `LEARN_LEVEL` from `lesson.level` then attaches the runner. **Verification task in MVP:** `enforceLevelEntitlement()` and `applyLockState()` must handle lesson ids without regressing the dormant `.level-locked` gate, and the `?lesson` parser must compose with — not race — the existing `?level` parser.

**Persistence** (Safari ITP wipes script storage after 7 Safari-days — every school holiday):
1. `localStorage['kidseq_lessons']` = `{v:1, stars:{...}, last:'a3'}` (~200 bytes) — account-free, COPPA/Children's-Code-clean; progress deliberately cheap to re-earn.
2. Logged-in: mirror to `users/{uid}.lessonProgress` via existing auth plumbing, merging `max(stars)` — never advertised to the child (sign-up nudges at kids violate the Children's Code).
3. v3: printable **QR progress card** (needs a QR generator — app only ships jsQR scanning) + add-to-home-screen prompt (exempts storage); solves shared classroom iPads (Clever-Badges pattern).

**Assets:** mascot (4–6 SVG poses, MVP-minimal), narration sprites, path art (CSS-heavy). No new instrument samples (piano's 6 s trim covers a semibreve even at tempo 70). Added payload target <3 MB for MVP.

---

## 6. Phasing

**MVP — Band A, A1–A5 (prove the loop):** lesson runner + step machine, `touch/demo/which/copy/gap/keep-the-rest/create` types, exact + `matchShifted` + choice + count pass modes, hint ladder with drop-down variants and demo-finger terminus, heartbeat row, **Start-button audio unlock + silent-mp3 trick + `<audio>` narration path**, TTS sprite (+ ~15 scratch human Band A clips before kid tests), localStorage stars, `?lesson=`, linear next-lesson chaining, A5 stave reveal, celebration spec. Deploy to a **dedicated hosting channel** (sibling worktrees overwrite `preview` — the scaffold-channel lesson). *Proves the three real unknowns cheapest: does completion detection feel fair, does a pre-reader follow demo-finger + voice, does the celebrate-playback loop land.* Success test: a real 5–7-year-old completes U1 unassisted on an iPhone — now valid because delivery failures (mute switch, unreadable text) are engineered out.

**v2 — Band B + notation bridge:** glyph-on-block skin, one-line proportional stave + playhead sync, read-and-build reverse tasks, note names + UK/US toggle, `fix`/`hold` types, path map modal with band zones + three-door placement, recorded human narration, Firestore mirror, colour-fade checkpoints, per-lesson tempo (~70 for long-note lessons), B5 zoomed half-bar.

**v3 — Band C + retention:** 3/4 re-grid, ties, whole note, C4 formative tap-along (logged, non-gating), C5 capstone print/QR, QR progress cards, A2HS prompt, review-node spacing across ≥2 units, analytics (lesson start/finish, audio-unlocked, installed — the evidence gaps to self-measure), optional per-lesson tier gating via the dormant `requiresTier`.

---

## 7. Top 5 risks

1. **Completion fairness** — zero algorithm-level evidence exists for grading kids' rhythm answers (the research's declared biggest gap). Mitigated by exact-match on tightly constrained grids, `matchShifted` for the figural case, free-create that can't fail, and owner's kids as the test bench before thresholds harden.
2. **Narration production is the critical path** — ~100 human clips (×2 if the terminology toggle ships), re-recorded on copy changes, owner-dependent. Mitigated: TTS placeholders gate nothing until wide ship; scratch human clips unblock kid testing; name-bearing clips minimal.
3. **Phone real estate** — top strip + heartbeat row + grid + stave on a scaled 1600×900 stage risks sub-2 cm cells. Mitigated by the explicit collapse order (§3), the Band A 8-col cap, the B5 zoomed half-bar, and the iPhone-Safari canary gating every band.
4. **Transfer failure (the DragonBox trap)** — kids finish able to build but not read. Mitigated: stave→grid tasks non-optional from B4, monochrome checkpoints, C5 producing paper notation a child physically hands to someone.
5. **Codebase risk** — 1,200–1,600 lines into a 5,300-line IIFE where main = prod. Mitigated: everything hangs off `LESSON`-truthy branches exactly as `LEARN_LEVEL` does, data externalized, existing functions touched only at documented chokepoints (`tick()`, `createNoteBlock`, `occ[]`, `renderStave`), `playOnce` wraps `stop()` without forking the timer, dedicated channel until owner sign-off.

## 8. Open questions (owner only)

1. **Classroom or home first?** Flips retention design (teacher cadence vs parent), muted-shared-iPad priority, and whether QR progress cards move up from v3.
2. **Monetisation:** stay default-open with the dormant gate, or arm `requiresTier` for a band (e.g. Band C Pro)? Currently designed so lesson unlocks never double as Pro teasers.
3. **Narration voice:** who records — you, a family member, hired VO? UK-only terms, or the UK/US toggle (doubles name-bearing clips)?
4. **Mascot appetite:** commission character art, or ship the minimal SVG creature and upgrade later? (Design works either way; personality lives in the voice.)
5. **Existing `?level=1–3` worksheets:** alias into Band A sandbox entry (the default here), or freeze as-is alongside the course?
6. **Tempo:** OK for long-note lessons to lock ~70 instead of 90? (A semibreve at 90 = 2.7 s — feelable; but B1's discrimination wants slower contrast, and the 6 s piano trim allows it.) Ships as the per-lesson `tempo` field either way.
7. **Course entry point in the full app:** a visible button on the main stage, link/QR-only, or worksheet-first? (Also decides QR-card priority.)

---

# Appendix A — Judge panel verdicts

Judge pedagogy: winner=pedagogy-first; scores=pedagogy-first:9, ux-first:7.5, leverage-first:6
  grafts: From leverage-first: the demo finger implemented as a driver of the real onCellClick path — demonstrations execute the actual UI with the real .placing animation, making the ghost-hand instruction channel truthful to what the child will do (and cheaper than sprite art). | From leverage-first: the shifted-match diff variant — detect 'right pattern, wrong start cell' and respond 'try starting on the first heartbeat' — the single cheapest fairness fix for figural-stage children, who preserve pattern shape but not metric anchor (Bamberger). | From leverage-first: the explicit keep-the-rest exercise type where filling a rest cell IS the error — it makes rest-as-performed-silence directly assessable rather than merely permitted. | From ux-first: the TOUCH do-first opener — the lesson begins on a preloaded playing pattern the child manipulates ('make this note longer — what changed?') before any instruction, so the ear encounters the duration contrast before teaching (Brilliant/Ableton modify-a-working-example). | From ux-first: the v2 'hold' exercise (touch-and-hold a big pad for the note's length, quantized to cells, feedback in beats never milliseconds) — the only proposed mechanic that assesses felt duration production rather than placement, correctly deferred past the motor-timing age floor. | From leverage-first: locked/undeletable preset notes in fill-the-gap steps — without them a child can wreck the scaffold, turning a completion problem into an unintended free-build. | From leverage-first: the over-build watch-list as a standing gate (no meta-game, no bespoke stave renderer, no mic assessment) — it protects the intrinsic-integration property that makes the sequencer pedagogically special.
  concerns: Internal contradiction on symbol timing: the universal micro-arc includes a NAME step (stave slides up, symbol pulses) in every lesson, but Band A is specified as 'no stave for A1-A4'. Resolve explicitly: in Band A the NAME step must be syllable-naming only (voice, no glyph, no stave), preserving Kodaly's extended preparation period before make-conscious. | The ECHO step is honour-system chanting, so audiation is never actually probed before the DO phase; ensure every Band A lesson places a which-one (PMMA same/different) item immediately after ECHO so there is at least one motor-free check that the sound is internalized before building begins. | B5 sixteenths require a 16-column grid — on a phone the cells fall below the ~2cm child touch target, and the design's own risk list caps Band A at 8 cols without resolving Band B; either verify 16-col motor feasibility on iPhone Safari or introduce tika-tika through listening/discrimination first with building on a zoomed half-bar. | MVP plans to user-test with TTS narration then swap in recorded voice — but the research says TTS measurably degrades 5-8s comprehension, so pre-reader comprehension findings from the TTS build will not transfer; test Band A with scratch human recordings even in MVP. | C4's graded tap-along, even with beat-proportional windows and shift detection, is the design's only timing-graded moment and its evidence base is thin; make it formative and non-gating (never blocks path progression), and log results to validate the window widths before they count for anything. | Practice dosage per value is light (2-4 exercises per lesson, one lesson per concept in places); the spaced warm-up covers only the previous value — schedule review nodes so each duration value is retrieved across at least two later units (Vlach & Sandhofer spacing), not just the adjacent one.

Judge kid-ux: winner=ux-first; scores=pedagogy-first:8.5, ux-first:9, leverage-first:6.5
  grafts: From pedagogy-first: progress rendered as a bar of music filling note-by-note (domain-native and countable by a 6-year-old) — prefer it over, or fuse it with, the abstract bead string. | From pedagogy-first: no-test band placement via three door-sized entrances with spoken + iconic labels ('I'm new to music' / 'I know ta and ti-ti' / 'I read some music') — replaces ux-first's adult-facing picker, which assumes an adult is present. | From pedagogy-first: the puppet check (mascot taps on/off the beat, child judges) — a playful, motor-free assessment format perfect for 5-6s. | From pedagogy-first: mascot behavioral contract — appears only at instruction/hint/payoff moments, leaves during doing-time, responds playfully when poked; and the NAME step capped at ~20 seconds. | From leverage-first: the demo finger drives the REAL onCellClick path at real cell coordinates so demonstrations use the actual UI with the actual .placing animation — implement the mascot's hand this way rather than as a parallel fake animation. | From leverage-first: tap-only everywhere with pre-sized palette tokens as the sole length mechanic (matching the existing quarter/eighth tools); no drag mechanic before Band C, if ever. | From leverage-first: 'demo finger places it, celebrate anyway, move on' as the ladder terminus — the child who never solves it still gets the celebration and forward motion, completing the no-dead-end guarantee. | From leverage-first: the over-build watch-list as a standing guardrail (no streaks, no separate app, no mic/tap grading, no bespoke renderer) — it protects the child-facing simplicity as much as the codebase.
  concerns: The TOUCH do-first opener ('make this note longer — press play') has no tap-only mechanic behind it in Band A: lengthening a note implies drag or a tool the child doesn't have yet. Rewrite every do-first prompt to use an action the current palette supports in one tap (e.g. 'add a running note', 'take one note away'). | Phone density is unresolved: top strip (mascot + beads + exit door) + heartbeat row + 8-col grid on a scaled 1600x900 stage risks cells below the 2cm minimum the design itself sets. Specify the collapse order on the smallest viewport (e.g. heartbeat row and stave never co-visible in Band A; beads shrink before cells do) and gate every band on the iPhone-Safari canary. | The exit-to-path 'door icon' in the top strip will be fat-fingered by 5-year-olds mid-exercise. It must be forgiving, not confirming: leaving and re-entering resumes the exact step with state intact, no progress lost, no dialog a pre-reader can't read. | MVP kid-testing runs on TTS placeholder narration — the exact delivery the research says 5-8s comprehend measurably worse. A failed MVP test may indict the placeholder, not the design; either record a minimal human-voice set for the ~15 load-bearing Band A clips before kid tests, or treat TTS-round results as directional only. | The v2 'hold' exercise type grades touch-hold duration — timing-adjacent for under-9s. If it ships, it needs beat-proportional generous windows, feedback in heartbeats never milliseconds, and it must never gate progression (optional enrichment only). | Celebration inventory is thinner than the principle: '.placing spring + a new confetti burst' needs an explicit proportionality spec per moment (step-complete = sparkle only; lesson-complete = <=2s confetti + full-groove playback; unit-complete = unlock reveal) so celebrations stay non-blocking and don't drift toward variable-reward territory during implementation.

Judge feasibility: winner=leverage-first; scores=pedagogy-first:6, ux-first:7, leverage-first:9
  grafts: From ux-first: ship TTS-placeholder narration behind the sprite-loader interface IN THE MVP (same clip-key contract as the final lessons.pack), so the pre-reader voice+demo channel is tested before the owner records anything — leverage-first's narration-free MVP under-proves the concept for its own target age. | From ux-first AND pedagogy-first: the Start-button audio unlock + silent-mp3 unmute trick + narration through an <audio> element must be MVP, not v2 — the iOS hardware silent switch mutes WebAudio, and the MVP's on-device kid test is exactly where a silently-muted iPhone would produce a false negative. | From ux-first: the Khan-Kids adaptive drop-down — on repeated failure across a lesson, swap to a simpler grid variant of the same concept rather than repeating the identical task; leverage-first's ladder ends at 'demo finger places it' with no easier-variant path. The LEARN_LEVELS variant machinery makes this nearly free. | From pedagogy-first: the matchLoose/shift-tolerant diff variant ('right pattern — try starting on the first heartbeat') as a named completion mode in the pass config, not just a risk-list aspiration — figural-stage kids producing shifted-but-correct patterns is the predicted #1 unfair-grading case. | From pedagogy-first: duration-voiced syllable chant clips (the mascot's 'ta-a-a' held for its real length, chanted in time over the demo playback) carried into the narration sprite as chant-type clips — cutting the mascot must not cut the chant, which is the channel that actually teaches duration. | From ux-first: Duolingo unit anatomy on the lesson path — intro node → exercise nodes → review node placed AHEAD on the path (spaced retrieval framed as forward progress) — as data-level path structure, no new UI component needed in the slide-up sheet. | From pedagogy-first: the tempo question — allow long-note lessons to lock tempo at ~70 instead of 90 (a semibreve at 90 is 2.7s; piano trim is 6s so there is headroom) — carried as a per-lesson tempo field in the config and an explicit owner question.
  concerns: Line-count honesty: 500-700 JS lines is optimistic. New len-4/len-8 note kinds touch tick()'s trigger scan (which has the eighth-pair special-case), createNoteBlock, the occ[] span logic, and renderStave (half/whole noteheads + half/whole rests don't exist in the renderer today). Budget 1,000-1,400 lines and keep the LESSONS data external as designed. | MVP proof validity: with no narration and no silent-switch handling, the 'real 5-7-year-old completes U1 unassisted on an iPhone' success test can fail because instructions are one-word text labels a pre-reader can't read, or because the silent switch mutes all audio — delivery failures masquerading as concept failures. Fix via the TTS-sprite and audio-unlock grafts. | The ?lesson=N entry 'derives LEARN_LEVEL then attaches the runner' — verify enforceLevelEntitlement() (line 943) and applyLockState() handle lesson ids without regressing the dormant .level-locked gate, and that lesson mode composes with the existing ?level parser rather than racing it. | Navigation in the load-sheet slide-up caps at ~5 visible rows (330px ≈ 5×66px per the documented max-height math) — fine for 8 MVP lessons, but the full course scrolls, and node states (done-star / current-nudge / hidden-locked) need new row rendering the estimate doesn't include. | The playOnce() primitive ('stops at bar wrap via stepCount') brushes against the self-correcting setTimeout timer and the tempo-ramp re-anchor block — both carry explicit do-not-touch invariants in CLAUDE.md; it must wrap stop() at the wrap boundary, never fork the tick loop, and needs an on-device check that the final step's audio (scheduled AUDIO_AHEAD_S ahead) isn't cut.

---

# Appendix B — Evidence digest

# Evidence Digest — Note-Length Lesson Course (Ages 5–11, Kid Step-Sequencer)

## 1. Pedagogy

**Sharpest findings**
- **Sound before symbol is universal law** (Kodály, Orff, Dalcroze, Gordon, Feierabend, descending from Pestalozzi): children perform/chant/move to a rhythm before ever seeing it written; notation only labels sounds already in the ear.
- **The canonical order is NOT whole→half→quarter.** Wichita State Kodály sequence: K = steady beat + "rest as silence"; Gr1 = ta (quarter) + ti-ti (eighth pair) + quarter rest + barlines; Gr2 = half note (ta-o), sixteenths, formal names; Gr3 = dotted half, 3/4, syncopation; **Gr4 = whole note**. Long durations are hardest to feel, not easiest — placing the whole note first because it's "mathematically simple" contradicts 100 years of practice.
- **Beat-function/word syllables beat ta/ti-ti empirically**: Palmer (1976) found Gordon's beat-based approach outperformed Kodály syllables; Colley (1987, 160 second/third-graders) found word-pattern and Gordon du-de both significantly better than ta/ti-ti for pattern recognition (Takadimi article; Lipscomb JMTP).
- **Children audiate patterns, not durations** (Gordon MLT): rhythm is taught as 2–4-beat patterns in meter context with a macrobeat (drum layer) under a microbeat layer — never isolated note-value drills. Notation appears only at stage 4 of 5 (Symbolic Association).
- **Beat vs rhythm confusion is developmental and universal**: sync improves sharply ages 5–7, adult-non-musician level ~7–8, not adult-like at 12 (Nature Sci Rep 2024; PMC3795075). Every lesson needs an audible/visible beat layer separate from the child's pattern.
- **Bamberger's invented-notation research**: untrained children notate rhythm *figurally* (grouped by gesture/phrase), not *metrically* — the grid externalizes exactly the metric dimension kids lack (Smith, Cuddy & Upitis 1994 replication).
- **The grid is legitimate IB PYP "non-traditional notation"** for phases 1–3; the stave panel delivers phase 4's "traditional notation" outcome — a 1:1 mapping onto the PYP arts scope & sequence (IST PYP music S&S).
- **Long notes = extended syllables** (ta-a, ta-a-a-a): duration is one attack sustained across felt beats — the instrument must audibly sustain and the block should glow across its length.

**Top patterns to steal**: Kodály prepare/present/practice as lesson template; per-lesson micro-arc LISTEN/echo → CHANT → READ (recognize) → WRITE (build) → CREATE (Feierabend/Gordon); stick notation as bridge representation; macrobeat drum layer under every exercise; rest as *performed* silence (gesture as playhead crosses empty cell), taught right after ta/ti-ti; press-and-hold as the Dalcroze duration gesture; word-rhythm seeding ("apple" = eighth pair); Orff creation endpoint ("make your own 4-beat pattern"); PYP phase badging with concept-driven framing ("long sounds tell different stories", not "Lesson 3: The Half Note").

**Top pitfalls**: fraction-pyramid ordering; symbols before sound; isolated note-value facts ("a quarter gets one beat"); formal names + number counting for 5–7s (names arrive Kodály Gr2); requiring precise live tapping from under-7s; sixteenths/dotted/syncopation before ~8–9; silent visual matching exercises; marking figural answers wrong.

## 2. Platforms (music apps)

**Sharpest findings**
- **Two families with opposite pedagogies**: the "toy" family (Chrome Music Lab, Incredibox, Toca Boca) teaches implicitly — zero text, nothing can sound bad, no failure states — but *none teach note duration* (Song Maker notes are all one cell, deliberately). The kid-sequencer's variable-length notes occupy a gap no mainstream kids' tool owns.
- **Ableton Learning Music's formula**: 2–3 sentences + ONE preloaded interactive the learner *modifies* (never a blank grid), linear "Next ›", no pass/fail anywhere, ends in a playground (ethanhein.com review).
- **Duolingo Music is the cautionary tale for this exact topic**: 69 units gamifying note reading, but duration is never enforced — "you can hold it as long as you want... no penalty" — so learners pass units without learning note lengths (dillonmok.com; duoplanet.com). It also drops crotchets/rests in "without explanation" and invents non-standard octave arrows.
- **Melodics' practice loop is the most complete design found**: Wait Mode (playback pauses until you act), BPM slider down to full stop, Auto-BPM (+10 when accuracy is high), note-by-note early/late feedback (support.melodics.com).
- **Rhythm Cat makes duration a gesture**: touch-and-HOLD for dotted/half/whole notes, 60 levels over real backing tracks — but educators note it "doesn't really teach the rhythms" (drill without instruction).
- **Yousician's fading notation scaffold**: Enhanced colored duration-bars → Colored Sheet → plain Sheet, plus timing-specific grading (perfect/a-bit-early/a-bit-late).
- **Groove Pizza**: circular grid + shapes (triangle/square/pentagon) producing maximally-even rhythms that "are nearly always musically satisfying"; math (angles, fractions) as a parallel path into rhythm — the 16-step grid is already a fraction wall.
- **Simply Piano's tri-state gate**: score pauses until correct; results are correct / incorrect / correct-with-assistance.

**Top patterns to steal**: preloaded working example per lesson, never blank; wait-mode playhead; Auto-BPM ladder (the app's tempo-ramp machinery implements it); touch-and-hold = note value with the block growing 1→2→4 cells; duration-axis feedback vocabulary ("held too long!"); fading grid→grid+stave→stave-only scaffold; meter as switchable templates (CML); constrain palette so everything sounds good (Incredibox); animated character feedback; low-stakes warm-up before performance; optional 3-star challenges over a never-blocked linear path.

**Top pitfalls**: notation reading without enforcing duration (the Duolingo failure — the course's core concept must be mechanically assessable, e.g. fail a 1-cell note where the stave asked 4); non-standard notation inventions on the staff side; text-heavy slides (musictheory.net anti-model); pure drill without a hear-and-copy demo; hard star-gates at the young end; single-verb exercise repetition; blank-canvas starts; upsell/lock UI inside lesson flow (the app's tier overlays must stay out).

## 3. Learning science

**Sharpest findings**
- **Mastery learning works, most for strugglers**: 108 evaluations (Kulik, Kulik & Bangert-Drowns 1990); criteria ≥75% needed for positive affective impact (Kulik & Kulik 1987). Gate on demonstrated criterion (~75–80%), route failures into a corrective loop.
- **Contingent scaffolding beats fixed fading**: computer scaffolding g=0.46 across 144 studies, but preset fading added nothing — only performance-contingent adaptation matters (Belland et al. 2017). Rule as simple as "two errors → restore the guide" outperforms hard-coded fade points.
- **PhET "implicit scaffolding"**: the strongest scaffolds are interface *affordances* — constrain what can be manipulated, pre-populate states. For pre-readers: offer ONLY 2-cell blocks in the half-note lesson; constraint IS the instruction.
- **Faded worked examples**: WATCH (pre-filled grid plays) → FINISH (completion problem) → MAKE (generation) beats jumping to problem solving; *adaptive* fading beats fixed (Renkl/Atkinson; Salden et al. 2009).
- **Productive failure is NOT for 5–8s**: evidence base is middle-school-up, mixed for younger (npj Sci. Learning 2019 boundary-conditions). Lead with the worked example; free exploration comes after competence.
- **Interleave confusable note values**: discriminative-contrast (Kornell & Bjork); replicated in beginner instrumentalists (Stambaugh, 5th–6th grade). Caveat: children benefit less than adults (2025 study) — short blocked burst first, then mix new value against nearest confusable (half vs whole, quarter vs eighth).
- **Mayer hard**: modality (narration beats on-screen text, d≈0.88 — critical for pre-readers), signaling (highlight what you name — the grid block AND stave symbol pulse together when the voice says "half note"), coherence (strip drums/tempo/instrument switching from lesson mode), pre-training (20-second name+sound+symbol intro card).
- **Rewards**: gamification effects largest for elementary learners (Zeng 2024, BJET) but expected tangible rewards undermine intrinsic motivation *most strongly in children* (Deci, Koestner & Ryan 1999, 128 studies). Leaderboards demotivate losers; time pressure links to anxiety. The best reward is hearing your own bar with a full backing groove.
- **Spacing works in children for generalization, not just retention** (Vlach & Sandhofer): open each session with a 60-second retrieval warm-up on previous note values.

**Top patterns to steal**: adaptive faded worked examples; criterion-gated unlock loop with 30-second corrective; retrieval warm-up openers (Firestore already tracks per-user state); discriminative-contrast drills (two bars differing in ONE note's length — "which sounds like this?"); synchronized dual grid+stave representation as one perceptual event (the app's structural advantage); duration-voiced audio labels (narration chants "ta-a" for exactly the note's length); self-set tempo challenge ("faster?" button); single voiced mascot at instruction moments only.

**Top pitfalls**: struggle-first design for 5–8s; on-screen text as the instruction channel; leaderboards/countdown timers/lives; expected prizes; pure blocked practice (fluent-feeling, poor discrimination) — but also interleaving from second zero; feedback on every action with no unaided checks (guidance dependency); progression by completion instead of criterion.

## 4. Kid UX

**Sharpest findings**
- **Three NN/g age bands span the course**: 3–5 pre-readers, 6–8 text-skippers who "mine-sweep" the screen, 9–12 who scan like adults and *reject anything babyish* (a 6-year-old dismissed a site as "for babies" from styling alone). One UI register fails both ends — map presentation tiers onto the existing 3 scaffolding levels.
- **Touch targets: 2cm × 2cm for young kids** — 4× the adult minimum; Apple/Google 44pt/48dp is calibrated for adults (NN/g; W3C). Years 1–2 lessons must run on reduced grids (4–8 steps) so cells are genuinely ~2cm.
- **Drag fails under 9**: ages 4–6 only 57% can tap an intended location, 20% manage tap-and-hold, drag largely out of reach; at 7–8 only 30% manage drag-and-drop; two-finger gestures ≤13% (PMC7303424; Vatavu et al., 89 children). **Drag-to-stretch cannot be the only way to make long notes** — teach length via tap-only mechanics (length token then tap, or tap-to-cycle) for years 1–3.
- **Pulsing/highlighting alone does NOT teach**: visual state changes were ineffective at prompting gestures across ages 2–5; animated on-screen demonstration + synchronized narration works from ~3.5, and audio alone fails (a distracted child loses it) — every prompt needs a replay button (Hiniker et al., UW, 34 children).
- **Lesson length**: 2–3 min attention per year of age; Khan Academy Kids' 3–5-minute lessons mixing interaction types reportedly raised completion ~50%.
- **Failure handling**: kids miss subtle feedback entirely (NN/g Panda Restaurant test), prefer direct-manipulation fixes (eraser over undo); Toca Boca/Sago Mini ship *zero* failure states. Wrong answers need exaggerated-but-kind reactions + immediate re-demonstration; after 2 misses the character does it and the child copies.
- **Progress must be concrete**: an NN/g 7-year-old repeatedly asked "What does this 2 mean? It's annoying!" about a bare counter. Duolingo's 2022 single-linear-path redesign measurably improved beginner completion by killing choice overload.
- **Color-blindness**: ~8% of boys are red-green CVD — never encode note length by color alone (length is already spatial; reinforce with glyph/pattern).
- **COPPA + UK ICO Children's Code** (binding on this UK app): the compliant *and* UX-correct choice is localStorage progress with no account, no sign-up nudges aimed at children.

**Top patterns to steal**: KAK 3–5-min auto-advancing lessons + sparkles-into-persistent-collection, language-free; action-praise scripting ("you made that note last two beats!" not "you're smart"); Duolingo single path with the child's character standing on it; Sesame guidelines (tap universal, show where to gesture, accept partial gestures, snap to intent); reward-as-playback (own pattern + full arrangement = the finale of every lesson); parent controls behind an adult-difficulty gate; token-then-place note-length input.

**Top pitfalls**: drag-as-only-length-mechanic; text for years 1–3; audio-only instructions; glow-as-teaching; blocking celebrations (keep 1–2s); abstract counters; one register for 5–11; login walls; small targets; multi-touch anywhere; error text/buzzers; decorations that don't respond to taps (kids judge them broken).

## 5. Notation bridge

**Sharpest findings**
- **"2 cells = twice as long" is the destination of instruction, not a starting intuition** (Bamberger): children read figurally; the grid needs an explicit pulse reference (heartbeat row) to teach duration rather than placement.
- **Kodály beat charts ARE the grid**: hearts/boxes for the steady beat with rhythms placed inside — make that identity explicit with a pulsing heart row under the grid; stick notation is the standard intermediate written form.
- **Color evidence is two-edged**: Rogers 1996 (134 first/second-graders, 23 weeks) — colored *rhythmic* notation helped read colored notation (p<.05) but gains did NOT transfer to uncolored; Rogers 1991 (92 beginners, 12 weeks) — pitch color-coding created dependence, no achievement gain, worst for LD students. Color must ship with a fade plan and colorless checkpoints.
- **The Synthesia lesson**: falling-notes fluency = "following lights", not reading; expert sight-readers look 6–7 notes ahead. Grid→stave display alone won't teach reading — the course needs stave→grid *construction* tasks and "clap it before you hear it" audiation.
- **Faber Primer's pre-staff staging**: real note-value glyphs floating off-staff for half the book ("safety... unfettered by busy lines"); a one-line rhythm staff (standard for unpitched percussion) precedes 5 lines. Pitch+rhythm+clef at once is the documented overload.
- **MusicFirst Rhythm Grids' three-skin ladder in one interface**: blobs → sticks → standard notation on the same grid — one data model, three renderings keyed to scaffolding level.
- **Fused glyph-on-block** (gorhyme Rhythm Notation Sequencer): the note glyph drawn on the block spanning its cells — the symbol literally occupies its duration.
- **Proportional stave spacing tested null for trained readers, but small-chunk segmentation (1–8-beat units with white-space gaps) significantly *improved* sight-reading, and one-phrase-per-line *worsened* it** (Scientific Reports 2019, 21 conservatoire percussionists). Use proportional spacing as a grid-alignment device (noteheads vertically over their columns), chunk the stave into beats/bars.
- **Sibelius Groovy Music** (Shapes 5–7 / Jungle 7–9 / City 9–11): the canonical icon-to-notation product for this exact age band — "see YOUR piece as real notation" as the hook. Positioning writ large: "Song Maker, but it teaches your students to read what they made" (CML lesson plans do the grid→paper-notation transfer manually).

**Top patterns to steal**: heartbeat row; glyph-on-block; three-skin ladder; pre-staff → one line → five lines; 1:1 vertical grid/stave alignment with shared playhead; sound-before-symbol micro-sequence; "you wrote real music" reveal of the child's own creation; per-level view states (grid only → grid+stave → stave-prominent → stave only); reverse-direction reading tasks; colored durations with planned fade; beat-strip dictation games ("Deal-a-Rhythm").

**Top pitfalls**: assuming proportional perception; grid-only fluency (passive stave = decoration); color-coded pitch; color without fade-out; expecting spacing alone to teach; chunks too big; full staff+clef+pitch+rhythm simultaneously; skipping informal/figural representation entirely; one duration-view for all of 5–11.

## 6. Progression UX

**Sharpest findings**
- **Duolingo killed its branching tree** for one linear path because learners couldn't tell whether to advance or grind; review nodes placed AHEAD reframe practice as forward progress (blog.duolingo.com).
- **Duolingo unit anatomy**: guidebook node → ~5 mixed-type lessons → mid-unit chest → unit review → optional harder "Legendary" replay. Maps to: unit = one note value; legendary = stave-only replay.
- **DragonBox is the notation-teaching blueprint**: zero algebra vocabulary at start; symbols gradually REPLACE pictures inside the same task from chapter one; one rule at a time; never name the concept until the behavior exists. Its documented weakness: children finish without transfer unless the formal-notation bridge is explicit — the child must *act on* the stave, not watch it.
- **ST Math's informative feedback**: a wrong answer plays an animation of the *consequence* (JiJi falls where the answer breaks), rewindable. The sequencer equivalent: play target then attempt with the playhead sweeping — the mistake is heard, not flagged.
- **Sesame Workshop's field-tested hint spec** (50+ studies): idle time-outs 6–8s in games → verbal+visual suggestion; wrong answers escalate exactly 3 tiers (encourage → restate goal + hint → highlight the correct answer and wait), optional auto-advance; instruction audio puts the action verb at the END ("To give Elmo a crayon, tap the X!"). Maps onto the app's existing pot idle-nudge pattern.
- **Self-serve hint buttons get abused** ("unproductive hint use" negatively associated with outcomes, LAK26); system-initiated, attempt-gated hints work better for low-prior-knowledge kids.
- **Harvard Reach Every Reader RCT** (240 preschoolers): feedback that NAMES the object ("You selected the green Plickatoo!") beat sounds-only and generic praise on accuracy; scaffolded gradually-increasing difficulty beat random ordering. So: "You made a loooong note — a half note, two boxes!"
- **IXL SmartScore is the anti-pattern**: asymmetric scoring (−3 to −8 per miss) documented to cause rage-quitting. Use small-N completion (~3 correct, not necessarily consecutive), misses cost nothing visible, progress only ever fills.
- **Daily streaks are flagged as harmful persuasive design for children** (5Rights "Disrupted Childhood"; U. Michigan) — use within-session completion chains + a growing collection (song shelf) instead.

**Top patterns to steal**: single linear path, review-ahead; DragonBox notation fade-in; audible-consequence feedback with "hear both again"; do-first-explain-after openers (Brilliant); the Sesame hint ladder with exact timings; concept-naming praise; adaptive drop-down to a simpler scaffolding-level variant on struggle (never the same task again — Khan Academy Kids); rewards ARE content (unlock instruments/drum styles, not coins — anti-Prodigy); worked-example fading; free play one tap from any lesson.

**Top pitfalls**: choice-heavy maps; math-as-toll meta-games; always-visible hint buttons; N-in-a-row with penalties; daily streaks; naming before behavior ("this is a crotchet" first); generic praise; audio-only prompts; long uninterruptible narration; random difficulty ordering; passively-updating stave; progress resets on error.

## 7. Gaps + follow-up findings

**Gaps** (the research stayed at design-principle altitude; two cross-cutting layers fell between dimensions): (1) **assessment algorithms** — no timing-tolerance windows by age, no grid-answer scoring scheme, no hold-duration thresholds, the single biggest build unknown; (2) **rests** — pedagogy placement clear, but no digital mechanism for intentional-rest vs empty cell; (3) **dotted notes/ties/3-4 meter** — curriculum position only, zero teaching mechanisms; the learning grid is fixed 8 columns of 4/4; (4) **grid semantics** — what one cell should MEAN per band (1 cell = 1 beat vs 1 eighth) is unresearched but shapes every lesson; (5) lesson tempo for duration perception (levels lock tempo at 90; whole note at 60 BPM = 4s vs piano trim 6s); (6) one adaptive course vs banded tracks, and how a child is placed into a band; (7) audio-instruction production (TTS vs recorded, iOS audio unlock); (8) persistence vs Safari ITP + shared classroom iPads; (9) classroom vs home deployment context never resolved (incl. muted classroom tablets); (10) no way to verify transfer off-app.

**Follow-up research answered most of these:**
- **Timing windows**: children's tapping CV ~0.20 at 5–6 vs ~0.07 adult; mean asynchrony *negative* (~−81ms — kids tap early; Carrer et al. 2023, N=305). Use beat-proportional, age-banded, early-biased windows: ~±33% of beat at PYP1–2 → ~±15% at PYP4–5; **no live-tap grading below ~age 7 at all** — grade untimed placement and perception instead. Rhythm-game windows (±15–40ms) are 3–10× too tight.
- **Motor-free mastery checks for 5–7s**: Gordon PMMA/IMMA same/different rhythm pairs (tap a picture) and cBAT ("is the puppet tapping with the music?") — validated, machine-gradable, zero timing machinery.
- **Scoring**: SmartMusic's green/red noteheads displaced left/right for rushed/dragged (adopt on the stave panel); Rhythm Lab separates onset grading from opt-in duration checking, margins scaling with tempo AND note value; Toussaint cyclic/swap edit distance — test constant-shift alignment first and return "right pattern, you started late". Hold-to-duration: quantize to nearest cell count with generous boundaries, feedback in beats not ms; exact constants must be prototyped with kids.
- **Rests**: Rhythm Cat grades tap-during-rest as the error; Rhythm Swing pairs each rest glyph with its note value level-by-level; Kodály freeze game before the glyph; "shh" fills the silence — bridge only. Empty-cell-as-meaningful is the established pattern; no product uses placeable rest tokens.
- **Dotted/meter**: the Heart Chart uses foam note pieces spanning 3 hearts — the 3-cell block IS the dotted-half lesson, never explained as arithmetic; 3/4 = re-grid to 6-cell bars (Song Maker precedent), skip circular views (conflict with left-to-right stave reading); ties render on the stave only.
- **Narration**: recorded human voice beats TTS for children (comprehension/retention deficits, worst for struggling readers); one instruction per clip, ≤10 words, ~110–140wpm; package as a mono AAC audio sprite with JSON offset map — the same container pattern as drums.pack/melodic.pack. UK fork: crotchet/minim/semibreve mandated by the English Model Music Curriculum vs quarter/half/whole in IB material — defer naming via ta/ti-ti for the youngest, make terminology a toggle swapping narration clips.
- **Audio unlock**: the iOS hardware silent switch mutes Web Audio but NOT `<audio>` elements — a lesson "Start" button should resume AudioContext + run the swevans/unmute silent-mp3 trick + play the first clip.
- **Persistence**: Safari ITP wipes all script-writable storage after 7 Safari-use days without a visit (every school holiday = progress wipe). Three-layer defense: add-to-home-screen prompt after lesson 2 (exempt), printable QR progress cards (the app already has a scanner + print; matches Clever Badges practice; COPPA/ICO-clean because anonymous), Firestore mirroring for logged-in households.
- **Retention**: streak evidence is adult/industry-sourced; strongest causal child evidence is adult-loop-driven (weekly parent alerts reduced course failures 28%, Columbia). Build teacher/parent weekly cadence + a take-home artifact, not push/streaks. No published data exists on classroom-vs-home or muted-device usage for browser music tools — instrument lessons from day one (audio-unlocked?, installed?, session origin) and measure it yourself.
