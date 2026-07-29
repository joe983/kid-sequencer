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

**This is the one real gap in the scanner, and it cannot be closed in software.**

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

The fill bar sits at 0.20 ink. The faintest square measured on a real sheet was
0.39, and a tapered run end came in at **0.14** — under the bar, which is why
`SCAN_FILL_EXTEND` exists (a cell touching a filled one is held to half the bar).
A child colouring faintly in pencil could still fall under. Either accept it, or
print "colour it in firmly" on the sheet. Not a code fix.

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

`?scandebug=1` (sticky) puts a panel on screen reporting why every frame was
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
