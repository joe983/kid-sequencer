# Five-note (C–G) beginner view + view toggle

## Context

The sequencer's 8-row grid (C4–C5) is a lot of choice for a very young child. This adds an
**alternative view showing only five notes, C–D–E–F–G**, with correspondingly bigger rows, and
draws the **note-length notation icon inside each placed block** so the child sees the ♩ / ♫ /
𝅗𝅥 they chose. A small button below the note-length circles switches between the two views.

Everything else stays: drums, instruments, rhythms, tempo, key picker, volume, pots, save/load,
AI, scan, login, 16 columns, all five note-length tools. This is **not** a `?level=N` learning
level — it is the full app with a shorter grid.

### The structural insight this is built on

**The 5-note view is exactly the bottom five rows of the existing grid.** `freqs`
([index.html:553](public/index.html:553)) is indexed top-down, so C–D–E–F–G are already model
indices 7,6,5,4,3, displayed top-to-bottom as G,F,E,D,C. Consequences, all free:

- `rowColors[3..7]` = `#3DA9FF #00FF00 #FFFF00 #FF8C00 #FF0000` — blue/green/yellow/orange/red,
  C=red, the exact palette the existing lesson levels use.
- `SCALES[key]` is reversed with index 7 = root ([index.html:576](public/index.html:576)), so
  `pitchFor(row)` needs **no change at all** — the key picker keeps working (G major → D C B A G).
- Save, cloud load, scan import and the AI payload all address *model* rows, so they need no
  change either.

So the feature is a **render/playback window over an unchanged 8×16 model**. No parse-time
`const` becomes mutable. `notesByRow`/`occ` stay 8 rows forever, which is what makes the owner's
"hide and restore" requirement fall out for free.

### Decisions already made by the owner

1. Notation glyphs appear **only** in the 5-note view; the 8-row grid's blocks are untouched.
2. Switching is **non-destructive**: notes on the hidden top three rows go silent and invisible,
   and return unchanged on switching back. Nothing is ever deleted.
3. **Print is hidden** in the 5-note view. `SHEET_GEOMETRY` and the scanner are not touched.
4. The toggle sits **below the note-length circles**, which shrink to make room.

---

## Approach

### State (insert after `rowColors`, [index.html:554](public/index.html:554))

```js
const FIVE_VIEW_ROWS   = 5;
const FIVE_VIEW_OFFSET = rows - FIVE_VIEW_ROWS;   // 3
const FIVE_VIEW_MAXCELL = 78;
const FIVE_VIEW_LS     = "kidseq_note_view";
const FIVE_VIEW_AVAILABLE = !LEARN_LEVEL;         // inert on ?level=N and ?lesson=
let _fiveNote = false;
try{ _fiveNote = FIVE_VIEW_AVAILABLE && localStorage.getItem(FIVE_VIEW_LS) === "5"; }catch(e){}
if(_fiveNote) document.documentElement.classList.add("fiveNote");
function viewRow0(){ return _fiveNote ? FIVE_VIEW_OFFSET : 0; }   // MODEL index of top visible row
function viewRowCount(){ return _fiveNote ? FIVE_VIEW_ROWS : rows; }
```

Must parse before `fitToViewport`/`buildGrid`/`tick`. With `_fiveNote === false` both helpers
return today's values, so **every 8-row expression is unchanged by construction, not by luck** —
that is the null contract, and it should be checkable by reading the diff.

**Convention: every function keeps taking MODEL row indices.** Only `buildGrid` and `_cellEl`
translate to a DOM child index. `onCellClick`/`canPlace`/`placeNote`/`smartPlaceNote`/
`deleteNoteById`/`applyNoteGeometry` need no changes at all, because `buildGrid` already closes
over `r` for `cell.onclick` ([index.html:3166](public/index.html:3166)).

### Cell size: 64 → 78

