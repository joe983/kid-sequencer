# Kid Sequencer — Claude Context

## What this app is
A browser-based music sequencer for kids. Users place notes on a grid, pick an instrument, set tempo, and hit play. A camera button lets them scan physical objects/cards to input notes. Built as a single HTML file with vanilla JS + Firebase backend.

**Production URL:** https://kid-sequencer.web.app
**Preview channel (use by default):** https://kid-sequencer--preview-h1j9zyru.web.app

---

## Active worktree — ALL work happens here

**Path:** `C:\Users\Joe_C\Documents\kid-sequencer-repo\.claude\worktrees\quizzical-darwin`
**Branch:** `claude/quizzical-darwin`

> ⚠️ **CRITICAL — read before doing anything else.**
> Every edit, every deploy, every test must happen inside this worktree.
> Do **NOT** create a new worktree at the start of a session. Do **NOT** work from the repo root. Do **NOT** work from `main`.
> A new worktree should only be created if a task is explicitly long-lived and isolated enough to warrant one — and even then, it must branch from `claude/quizzical-darwin`, not from `main`.
> If Claude Code has auto-created a new worktree for the current session, **ignore it** and make all changes in `quizzical-darwin` instead.

This is the most up-to-date working branch. It contains the camera modal overhaul, QR-to-sequence feature, and all audio engine fixes — none of which are in `main`. Always deploy and test from this directory.

```bash
# Deploy from the worktree (not repo root)
cd C:\Users\Joe_C\Documents\kid-sequencer-repo\.claude\worktrees\quizzical-darwin
firebase hosting:channel:deploy preview
```

For new features, continue work directly in `quizzical-darwin`. Only create a new worktree if the user explicitly asks for one or the task is a large independent experiment.

---

## Repo layout
```
public/
  index.html          ← entire app (HTML + inline CSS + inline JS ~3000 lines)
  css/styles.css      ← extracted styles (linked from index.html, currently ?v=7)
  js/firebase-init.js ← Firebase config + exports (auth, db)
firebase.json         ← hosting config
firestore.rules       ← Firestore security rules
serve.js              ← local static server (node serve.js → localhost:3000)
```

---

## Critical architecture — read before touching JS

### Everything lives in one IIFE
The entire main script is one arrow-function IIFE:
```js
(() => {
  // ALL state: notesByRow, tempo, isPaid, isLoggedIn, etc.
  // ALL functions: play(), stop(), applyLockState(), saveToCloud(), etc.
})();
```
Variables declared inside are **not on `window`** unless explicitly placed there.

### Firebase auth is a separate ES module
```html
<script type="module"> … </script>
```
This has its own lexical scope. It **cannot** read IIFE variables by name. Cross-scope communication uses:
- `window.KidSequencer.UI.applyLockState()` — exposed deliberately for this purpose
- `sessionStorage` — module writes `kidseq_tier` and `kidseq_logged_in`; IIFE reads them inside `applyLockState()`

### `isPaid` scope gotcha
`isPaid` is declared inside the IIFE (function-scoped). `var` inside an IIFE is still function-scoped — **not** `window.isPaid`. The fix: `applyLockState()` re-reads from sessionStorage at its top:
```js
try { isPaid = isLoggedIn && sessionStorage.getItem('kidseq_tier') === 'paid'; } catch(e) {}
```

### `auth.currentUser` is null on page load
Firebase restores auth state asynchronously. `saveToCloud()` and `loadFromCloud()` use `_getFirebaseUser()` which falls back to an `onAuthStateChanged` promise if `currentUser` is null.

### Firestore data shape
```
users/{uid}/
  sequences/{slug}   ← slug = slugified tune name
    name: string
    savedAt: Timestamp
    tempo: number
    instrument: string
    steps: number
    drumsEnabled: boolean
    notes: [{row, start, len}]   ← FLAT array (Firestore rejects nested arrays)
    drumPattern: {…}
```

---

## Tier system

| Feature | Guest (not logged in) | Free (logged in) | Paid |
|---|---|---|---|
| Tempo | ✅ | ✅ | ✅ |
| Piano / Trumpet | ✅ | ✅ | ✅ |
| Strings / Synth | 🔒 | 🔒 | ✅ |
| Camera scan | ✅ (6/week) | ✅ | ✅ |
| Cloud save/load | 🔒 | 🔒 | ✅ |

Scan limit: tracked in `localStorage` (`kidseq_scan_week`, `kidseq_scan_count`). Resets each Monday.

Tier is stored in Firestore `users/{uid}.tier` and mirrored to `sessionStorage['kidseq_tier']` by the auth module.

---

## Deployment

