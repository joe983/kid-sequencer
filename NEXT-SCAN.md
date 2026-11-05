# Worksheet scanner — state, open work, and how the numbers were arrived at

Everything in the scan pipeline was tuned against **measured scan logs from a
real printed sheet**, not by eye. This file records what those logs said, so the
constants can be re-opened against evidence rather than by feel.

Run the fixtures: `node serve.js`, then open <http://localhost:3000/scan-tests.html>.
Machine-readable results land in `window.__scanTests`. The page is hosting-ignored
(see `firebase.json`), so it is committed but never deployed.

---

## ⚠️ OPEN — do this after the sheet is next reprinted

### 1. Print the corner marks as a RING, not a solid square

**Status: the SCANNER half is done and shipped. What remains is the print flip,
which needs a reprint to verify — that is the only reason it is still open.**

To do it, in one sitting with a printer to hand:

1. `PRINT_MARK_SHAPE = "ring"` in index.html (the CSS and the wall thickness are
   already written; the constant is the whole switch).
2. **Bump `PRINT_MARK_K` from 0.56 to ~0.9.** At 0.56 the mark lands ~6px across
   in the 420px working frame, giving a hole of ~2px that will not survive blur
   or JPEG. ~0.9 gives a ~10px mark and a ~4px hole. Fixture `ringSmall` covers
   the small end and passes by falling back to the solid path, but that is a
   safety net, not the target.
3. Print, scan, and check the log says `pool ring` rather than `pool solid`.
4. Re-run `scan-tests.html`; `ringMissingBL` should keep refusing.
5. Add the printed sheet's frame to `public/scan-fixtures/` as the first real
   ring evidence — every fixture with a ring today is synthetic.

The scanner already accepts BOTH shapes and **prefers rings**: when four ringed
candidates exist they are the only ones considered, otherwise the solid path runs
exactly as before. That back-compatibility is not optional — every sheet already
printed carries solid marks.

Two things learned building it, both worth keeping:

- A ring's solidity is exactly `1 − holeFrac`, so a 22% wall lands at 0.69 and
  the ordinary 0.70 floor threw the mark away *before* its hole was examined.
  Holes are therefore computed before the solidity decision, with a lower floor
  (`SCAN_RING_SOL_MIN`) for blobs that have one.
- The first thresholds (hole ≥ 6% of bbox, ≥3px) were far too permissive on real
  photographs: camera noise punched a **three pixel** hole in a 7×7 blob, which
  then qualified as a ring, took the top-left corner from the real mark 40px
  away, and misregistered the grid. Caught only because the real frames are in
  the fixture suite. A genuine ring's hole is 16–31% of its box, so the bars are
  now 12% and 6px.

**The underlying problem this closes.**

If a mark is smudged, cut off or obscured, the corner-most search promotes the
next blob inwards. On three of the four corners that self-destructs — the quad
collapses or the aspect goes out of band. Losing the **bottom-left** one does
not: a printed **tool icon** stands in, and every downstream test still passes.

| | measured |
|---|---|
| genuine angled scan (fixture `askew2`) | aspect **1.497** |
| impostor quad, BL mark missing (fixture `missingBL`) | aspect **1.55** |

3.5% apart. Aspect is simply the wrong instrument, and squeezing the band to fit
would start refusing good scans — the wrong trade, since a refusal costs a retry
whereas a false lock silently replaces the tune the child made with noise.

Today `missingBL` is caught **only** by the grid-registration check
(`_gridRegistration`), which re-samples the printed grid lines and confirms they
landed where `SHEET_GEOMETRY.grid` predicts. That works, but it is one test
standing between a wrong lock and a garbled import.

**The structural fix:** print each mark as a ring / concentric square instead of
a solid one. Solidity then separates marks from every solid icon on the sheet in
a single test (`SCAN_MARK_SOL`), because nothing else printed has a hole in it.
Most of the delicate threshold work below stops carrying weight.

