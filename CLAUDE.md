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

## What's been built (as of 2026-03-15, after PR #1 merged)

1. **Core sequencer** — grid, play/stop, tempo, multiple instruments, drums
2. **Firebase auth** — login/register modal, persistent sessions
3. **Guest tier** — tempo, piano/trumpet, camera unlocked for guests; 6 scans/week cap with slide-in limit panel
4. **Cloud save/load** — paid tier only; named save slots; slide-up load sheet with delete; Firestore storage
5. **Scan limit panel** — fixed for Safari, Edge, iPhone (position:fixed, safe-area-inset)

---

## Key UX patterns in the codebase

- **Locked button nudge:** `.locked` class on buttons; `bindLockedNudge()` adds a wiggle + shows login CTA on tap
- **Slide-up sheet:** `transform: translateY(100%)` → `translateY(0)` with `cubic-bezier(0.32,0.72,0,1)`
- **Toast notifications:** `showToast(msg, isError)` — auto-dismiss after 2.5s
- **Undo stack:** `pushUndo()` before state changes; `undo()` to restore
- **Spacebar:** plays/stops sequencer; skips if `document.activeElement` is INPUT or TEXTAREA

---

## Things to watch out for

- `isLoggedIn` is an **implicit global** (assigned without `let/var/const` in non-strict IIFE — lands on `window`)
- Don't use `var` thinking it'll become a global inside the IIFE — it won't
- Always test on iPhone Safari — positioning bugs tend to appear there first
- Firestore rejects nested arrays — flatten before writing, reconstruct after reading
- The load sheet list max-height is `330px` ≈ 5 rows × 66px; adjust if row height changes