```bash
# Preview channel (default — use this unless told otherwise)
# Run from the active worktree directory (quizzical-darwin)
firebase hosting:channel:deploy preview
# → https://kid-sequencer--preview-h1j9zyru.web.app  (expires ~7 days, redeploy to refresh)

# Production (only when explicitly asked)
firebase deploy --only hosting
# → https://kid-sequencer.web.app
```

**Always deploy from the active worktree directory, not the repo root.**

---

## Dev workflow

```bash
# Local preview (run from quizzical-darwin)
node serve.js   # → http://localhost:3000

# All new work: edit files directly in quizzical-darwin
# Do NOT create a new worktree unless the user explicitly requests it
# Main branch is always deployable but is significantly behind quizzical-darwin
```

---

## Git / GitHub

- Remote: https://github.com/joe983/kid-sequencer
- `gh` CLI is at: `C:\Program Files\GitHub CLI\gh.exe`
- Default branch: `main`
- Active feature branch: `claude/quizzical-darwin`
- Single-person project — push directly to `main`, no PRs
- Claude works on feature branches (`claude/…`) but merges directly (no PR review needed)

---

## What's been built (as of 2026-05-10)

1. **Core sequencer** — grid, play/stop, tempo, multiple instruments, drums
2. **Firebase auth** — login/register modal, persistent sessions
3. **Guest tier** — tempo, piano/trumpet, camera unlocked for guests; 6 scans/week cap with slide-in limit panel
4. **Cloud save/load** — paid tier only; named save slots; slide-up load sheet with delete; Firestore storage
5. **Scan limit panel** — fixed for Safari, Edge, iPhone (position:fixed, safe-area-inset)
6. **Camera modal overhaul** — mode bar (Camera / QR / Sheet Scan), landscape iPhone fix
7. **QR-to-sequence** — live QR scan loop, greyed Use button until code detected, toast notification, pulse animation, `qrToSequence()` algorithm (C4–C5 scale, multiplicative hash + LCG, melodic contour bias)
8. **Audio engine timing fixes** — self-correcting sequencer timer + audio lookahead
9. **Circular note-length buttons** — left column buttons refactored from rectangles to large 124px circles showing only the musical symbol; all note lengths unlocked for all tiers
10. **Top bar layout refactor** — robot mascot, login/logout, and print button moved into the top bar; `syncTopBarLayout()` aligns transport cluster to grid; `syncTopBarLoginPosition()` centres login equidistant between Print and Tempo-Up
11. **Page centering** — `--centerPad` CSS variable computed in `fitToViewport()` and applied to topBar + mainLayout padding; `margin: 0 auto` on `#page` for wide screens
12. **16 rhythm buttons** — Techno + Drum 'n' Bass + 14 greyed-out "?" placeholders in a single row, evenly spaced (`space-evenly`), 44×44px each
13. **Drag-to-pan removed** — viewport pan handler deleted; fixed stage doesn't need scrolling
14. **Note click-to-delete fix** — note blocks are now `pointer-events:none`; all clicks pass through to cells where `onCellClick` handles both placement and deletion reliably

---

## Key UX patterns in the codebase

- **Locked button nudge:** `.locked` class on buttons; `bindLockedNudge()` adds a wiggle + shows login CTA on tap
- **Slide-up sheet:** `transform: translateY(100%)` → `translateY(0)` with `cubic-bezier(0.32,0.72,0,1)`
- **Toast notifications:** `showSaveToast(state)` — state keys: `saving`, `saved`, `error`, `upgrade`, `loading`, `loaded`, `empty`, `qr`. Auto-dismiss after 2.4s.
- **Undo stack:** `pushUndo()` before state changes; `undo()` to restore
- **Spacebar:** plays/stops sequencer; skips if `document.activeElement` is INPUT or TEXTAREA
- **Rhythm placeholders:** 14 greyed-out `?` buttons (`drumStylePlaceholder` class) — `opacity:0.3`, disabled, `aria-hidden`. Will become real buttons as rhythms are added.

---

## Camera modal — architecture

### HTML structure
```
#camModal  (overlay, position:fixed inset:0)
  .modalCard.camModalCard
    .camModeBar          ← Camera / QR / Sheet icon buttons + mode label + × close
    .camBody             ← flex row in landscape, flex col on desktop
      .camStage          ← video + preview img + .camOverlay#camOverlay
      .camActions        ← Capture button + Use button (#camUseBtn)
    .modalHint#camHint   ← "Tip:" text, only visible in sheet mode
```

### Mode switching
`setCamMode(mode)` — exported to `window.setCamMode`. Toggles `.active` on mode buttons, updates label text, sets `camOverlay.className` to `'camOverlay'` + optionally `' mode-sheet'` or `' mode-qr'`. Uses plain class toggling (NOT data-attribute selectors — unreliable cross-browser). `camHint` shown only in sheet mode.