Derived, not guessed. `totalContentW = 302 + 16·cell` and `stageInner = 1572`
([index.html:1894-1896](public/index.html:1894)), so `cell ≤ 79.375`. 78 leaves 11px of
`--centerPad` each side.

⚠️ **`fitToViewport`'s own solve is 1px optimistic** — `outerPadding` is 24 where the real page
padding is 28, and `gridExtra` is 20 where the shell's padding+border is 32, so `maxCellByWidth`
returns 80. Today the `MAXCELL = 64` cap hides this. Do **not** raise the cap without also
capping at 78, or the layout overflows the stage by ~10px. Leave the solve's constants alone
(changing them is a needless null-contract risk); just cap.

The 5-row grid is *shorter* than today's despite bigger cells: 5×78+4×4 = **406** vs 8×64+7×4 =
540. Vertical room is not the constraint; horizontal width is.

### Glyphs derive from `note.len`, never from `note.kind`

This is the key simplification. `kind` is a learning-mode concept that is never set in the full
app, and routing glyphs through it would drag in five separate problems: `cloneState` drops
`kind` on undo, cloud save/load has no `kind` field, `_applyScannedNotes` forces a single kind,
`tick` line 3993 branches on `kind === "eighth"`, and the learning CSS at
[styles.css:2646-2653](public/css/styles.css:2646) would fire.

Instead build a lookup from the tool definitions themselves, after
[index.html:599](public/index.html:599):

```js
const NOTE_ART = {};
if(!LEARN_LEVEL) for(const t of toolSteps) NOTE_ART[t.steps] = { svg: t.svg || null, symbol: t.symbol || "" };
```

Keys are 1/2/4/8/16 — a total function over every width the tools can produce, `undefined` for
anything else (no glyph, no throw). The block shows **literally the artwork on the button the
child pressed**, and the two can never drift.

---

## Ordered steps

All line numbers are pre-edit.

### JavaScript — [public/index.html](public/index.html)