Requires a reprint, so it was deferred — the sheet in hand at the time could not
be reprinted. **When the sheet is next reprinted, do this first**, then:

- retune `SCAN_MARK_SOL` to select for the ring (expect solidity ~0.4-0.6 for a
  ring vs ~0.9+ for a solid icon — the test likely INVERTS)
- re-run `scan-tests.html`; `missingBL` should then fail for the right reason
  (no fourth mark found) rather than relying on registration
- consider relaxing `SCAN_QUAD_TOL` back toward 1.2 once marks are unambiguous

### 2. Light colouring

A square is filled at 0.16 AVERAGE DARKNESS (Round 8; it was an ink count at
0.20, then 0.15; first 0.14). Real pencil on iPad and iPhone measured 0.23-0.49, empty
squares 0.00-0.11. There is no taper rule any more. Colouring much fainter than the
lightest pencil measured (0.23) will be missed — the options are "colour it in
firmly" on the sheet or a lower bar, which trades against grainy-iPad empties.

---

## Round 8 (2026-11-04) — judge squares on average darkness, not an ink count

**Symptom (first live iPhone scans after Round 7).** The 5-row sheet's four-square
pencil bar read whole on the iPad but as 2+1 on two iPhone scans, and a later iPhone
portrait scan read a single square as a pair (`0:0+2`).

**Two wrong fixes first.** (1) Loosening the per-pixel ink test (`SCAN_FILL_RATIO`
0.70 -> 0.78) made the light iPhone squares read 0.66 instead of 0.17 in emulation,
but the iPad's grain and the blurred halos of printed lines then read as ink: one iPad
scan returned 9 notes for 4. Reverted (`ad7efab`). (2) I had only emulated the
iPhone's softness, not the iPad's grain — see the rule below.

