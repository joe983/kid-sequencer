# Kid Sequencer — Module Structure

The original single `index.html` (4,457 lines) has been broken into separate files for easier editing.

---

## File Structure

```
kid-sequencer/
├── index.html              ← Slim shell: HTML structure + script tags only
├── css/
│   └── styles.css          ← All styles (layout, grid, buttons, modals, debug, animations)
├── js/
│   ├── sequencer.js        ← Main app logic (see Table of Contents below)
│   └── firebase-auth.js    ← Firebase auth watcher (ES module, optional)
└── README.md
```

---

## What's in `sequencer.js`

The main app is one IIFE with clearly marked sections. Use your editor's **search** to jump to any section:

| Section marker | Contents |
|---|---|
| `§ CONFIG` | rows/cols, frequencies, note lengths, SVG icons |
| `§ STATE` | runtime variables (notesByRow, occ, tempo, instrument, etc.) |
| `§ AUTH-CLOSE` | Close-tab logout logic |
| `§ DRUMS-DATA` | Drum patterns (techhouse / dnb) |
| `§ DRUMS-UI` | Drum style buttons, mute/unmute, `syncAudioAndUI` |
| `§ AUTH-UI` | Lock state, login nudges, `applyLockState`, `logout` |
| `§ PLAYHEAD-WOBBLE` | Tempo-linked CSS animation scaling |
| `§ LAYOUT-FIT` | `fitToViewport`, `positionRobotLogo`, viewport helpers |
| `§ AUDIO-ENGINE` | AudioContext, reverb buses, drums synthesis, warmup |
| `§ INSTRUMENT-UI` | `setInstrument()`, button highlight |
| `§ TOOLS-UI` | Note-length tool panel (`buildTools`) |
| `§ GRID` | Grid DOM build, note placement (`canPlace`, `placeNote`, `smartPlaceNote`) |
| `§ PLAYHEAD` | Playhead DOM helpers |
| `§ ENVELOPE` | `scheduleEnvelope()` shared helper |
| `§ INSTRUMENTS` | `playPiano` / `playTrumpet` / `playStrings` / `playSynth` |
| `§ PLAYBACK` | `play()` / `stop()` / `startSequencer()` / `tick()` |
| `§ TEMPO` | `tempoUp` / `tempoDown` / `requestTempo` |
| `§ CLEAR` | `clearGrid()` |
| `§ CAMERA` | Camera modal, capture, `importGridFromDataUrl` |
| `§ INIT-LAYOUT` | Layout manager IIFE + `init()` |
| `§ EXPORTS` | `window.*` globals + `window.KidSequencer` namespace |

---

## What's in the standalone modules

These are self-contained IIFEs or ES modules — they don't share state with `sequencer.js` except via `window.*`.

- **`firebase-auth.js`** — ES module. Watches Firebase auth state. Imports `./js/firebase-init.js` (not included — add your own).

---

## Editing Tips

- **Changing sounds?** → Edit the `§ INSTRUMENTS` section in `sequencer.js`
- **Changing drum patterns?** → Edit `§ DRUMS-DATA` in `sequencer.js`
- **Changing layout/sizing?** → Edit `css/styles.css` (CSS variables at the top) and `§ LAYOUT-FIT`
- **Changing note-length tools?** → Edit `toolSteps` array in `§ CONFIG`
- **Changing colors?** → Edit `rowColors` in `§ CONFIG`