| # | Anchor | Edit |
|---|---|---|
| 1 | after `rowColors`, :554 | Insert the state block above. |
| 2 | after `toolSteps`, :599 | Insert `NOTE_ART`. |
| 3 | `cloneState()`, :798-804 | Add `kind: n.kind \|\| null` to the mapped note. **Pre-existing bug**: undo strips `kind`, so a lesson eighth loses its ♫ *and* starts playing full-length. One word, in the blast radius. |
| 4 | `fitToViewport()`, :1873 | `const vRows = viewRowCount();` → `Math.floor((availableH - (vRows-1)*GAP) / (vRows + hdrK))` |
| 5 | `fitToViewport()`, :1878 | `MAXCELL = (LEARN_LEVEL && LEARN_LEVEL.maxCell) ? LEARN_LEVEL.maxCell : (_fiveNote ? FIVE_VIEW_MAXCELL : 64)` |
| 6 | `buildGrid()`, :3148 & :3150 & :3183 | `noteLayerEls = new Array(rows).fill(null);` — loop `for(let i=0, r0=viewRow0(), n=viewRowCount(); i<n; i++){ const r = r0+i; …unchanged… }` — replace `.push(layer)` with `noteLayerEls[r] = layer`. Change the lesson beat-number guard `r === 0` → `i === 0` (equivalent today, honest tomorrow). |
| 7 | `redrawRowNotes()`, :3297 | `const layer = noteLayerEls[r]; if(!layer) return;` — this single guard makes every existing model-row caller safe; `redrawAllNotes` (:3259) then needs **no change**. |
| 8 | `createNoteBlock()`, after the `if(note.kind)` block :3283 | Add an independent `if(_fiveNote){ … }` block appending `<span class="noteGlyph" data-nv="<len>">` containing `NOTE_ART[note.len].svg` (as `innerHTML`) or `.symbol` (as `textContent`, plus class `txt`). Leave the existing `kind` block byte-identical. |
| 9 | `tick()`, :3962 | Window the `stepNotes` collection loop to `viewRow0() … +viewRowCount()`. **This one line is the whole of "hidden rows go silent"** — `stepNotes` is the sole source of `playInstrument` calls (:3988-3993) and of `_triggeredNotes` entries (:3967). Leave the sweep at :3971 and the `if(LEARN_LEVEL)` loop at :4025 alone. |
| 10 | `tick()`, :3995 | `noteLayerEls[r]?.querySelector(…)` — defensive; the array now has holes and this site has no guard (`_placePreset` at :6751 already has one). |
| 11 | new fn, near `clearGrid` ~:4392 | `setNoteView(v)` / `toggleNoteView()` / `_syncViewToggleBtn()`. Sets `_fiveNote`, toggles `html.fiveNote`, writes localStorage, updates the button's `aria-pressed`/`aria-label`/icon, then calls **`window.scheduleLayout()`** — never `fitToViewport()` directly ([index.html:7637-7645](public/index.html:7637) explains why). No `stop()` needed: `layoutPass` already rebuilds the grid on every resize with no play guard. |
| 12 | `_applySequenceData()` after the load loop :4453 | `if(_fiveNote && (d.notesByRow\|\|[]).some(n => n.row < FIVE_VIEW_OFFSET)) setNoteView("8");` — a loaded tune must never appear silently truncated. |
| 13 | `_applyScannedNotes()`, :5795 | Same: scanned sheets are always 8-row, so `setNoteView("8")` before applying. |
| 14 | `_cellEl()`, :6421 | `sequencerEl.children[r - viewRow0()]`. Lesson-only today (so a no-op), but leaving it stale is a landmine. |
| 15 | `_buildPrintMarks()`, top ~:7467 | `if(_fiveNote){ _printMarkBox = null; return null; }` — **Ctrl+P still fires `beforeprint` ([:7649](public/index.html:7649)) even with the button hidden.** Without this, a 5-row sheet gets corner marks whose insets don't match `SHEET_GEOMETRY["kidseq:main"]` — a sheet that *looks* scannable and isn't. With no marks the scanner refuses at `no-sheet`. |
| 16 | `printSheet()`, :7652 | `if(_fiveNote) return;` — `window.printSheet` is global. |
| 17 | `#tools`, :101-103 | Add `<button id="viewToggleBtn" type="button" aria-pressed="false" onclick="toggleNoteView()"></button>` as a sibling **after** `#toolsList`. |
| 18 | `window.KidSequencer.Sequencer`, ~:7686 | Expose `setNoteView`, `toggleNoteView`, `get fiveNote()`. Needed by the verification below. |
| 19 | :15 | `css/styles.css?v=71` |

**Icon**: two inline SVGs (`viewBox="0 0 32 32"`, no width/height, sized by CSS like the tool
SVGs) — five fat coloured bars for "switch to 5", eight thin ones for "switch to 8". Colour-coded
to the actual row colours, so it shows a pre-reading child what they'll get. Visual vocabulary
copies `#keyBtn` ([styles.css:1043](public/css/styles.css:1043)): 58×58, radius 16, `4px #1d1d1d`,
`0 8px 0` shadow, −1px hover / +2px active; lit state `#ffe14d` from `#staveBtn.active`, the app's
only existing `aria-pressed` mode toggle.

### CSS — [public/css/styles.css](public/css/styles.css)