**What fixed the diagnosis: per-square numbers in the report** (`67bc165`: `read.ink`,
`read.dark`, `fill`, `noise`, `cam`, `orient`). On the iPad the same four pencil
squares read 90/94/43/76 on the ink count but 34/34/30/33 on average darkness; the iPhone
81/62/28/68 vs 35/31/26/32. The invented `0:0+2` was an ink count of 10% (the taper
rule's floor) on a square whose average darkness was 3%.

**The decision now.** `_scanNotesFromFrame` computes, per square, the mean of
`max(0, 1 - lum/localMean)` over a 10x10 grid in the window (`darkMap`) and fills a square at
`max(SCAN_DARK_MIN 0.14, blank + SCAN_DARK_MARGIN 0.10)`. Averages survive both soft
and grainy pictures where a yes/no count does not. The taper rule (`SCAN_FILL_EXTEND`,
core window) is gone. The ink count is still computed for the report and the join fallback.

**Measured.** Owner photos x emulations (720 clean, 480 soft, 480 softer, 360, and 640/480
with added grain sd 18-30 lum and a 35% shading gradient): weakest coloured square 0.25-0.40,
strongest empty 0.08. Live reports: empty 0.00-0.09, coloured 0.23-0.49. Stress 140/140
correct, 0 wrong in 1,400; scan-tests 124/124 (three synthetic scribbles restated at the
faint end of REAL pencil, 9-11 strokes, because 7-8 read 0.13-0.16 — fainter than any pencil
measured; the July frames now also read their faint r6c6).

**Follow-up (2026-11-05).** 12 live scans, all correct: coloured 0.25+, empty up to 0.11
(the 8-row sheet's bottom row, landscape) -> bar 0.14 -> 0.16. The grain emulation also
showed an older fault: with heavy grain the WRONG way up could pass every check at
registration ~30 against ~80 for the right way, and the beat-1 badge tiebreak (grain makes
the empty badge window look inked) then picked it, giving wrong notes. The badge now only
settles a NEAR tie (`SCAN_TURN_TIE` 0.65; the 3-note sheet's real tie is 39/48 = 0.81).
Three repeated grainy runs: no wrong-way reads. The July frames' faint r6c6 (0.14-0.15)
is back to "may be missed, never invented".

**A button standing in for a hidden ring (2026-11-05, iPad portrait, sat at a table).**
Three scans of the /02 sheet (photo 3) in a row read wrong notes, upside down and a row
out. All three picked a "bottom-right mark" ~40 px above the real one and 0.65 of the
other marks' size: the round AI button just above that corner. With only three rings
visible the pick falls back to the solid pool, where the button (a solid disc in soft
video) is the corner-most blob; the twisted grid then fitted the turned template better
(31 vs -27, 82% column lines) and passed. New refusal `marks-mixed` (hint "Show corners"):
when some picks are rings and some aren't, a solid pick SMALLER than the rings
(`SCAN_STANDIN_REL` 0.9) is a stand-in. Blur also closes real rings, but a ring closed
by blur gets bigger (167-194 px vs 90-124 for its neighbours), and every stand-in
measured 0.36-0.65 — refusing every mixed pick broke the blurred-3-note fixtures.
Reports now print `ring` on each picked corner and the pool. Not reproduced from a
real iPad frame (no photo upload yet): the fixture hides the ring on the printed sheets.

**6/8 time is switched off (`SHOW_TIME_68 = false`, 2026-11-05, owner: "temporarily").**
Only the /02 time-signature button changes: it cycles 4/4 <-> 3/4. The unlinked
`/02?time=68` page, the 6/8 sheet geometry, the scanner's 3/4-vs-6/8 reading and the
fixtures are untouched, so setting the switch back to true restores the third stop.

**Rule: before pushing any change to how a square is judged, test it on a GRAINY picture and
a SOFT picture of the owner's photos** (`ratio.mjs`/`grade.mjs`-style harness: downscale, blur,
JPEG, add noise, stretch to 720), not just one.

---

## Round 7 (2026-11-04) — the template never matched the print

**Symptom.** On the owner's iPhone, the 8-row sheet kept dropping one pencil
block (row 3, columns 5-6), and an earlier scan of the same sheet invented
three notes. The same sheet photographed still failed to lock at all
(registration 3, needs 20). Owner photos of all five printed sheets are the
evidence for everything below.

**Cause — three geometry errors, found by drawing the template over the photos:**
1. `cellFrac: 0.72` on every sheet. The print is a 64px square with a 4px gap
   (78/4 on the five-row sheets, 140/4 on the 3-note sheet), i.e. 0.94-0.97.
   The template put a quarter of every square in the "gap". The cell window
   therefore sat on each square's left border, and **every empty square read
   0.17 against a 0.20 bar** — the invented notes, and the reason a real light
   block (reading 0.1-0.2) could not be told from an empty one.
2. The grid box has 15 gaps across, not 16; the slots drifted right by most of
   a gap by column 16. `_gridMapper` now scales slots by C/(C - gapFrac).
3. "kidseq:main"'s vertical insets were out of date by ~0.1 row each end
   (0.20202/0.83115 vs `printMarkInsets()` 0.20951/0.82240). The old
   "~0.008 disagreement" caveat was this. The July frames (real-01..05, with 4
   tool circles) are the OLD layout; every sheet printed since has 5 circles.

**And the line checks predicted lines at slot boundaries** — the paper gap
beside a border. Registration now samples border centres (`_gridLineAt`) with
one camera pixel of tolerance across the line. Tried and rejected on the way:
the darkest point across the whole border|gap|border strip (wrong templates
found lines too: 16 one-corner-covered stand-ins read wrong), and sliding the
whole template to the best registration (it moved the reading window; a 4-cell
run split).

**Reading changes, each measured on the 5 photos + 10 frames + fixtures:**
`SCAN_CELL_INSET` 0.10 (window clear of the border; 0.15 lost a tapered run's
first cell, 0.04 misread photo 3), `SCAN_CELL_SAMPLES` 6→10 (36 points measured
1px strokes by luck: 0.08 vs 0.47 for a sub-pixel move), `SCAN_FILL_MIN`
0.20→0.15, `SCAN_FOUR_RMS` 0.26→0.22 (correct reads now ≤ 0.207, the stand-ins
that slipped through 0.230+). Joining: neighbours stay ONE note unless the real
4px gap between them reads clearly white (`gapJoined`, `SCAN_GAP_WHITE` 0.6 —
brightest pixel within 1 camera px of the gap centre, darker quarter of the rows).
Coloured across: the owner's photos ≤ 0.40. Coloured separately: renders 0.38-1.38,
median 0.84, so most separate pairs now split; the rest join, as every pair did
before (the old window sat on the square's own edge). `extendAt` is floored at
0.10, and a run made only of extended cells is dropped.

**Result:** the 5 photos read exactly what is on the paper at 720/480/360 px;
stress test 140/140 uncovered correct (was 130 + 10 refused), 0 wrong in 1,400
covered; scan-tests 123/123 (two expectations restated: the synthetic "beat
pair" had a fake 28% gap; real-02/03's faint r6c6 → subset).

---

## What the logs actually said

Four rounds against the same printed sheet. Each fix below replaced a guess with
a measurement.

### Round 1 — the scan "worked" but read almost nothing

`dark 0.4-1.4%`, lock 3/3, aspect 1.447 (nominal 1.438) — the marks were found
correctly. But `notes 1`, and the cell map was a wall of marginal values. Two
findings:

- Marks measured `fa 0.00020-0.00042` against a **0.0004** size floor. The
  detector was discarding the very things it was hunting for: `rej small fa
  0.00039 ar 1.14 sol 0.93 @358,54` sits exactly where the top-right mark is.
  103 consecutive frames were rejected before one scraped through.
  → floor **0.0004 → 0.00008**, carried by a solidity floor of **0.70**
  (real marks 0.93-1.00, clutter 0.13-0.60 — the cleanest split in the data).

### Round 2 — a shadow, and the same bug in two places

`dark 18.8-28.5%` (vs 0.4-1.4% when it worked), 400-600 blobs, candidate
solidity 0.13-0.55, quads collapsing to `minSep 0` or coming back impossible
(`aspect 0.679`, `skewH 3.51`).

Both stages compared pixels against **one whole-frame statistic**. A shadow over
one corner drags the frame mean down and paper on the lit side stops separating
from ink on the dark side.

→ `_lumField()`: a summed-area table, so every pixel is judged against the
average brightness of its own neighbourhood at 4 lookups regardless of window
size. The window is ~1/8 of the frame — several cells across, five times a mark —
because a window near the size of the thing being detected lets that thing darken
its own reference.

**Fixing the mark detector immediately exposed the identical bug in the cell
reader**, caught by the shadow fixture: whole shadowed rows read as coloured in
(`0:0+13 1:0+12 …`). Same fix applied there.

### Round 3 — false locks at the frame edge, and bad fixtures

Every false lock picked points hard against the border — `y=1..3`, `y=312..313`
of a 315-tall frame, `x=1`, `x=413` — while the session that genuinely worked
picked `63,56 / 359,53 / 377,262 / 56,273`, all well inside. **The sheet was
overflowing the frame**; the marks were cut off.

Worse, one frame returned `ok` and imported garbage silently.

- A printed mark always has paper around it → blobs clipped by the picture edge
  are rejected (`SCAN_MARK_EDGE`).
- `SCAN_QUAD_TOL` **1.6 → 1.12**. The old band accepted 0.707, 0.836, 0.903,
  1.059, 1.758, 1.763, 1.765 — it was not a check.
- New `marks-not-outermost`: the marks bound the whole sheet, so mark-like ink
  *outside* the quad means the wrong four were picked. Only blobs of mark-like
  SIZE get a vote (`SCAN_OUTSIDE_MIN_REL`) — a crumb should not veto a scan, and
  one did.

**The fixtures were as much at fault as the code.** Every synthetic sheet was
four marks and three cells on white — `dark 0.3%`, where real frames report
11-22%. They were passing a test the real input never takes. The builder now
prints the grid, title block, tool icons and tempo box, and immediately caught
the tool-icon false lock that bare fixtures could not see.

### Round 4 — a note came back a cell short

Owner reported a missing square on the bottom row. It was the **leading** cell of
a four-cell run, not the trailing one — a hand-drawn stroke tapers where it
starts:

```
col:   8     9     10    11
ink:  0.14  0.75  0.86  0.64      bar 0.20
```

Lowering the bar to 0.14 is not available: a half-pixel registration error puts
**0.17** of grid-line bleed into every cell, which trades one missing square for
whole-sheet garbage.

→ `SCAN_FILL_EXTEND`: a cell TOUCHING a filled one is held to half the bar. It can
only extend an existing run, never invent a note, and neighbours are tested
against the ORIGINAL decisions so faint cells cannot cascade.

### Round 5 — note lengths the app cannot place

The scan emitted whatever run length it measured, so three coloured cells became
a 3-column note. There is no such note: the palette is 16th/8th/quarter/half/whole
= **1/2/4/8/16** columns at `COLS_PER_BEAT=4`.

→ Round, don't split. Splitting a 3 into an 8th plus a 16th keeps the duration but
turns one coloured block into two attacks — the child hears two notes where they
drew one. Block-to-note correspondence is the part they can see, so it is the part
to preserve. It also degrades better at the top: 15 cells becomes one whole note,
where splitting would give 8+4+2+1.

Nearest is measured on a **log** scale because note lengths are geometric — the
quarter/half boundary is at 5.66 columns, not 6. Ties go up. A note may grow into
blank cells but never over its neighbour and never past the bar end.

### Round 6 — the fixtures earned their keep on day one

Committing the suite immediately failed a case that every ad-hoc run had passed:
`marks5`. Marks 5px and 7px across read a single coloured cell as **two** notes;
4px, 6px and 10px read it correctly.

Odd mark sizes put the drawn square's centroid half a pixel off where even sizes
put it, so the detected quad — and with it the whole grid mapping — sits half a
pixel out. That is enough for a filled cell to **spill into its neighbour's
sample window at 0.17**, and the round-4 taper rule extended straight into it.

The trap: 0.17 of leakage and the 0.14 of a genuine tapered end are the same
magnitude, so **no threshold separates them**. What separates them is where the
ink sits — leakage hugs the edge shared with the coloured cell, a real stroke
crosses the middle. The taper rule is now judged on the middle half of the cell
(`coreU`) rather than the whole of it.

Worth stating plainly: this was a real bug shipped in round 4, invisible to five
rounds of hand-testing, found within minutes of the fixtures being written down.

---

## Feeding the REAL print output to the scanner

Every fixture in `scan-tests.html` draws an *approximation* of the sheet from the
geometry constants. The actual print path had never been fed through the scanner,
which leaves an obvious hole: the fixtures cannot disagree with the constants
they are built from.

The real sheet can be produced with no printer:

```bash
# 1. serve the app:  node serve.js
# 2. TEMPORARILY neutralise the portrait fallback in styles.css, or headless
#    Chrome evaluates print `orientation` as portrait, rotates the stage, and
#    clips the page (confirmed — it is not a theoretical warning):
#       @media print and (orientation: portrait) and (min-width: 99999px) {
# 3. print (a --user-data-dir is required or nothing is written):
chrome --headless=new --disable-gpu --no-sandbox --no-pdf-header-footer \
  --virtual-time-budget=10000 --user-data-dir=<tmp> \
  --print-to-pdf=<tmp>/sheet.pdf http://localhost:3000/
# 4. rasterise (PyMuPDF):  fitz.open(pdf)[0].get_pixmap(dpi=200).save(png)
# 5. RESTORE styles.css
```

Result: A4 landscape, one page, all four marks present.

**What it proved.** Fed through the scanner, the mark quad measures aspect
**1.435 against the stored `quadAspect` of 1.438** — 0.2% apart, from the real
print path rather than a hand-drawn approximation. The print geometry and the
scanner's expectation genuinely agree.

**What it could not yet prove, and why.** The registration check scores 5 against
a floor of 20 on this render, while real photographs of a printed sheet score
41–115 on the same code. That is a fidelity problem in the render, not evidence
of misregistration: the printed cell outlines are hairlines at 2339px, and
scaling the page down to a 420px working frame with `drawImage` averages them to
near-paper grey, so the registration sampler finds nothing to measure. A real
camera blurs but preserves contrast. Making this a usable fixture needs the page
rendered closer to the working resolution (or sharpened on the way down) so the
grid lines survive — do that before trusting any registration number from it.

Also beware: measuring "where the grid is" by projecting dark pixels between the
marks does NOT measure the note grid. It measures the bounding box of every
printed thing — top bar, tools column, bottom instrument row — and reports a
drift of ~1.9 cells that is entirely the furniture. Isolating the note grid needs
the 16x8 periodicity, not the ink extent.

## Tuning levers

| constant | value | set by |
|---|---|---|
| `SCAN_LOCAL_K` | 0.75 | fraction of local brightness that counts as ink |
| `SCAN_MARK_MIN` / `_MIN_PX` | 0.00008 / 9 | real marks measured 0.00020-0.00042 |
| `SCAN_MARK_SOL` | 0.70 | real marks 0.93-1.00 vs clutter 0.13-0.60 |
| `SCAN_MARK_EDGE` | 2 | a whole mark always has paper around it |
| `SCAN_MARK_SPREAD` | 3 | four marks print at ONE size |
| `SCAN_OUTSIDE_MIN_REL` | 0.4 | a speck must not veto a lock |
| `SCAN_QUAD_TOL` | 1.12 | genuine 1.412-1.497; false 0.707-1.765 |
| `SCAN_FILL_RATIO` | 0.70 | cell ink vs local paper |
| `SCAN_FILL_EXTEND` | 0.50 | tapered run ends measured 0.14 against a 0.20 bar; judged on the cell CORE so neighbour leakage cannot trigger it |
| `SCAN_GAP_JOIN` | 0.50 | inter-cell gap inked ⇒ notes merge |

## Diagnostics

`?scandebug=1` (this browser tab only, 30 min — never stored on the device, 2026-11-05) puts a panel on screen reporting why every frame was
refused and with what numbers, plus `send` to upload the log and the camera frame
to Firestore under `users/{uid}/scanlogs`. See the "Scan diagnostics" section of
CLAUDE.md. Keep it: three rounds of guessing produced nothing, and every fix
above came from a number this panel printed.

## Fixture gotchas

- **Do not stack test runs at the same start column across many rows.** That
  builds a solid vertical block of ink which genuinely defeats local
  thresholding, and interior cells stop registering. It is a pathological
  fixture, not a real sheet — measure one run per image.
- **Alpha is the wrong model for faint colouring.** An alpha-blended cell has no
  pixel dark enough to register at all. Real faintness is SPARSE full-strength
  ink — use the `scribble` option.
- **A run only merges into one note if the colouring crosses the gaps** between
  cells, which real scribble does and a per-cell generator does not.

## ⚠️ /02 and /03 sheets are measured but NOT paper-verified (2026-09-05)

The five-note (`/02`) and first-notes (`/03`) views now print and scan their own
sheets, `SHEET_GEOMETRY["kidseq:main5"]` and `["kidseq:main3"]`. Their insets and
`quadAspect` came from `printMarkInsets()` plus a mark-quad read, both taken in
one pass on one machine — **no printed sheet has been photographed and scanned
back yet.** Do that before trusting them the way `kidseq:main` is trusted.

**The reason to be careful.** On the SAME instrument, `kidseq:main` measures

| | u0 | v0 | u1 | v1 | aspect |
|---|---|---|---|---|---|
| committed (production-verified) | 0.07425 | 0.20202 | 0.95248 | 0.83115 | 1.438 |
| `printMarkInsets()` today        | 0.07425 | 0.20939 | 0.95248 | 0.82296 | 1.403 |

The horizontal insets agree to five decimal places; the vertical ones are ~0.008
apart and the aspect 2.4% low. **This predates the /02+/03 work** — unmodified
`main` at `?v=81` measures byte-identically to the branch that added them, so it
is not a regression, and it is not measurement noise either: repeated calls, a
fresh load, a 1440x900 viewport and `await document.fonts.ready` all return the
same numbers. Ruled out so far: stale marks inflating the content box, first-call
vs later-call state, viewport size, web fonts (the app uses none), and
`@media print` hiding `#beatHeader` (it doesn't).

So whatever produced the committed values is not what `printMarkInsets()` reports
now, and the two new templates were measured with the reporting instrument. They
very likely carry the same ~0.008 vertical bias. That is inside what the pipeline
tolerates in practice — `kidseq:main` has been scanning real sheets correctly
with exactly that disagreement — but it is unproven for a sheet nobody has
printed.

**To settle it:** print one `/02` and one `/03` sheet, photograph each, and run
them through `?scandebug=1`. If `grid-misregistered` fires or the registration
score sits near `SCAN_REG_MIN`, re-derive that template's `v0`/`v1` from the
photograph rather than from the DOM. Commit the frames to
`public/scan-fixtures/` and add them to the REAL block in `scan-tests.html`,
which is the only part of that suite that has ever caught something the
synthetic sheets agreed with.

Related open item: the ring-mark reprint above needs a printer too — do both in
one sitting.

**Third template, same caveat (2026-10-07):** `/02?time=34` (3/4) prints and
scans its own 12-column sheet, `SHEET_GEOMETRY["kidseq:main5_34"]`. Measured in
headless Chrome at 1600x900 in one run with `/02` and `/03` as controls — both
re-read within 0.0006 of their committed values, so the 3/4 numbers sit on the
same footing as theirs. A headless `printToPDF` of the sheet shows the marks clear
of the content and a mark-quad aspect of ~1.476 against the committed 1.477. Not
paper-verified: print and scan one alongside the /02 and /03 sheets. `_currentSheetId`
picks it by time signature (`TS_SHEET_ID`), and `_routeScannedNotes` now matches on
view AND time signature. Note its aspect (1.477) is within the aspect tolerance of
the full sheet's (1.438), so only `grid-misregistered` separates the two if a full
sheet is scanned on the 3/4 page.

**And a fourth: `/02?time=68` (6/8), `SHEET_GEOMETRY["kidseq:main5_68"]`.** Same 5x12
grid and the same number of tools as 3/4, so it measured identical to 3/4 in the
same run; it exists as its own id so a scan routes back to 6/8 and so the reader
accepts 6/8's dotted lengths — `_legalNoteLens(geom)` now takes the SHEET and adds
6 and 12 for a 6/8 one (a coloured 6-run is the dotted-quarter beat; rounding it
to 4 or 8 would knock it off the beat). On the 6/8 page `_snapScanToBeat` lets a
quarter start on any 8th inside a beat. Fixtures: 5 cases, 77/77.

**Known limit found while writing them (pre-existing, every template):** two
coloured runs that TOUCH on one row, with the printed gap between them left white,
read back as ONE note — e.g. on `/02` 4/4 a quarter then a quarter comes back as a
half (`{runs:[[2,0,4],[2,4,4]]}` → `2:0+8`). Separate single squares split fine.
Not yet investigated (reader bug vs fixture artefact); tracked as T-012.
