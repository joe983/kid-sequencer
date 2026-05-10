# Kid Sequencer — Claude Context

## What this app is
A browser-based music sequencer for kids. Users place notes on a grid, pick an instrument, set tempo, and hit play. A camera button lets them scan physical objects/cards to input notes. Built as a single HTML file with vanilla JS + Firebase backend.

**Production URL:** https://kid-sequencer.web.app
**Preview channel (use by default):** https://kid-sequencer--preview-h1j9zyru.web.app

---

## Repo layout
```
public/
  index.html          ← entire app (HTML + inline CSS + inline JS ~2600 lines)
  css/styles.css      ← extracted styles (linked from index.html)
  js/firebase-init.js ← Firebase config + exports (auth, db)
firebase.json         ← hosting config
firestore.rules       ← Firestore security rules
serve.js              ← local static server (node serve.js → localhost:3000)
```

---

## Critical architecture — read before touching JS

### Everything lives in one IIFE
The entire main script (lines ~174–2575 in `index.html`) is one arrow-function IIFE:
```js
(() => {
  // ALL state: notesByRow, tempo, isPaid, isLoggedIn, etc.
  // ALL functions: play(), stop(), applyLockState(), saveToCloud(), etc.
})();
```
Variables declared inside are **not on `window`** unless explicitly placed there.

### Firebase auth is a separate ES module
```html
<script type="module"> … </script>   ← line ~2578
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
firebase hosting:channel:deploy preview
# → https://kid-sequencer--preview-h1j9zyru.web.app  (expires ~7 days, redeploy to refresh)

# Production (only when explicitly asked)
firebase deploy --only hosting
# → https://kid-sequencer.web.app
```

Working directory for deploy: repo root (`C:\Users\Joe_C\Documents\kid-sequencer-repo`)

---

## Dev workflow

```bash
# Local preview
node serve.js   # → http://localhost:3000

# Branch for new work (Claude Code creates worktrees automatically)
# Main branch is always deployable
```

---

## Git / GitHub

- Remote: https://github.com/joe983/kid-sequencer
- `gh` CLI is at: `C:\Program Files\GitHub CLI\gh.exe`
- Default branch: `main`
- Claude works on feature branches (`claude/…`) and opens PRs into `main`

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
10. **Top bar layout refactor** — robot mascot, login/logout, and print button moved into the top bar
11. **Page centering** — `--centerPad` CSS variable computed in `fitToViewport()` and applied to topBar + mainLayout padding; `margin: 0 auto` on `#page` for wide screens
12. **16 rhythm buttons** — Techno + Drum 'n' Bass + 14 greyed-out "?" placeholders in a single row
13. **Drag-to-pan removed** — viewport pan handler deleted; fixed stage doesn't need scrolling
14. **Note click-to-delete fix** — note blocks are `pointer-events:none`; clicks pass through to cells
15. **Audio ducking fix & volume normalization** — master compressor retuned from brick-wall (-20dB/20:1) to gentle safety limiter; LEVEL constants rebalanced so all instruments hit equal effective dry peak; organ/synth filters softened to reduce abrasiveness when layered
16. **Dynamic compressor** — compressor settings switch per step based on note count: ≤3 notes get gentle compression (threshold -4dB, ratio 3:1), 4+ notes get firm limiting (threshold -10dB, ratio 8:1, knee 8dB); transitions via `setTargetAtTime` with 15ms time constant

---

## Key UX patterns in the codebase

- **Locked button nudge:** `.locked` class on buttons; `bindLockedNudge()` adds a wiggle + shows login CTA on tap
- **Slide-up sheet:** `transform: translateY(100%)` → `translateY(0)` with `cubic-bezier(0.32,0.72,0,1)`
- **Toast notifications:** `showToast(msg, isError)` — auto-dismiss after 2.5s
- **Undo stack:** `pushUndo()` before state changes; `undo()` to restore
- **Spacebar:** plays/stops sequencer; skips if `document.activeElement` is INPUT or TEXTAREA

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

## Audio engine — architecture

### Signal chain
```
Instruments → per-instrument reverb bus (dry/wet split) → masterGain (0.65) → masterComp → audioCtx.destination
Drums → drumBus (0.70) → masterGain → masterComp → audioCtx.destination
```

### Dynamic compressor (`_compDense` flag)
The master compressor switches settings per sequencer step based on note count:
- **≤3 notes (gentle):** threshold -4 dB, ratio 3:1, knee 14 dB — nearly transparent
- **4+ notes (dense):** threshold -10 dB, ratio 8:1, knee 8 dB — firm limiting
- Transitions use `setTargetAtTime(value, now, 0.015)` for smooth 15ms ramps
- `_compDense` tracks current state to avoid redundant updates
- State persists across stop/start — only changes when a step with different density plays

### Instrument LEVEL constants
```js
const LEVEL = { piano: 0.40, trumpet: 0.77, strings: 0.86, synth: 0.34 };
```
Calibrated so all instruments hit ~0.25 effective dry peak per note (accounting for envelope peaks and bus dry gains). Organ (piano) and synth are lower because they have denser harmonic content that stacks aggressively.

### Key audio parameters
- `AUDIO_AHEAD_S = 0.010` — 10ms lookahead for all scheduled audio
- `masterGain = 0.65` — provides headroom for stacking
- `drumBus = 0.70` — drums slightly below melodic instruments
- Kick peak: `0.80 * vel` — reduced from 1.10 to prevent compressor hammering
- Organ LP: 3200 Hz (Q 0.5) — lowered from 4200 to reduce abrasiveness when layered
- Synth LP: 2200→1500 Hz (Q 0.5) — lowered from 2600→1800, Q from 0.9 to reduce harshness

---

## Things to watch out for

- `isLoggedIn` is an **implicit global** (assigned without `let/var/const` in non-strict IIFE — lands on `window`)
- Don't use `var` thinking it'll become a global inside the IIFE — it won't
- Always test on iPhone Safari — positioning bugs tend to appear there first
- Firestore rejects nested arrays — flatten before writing, reconstruct after reading
- The load sheet list max-height is `330px` ≈ 5 rows × 66px; adjust if row height changes
- **iOS Safari viewport units:** `100vh` ≠ `window.innerHeight` when browser bars are visible. Use `window.innerHeight` in JS for anything that needs to fit in the visible area. Use `100svh` in CSS as a better estimate (Safari 15.4+).
- **Note blocks are `pointer-events: none`** — `.noteBlock` elements are purely visual. All click/tap interactions go through to `.cell` elements, where `onCellClick` handles both placement and deletion via `occ[r][c]`.
- **No viewport panning** — the drag-to-pan handler was removed. The fixed stage doesn't scroll.
- **Do NOT revert compressor to static settings** — the dynamic per-step switching is deliberate. Static aggressive settings cause audible ducking/pumping on sustained notes.
- **Do NOT raise organ/synth filter cutoffs** — they were specifically lowered to reduce abrasiveness when multiple notes are layered. Brass and strings sound good at current settings.
- **`taperGain` multiplier must match `masterGain` default** — currently both are 0.65. If you change one, change the other, plus the reset value in `stopAllAudioNow()`.
