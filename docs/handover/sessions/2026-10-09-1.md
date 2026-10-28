# Project Handover — Current State

**Last updated:** 2026-10-09

## Project State

A live-classroom debugging session: the owner's school ran the app on shared iPads (Safari 15.6.1 / 16.6 / 17.6 / 18.7.6 / 26.x) while I collected data **from the live app** and pushed fixes during the school day (owner: "push live when done", "stop testing in Chrome, use the live data"). Everything is **pushed and live**; `main` = `origin/main` at `8af0e7c`. The app now **reports its own audio health** to Firestore `audioReports` (create-only rule, deployed) and `node tools/read-audio-reports.js [n] [--full|--json]` reads it with the Firebase CLI login. 44 iPad reports came in. Findings and fixes: (1) **skipping-CD glitch = the iPad's audio thread falling behind** (audio clock 0.23–0.85 of real time) whenever **synthesised** voices played — the synth bass and the synth tech-house kick/sub; sampled voices were fine. Fixed by **rendering the bass (5 zones) and all 9 synth drums once into samples** with OfflineAudioContext, plus drum choke, voice caps and an automatic two-stage **light mode**. Final sessions on that code: 173 s / 79 notes and 221 s with **zero glitches**. (2) **"cut out, refresh fixed it"**: one confirmed case was a child pulling the **volume fader to zero**; another was iOS leaving the context `interrupted` — app now self-repairs a stuck master gain and rebuilds the engine after 2 failed resume taps. (3) **"cut out, only a reboot fixes it"**: data showed the app internally healthy (running, clock 1.00, output −7 dB) while students heard nothing → iOS audio session. The silent-video session keeper **never ran on iPads** (UA reports Mac). `8af0e7c` sets `navigator.audioSession.type = "playback"` and fixes the iPad detection — **no report from an iPad on that version yet, so unconfirmed.** (4) QR-code new tab silent: an old tab held the audio → Play now makes other tabs release it. Also shipped (owner request): greyed **AI button for guests → sign-up**, and the **view-switch button in black and white** (`styles.css?v=94`). The iPad stuck-stage fix `ef5c822` (T-016) was pushed with the first push of the day and is live, still not tested by the owner on an iPad.

## Open Todos

(Summary — `TODOS.md` is the real list.)

- **T-017** Confirm the reboot-only cut-out fix (`8af0e7c`, audio session "playback" + iPad detection) from the next class's reports: look for `session: "playback"` and `silentVideo: "playing"` in records, and whether `repeat-loads` / cut-out reports recur.
- **T-018** Confirm skipping stays cured on the final version (glitch reports with `melKit:true`, live kind `drumR`, `clockSpeed`); then decide whether light mode stage 2 is still needed.
- **T-019** iPads that entered light mode before the fixes stay in it for 7 days (`localStorage kidseq_audiolite`) — reverbs off for no reason now.
- **T-020** Delete the output-timestamp ("output-stalled") check — Safari reports `getOutputTimestamp().contextTime` stuck near 0; it only fired false alarms.
- **T-021** Write today's audio work into `CLAUDE.md` "What's been built" (nothing about it is in CLAUDE.md yet).
- **T-022** `audioReports` grows without limit (~1 write per iPad per 2 min while playing) — add cleanup/TTL.
- Carried: T-016 (owner iPad test of `ef5c822`, now live), T-006/T-010 (superseded in practice by today's data but still open), T-007/T-011 (conditional), T-012 (scanner merge), T-015, T-002, T-003.

## Decisions & Rationale

- **Debug from the live app, not Chrome.** Owner asked explicitly; Chrome's audio engine never reproduced any iPad behaviour (offline NaN tests, frozen meters, timestamps all differ). Chrome was used only for pre-push smoke checks that a change still makes sound.
- **Self-report via Firestore `audioReports`** (create-only rule, ≤ 9000-char JSON string, no user id) rather than photos of `?audiodebug=1`: owner asked why they had to photograph data the app could collect.
- **Render synth voices into samples** rather than make them cheaper: live data showed sample playback was fine on these iPads while synth voices collapsed the clock. Synth drums are rendered by their own unchanged `play*` functions with `audioCtx`/`drumBus` swapped to an OfflineAudioContext for one synchronous call — no duplicate drum code. The bass uses a copied recipe (`renderBassKit`).
- **Rejected:** capping synth voices by disconnecting them (it dented the bass level in tests); relying on light mode alone (live data: light mode on and still skipping).
- **Volume fader may reach silence** — owner declined a minimum-volume floor; instead the dead-output self-repair skips when the fader is at zero.
- **AI sign-up box** highlighting the free Member plan for guests is fine (owner).
- **Reports sent immediately from a failing page** (nostart, dead, stuck, repeat-loads) and **a summary per play session** — because a page that needs a reboot never sends its record on the next reopen.

## Blockers / Open Questions

- Needs a class session on the latest version to confirm T-017/T-018. Waiting on: owner (next time the iPads are used — refresh each iPad first).

## Next Step

Run `node tools/read-audio-reports.js 300 --json` after the next class session and check, for reports carrying a `session` field: is it `"playback"`, did any `now:*` / `repeat-loads` / `bad` reports arrive, and are there glitch reports with `melKit: true`? That settles T-017 and T-018.

## Landmines

- **The analysis helper scripts are in this session's scratchpad, not the repo** (`watch.cjs` polls every 3 min and exits on new reports; `analyze.cjs <json> [sinceISO]`). Rebuild from `tools/read-audio-reports.js --json` if needed.
- `tools/read-audio-reports.js` uses **firebase-tools' internal modules** (`lib/auth`, `lib/requireAuth`, `lib/apiv2`) from the global npm install — a firebase-tools upgrade can break it. It needs `getGlobalDefaultAccount()` passed into `requireAuth`. The owner authorised using the CLI login for this read-only query.
- **Meter readings sampled every 500 ms phase-lock with 120 bpm** (one beat = 500 ms) — a smoke test can read the same gap every time and look "silent". Don't conclude a regression from that; check state (notes, live kinds) instead.
- Chrome **also** freezes AnalyserNode output when its input is silent (`-41dB*` frozen marker after Stop) — not a fault.
- `getOutputTimestamp().contextTime` on Safari is stuck at 0.000–0.002 even when healthy.
- Reports from iPads that haven't refreshed carry old field sets (no `session`, `melKit`, `lite2`…) — check fields before comparing.
- The CSS cache key is `?v=94`.
- Several of my test reports in `audioReports` have a **Windows** UA — ignore them.

## State

- **Branch:** main
- **Last commit:** 8af0e7c — iPads: put the page's audio in the playback session; fix the iPad check (2026-10-09). In sync with `origin/main` (0/0).
- **Working tree:** Dirty — uncommitted changes in: `CLAUDE.md` (only the "Session Handover" pointer block). Untracked: `docs/handover/` (these files + `perf-harness/` + `sessions/`).