1. **Circles 124 → 108, scoped away from learning mode**:
   `html:not(.learning-mode){ --toolBtnSize: 108px; }` plus
   `html:not(.learning-mode) #toolsList{ align-items: center; }`.
   ⚠️ The second rule is **required, not cosmetic**: `#toolsList`
   ([:1695](public/css/styles.css:1695)) has no `align-items`, and `.tool` has an explicit
   `width`, so a 108px circle defaults to flex-start and sits **left** in the 124px column.
   Scoping away from `.learning-mode` keeps `?level=` / `?lesson=` byte-identical (lesson chrome
   is positioned at hand-tuned stage coords).
   Budget: 5×108 + 4×10 + 14 + 58 = **652**, vs today's 660 — 8px *shorter*, so the column still
   clears the ~stage-y 760 iPhone-landscape crop.
   **`--toolW` stays 124** so `#titleBox` ([:199](public/css/styles.css:199)), `--centerPad`, and
   `_buildPrintMarks`' `centreOf(['titleBox','toolsList','tools'])` cannot move a pixel.
2. **New block at end of file**: `#viewToggleBtn` styling; `.learning-mode #viewToggleBtn{display:none}`;
   `html.fiveNote #printBtn{display:none !important}`; `.noteGlyph` positioning under
   `html.fiveNote` (`position:absolute; inset:0; z-index:3` to clear the candy-bar `::after`),
   text variant at `calc(var(--cell)*0.62)` with the per-glyph `translateY` nudges keyed on
   `data-nv`, SVG variant at `height:calc(var(--cell)*0.66); width:auto`; and
   `html:not(.fiveNote) .noteBlock .noteGlyph{display:none !important}` as a belt-and-braces lock.
3. **Pin the fader**: `html.fiveNote #masterVolUI{ --faderTrackH: 190px; }`.
   ⚠️ [index.html:7922](public/index.html:7922) hardcodes 8 rows: `--faderTrackH` =
   `cell*8 − 322`, which is 190px today but **302px at cell 78**, growing `#rightCol` by 112px.
   Scaling it to 5 rows instead gives 406−350 = 56px — an unusable stub, because the fader's fixed
   chrome (4 instrument buttons + 88px) is 350px. Pinning to today's 190px makes **the right
   column pixel-identical in both views**, which is both the safest and the least surprising
   answer. Mirrors the existing precedent at [styles.css:2585](public/css/styles.css:2585).
4. **Add `#viewToggleBtn` to the `@media print` hide list** ([:2479](public/css/styles.css:2479)).
   Note `.noteBlock` is already there, so the new glyphs can never print — that whole class of
   risk is pre-solved.

---

## Gotchas

- **The learning-mode glyph CSS cannot collide.** `toolSteps` has no `kind`, `selectedKind` is
  `null` in the full app, and `_applyScannedNotes` passes `null`, so `data-kind` is *never* set
  outside learning mode — `[data-kind="quarter"]::after{display:none}` and the ♩/♫ nudges can't
  match a 5-note block. We use `data-nv` and keep the candy-bar segmentation on every length
  (a whole note showing 16 segments behind the glyph is the existing visual language, and helps
  a child count).
- **`redrawRowNotes`'s diff-reuse can't leave a stale glyph.** A view toggle routes through
  `buildGrid`, which does `sequencerEl.innerHTML = ""` and destroys every layer, so every block is
  rebuilt by `createNoteBlock`. Within a view, a note's `len` never changes.
- **The drum panel widens 1084 → 1308px** ([styles.css:564](public/css/styles.css:564) tracks the
  shell exactly, so no overflow). Its buttons are `space-evenly`; they just spread. Cosmetic —
  eyeball it before the owner does.
- **Hidden notes still reach cloud save and the AI engine** (`runAiGeneration`
  [:1310](public/index.html:1310), save payload [:4515](public/index.html:4515) both `flatMap`
  all 8 rows). Deliberate, one rule: *the model is the tune, the view is a window.* Save must stay
  full-model or the non-destructive promise breaks; the AI matching save keeps one explanation
  rather than two. Only reachable after an 8→5 switch. If the owner prefers "the AI builds what
  you hear", window line 1310 — one line.
- **`--toolBtnSize` shrinks in the main view too.** The owner asked for exactly this, but it is
  the one visible change to the shipped screen; everything else about the 8-row view is identical.