**QR mode additionally:** disables `#camUseBtn`, clears `_detectedQRText`, starts `_startQRScan()` loop. Switching away from QR mode calls `_stopQRScan()` and re-enables Use.

### Overlays (CSS class-based)
- `.camOverlay` — hidden by default (camera mode = plain viewfinder)
- `.camOverlay.mode-sheet` — dashed border + grid lines (16×8 repeating-linear-gradient)
- `.camOverlay.mode-qr` — centred crosshair + corner brackets via `::before`/`::after`

### QR live-scan loop
- `_startQRScan()` / `_stopQRScan()` / `_qrRafId` — rAF loop running only in QR mode
- `_detectedQRText` — stores the decoded string once found; `null` when no code seen yet
- On detection: calls `showSaveToast('qr')`, enables + pulses `#camUseBtn` (`.cam-use-pulse`)
- Loop stops itself after first detection; resets on `closeCameraModal()` and on mode switch
- `camImport()` checks `camMode === 'qr'` and routes to `qrToSequence(_detectedQRText)`

### qrToSequence algorithm
- **Hash:** `bytes.reduce((acc, b) => (Math.imul(acc, 31) + b) >>> 0, 0)`
- **LCG:** `s = (Math.imul(1664525, s) + 1013904223) >>> 0`
- **Scale:** C major C4–C5 (`['C4','D4','E4','F4','G4','A4','B4','C5']`) — hardcoded const, not user-selectable
- **Grid:** uses `cols` (16 slots); iterates in `selectedSteps` increments
- **Rests:** `rand() % 5 === 0` (~20%)
- **Melodic contour:** 60% chance step within ±2 degrees of previous; starts at index 3 (F4)
- **Row mapping:** degree 0 (C4) → row 7 (lowest); degree 7 (C5) → row 0 (highest)

### Landscape iPhone fix — CRITICAL
**Problem:** `100vh` in Safari iOS = layout viewport height (bars collapsed), but `window.innerHeight` = visual viewport (below browser chrome). Using `100vh` for sizing makes the stage enormous; centering the card with `align-items:center` pushes the mode bar behind the browser chrome.

**Solution (in `_sizeCamStageForLandscape()`):**
1. Detect landscape phone: `innerWidth > innerHeight && innerHeight <= 500`
2. Set `card.style.height = (window.innerHeight - 16) + 'px'` — uses visual viewport
3. `stageH = cardH − modeBar.offsetHeight − 12` (body padding 6px×2)
4. `stageW = stageH × 1.618` — golden ratio, capped by `card.clientWidth − 92` to avoid overflow
5. Set stage `height` + `width` inline

**CSS overlay in landscape:** `#camModal` uses `align-items: flex-start` (not center!) so the card anchors to the **top** of the visible viewport. `100svh` (Safari 15.4+) / `100vh` fallback gives initial card height until JS corrects it in the first double-rAF.

**Wiring:**
- `openCameraModal()` → `requestAnimationFrame(() => requestAnimationFrame(() => _sizeCamStageForLandscape()))` + `window.addEventListener('resize', _sizeCamStageForLandscape)`
- `closeCameraModal()` → removes listener, clears `card.style.height`, `stage.style.height/width`

### CSS cache busting
The `<link>` tag uses `css/styles.css?v=N`. Bump `N` on every deploy that changes styles.css (currently `?v=7`).

---

## Audio engine — architecture & known fixes

### Sequencer timing — self-correcting timer
`startSequencer()` uses `setTimeout` (NOT `setInterval`) with a self-correcting loop. Each tick schedules the next tick at an absolute time:
```js
const nextAt = seqStartTime + stepCount * intervalMs;
timer = setTimeout(tick, Math.max(0, nextAt - performance.now()));
```
`seqStartTime` is captured once when the sequencer starts. `stepCount` increments every tick. This means drift from tick execution time (creating audio nodes, DOM updates) is fully corrected — the timer always fires at `seqStartTime + N × interval` regardless of how long each tick took.

**Do NOT revert to `setInterval`.** `setInterval` accumulates drift when ticks are heavy (many simultaneous notes), causing the tempo to gradually slow and settle ~5–8% below the target.

When tempo changes (`pendingTempo` applied at step 0), `seqStartTime` is reset to `performance.now()` and `stepCount` resets to 0 so correction starts fresh from the new tempo.

`stop()` uses `clearTimeout` (matching `setTimeout`) — not `clearInterval`.

### Audio lookahead
All instrument functions and `playDrumsAtStep` schedule audio at `audioCtx.currentTime + AUDIO_AHEAD_S` (10ms ahead), not at `audioCtx.currentTime` directly.
```js
const AUDIO_AHEAD_S = 0.010; // defined once, before the instrument functions
```
This gives the audio render thread one buffer-quantum of preparation time when many nodes are created in a single tick, preventing glitches on busy steps.

