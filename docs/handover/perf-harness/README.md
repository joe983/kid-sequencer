# Perf harness (saved 2026-10-07 — NOT committed, NOT part of the app)

Scripts used to find and fix the "music skips when lots of notes are added" bug
(commit `7b62fa4`). They drive a **real headless Chrome** over the DevTools protocol
(Node 24 has a global `WebSocket`; no npm packages needed). Chrome path is hard-coded
to `C:/Program Files/Google/Chrome/Application/chrome.exe`; they expect `node serve.js`
running on `:3000`.

**Do not measure rendering cost in the Browser pane.** Its compositor is frozen: a forced
layout costs 30-45 ms even when nothing changed and `document.getAnimations()` lists ~127
phantom animations. Every number below came from headless Chrome.

| Script | What it does |
|---|---|
| `measure.mjs <cpuThrottle> <tapsPerSec> <seconds>` | Opens `/?audiodebug=1`, seeds a tune, presses Play, then taps cells with real mouse events while `Emulation.setCPUThrottlingRate` slows the CPU. Prints main-thread busy %, script/layout/style ms, long tasks, audio underruns (`playbackStats`) and the scheduler's own `worst tick late / late / dropped` line. Env: `FILL=120` pre-fills the grid, `INJECT_CSS`/`INJECT_JS` for A/B experiments, `TRACE=1` sums main-thread trace events, `NOPLAY=1`, `DUMPANIM=1` lists running animations, `PAGE=<file>` loads another page from `public/`. |
| `matrix.ps1 -Label x -Throttle 4 -Fill 120 [-Taps 8] [-Css ...] [-Extra js] [-Page file]` | Runs `measure.mjs` 3x and prints one comparable line. **Edit `$sp` on line 13 to this folder first** (it still points at the old temp scratchpad). |
| `timing.mjs <page> <jankMs>` | Hooks every `AudioBufferSourceNode`/`OscillatorNode.start`, adds main-thread jank, reports grid error vs a perfect step grid, steady-state lead, first-sound latency and whether anything starts after Stop. |
| `smoke.mjs <path...>` | Loads each view, taps, plays, changes tempo mid-play, reports errors and the panel line. |
| `shot.mjs <page> <outPrefix> [reduce]` | Freezes the beat-badge flash at 0/550/900 ms and screenshots it (add `reduce` for reduced motion). |

To compare against the previous build: `git show <old>:public/index.html > public/_orig_index.html`
(and the old stylesheet to `public/css/_orig_styles.css`, repointing the `<link>`), run with
`-Page _orig_index.html`, then **delete both files** — they must never be committed.

CPU throttling is only a stand-in for a slower device: the iPad's real slowdown relative to
this PC, and Safari's paint model, are unknown. The iPad result is what counts.