- The toggle is **free for all tiers** (guest included) — it is an age/accessibility affordance,
  not a premium feature. Default view is the 8-row one; the choice persists in localStorage.

---

## Verification

### A. Gate — the printed layout must not move (do this FIRST)

`node serve.js` → `localhost:3000`, default view, console:

```
KidSequencer.Scan.printMarkInsets()
```

Must return the committed `{u0:0.07425, v0:0.20202, u1:0.95248, v1:0.83115}`
([index.html:528](public/index.html:528)). Arithmetic says `#drumPanel` (~stage-y 804) is the
print bbox's bottom, not `#toolsList` (~752 today, ~672 after the shrink), so the circle shrink
should not move it — **but `_applyPrintScale` does measure `toolsList`
([:7576](public/index.html:7576)), so this must be measured, not argued.** If it moved, stop:
either re-derive and update `SHEET_GEOMETRY` (which invalidates already-printed sheets) or scope
the shrink to `html.fiveNote` and rethink the button size. Then run
`public/scan-tests.html` — all 54 checks green.

### B. The 8-row app is unchanged

Structural first: every touched expression must reduce to its current value when
`_fiveNote === false`. Then measure: `--cell` is `64px`; 8 `.rowWrap`s × 16 `.cell`s;
`#drumPanel` width `1084`; **zero `.noteGlyph` elements** after placing one note of every length;
`?level=1`, `?level=3`, `?lesson=a1` all show `--toolBtnSize: 124px`, no `#viewToggleBtn`, and A1
is drivable end to end.

### C. The 5-note view works

5 `.rowWrap`s; `--cell` `78px`; `#drumPanel` `1308`; `#mainLayout` `scrollWidth <= 1600` and
`--centerPad` ≈ 11 (this is the check that 78 was the right cap). Colours top→bottom
`#3DA9FF #00FF00 #FFFF00 #FF8C00 #FF0000`. Pitch: a note on the top visible row plays
`pitchFor(3)` ≈ 392 Hz (G4); switch the key to G and confirm it becomes D — that proves the offset
composes with `SCALES`. Glyphs: five lengths → five `.noteGlyph`s with `data-nv` 1/2/4/8/16, and
each must be visibly the same artwork as its tool button. `#rightCol`'s bottom measured against
the 900px stage floor.

### D. Hide-and-restore — the requirement that matters

Place a note on all 8 rows with distinct lengths; record `JSON.stringify(notesByRow)`. Toggle to
5-note: 5 rowWraps, the three top blocks gone from the DOM, `notesByRow` **unchanged**. Play and
confirm exactly five pitches sound. Toggle back: 8 rows, all 8 blocks, and `notesByRow` matches
the recording **byte for byte including ids**. Then toggle 5↔8 ten times with notes placed and
assert glyph count equals block count in the 5-note view and zero in the 8-row view.

### E. Runtime + devices

Toggle mid-playback: no console error, playhead keeps moving, no tempo hitch. Ctrl+P in the
5-note view produces a sheet with **no corner marks**. Then iPhone landscape (the stage-floor
crop — confirm the toggle is fully visible and tappable in both views), iPad, desktop.

Deploy to a **dedicated** hosting channel (`firebase hosting:channel:deploy fivenote`), not
`preview` — concurrent worktrees overwrite `preview`.

---

## Still needs your call (low stakes, defaults chosen)

1. **Cell 78** is the largest the centring solve allows. Bigger squares would mean narrowing the
   124px tool column or the 58px right column — both move the printed layout and force
   `SHEET_GEOMETRY` to be re-measured. Worth checking 78 reads as "larger to fit" enough on a real
   iPad before committing.
2. **AI from hidden rows** — defaulting to full-model (see Gotchas). One line to change.
3. A **5-row printable worksheet** stays deferred (needs measured insets + a `kidseq:main5`
   template + new fixtures). Nothing here forecloses adding it later.