**Do NOT schedule at `audioCtx.currentTime` exactly** — doing so forces the audio thread to start mixing brand-new nodes immediately, which causes audible glitches when 6+ notes fire simultaneously.

### Kick drum WaveShaper
`shaper.oversample = "2x"` in `playKick`. Do not raise back to `"4x"` — it halves CPU cost with no audible difference at 44100 Hz for a kids' app.

---

## Camera modal — architecture (as of 2026-03-15)

### HTML structure
```
#camModal  (overlay, position:fixed inset:0)
  .modalCard.camModalCard
    .camModeBar          ← Camera / QR / Sheet buttons + label + × close
    .camBody             ← flex row in landscape, flex col on desktop
      .camStage          ← video + preview img + .camOverlay
      .camActions        ← Capture / Use buttons
    .modalHint           ← "Tip:" text, only visible in sheet mode
```

### Mode switching
`setCamMode(mode)` — exported to `window.setCamMode`. Toggles `.active` on mode buttons, updates label text, sets `camOverlay.className` to `'camOverlay'` + optionally `' mode-sheet'` or `' mode-qr'`. Uses plain class toggling (NOT data-attribute selectors — unreliable cross-browser). `camHint` shown only in sheet mode.

### Overlays (CSS class-based)
- `.camOverlay` — hidden by default (camera mode = plain viewfinder)
- `.camOverlay.mode-sheet` — dashed border + grid lines (16×8 repeating-linear-gradient)
- `.camOverlay.mode-qr` — centred crosshair + corner brackets via `::before`/`::after`

### Landscape iPhone fix — CRITICAL
**Problem:** `100vh` in Safari iOS = layout viewport height (bars collapsed), but `window.innerHeight` = visual viewport (below browser chrome). Using `100vh` for sizing makes the stage enormous; centering the card with `align-items:center` pushes the mode bar behind the browser chrome.

**Solution (in `_sizeCamStageForLandscape()`):**
1. Detect landscape phone: `innerWidth > innerHeight && innerHeight <= 500`
2. Set `card.style.height = (window.innerHeight - 16) + 'px'` — uses visual viewport
3. `stageH = cardH − modeBar.offsetHeight − 12` (body padding 6px×2)
4. `stageW = stageH × 1.618` — golden ratio, capped by `card.clientWidth − 92` to avoid overflow
5. Set stage `height` + `width` inline

**CSS overlay in landscape:** `#camModal` uses `align-items: flex-start` (not center!) so the card anchors to the **top** of the visible viewport. `100svh` (Safari 15.4+) / `100vh` fallback gives initial card height until JS corrects it in the first double-rAF.

**Wiring:**
- `openCameraModal()` → `requestAnimationFrame(() => requestAnimationFrame(() => _sizeCamStageForLandscape()))` + `window.addEventListener('resize', _sizeCamStageForLandscape)`
- `closeCameraModal()` → removes listener, clears `card.style.height`, `stage.style.height/width`

### CSS cache busting
The `<link>` tag uses `css/styles.css?v=N`. Bump `N` on every deploy that changes styles.css (currently `?v=6`).

---

## Things to watch out for

- `isLoggedIn` is an **implicit global** (assigned without `let/var/const` in non-strict IIFE — lands on `window`)
- Don't use `var` thinking it'll become a global inside the IIFE — it won't
- Always test on iPhone Safari — positioning bugs tend to appear there first
- Firestore rejects nested arrays — flatten before writing, reconstruct after reading
- The load sheet list max-height is `330px` ≈ 5 rows × 66px; adjust if row height changes
- **iOS Safari viewport units:** `100vh` ≠ `window.innerHeight` when browser bars are visible. Use `window.innerHeight` in JS for anything that needs to fit in the visible area. Use `100svh` in CSS as a better estimate (Safari 15.4+).
- **Note blocks are `pointer-events: none`** — `.noteBlock` elements are purely visual. All click/tap interactions go through to `.cell` elements, where `onCellClick` handles both placement and deletion via `occ[r][c]`. Do not add click handlers to note blocks.
- **No viewport panning** — the drag-to-pan handler was removed. The fixed stage doesn't scroll. Do not re-add `body.can-pan` or `body.dragging-pan` cursor styles.
- **`syncTopBarLoginPosition()`** — centres login button equidistant between Print and Tempo-Up using `getBoundingClientRect()`. Uses a transform sandwich in `__reveal()` (temporarily removes page scale to measure, then restores). Do not anchor login to the sequencer right edge.
- **jsQR** is loaded from CDN (`https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js`) in the `<head>`. The QR scan loop guards with `typeof jsQR === 'function'` is not needed in quizzical-darwin (it's always present) but keep it if moving code around.
