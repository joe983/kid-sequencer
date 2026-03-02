/**
 * sequencer.js — Kid Sequencer main application logic
 *
 * TABLE OF CONTENTS  (search for the section marker to jump there)
 * ================================================================
 *  § CONFIG          — rows/cols, frequencies, note lengths, SVG icons
 *  § STATE           — runtime variables (notes, audio, tempo, etc.)
 *  § AUTH-CLOSE      — close-tab logout logic
 *  § DRUMS-DATA      — drum patterns (techhouse / dnb)
 *  § DRUMS-UI        — drum style buttons, mute/unmute, syncAudioAndUI
 *  § AUTH-UI         — lock state, login nudges, applyLockState, logout
 *  § PLAYHEAD-WOBBLE — tempo-linked CSS wobble
 *  § LAYOUT-FIT      — fitToViewport, positionRobotLogo, viewport helpers
 *  § AUDIO-ENGINE    — AudioContext, buses, drums synthesis, warmup
 *  § INSTRUMENT-UI   — setInstrument(), button highlight
 *  § TOOLS-UI        — note-length tool panel (buildTools)
 *  § GRID            — grid DOM build, note placement, canPlace/placeNote
 *  § PLAYHEAD        — playhead DOM helpers
 *  § ENVELOPE        — scheduleEnvelope() shared helper
 *  § INSTRUMENTS     — playPiano / playTrumpet / playStrings / playSynth
 *  § PLAYBACK        — play() / stop() / startSequencer() / tick()
 *  § TEMPO           — tempoUp / tempoDown / requestTempo
 *  § CLEAR           — clearGrid()
 *  § CAMERA          — camera modal, capture, importGridFromDataUrl
 *  § INIT-LAYOUT     — layout manager IIFE + init()
 *  § EXPORTS         — window.* globals + window.KidSequencer namespace
 */

/* OPTION A ORGANISATION START */
// This file is intentionally single-file, but the JS is grouped into logical modules.
// Layout + behavior are unchanged; we only add structure + a small public API.
(() => {
/* Option A: single-file organisation (no layout/behaviour changes) */


/* -------------------- CONFIG -------------------- */
const rows = 8;
const cols = 16;

let CELL = 46;
const GAP  = 4;

const freqs = [523.25,493.88,440.00,392.00,349.23,329.63,293.66,261.63];
const rowColors = ["#FF0000","#FF4FD8","#7A5CFF","#3DA9FF","#00FF00","#FFFF00","#FF8C00","#FF0000"];

const EIGHTH_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
  <text x="16" y="22" text-anchor="middle"
        font-size="24"
        font-family="Noto Music, Bravura, Arial Unicode MS, Segoe UI Symbol, sans-serif"
        fill="#000000">♫</text>
</svg>`;



const HALF_NOTE_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 220" aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid meet">
  <rect x="78" y="10" width="12" height="150" rx="6" ry="6" fill="#000"/>
  <path fill="#000" fill-rule="evenodd"
        d="M 55 165 m -36 0 a 36 24 0 1 0 72 0 a 36 24 0 1 0 -72 0
           M 57 167 m -18 0 a 18 11 0 1 0 36 0 a 18 11 0 1 0 -36 0"
        transform="rotate(-18 55 165)"/>
</svg>
`;




const WHOLE_NOTE_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 220" aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid meet">
  <path fill="#000" fill-rule="evenodd"
        d="M 55 165 m -36 0 a 36 24 0 1 0 72 0 a 36 24 0 1 0 -72 0
           M 57 167 m -18 0 a 18 11 0 1 0 36 0 a 18 11 0 1 0 -36 0"
        transform="rotate(-18 55 165)"/>
</svg>
`;


const toolSteps = [
  { steps: 1,  label: "16th",  symbol: "♬", divs: 16, symClass:"sixteenth" },
  { steps: 2,  label: "8th",   svg: EIGHTH_SVG, divs: 8,  symClass:"eighth" },
  { steps: 4,  label: "1/4",   symbol: "♩", divs: 4,  symClass:"normal" },
  { steps: 8,  label: "1/2",   svg: HALF_NOTE_SVG,  divs: 2,  symClass:"half" },
  { steps: 16, label: "Whole",  svg: WHOLE_NOTE_SVG,  divs: 1,  symClass:"whole" }
];

let selectedSteps = 1;

try{ isLoggedIn = sessionStorage.getItem("kidseq_logged_in") === "1"; }catch(e){ isLoggedIn = false; }

/* -------------------- CLOSE TAB/WINDOW LOGOUT (but NOT reload) -------------------- */
(function(){
  const PENDING_KEY = "kidseq_logout_pending_v1";
  // If the previous navigation was a reload, cancel any pending logout.
  let navType = "";
  try{
    const nav = performance.getEntriesByType("navigation")[0];
    navType = nav && nav.type ? nav.type : "";
  }catch(e){}
  const isReload = navType === "reload";

  try{
    if(isReload){
      localStorage.removeItem(PENDING_KEY);
    }else{
      const pending = localStorage.getItem(PENDING_KEY) === "1";
      if(pending){
        localStorage.removeItem(PENDING_KEY);
        try{ sessionStorage.removeItem("kidseq_user_email"); }catch(e){}
        try{ sessionStorage.removeItem("kidseq_user_uid"); }catch(e){}
      }
    }
  }catch(e){}

  // Mark pending logout when leaving the page (covers close + navigate away + refresh).
  // Refresh is handled on next load by clearing PENDING_KEY if navType === "reload".
  window.addEventListener("pagehide", (ev) => {
    if(ev && ev.persisted) return; // bfcache
    try{ localStorage.setItem(PENDING_KEY, "1"); }catch(e){}
  });
})();

const LOCKED_STEPS = new Set([4,8,16]);

/* -------------------- STATE -------------------- */
let notesByRow = Array.from({length: rows}, () => []);
let occ = Array.from({length: rows}, () => Array(cols).fill(null));

let audioCtx = null;
let tempo = 120;
let pendingTempo = null;
let step = 0;
let timer = null;

let masterGain = null;
let masterComp = null;

let startTimeout = null;
let audioPrimed = false;
let hasEverStartedPlayback = false;
let lastStopAt = null;

/* track when audio last actually made a sound */
let lastAudioActivityAt = null;

const liveNodes = new Set();
let bus = null;

let instrument = "piano";

/* -------------------- DRUMS -------------------- */
let drumsMuted = true;            // start muted
let drumStyle = "techhouse";      // techhouse | dnb
let drumBus = null;               // GainNode
let drumNoise = null;             // AudioBuffer

const DRUM_PATTERNS = {
  techhouse: {
    // 4-on-the-floor + claps on 2 & 4 + driving hats
    kick: [1,0,0,0,  1,0,0,0,  1,0,0,0,  1,0,0,0],
    clap: [0,0,0,0,  1,0,0,0,  0,0,0,0,  1,0,0,0],
    // closed hat: 16ths with gentle accents
    hatC: [0.26,0.14,0.20,0.14,  0.26,0.14,0.20,0.14,  0.26,0.14,0.20,0.14,  0.26,0.14,0.20,0.14],
    // open hat: offbeats (the "and")
    hatO: [0,0,0.24,0,  0,0,0.24,0,  0,0,0.24,0,  0,0,0.24,0],
  },
  dnb: {
    // classic DnB feel: snare on 2 & 4, syncopated kicks, fast hats
    kick:  [1,0,0,0,  0,0,0,0,  0,0,1,0,  0,0,0,0],
    snare: [0,0,0,0,  1,0,0,0,     0,0,0,0,     1,0,0,0],
    hatC:  [0.20,0.14,0.20,0.14,  0.22,0.14,0.20,0.14,  0.20,0.14,0.24,0.14,  0.20,0.14,0.20,0.14],
    // occasional open hat stabs
    hatO:  [0,0,0,0,   0,0,0,0.18,  0,0,0,0,   0,0.18,0,0]
  }
};

const LEVEL = {
  piano:   0.60,
  trumpet: 1.18,
  strings: 1.30,
  synth:   0.55
};

/* Undo history (max 10 user actions) */
const undoStack = [];
const UNDO_MAX = 10;

function cloneState(){
  return {
    notesByRow: notesByRow.map(row => row.map(n => ({ id:n.id, start:n.start, len:n.len }))),
    occ: occ.map(row => row.slice()),
    nextId
  };
}
function pushUndo(){
  undoStack.push(cloneState());
  while(undoStack.length > UNDO_MAX) undoStack.shift();
}
function undo(){
  if(!undoStack.length) return;
  const snap = undoStack.pop();
  notesByRow = snap.notesByRow.map(row => row.map(n => ({...n})));
  occ = snap.occ.map(row => row.slice());
  nextId = snap.nextId;
  redrawAllNotes();
}

/* DOM */
const tempoBox = document.getElementById("tempoBox");
const sequencerEl = document.getElementById("sequencer");
const toolsEl = document.getElementById("tools");
const toolsListEl = document.getElementById("toolsList");
const toolLoginBtnEl = document.getElementById("toolLoginBtn");

const tempoControlsEl = document.getElementById("tempoControls");
const tempoUpBtnEl = document.getElementById("tempoUpBtn");
const tempoDownBtnEl = document.getElementById("tempoDownBtn");
const instButtonsEl = document.getElementById("instButtons");
const playheadEl = document.getElementById("playhead");
const controlsEl = document.getElementById("controls");
const mainLayoutEl = document.getElementById("mainLayout");
const titleBoxEl = document.getElementById("titleBox");

const cameraBtnEl = document.getElementById("cameraBtn");

const btnPiano   = document.getElementById("btnPiano");
const btnTrumpet = document.getElementById("btnTrumpet");
const btnStrings = document.getElementById("btnStrings");
const btnSynth   = document.getElementById("btnSynth");

/* Drums UI */
const drumMuteBtnEl = document.getElementById("drumMuteBtn");
const drumStatusEl  = document.getElementById("drumStatus");
const drumStyleTechEl = document.getElementById("drumStyleTech");
const drumStyleDnBEl  = document.getElementById("drumStyleDnB");

btnPiano.onclick   = () => { if(!isLoggedIn){ showLockNudge(); hideLockNudgeSoon(900); return; } ensureAudioRunning(); setInstrument("piano"); };
btnTrumpet.onclick = () => { if(!isLoggedIn){ showLockNudge(); hideLockNudgeSoon(900); return; } ensureAudioRunning(); setInstrument("trumpet"); };
btnStrings.onclick = () => { if(!isLoggedIn){ showLockNudge(); hideLockNudgeSoon(900); return; } ensureAudioRunning(); setInstrument("strings"); };
btnSynth.onclick   = () => { if(!isLoggedIn){ showLockNudge(); hideLockNudgeSoon(900); return; } ensureAudioRunning(); setInstrument("synth"); };


/* -------------------- DRUMS UI -------------------- */

/*
  Radio-toggle drum logic:
  activeDrumStyle: "techno" | "dnb" | null
  - default: "techno"
  - click active => null (all muted)
  - click other  => switch (mutual exclusive)
*/
let activeDrumStyle = "techno";

function setDrumsMuted(m){
  drumsMuted = !!m;

  // Keep the legacy button synced (it is hidden via CSS, but leaving it in-place preserves layout).
  if(drumMuteBtnEl){
    drumMuteBtnEl.classList.toggle("muted", drumsMuted);
    drumMuteBtnEl.textContent = drumsMuted ? "🔇" : "🔊";
    drumMuteBtnEl.setAttribute("aria-pressed", String(!drumsMuted));
    drumMuteBtnEl.setAttribute("aria-hidden", "true");
    drumMuteBtnEl.title = drumsMuted ? "Unmute drums" : "Mute drums";
  }

  // If audio is running, fade the drum bus smoothly
  if(audioCtx && drumBus){
    const now = audioCtx.currentTime;
    const target = drumsMuted ? 0.0001 : 0.92;
    try{
      drumBus.gain.cancelScheduledValues(now);
      drumBus.gain.setValueAtTime(drumBus.gain.value, now);
      drumBus.gain.linearRampToValueAtTime(target, now + 0.03);
    }catch(e){}
  }
}

/*
  The audio engine uses drumStyle = "techhouse" or "dnb".
  Map activeDrumStyle -> drumStyle, and update button visuals.
*/
function syncAudioAndUI(){
  const isMuted = (activeDrumStyle == null);

  // Audio: mute/unmute the drum bus
  setDrumsMuted(isMuted);

  // Audio: pick which pattern to play when unmuted
  if(activeDrumStyle === "dnb"){
    drumStyle = "dnb";
  }else{
    drumStyle = "techhouse"; // "techno" UI maps to the existing techhouse pattern
  }

  // UI: selected state
  if(drumStyleTechEl && drumStyleDnBEl){
    const techOn = (activeDrumStyle === "techno");
    const dnbOn  = (activeDrumStyle === "dnb");

    drumStyleTechEl.classList.toggle("selected", techOn);
    drumStyleDnBEl.classList.toggle("selected", dnbOn);

    drumStyleTechEl.setAttribute("aria-pressed", String(techOn));
    drumStyleDnBEl.setAttribute("aria-pressed", String(dnbOn));
  }
}

// Function called when a drum button (style) is clicked
function handleDrumClick(clickedStyle){
  // Ensure audio exists if the user is trying to hear drums.
  getAudio();
  ensureAudioRunning();

  if(activeDrumStyle === clickedStyle){
    activeDrumStyle = null; // toggle off
  }else{
    activeDrumStyle = clickedStyle; // switch style
  }
  syncAudioAndUI();
}

if(drumStyleTechEl) drumStyleTechEl.onclick = () => handleDrumClick("techno");
if(drumStyleDnBEl)  drumStyleDnBEl.onclick  = () => handleDrumClick("dnb");

// Init: Techno selected by default (unmuted state), but actual sound will only start after first user gesture.
syncAudioAndUI();

/* -------------------- LOCKED UI (Login nudges) -------------------- */
const loginCtaWrapEl = document.getElementById("loginCtaWrap");

let lockNudgeHideT = null;
function showLockNudge(){
  if(!loginCtaWrapEl) return;
  clearTimeout(lockNudgeHideT);
  loginCtaWrapEl.classList.add("pulsing");
}
function hideLockNudgeSoon(ms=0){
  if(!loginCtaWrapEl) return;
  clearTimeout(lockNudgeHideT);
  lockNudgeHideT = setTimeout(() => {
    loginCtaWrapEl.classList.remove("pulsing");
  }, ms);
}
function bindLockedNudge(el){
  if(!el) return;
  el.addEventListener("mouseenter", () => { if(!isLoggedIn) showLockNudge(); });
  el.addEventListener("mouseleave", () => { if(!isLoggedIn) hideLockNudgeSoon(0); });
  el.addEventListener("pointerdown", () => { if(!isLoggedIn){ showLockNudge(); hideLockNudgeSoon(900); } }, { passive:true });
}

/* Make login links return to this page */
function updateLoginLinks(){
  const current = (location.pathname.split("/").pop() || "index.html");
  document.querySelectorAll("a.loginLink").forEach(a => {
    a.href = "login.html?return=" + encodeURIComponent(current);
  });
}
updateLoginLinks();

// Make the header Login button act as Logout when signed in
(function(){
  const btn = document.getElementById("toolLoginBtn");
  if(!btn) return;
  btn.addEventListener("click", (e) => {
    if(isLoggedIn){
      e.preventDefault();
      logout();
    }
  });
})();

function applyLockState(){
  const locked = !isLoggedIn;
  const robotLogoEl = document.getElementById("robotLogo");
  if(robotLogoEl) robotLogoEl.style.display = "flex";

  // If we just moved into Guest/locked mode and a locked note-length was selected,
  // bump back to a free length (16th).
  if(locked && typeof LOCKED_STEPS !== "undefined" && LOCKED_STEPS.has(selectedSteps)){
    selectedSteps = 1;
  }

  // Rebuild tool buttons so their locked state updates on login/logout.
  try{ buildTools(); }catch(e){}

  const instWasLocked = !!(instButtonsEl && instButtonsEl.classList.contains("locked"));

  if(tempoControlsEl) tempoControlsEl.classList.toggle("locked", locked);
  if(instButtonsEl) instButtonsEl.classList.toggle("locked", locked);
  if(instButtonsEl && instWasLocked && !locked){
    instButtonsEl.classList.add("justUnlocked");
    setTimeout(()=>instButtonsEl.classList.remove("justUnlocked"), 700);
  }
  if(cameraBtnEl) cameraBtnEl.classList.toggle("locked", locked);
  document.body.classList.toggle("loggedIn", isLoggedIn);

  // Swap Login -> Logout (bright red) when signed in
  const toolLoginBtnEl = document.getElementById("toolLoginBtn");
  if(toolLoginBtnEl){
    if(isLoggedIn){
      toolLoginBtnEl.textContent = "Logout";
      toolLoginBtnEl.classList.add("logout");
      toolLoginBtnEl.setAttribute("href", "#");
    }else{
      toolLoginBtnEl.textContent = "Login";
      toolLoginBtnEl.classList.remove("logout");
      toolLoginBtnEl.setAttribute("href", "login.html");
    }
  }
}
// Apply lock state without triggering any layout/position functions
applyLockState();
// Ensure the correct state when the browser restores the page from cache
window.addEventListener('pageshow', () => {
  try{ isLoggedIn = sessionStorage.getItem('kidseq_logged_in') === '1'; }catch(e){ isLoggedIn = false; }
  if(loginCtaWrapEl) loginCtaWrapEl.classList.remove('pulsing');
  applyLockState();
});

function logout(){
  // Sign out of Firebase (if the auth module is loaded)
  try{ if(window.__doFirebaseSignOut){ window.__doFirebaseSignOut(); } }catch(e){}
// Clear session flags (so closing/reopening returns to locked landing)
  try{ sessionStorage.removeItem('kidseq_logged_in'); }catch(e){}
  try{ sessionStorage.removeItem('kidseq_user_email'); }catch(e){}
  try{ sessionStorage.removeItem('kidseq_user_uid'); }catch(e){}

  isLoggedIn = false;
  try{ stop(); }catch(e){}

  // Restore the locked/landing UI immediately
  if(loginCtaWrapEl) loginCtaWrapEl.classList.remove('pulsing');
  applyLockState();
  updateLoginLinks();
}
/* Bind hover nudges for locked groups */
bindLockedNudge(cameraBtnEl);
bindLockedNudge(tempoUpBtnEl);
bindLockedNudge(tempoDownBtnEl);
bindLockedNudge(tempoBox);

[btnPiano, btnTrumpet, btnStrings, btnSynth].forEach(bindLockedNudge);

/* Prime audio */
function primeAudioOnce(){
  if (audioPrimed) return;
  audioPrimed = true;
  getAudio();
}
window.addEventListener("pointerdown", primeAudioOnce, { once: true, passive: true });

window.addEventListener("touchstart", primeAudioOnce, { once: true, passive: true });
window.addEventListener("mousedown", primeAudioOnce, { once: true, passive: true });
window.addEventListener("keydown", primeAudioOnce, { once: true });

/* Prevent focus caret */
window.addEventListener("pointerdown", () => {
  if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
}, { passive: true });

/* Spacebar start/stop */
window.addEventListener("keydown", (e) => {
  if (e.code !== "Space") return;
  e.preventDefault();
  if (timer || startTimeout) stop();
  else play();
});

/* -------------------- PLAYHEAD WOBBLE SCALING -------------------- */
function clamp01(x){ return Math.max(0, Math.min(1, x)); }
function setPlayheadWobbleFromTempo(t){
  const ratio = (t >= 90) ? 1 : clamp01((t - 40) / (90 - 40));
  document.documentElement.style.setProperty("--wiggleDeg",   (1.2 * ratio).toFixed(3) + "deg");
  document.documentElement.style.setProperty("--wiggleScale", (0.01 * ratio).toFixed(4));
}

/* -------------------- RESPONSIVE FIT -------------------- */
/* Single source of truth:
   - The internal "design stage" size is defined by CSS vars --stageW/--stageH (defaults in :root).
   - We scale the whole stage to fit the *visible* viewport (VisualViewport on iOS) so refresh/devtools cannot flip layout. */
function __ksStageSize(){
  const cs = getComputedStyle(document.documentElement);
  const stageW = parseFloat(cs.getPropertyValue('--stageW')) || 1600;
  const stageH = parseFloat(cs.getPropertyValue('--stageH')) || 900;
  return { stageW, stageH };
}
function __ksViewport(){
  const vv = window.visualViewport;
  return {
    vw: vv ? vv.width : window.innerWidth,
    vh: vv ? vv.height : window.innerHeight,
    offX: vv ? vv.offsetLeft : 0,
    offY: vv ? vv.offsetTop : 0
  };
}

// Keep CSS in sync with the *visible* viewport so the fixed #viewport never ends up a few pixels taller
// than what the user can actually see on iOS (common source of tiny scroll in landscape).
function __ksSyncViewportVars(){
  const vv = window.visualViewport;
  const vvw = vv ? vv.width  : window.innerWidth;
  const vvh = vv ? vv.height : window.innerHeight;
  document.documentElement.style.setProperty('--vvw', vvw + 'px');
  document.documentElement.style.setProperty('--vvh', vvh + 'px');

  // On iPhone Safari the visual viewport can be offset vertically when the toolbar is visible.
  // Shift the fixed #viewport down so its content starts below the toolbar.
  const vpEl = document.getElementById('viewport');
  if(vpEl && vv){
    const oY = vv.offsetTop || 0;
    // Override inset:0 with explicit positioning so the viewport matches the visible area
    vpEl.style.top = oY + 'px';
    vpEl.style.bottom = 'auto';
    vpEl.style.height = vvh + 'px';
    vpEl.style.width = vvw + 'px';
    vpEl.style.left = (vv.offsetLeft || 0) + 'px';
    vpEl.style.right = 'auto';
  }
}

function fitToViewport(){
  const { stageW: vw, stageH: vh } = __ksStageSize();

  const headerH = 92;
  const controlsH = 70;
  const vMargins = 24;
  const gridExtra = 20;

  let toolW = Math.min(210, Math.max(150, Math.floor(vw * 0.27)));
  let rightW = Math.min(115, Math.max(96, Math.floor(vw * 0.16)));

  const outerPadding = 24;
  const gaps = 14 * 2;
  const maxCellByWidth = Math.floor(
    (vw - toolW - rightW - outerPadding - gaps - (cols - 1) * GAP - gridExtra) / cols
  );

  const availableH = vh - headerH - controlsH - vMargins - gridExtra;
  const maxCellByHeight = Math.floor((availableH - (rows - 1) * GAP) / rows);

  let cell = Math.min(maxCellByWidth, maxCellByHeight);
  cell = Math.max(26, Math.min(64, cell));

  if(cell <= 36){
    toolW = Math.max(150, Math.floor(vw * 0.28));
    rightW = Math.max(96, Math.floor(vw * 0.16));
  }

  document.documentElement.style.setProperty("--toolW", toolW + "px");
  document.documentElement.style.setProperty("--rightW", rightW + "px");
  document.documentElement.style.setProperty("--cell", cell + "px");
  CELL = cell;

  let __titleInsetPx = 0;
  // The title box is now part of the left column (#tools). Only compute an inset
  // when the title is in the top header bar (legacy layout).
  if(titleBoxEl && titleBoxEl.closest && titleBoxEl.closest('#topBar')){
    const toolsRect = toolsEl.getBoundingClientRect();
    const pageLeft = 14;
    __titleInsetPx = Math.max(0, Math.round(toolsRect.left - pageLeft));
  }
  document.documentElement.style.setProperty("--titleInset", __titleInsetPx + "px");

  const controlsRect = controlsEl.getBoundingClientRect();
  const mainRect = mainLayoutEl.getBoundingClientRect();
  document.documentElement.style.setProperty("--rightLift", Math.max(0, Math.round(mainRect.top - controlsRect.top)) + "px");

  const playBtn = controlsEl.querySelector(".bigBtn");
  const contentWrap = document.getElementById('contentWrap');
  const titleInsideContent = !!(contentWrap && titleBoxEl && contentWrap.contains(titleBoxEl));

  // IMPORTANT:
  // The --contentLift system was designed for the original layout where the title lived in #topBar
  // (outside #contentWrap). If the title is moved into the left column, lifting #contentWrap lifts
  // BOTH the title and the controls, so the relative delta never changes and the lift can "run away".
  if (playBtn && !titleInsideContent) {
    const currentLift = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--contentLift")) || 0;

    const playRect  = playBtn.getBoundingClientRect();
    const titleRect = titleBoxEl.getBoundingClientRect();

    const playCenter  = playRect.top  + playRect.height / 2;
    const titleCenter = titleRect.top + titleRect.height / 2;

    const delta = Math.round(playCenter - titleCenter);
    let newLift = Math.round(currentLift + delta);
    newLift = Math.max(0, Math.min(260, newLift));
    document.documentElement.style.setProperty("--contentLift", newLift + "px");
  }
}
function positionRobotLogo(){
  const logo = document.getElementById('robotLogo');
  const toolsList = document.getElementById('toolsList');
  const loginWrap = document.getElementById('loginCtaWrap');
  const seqWrap = document.getElementById('sequencerWrapper') || document.getElementById('sequencer');
  const page = document.getElementById('page');
  const root = document.documentElement;
  if(!logo || !toolsList || !seqWrap || !page) return;

  // When the stage is scaled we apply a transform on #page. We must compute positions in the *page*
  // coordinate system (unscaled), not viewport coordinates.
  const isScaled = root.classList.contains('stageScaled') || root.classList.contains('tabletScaled');
  const prevTransform = isScaled ? page.style.transform : null;
  if(isScaled) page.style.transform = '';

  const pageRect = page.getBoundingClientRect();
  const toolsRect = toolsList.getBoundingClientRect();
  const gridRect  = seqWrap.getBoundingClientRect();

  // Convert viewport rects -> page-local coords
  const tools = {
    left: toolsRect.left - pageRect.left,
    top: toolsRect.top - pageRect.top,
    width: toolsRect.width,
    height: toolsRect.height,
    bottom: toolsRect.bottom - pageRect.top
  };
  const grid = {
    bottom: gridRect.bottom - pageRect.top
  };

  // Desired size (px) from CSS variable
  const desired = Math.round((parseFloat(getComputedStyle(document.body).getPropertyValue('--robotSize')) || 180));

  // Anchor: always keep it below the note-length buttons.
  let topMin = tools.bottom + 18;

  // If the Login button exists and is visible, keep it below that too.
  if(loginWrap){
    const r = loginWrap.getBoundingClientRect();
    if(r.width > 0 && r.height > 0){
      const rBottom = r.bottom - pageRect.top;
      topMin = Math.max(topMin, rBottom + 28);
    }
  }

  // Align the badge to the bottom of the grid (but never above topMin)
  const bottom = grid.bottom;
  const nudgeY = 6;

  const avail = Math.floor(bottom - topMin);
  if (avail < 40) { if(isScaled) page.style.transform = prevTransform; return; }

  // Use the CSS-defined size (do not resize dynamically — requested behavior).
  // We still *position* the logo, but we leave width/height/padding alone.
  const cssSize = parseFloat(getComputedStyle(logo).width);
  const size = Number.isFinite(cssSize) && cssSize > 0 ? cssSize : Math.max(40, Math.min(desired, avail));
  // Center horizontally to the note-length tool column (page-local)
  const xCenter = tools.left + tools.width / 2;

  // Prefer aligning bottom to the grid; clamp to topMin
  const top = Math.round(bottom - size + nudgeY);
  logo.style.left = Math.round(xCenter - size/2) + 'px';
  logo.style.top  = Math.max(Math.round(topMin), top) + 'px';

  if(isScaled) page.style.transform = prevTransform;
}



/* -------------------- AUDIO -------------------- */
function ensureAudioRunning(){
  if (!audioCtx) return;
  if (audioCtx.state === "suspended") audioCtx.resume().catch(()=>{});
}

function trackNode(node){
  liveNodes.add(node);
  node.onended = () => liveNodes.delete(node);
}

function makeHallImpulse(ctx, seconds, decay){
  const rate = ctx.sampleRate;
  const length = Math.floor(rate * seconds);
  const impulse = ctx.createBuffer(2, length, rate);
  for(let ch=0; ch<2; ch++){
    const data = impulse.getChannelData(ch);
    for(let i=0;i<length;i++){
      const t = i / length;
      const env = Math.pow(1 - t, decay);
      data[i] = (Math.random()*2 - 1) * env * (ch === 0 ? 1 : 0.96);
    }
  }
  return impulse;
}

function makeNoiseBuffer(ctx){
  const len = Math.max(1, Math.floor(ctx.sampleRate * 1.0));
  const buf = ctx.createBuffer(1, len, ctx.sampleRate);
  const data = buf.getChannelData(0);
  for(let i=0;i<len;i++) data[i] = (Math.random() * 2 - 1);
  return buf;
}

function playKick(at, vel=1){
  if(!audioCtx || !drumBus) return;
  lastAudioActivityAt = performance.now();

  const ctx = audioCtx;

  // Main body
  const osc = ctx.createOscillator();
  const g = ctx.createGain();

  osc.type = "sine";
  // Faster, deeper sweep = more punch
  osc.frequency.setValueAtTime(190, at);
  osc.frequency.exponentialRampToValueAtTime(62, at + 0.065);
  osc.frequency.exponentialRampToValueAtTime(48, at + 0.135);

  // Envelope
  const peak = 1.10 * vel;
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(peak, at + 0.003);
  g.gain.exponentialRampToValueAtTime(0.0001, at + 0.17);

  // Short tonal transient (no noise "click")
  const tosc = ctx.createOscillator();
  const tg = ctx.createGain();
  tosc.type = "triangle";
  tosc.frequency.setValueAtTime(320, at);
  tosc.frequency.exponentialRampToValueAtTime(140, at + 0.030);

  tg.gain.setValueAtTime(0.0001, at);
  tg.gain.exponentialRampToValueAtTime(0.22 * vel, at + 0.0015);
  tg.gain.exponentialRampToValueAtTime(0.0001, at + 0.030);

  // Mild saturation to make it feel punchier
  const shaper = ctx.createWaveShaper();
  shaper.oversample = "4x";
  const N = 256;
  const curve = new Float32Array(N);
  const amt = 2.0;
  for(let i=0;i<N;i++){
    const x = (i / (N - 1)) * 2 - 1;
    curve[i] = Math.tanh(amt * x);
  }
  shaper.curve = curve;

  const lp = ctx.createBiquadFilter();
  lp.type = "lowpass";
  lp.frequency.setValueAtTime(9000, at);
  lp.Q.setValueAtTime(0.7, at);

  osc.connect(g);
  g.connect(shaper);

  tosc.connect(tg);
  tg.connect(shaper);

  shaper.connect(lp);
  lp.connect(drumBus);

  trackNode(osc);
  trackNode(tosc);

  osc.start(at);
  osc.stop(at + 0.22);

  tosc.start(at);
  tosc.stop(at + 0.06);
}

function playPerc(at, vel=1){
  if(!audioCtx || !drumBus) return;
  lastAudioActivityAt = performance.now();

  const ctx = audioCtx;
  const osc = ctx.createOscillator();
  const g = ctx.createGain();

  osc.type = "triangle";
  osc.frequency.setValueAtTime(320, at);
  osc.frequency.exponentialRampToValueAtTime(170, at + 0.06);

  const peak = 0.22 * vel;
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(peak, at + 0.004);
  g.gain.exponentialRampToValueAtTime(0.0001, at + 0.10);

  const bp = ctx.createBiquadFilter();
  bp.type = "bandpass";
  bp.frequency.setValueAtTime(520, at);
  bp.Q.setValueAtTime(2.2, at);

  osc.connect(bp);
  bp.connect(g);
  g.connect(drumBus);

  trackNode(osc);
  osc.start(at);
  osc.stop(at + 0.14);
}

function playSnare(at, vel=1){
  if(!audioCtx || !drumBus) return;
  lastAudioActivityAt = performance.now();

  const ctx = audioCtx;

  const src = ctx.createBufferSource();
  src.buffer = drumNoise || makeNoiseBuffer(ctx);

  const hp = ctx.createBiquadFilter();
  hp.type = "highpass";
  hp.frequency.setValueAtTime(700, at);

  const bp = ctx.createBiquadFilter();
  bp.type = "bandpass";
  bp.frequency.setValueAtTime(1800, at);
  bp.Q.setValueAtTime(0.9, at);

  const g = ctx.createGain();
  const peak = 0.42 * vel;
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(peak, at + 0.003);
  g.gain.exponentialRampToValueAtTime(0.0001, at + 0.13);

  src.connect(hp);
  hp.connect(bp);
  bp.connect(g);
  g.connect(drumBus);

  // Small tonal body
  const body = ctx.createOscillator();
  body.type = "triangle";
  body.frequency.setValueAtTime(210, at);
  body.frequency.exponentialRampToValueAtTime(150, at + 0.09);

  const bg = ctx.createGain();
  bg.gain.setValueAtTime(0.0001, at);
  bg.gain.exponentialRampToValueAtTime(0.10 * vel, at + 0.004);
  bg.gain.exponentialRampToValueAtTime(0.0001, at + 0.10);

  body.connect(bg);
  bg.connect(drumBus);

  trackNode(src);
  trackNode(body);

  src.start(at);
  src.stop(at + 0.18);

  body.start(at);
  body.stop(at + 0.14);
}

function playClap(at, vel=1){
  if(!audioCtx || !drumBus) return;
  lastAudioActivityAt = performance.now();

  const ctx = audioCtx;
  const bursts = [0.0, 0.014, 0.028];

  for(let i=0;i<bursts.length;i++){
    const t = at + bursts[i];

    const src = ctx.createBufferSource();
    src.buffer = drumNoise || makeNoiseBuffer(ctx);

    const hp = ctx.createBiquadFilter();
    hp.type = "highpass";
    hp.frequency.setValueAtTime(950, t);

    const bp = ctx.createBiquadFilter();
    bp.type = "bandpass";
    bp.frequency.setValueAtTime(2100, t);
    bp.Q.setValueAtTime(0.8, t);

    const g = ctx.createGain();
    const peak = (i == 0 ? 0.32 : 0.22) * vel;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + 0.002);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.055);

    src.connect(hp);
    hp.connect(bp);
    bp.connect(g);
    g.connect(drumBus);

    trackNode(src);
    src.start(t);
    src.stop(t + 0.10);
  }
}

function playHatClosed(at, vel=1){
  if(!audioCtx || !drumBus) return;
  lastAudioActivityAt = performance.now();

  const ctx = audioCtx;

  const src = ctx.createBufferSource();
  src.buffer = drumNoise || makeNoiseBuffer(ctx);

  const hp = ctx.createBiquadFilter();
  hp.type = "highpass";
  hp.frequency.setValueAtTime(7200, at);

  const bp = ctx.createBiquadFilter();
  bp.type = "bandpass";
  bp.frequency.setValueAtTime(9400, at);
  bp.Q.setValueAtTime(0.7, at);

  const g = ctx.createGain();
  const peak = 0.18 * vel;
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(peak, at + 0.001);
  g.gain.exponentialRampToValueAtTime(0.0001, at + 0.045);

  src.connect(hp);
  hp.connect(bp);
  bp.connect(g);
  g.connect(drumBus);

  trackNode(src);
  src.start(at);
  src.stop(at + 0.08);
}

function playHatOpen(at, vel=1){
  if(!audioCtx || !drumBus) return;
  lastAudioActivityAt = performance.now();

  const ctx = audioCtx;

  const src = ctx.createBufferSource();
  src.buffer = drumNoise || makeNoiseBuffer(ctx);

  const hp = ctx.createBiquadFilter();
  hp.type = "highpass";
  hp.frequency.setValueAtTime(6000, at);

  const bp = ctx.createBiquadFilter();
  bp.type = "bandpass";
  bp.frequency.setValueAtTime(8600, at);
  bp.Q.setValueAtTime(0.6, at);

  const g = ctx.createGain();
  const peak = 0.16 * vel;
  g.gain.setValueAtTime(0.0001, at);
  g.gain.exponentialRampToValueAtTime(peak, at + 0.002);
  g.gain.exponentialRampToValueAtTime(0.0001, at + 0.20);

  src.connect(hp);
  hp.connect(bp);
  bp.connect(g);
  g.connect(drumBus);

  trackNode(src);
  src.start(at);
  src.stop(at + 0.26);
}

function playDrumsAtStep(s){
  if(drumsMuted) return;
  if(!audioCtx || !drumBus) return;

  const pat = DRUM_PATTERNS[drumStyle] || DRUM_PATTERNS.techhouse;
  const stepDur = stepDurationSec();

  // Subtle shuffle for Tech-House hats only (keeps the playhead/grid exact)
  const swing = (drumStyle === "techhouse") ? 0.08 : 0.0;
  const offs = ((drumStyle === "techhouse") && (s % 2 === 1)) ? (stepDur * swing) : 0;

  const t = audioCtx.currentTime + 0.002 + offs;

  const k = (pat.kick && pat.kick[s]) ? pat.kick[s] : 0;
  if(k > 0) playKick(t, k);

  if(drumStyle === "techhouse"){
    const c = (pat.clap && pat.clap[s]) ? pat.clap[s] : 0;
    if(c > 0) playClap(t, c);
  }else{
    const sn = (pat.snare && pat.snare[s]) ? pat.snare[s] : 0;
    if(sn > 0) playSnare(t, sn);
  }

  const hc = (pat.hatC && pat.hatC[s]) ? pat.hatC[s] : 0;
  if(hc > 0) playHatClosed(t, hc);

  const ho = (pat.hatO && pat.hatO[s]) ? pat.hatO[s] : 0;
  if(ho > 0) playHatOpen(t, ho);
}

function makeInstrumentBuses(ctx, masterOut){
  const pianoIR   = makeHallImpulse(ctx, 1.60, 2.4);
  const trumpetIR = makeHallImpulse(ctx, 0.70, 2.0);
  const stringsIR = makeHallImpulse(ctx, 1.30, 2.5);
  const synthIR   = makeHallImpulse(ctx, 0.45, 2.0);

  function buildBus(ir, dryAmt, wetAmt){
    const input = ctx.createGain();

    const dry = ctx.createGain();
    dry.gain.value = dryAmt;

    const wet = ctx.createGain();
    wet.gain.value = wetAmt;

    const conv = ctx.createConvolver();
    conv.buffer = ir;

    input.connect(dry);
    input.connect(conv);
    conv.connect(wet);

    dry.connect(masterOut);
    wet.connect(masterOut);

    return { input };
  }

  return {
    piano:   buildBus(pianoIR,   0.72, 0.46),
    trumpet: buildBus(trumpetIR, 0.90, 0.12),
    strings: buildBus(stringsIR, 0.76, 0.32),
    synth:   buildBus(synthIR,   0.92, 0.12)
  };
}


// iOS Safari: when the hardware silent/ringer switch is OFF, WebAudio may be muted.
// Workaround: start a looping *silent video* from a user gesture and keep it playing.
// Requires `silent.mp4` deployed next to this HTML.
let __iosSilentVideoStarted = false;
function iosStartSilentVideo(){
  const ua = navigator.userAgent || "";
  const isIOS = /iP(hone|ad|od)/.test(ua);
  if(!isIOS) return;
  if(__iosSilentVideoStarted) return;

  const v = document.getElementById("iosSilentVideo");
  if(!v) return;

  // The file must contain silence; keep element unmuted so iOS treats it as a real media session.
  v.muted = false;
  v.volume = 1.0;

  try{
    const p = v.play();
    if(p && typeof p.then === "function"){
      p.then(() => { __iosSilentVideoStarted = true; })
       .catch(() => { __iosSilentVideoStarted = false; });
    }else{
      __iosSilentVideoStarted = true;
    }
  }catch(e){
    __iosSilentVideoStarted = false;
  }
}

function getAudio(){
  iosStartSilentVideo();
  if(!audioCtx){
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();

    
    window.audioCtx = audioCtx;
masterGain = audioCtx.createGain();
    
    window.masterGain = masterGain;
masterGain.gain.setValueAtTime(1, audioCtx.currentTime);

    masterComp = audioCtx.createDynamicsCompressor();
    masterComp.threshold.setValueAtTime(-18, audioCtx.currentTime);
    masterComp.knee.setValueAtTime(18, audioCtx.currentTime);
    masterComp.ratio.setValueAtTime(3.4, audioCtx.currentTime);
    masterComp.attack.setValueAtTime(0.004, audioCtx.currentTime);
    masterComp.release.setValueAtTime(0.12, audioCtx.currentTime);

    masterGain.connect(masterComp);
    masterComp.connect(audioCtx.destination);

    bus = makeInstrumentBuses(audioCtx, masterGain);

    // Drums: dedicated bus (starts muted)
    drumBus = audioCtx.createGain();
    drumBus.gain.setValueAtTime(drumsMuted ? 0.0001 : 0.92, audioCtx.currentTime);
    drumBus.connect(masterGain);

    // Shared noise buffer for hats/snare/claps
    drumNoise = makeNoiseBuffer(audioCtx);

    warmUpAudio(2);
  }
  ensureAudioRunning();
}

function warmUpAudio(iterations=2){
  // iOS Safari: warm the audio graph WITHOUT producing any audible ticks/clicks.
  // Use a 1-sample silent buffer through a zero-gain node.
  try{
    const ctx = getAudio();
    if(!ctx) return;

    const g = ctx.createGain();
    g.gain.setValueAtTime(0, ctx.currentTime);
    g.connect(ctx.destination);

    for(let i=0;i<iterations;i++){
      const b = ctx.createBuffer(1, 1, ctx.sampleRate);
      const s = ctx.createBufferSource();
      s.buffer = b; // silence
      s.connect(g);
      s.start();
      s.stop(ctx.currentTime + 0.001);
    }
  }catch(e){}
}

function hardResetAudioEngine(){
  try{
    if(audioCtx){
      try { audioCtx.close(); } catch(e){}
    }
  }catch(e){}

  audioCtx = null;
  masterGain = null;
  masterComp = null;
  bus = null;
  drumBus = null;
  drumNoise = null;

  for(const n of Array.from(liveNodes)){
    try { n.stop(0); } catch(e){}
    liveNodes.delete(n);
  }

  getAudio();
  warmUpAudio(4);
}

function sleep(ms){ return new Promise(res => setTimeout(res, ms)); }

async function ensureAudioReady(){
  getAudio();

  const nowMs = performance.now();
  const audioIdleMs = (lastAudioActivityAt == null) ? Infinity : (nowMs - lastAudioActivityAt);

  if(audioIdleMs > 25000){
    hardResetAudioEngine();
  }

  if(!audioCtx) return;

  try{
    if(audioCtx.state !== "running"){
      const p = audioCtx.resume();
      await p;
    }
  }catch(e){}

  const t1 = audioCtx.currentTime;
  await sleep(40);
  const t2 = audioCtx.currentTime;

  if(!(t2 > t1 + 0.0005)){
    hardResetAudioEngine();
    if(audioCtx){
      try{
        if(audioCtx.state !== "running") await audioCtx.resume();
      }catch(e){}
      warmUpAudio(4);
    }
  }else{
    warmUpAudio(2);
  }
}

function stopAllAudioNow(){
  if(!audioCtx || !masterGain) return;

  for (const n of Array.from(liveNodes)){
    try { n.stop(0); } catch(e) {}
    liveNodes.delete(n);
  }

  const now = audioCtx.currentTime;
  masterGain.gain.cancelScheduledValues(now);
  masterGain.gain.setValueAtTime(masterGain.gain.value, now);
  masterGain.gain.linearRampToValueAtTime(0.0001, now + 0.02);
  masterGain.gain.setValueAtTime(1, now + 0.03);
}

function stepDurationSec(){
  return (60 / tempo) / 4;
}

/* -------------------- INSTRUMENT UI -------------------- */
function setInstrument(name){
  instrument = name;

  const all = [btnPiano, btnTrumpet, btnStrings, btnSynth];
  all.forEach(b => { b.classList.remove("selected","notSelected"); });

  const map = { piano: btnPiano, trumpet: btnTrumpet, strings: btnStrings, synth: btnSynth };
  const selected = map[name];
  selected.classList.add("selected");
  all.forEach(b => { if(b !== selected) b.classList.add("notSelected"); });
}

/* -------------------- TOOLS UI -------------------- */
function buildTools(){
  if(!toolsListEl) return;
  toolsListEl.innerHTML = "";

  toolSteps.forEach((t) => {
    const tool = document.createElement("div");
    tool.className = "tool";

    const isLocked = (!isLoggedIn) && LOCKED_STEPS.has(t.steps);
    if(isLocked){
      tool.classList.add("locked");
      tool.setAttribute("aria-disabled","true");
    }

    const sym = document.createElement("div");
    sym.className = "toolSymbol " + (t.symClass || "");
    if(t.svg){
      sym.innerHTML = t.svg;
    }else{
      sym.textContent = t.symbol;
    }

    const barWrap = document.createElement("div");
    barWrap.className = "toolBarWrap";

    const bar = document.createElement("div");
    bar.className = "toolBar";
    bar.style.setProperty("--fill", (t.steps / 16).toFixed(4));
    bar.style.setProperty("--divs", String(t.divs));

    const fill = document.createElement("div");
    fill.className = "toolBarFill";

    const divs = document.createElement("div");
    divs.className = "toolBarDivs";
    if(t.steps === 16) divs.style.display = "none";

    bar.appendChild(fill);
    bar.appendChild(divs);

    const lab = document.createElement("div");
    lab.className = "toolLabel";
    lab.textContent = t.label;
    if(t.steps === 16) lab.classList.add("comicWhole");

    barWrap.appendChild(bar);
    barWrap.appendChild(lab);

    tool.appendChild(sym);
    tool.appendChild(barWrap);

        if(isLocked){
      bindLockedNudge(tool);
    }
    tool.onclick = () => {
      if(isLocked){
        showLockNudge();
        hideLockNudgeSoon(900);
        return;
      }
      selectedSteps = t.steps;
      toolsListEl.querySelectorAll(".tool").forEach(x => x.classList.remove("selected"));
      tool.classList.add("selected");
    };

    if(t.steps === selectedSteps) tool.classList.add("selected");
    toolsListEl.appendChild(tool);
  });
}

/* -------------------- GRID -------------------- */
let noteLayerEls = [];
let nextId = 1;

function buildGrid(){
  sequencerEl.innerHTML = "";
  noteLayerEls = [];

  for(let r=0;r<rows;r++){
    const wrap = document.createElement("div");
    wrap.className = "rowWrap";
    wrap.style.width = `${cols * CELL + (cols-1) * GAP}px`;

    const grid = document.createElement("div");
    grid.className = "grid";
    grid.style.gridTemplateColumns = `repeat(${cols}, var(--cell))`;

    const layer = document.createElement("div");
    layer.className = "noteLayer";

    for(let c=0;c<cols;c++){
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.onmousedown = (e) => e.preventDefault();
      cell.onclick = () => onCellClick(r, c);
      grid.appendChild(cell);
    }

    wrap.appendChild(grid);
    wrap.appendChild(layer);
    sequencerEl.appendChild(wrap);

    noteLayerEls.push(layer);
  }

  redrawAllNotes();
}

function canPlace(r, start, len){
  if(start < 0) return false;
  if(start + len > cols) return false;
  for(let c=start; c<start+len; c++){
    if(occ[r][c] !== null) return false;
  }
  return true;
}

function placeNote(r, start, len){
  const id = nextId++;
  notesByRow[r].push({ id, start, len });
  for(let c=start; c<start+len; c++) occ[r][c] = id;
}

function deleteNoteById(r, id){
  const idx = notesByRow[r].findIndex(n => n.id === id);
  if(idx === -1) return;
  const { start, len } = notesByRow[r][idx];
  for(let c=start; c<start+len; c++) occ[r][c] = null;
  notesByRow[r].splice(idx, 1);
}

function overlappingNoteIds(r, start, len){
  const set = new Set();
  for(let c=start; c<start+len; c++){
    const id = occ[r][c];
    if(id !== null) set.add(id);
  }
  return set;
}

function smartPlaceNote(r, clickCol, len){
  let baseStart = Math.min(clickCol, cols - len);
  baseStart = Math.max(0, baseStart);

  for(let start = baseStart; start >= 0; start--){
    if(start + len > cols) continue;
    if(canPlace(r, start, len)){
      placeNote(r, start, len);
      return;
    }
  }

  const overlaps = overlappingNoteIds(r, baseStart, len);
  overlaps.forEach(id => deleteNoteById(r, id));
  placeNote(r, baseStart, len);
}

function onCellClick(r, c){
  const existing = occ[r][c];
  if(existing !== null){
    pushUndo();
    deleteNoteById(r, existing);
    redrawRowNotes(r);
    return;
  }

  pushUndo();
  smartPlaceNote(r, c, selectedSteps);
  redrawRowNotes(r);
}

function redrawAllNotes(){
  for(let r=0;r<rows;r++) redrawRowNotes(r);
}

function redrawRowNotes(r){
  const layer = noteLayerEls[r];
  layer.innerHTML = "";

  for(const note of notesByRow[r]){
    const block = document.createElement("div");
    block.className = "noteBlock";
    block.dataset.id = String(note.id);

    const left = note.start * (CELL + GAP);
    const width = note.len * CELL + (note.len - 1) * GAP;

    block.style.left = `${left}px`;
    block.style.top = `0px`;
    block.style.width = `${width}px`;
    block.style.background = rowColors[r];

    block.onmousedown = (e) => e.preventDefault();

    block.onclick = (e) => {
      e.stopPropagation();
      pushUndo();
      deleteNoteById(r, note.id);
      redrawRowNotes(r);
    };

    layer.appendChild(block);
  }
}

/* -------------------- PLAYHEAD -------------------- */
function setPlayheadVisible(on){ playheadEl.style.display = on ? "block" : "none"; }
function setPlayheadPlaying(isPlaying){ playheadEl.classList.toggle("playing", isPlaying); }
function movePlayheadToStep(s){ playheadEl.style.left = `${s * (CELL + GAP)}px`; }
function resetPlayheadInstant(){
  playheadEl.style.transition = "none";
  movePlayheadToStep(0);
  void playheadEl.offsetWidth;
  playheadEl.style.transition = "left 70ms linear";
}

/* -------------------- ENVELOPE -------------------- */
function scheduleEnvelope(g, now, hold, attack, peak, sustain, release, decay1){
  g.gain.setValueAtTime(0.0001, now);
  g.gain.exponentialRampToValueAtTime(peak, now + attack);
  if(decay1 > 0){
    g.gain.exponentialRampToValueAtTime(sustain, now + attack + decay1);
  }else{
    g.gain.setValueAtTime(sustain, now + attack);
  }
  g.gain.setValueAtTime(sustain, now + hold);
  g.gain.exponentialRampToValueAtTime(0.0001, now + hold + release);
}

/* -------------------- INSTRUMENTS -------------------- */
function playPiano(freq, steps){
  const now = audioCtx.currentTime;
  const hold = steps * stepDurationSec();

  const release = Math.min(0.32, Math.max(0.16, hold * 0.12));
  const stopAt = now + hold + release + 0.20;

  const env = audioCtx.createGain();
  scheduleEnvelope(env, now, hold, 0.012, 0.70, 0.62, release, 0.03);

  const level = audioCtx.createGain();
  level.gain.setValueAtTime(LEVEL.piano, now);
  env.connect(level);

  const partials = [
    { mult: 1, amp: 0.34 },
    { mult: 2, amp: 0.24 },
    { mult: 3, amp: 0.18 },
    { mult: 4, amp: 0.13 },
    { mult: 5, amp: 0.09 },
    { mult: 6, amp: 0.06 },
    { mult: 8, amp: 0.04 }
  ];

  const mix = audioCtx.createGain();
  mix.gain.setValueAtTime(1.0, now);

  const oscs = [];
  for(const p of partials){
    const o = audioCtx.createOscillator();
    o.type = "sine";
    o.frequency.setValueAtTime(freq * p.mult, now);

    const g = audioCtx.createGain();
    g.gain.setValueAtTime(p.amp, now);

    o.connect(g);
    g.connect(mix);

    oscs.push(o);
  }

  const chiffBuf = audioCtx.createBuffer(1, Math.floor(audioCtx.sampleRate * 0.04), audioCtx.sampleRate);
  const data = chiffBuf.getChannelData(0);
  for(let i=0;i<data.length;i++){
    const t = i / data.length;
    data[i] = (Math.random()*2-1) * Math.pow(1 - t, 5);
  }
  const chiff = audioCtx.createBufferSource();
  chiff.buffer = chiffBuf;

  const chiffBP = audioCtx.createBiquadFilter();
  chiffBP.type = "bandpass";
  chiffBP.frequency.setValueAtTime(2400, now);
  chiffBP.Q.setValueAtTime(0.9, now);

  const chiffG = audioCtx.createGain();
  chiffG.gain.setValueAtTime(0.0001, now);
  chiffG.gain.exponentialRampToValueAtTime(0.10, now + 0.005);
  chiffG.gain.exponentialRampToValueAtTime(0.0001, now + 0.04);

  chiff.connect(chiffBP);
  chiffBP.connect(chiffG);
  chiffG.connect(env);

  const hp = audioCtx.createBiquadFilter();
  hp.type = "highpass";
  hp.frequency.setValueAtTime(80, now);
  hp.Q.setValueAtTime(0.7, now);

  const lp = audioCtx.createBiquadFilter();
  lp.type = "lowpass";
  lp.frequency.setValueAtTime(4200, now);
  lp.Q.setValueAtTime(0.6, now);

  mix.connect(hp);
  hp.connect(lp);
  lp.connect(env);

  level.connect(bus.piano.input);

  for(const o of oscs) trackNode(o);
  trackNode(chiff);

  for(const o of oscs) o.start(now);
  chiff.start(now);

  for(const o of oscs) o.stop(stopAt);
  chiff.stop(now + 0.05);
}

function playTrumpet(freq, steps){
  const now = audioCtx.currentTime;
  const hold = steps * stepDurationSec();
  const release = Math.min(0.16, Math.max(0.09, hold * 0.08));
  const stopAt = now + hold + release + 0.10;

  const env = audioCtx.createGain();
  scheduleEnvelope(env, now, hold, 0.016, 0.36, 0.24, release, 0.07);

  const level = audioCtx.createGain();
  level.gain.setValueAtTime(LEVEL.trumpet, now);
  env.connect(level);

  const o1 = audioCtx.createOscillator();
  const o2 = audioCtx.createOscillator();
  o1.type = "sawtooth";
  o2.type = "sawtooth";
  o1.frequency.setValueAtTime(freq, now);
  o2.frequency.setValueAtTime(freq, now);
  o2.detune.setValueAtTime(+8, now);

  const bp = audioCtx.createBiquadFilter();
  bp.type = "bandpass";
  bp.frequency.setValueAtTime(freq * 2.5, now);
  bp.Q.setValueAtTime(0.95, now);

  const lfo = audioCtx.createOscillator();
  lfo.type = "sine";
  lfo.frequency.setValueAtTime(5.4, now);
  const lfoG = audioCtx.createGain();
  lfoG.gain.setValueAtTime(9, now);
  lfo.connect(lfoG);
  lfoG.connect(o1.detune);
  lfoG.connect(o2.detune);

  const g1 = audioCtx.createGain();
  const g2 = audioCtx.createGain();
  g1.gain.setValueAtTime(0.60, now);
  g2.gain.setValueAtTime(0.55, now);

  o1.connect(g1); o2.connect(g2);
  g1.connect(bp); g2.connect(bp);
  bp.connect(env);

  level.connect(bus.trumpet.input);

  trackNode(o1); trackNode(o2); trackNode(lfo);

  o1.start(now); o2.start(now); lfo.start(now);
  o1.stop(stopAt); o2.stop(stopAt); lfo.stop(stopAt);
}

function playStrings(freq, steps){
  const now = audioCtx.currentTime;
  const hold = steps * stepDurationSec();

  const padHold = Math.max(hold, 0.22);
  const release = Math.min(0.55, Math.max(0.22, padHold * 0.35));
  const stopAt = now + padHold + release + 0.18;

  const env = audioCtx.createGain();
  scheduleEnvelope(env, now, padHold, 0.045, 0.38, 0.26, release, 0.18);

  const level = audioCtx.createGain();
  level.gain.setValueAtTime(LEVEL.strings, now);
  env.connect(level);

  const s1 = audioCtx.createOscillator();
  const s2 = audioCtx.createOscillator();
  const s3 = audioCtx.createOscillator();
  const sub = audioCtx.createOscillator();

  s1.type = "sawtooth";
  s2.type = "sawtooth";
  s3.type = "sawtooth";
  sub.type = "triangle";

  s1.frequency.setValueAtTime(freq, now);
  s2.frequency.setValueAtTime(freq, now);
  s3.frequency.setValueAtTime(freq, now);
  sub.frequency.setValueAtTime(freq * 0.5, now);

  s2.detune.setValueAtTime(+9, now);
  s3.detune.setValueAtTime(-11, now);

  const lfo = audioCtx.createOscillator();
  lfo.type = "sine";
  lfo.frequency.setValueAtTime(0.35, now);
  const lfoG = audioCtx.createGain();
  lfoG.gain.setValueAtTime(10, now);
  lfo.connect(lfoG);
  lfoG.connect(s1.detune);
  lfoG.connect(s2.detune);
  lfoG.connect(s3.detune);

  const mix = audioCtx.createGain();
  const g1 = audioCtx.createGain();
  const g2 = audioCtx.createGain();
  const g3 = audioCtx.createGain();
  const gs = audioCtx.createGain();
  g1.gain.setValueAtTime(0.30, now);
  g2.gain.setValueAtTime(0.28, now);
  g3.gain.setValueAtTime(0.28, now);
  gs.gain.setValueAtTime(0.20, now);

  const lp = audioCtx.createBiquadFilter();
  lp.type = "lowpass";
  lp.frequency.setValueAtTime(1900, now);
  lp.frequency.exponentialRampToValueAtTime(980, now + 0.40);
  lp.Q.setValueAtTime(0.85, now);

  const shelf = audioCtx.createBiquadFilter();
  shelf.type = "highshelf";
  shelf.frequency.setValueAtTime(3400, now);
  shelf.gain.setValueAtTime(2.0, now);

  s1.connect(g1); s2.connect(g2); s3.connect(g3); sub.connect(gs);
  g1.connect(mix); g2.connect(mix); g3.connect(mix); gs.connect(mix);

  mix.connect(lp);
  lp.connect(shelf);
  shelf.connect(env);

  level.connect(bus.strings.input);

  trackNode(s1); trackNode(s2); trackNode(s3); trackNode(sub); trackNode(lfo);

  s1.start(now); s2.start(now); s3.start(now); sub.start(now); lfo.start(now);
  s1.stop(stopAt); s2.stop(stopAt); s3.stop(stopAt); sub.stop(stopAt); lfo.stop(stopAt);
}

function playSynth(freq, steps){
  const now = audioCtx.currentTime;
  const hold = steps * stepDurationSec();
  const release = Math.min(0.18, Math.max(0.10, hold * 0.08));
  const stopAt = now + hold + release + 0.12;

  const env = audioCtx.createGain();
  scheduleEnvelope(env, now, hold, 0.0025, 0.62, 0.22, release, 0.055);

  const level = audioCtx.createGain();
  level.gain.setValueAtTime(LEVEL.synth, now);
  env.connect(level);

  const osc = audioCtx.createOscillator();
  osc.type = "square";
  osc.frequency.setValueAtTime(freq, now);

  const lp = audioCtx.createBiquadFilter();
  lp.type = "lowpass";
  lp.frequency.setValueAtTime(2600, now);
  lp.frequency.exponentialRampToValueAtTime(1800, now + 0.10);
  lp.Q.setValueAtTime(0.9, now);

  osc.connect(lp);
  lp.connect(env);
  level.connect(bus.synth.input);

  trackNode(osc);
  osc.start(now);
  osc.stop(stopAt);
}

function playInstrument(freq, steps){
  lastAudioActivityAt = performance.now();

  if(instrument === "piano")   return playPiano(freq, steps);
  if(instrument === "trumpet") return playTrumpet(freq, steps);
  if(instrument === "strings") return playStrings(freq, steps);
  return playSynth(freq, steps);
}

/* -------------------- PLAYBACK -------------------- */
async function play(){
  iosStartSilentVideo();
  await ensureAudioReady();

  stop();

  step = 0;
  setPlayheadVisible(true);
  setPlayheadPlaying(false);
  resetPlayheadInstant();

  const nowMs = performance.now();
  const idleMs = (lastStopAt === null) ? Infinity : (nowMs - lastStopAt);
  const audioIdleMs = (lastAudioActivityAt == null) ? Infinity : (nowMs - lastAudioActivityAt);

  let delayMs = 80;
  if(!hasEverStartedPlayback) delayMs = 500;
  else if(Math.max(idleMs, audioIdleMs) > 25000) delayMs = 750;
  else if(Math.max(idleMs, audioIdleMs) > 5000) delayMs = 500;

  startTimeout = setTimeout(() => {
    startTimeout = null;
    startSequencer();
    hasEverStartedPlayback = true;
  }, delayMs);
}



function setBlockPulseVars(el){
  // Make the "swell" feel like a consistent number of pixels for every block,
  // instead of a constant scale factor (which exaggerates long blocks).
  try{
    const r = el.getBoundingClientRect();
    const w = Math.max(1, r.width);
    const h = Math.max(1, r.height);
    const delta = 4; // px added per side
    let sx = (w + delta*2) / w;
    let sy = (h + delta*2) / h;
    // Clamp so tiny blocks don't blow up
    sx = Math.min(1.12, Math.max(1.0, sx));
    sy = Math.min(1.18, Math.max(1.0, sy));
    const sx2 = 1 + (sx - 1) * 0.35;
    const sy2 = 1 + (sy - 1) * 0.35;
    el.style.setProperty('--sx', sx.toFixed(4));
    el.style.setProperty('--sy', sy.toFixed(4));
    el.style.setProperty('--sx2', sx2.toFixed(4));
    el.style.setProperty('--sy2', sy2.toFixed(4));
  }catch(e){
    // ignore
  }
}

function startSequencer(){
  let firstTick = true;

  function tick(){
    movePlayheadToStep(step);

    if(firstTick){
      setPlayheadPlaying(true);
      firstTick = false;
    }

    for(let r=0;r<rows;r++){
      const note = notesByRow[r].find(n => n.start === step);
      if(note){
        playInstrument(freqs[r], note.len);

        const block = noteLayerEls[r].querySelector(`.noteBlock[data-id="${note.id}"]`);
        if(block){
          setBlockPulseVars(block);
          block.classList.remove("playing");
          void block.offsetWidth;
          block.classList.add("playing");
        }
      }
    }

    // Drums (runs in time with the sequencer)
    playDrumsAtStep(step);

    step = (step + 1) % cols;

    if(step === 0 && pendingTempo !== null){
      tempo = pendingTempo;
      pendingTempo = null;
      updateTempoBox();
      setPlayheadWobbleFromTempo(tempo);
      restartInterval(stepDurationSec() * 1000);
    }
  }

  function restartInterval(intervalMs){
    if(timer){
      clearInterval(timer);
      timer = null;
    }
    timer = setInterval(tick, intervalMs);
  }

  tick();
  restartInterval(stepDurationSec() * 1000);
}

function stop(){
  if(timer){
    clearInterval(timer);
    timer = null;
  }
  if(startTimeout){
    clearTimeout(startTimeout);
    startTimeout = null;
  }
  setPlayheadPlaying(false);
  setPlayheadVisible(false);
  stopAllAudioNow();
  lastStopAt = performance.now();
}

/* -------------------- TEMPO -------------------- */
function updateTempoBox(){
  tempoBox.textContent = (pendingTempo !== null) ? pendingTempo : tempo;
}
function requestTempo(newTempo){
  newTempo = Math.max(40, Math.min(200, newTempo));
  if(timer){
    pendingTempo = newTempo;
    updateTempoBox();
    setPlayheadWobbleFromTempo(pendingTempo);
    return;
  }
  tempo = newTempo;
  pendingTempo = null;
  updateTempoBox();
  setPlayheadWobbleFromTempo(tempo);
}
function tempoUp(){
  if(!isLoggedIn){ showLockNudge(); hideLockNudgeSoon(900); return; }
const base = (pendingTempo !== null) ? pendingTempo : tempo;
  requestTempo(base + 5);
}
function tempoDown(){
  if(!isLoggedIn){ showLockNudge(); hideLockNudgeSoon(900); return; }
const base = (pendingTempo !== null) ? pendingTempo : tempo;
  requestTempo(base - 5);
}

/* -------------------- CLEAR -------------------- */
function clearGrid(){
  pushUndo();
  notesByRow = Array.from({length: rows}, () => []);
  occ = Array.from({length: rows}, () => Array(cols).fill(null));
  redrawAllNotes();
}



/* -------------------- CAMERA SCAN (simple heuristic) -------------------- */
let camStream = null;
let camCapturedDataUrl = null;

const camModalEl = document.getElementById("camModal");
const camVideoEl = document.getElementById("camVideo");
const camCanvasEl = document.getElementById("camCanvas");
const camPreviewEl = document.getElementById("camPreview");

async function openCameraModal(){
  if(!isLoggedIn){ showLockNudge(); hideLockNudgeSoon(900); return; }
  try{
    if(!camModalEl || !camVideoEl || !camCanvasEl || !camPreviewEl){
      alert("Camera UI is missing in the HTML (camModal/camVideo/camCanvas/camPreview).\nIf you edited the file, make sure that block still exists.");
      return;
    }

    if(!window.isSecureContext){
      alert("Camera access needs a secure context.\nOpen this page via https:// or http://localhost (not file://).\n\nCurrent URL:\n" + location.href);
      return;
    }

    if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
      alert("Camera API not available in this browser.");
      return;
    }

    camCapturedDataUrl = null;
    camPreviewEl.style.display = "none";
    camVideoEl.style.display = "block";

    camModalEl.classList.add("show");
    camModalEl.setAttribute("aria-hidden", "false");

    const primaryConstraints = { video: { facingMode: { ideal: "environment" } }, audio: false };
    const fallbackConstraints = { video: true, audio: false };

    try{
      camStream = await navigator.mediaDevices.getUserMedia(primaryConstraints);
    }catch(err){
      // Some devices/browsers don't like facingMode constraints.
      if(err && (err.name === "OverconstrainedError" || err.name === "NotFoundError")){
        camStream = await navigator.mediaDevices.getUserMedia(fallbackConstraints);
      }else{
        throw err;
      }
    }

    camVideoEl.srcObject = camStream;
    await camVideoEl.play().catch(()=>{});
  }catch(e){
    console.error("Camera open failed:", e);
    const name = (e && e.name) ? e.name : "Error";
    const msg  = (e && e.message) ? e.message : "";

    if(name === "NotAllowedError" || name === "SecurityError"){
      alert("Camera permission was blocked.\n\nFix:\n1) Click the padlock icon in the address bar\n2) Site settings -> Camera -> Allow\n3) Reload the page\n\n(" + name + (msg ? ": " + msg : "") + ")");
      return;
    }

    if(name === "NotReadableError"){
      alert("The camera may be in use by another app/tab (Zoom/Meet/etc).\nClose other apps using the camera, then try again.\n\n(" + name + (msg ? ": " + msg : "") + ")");
      return;
    }

    alert("Could not open the camera.\n\n(" + name + (msg ? ": " + msg : "") + ")");
  }
}

function closeCameraModal(){
  camModalEl.classList.remove("show");
  camModalEl.setAttribute("aria-hidden", "true");
  try{
    if(camStream){
      camStream.getTracks().forEach(t => { try{ t.stop(); }catch(e){} });
    }
  }catch(e){}
  camStream = null;
}

function camCapture(){
  if(!camVideoEl || !camVideoEl.videoWidth) return;
  const w = camVideoEl.videoWidth;
  const h = camVideoEl.videoHeight;
  camCanvasEl.width = w;
  camCanvasEl.height = h;
  const ctx = camCanvasEl.getContext("2d");
  ctx.drawImage(camVideoEl, 0, 0, w, h);
  camCapturedDataUrl = camCanvasEl.toDataURL("image/png");
  camPreviewEl.src = camCapturedDataUrl;
  camPreviewEl.style.display = "block";
  camVideoEl.style.display = "none";
}

function camImport(){
  if(!camCapturedDataUrl){
    camCapture();
    if(!camCapturedDataUrl) return;
  }
  importGridFromDataUrl(camCapturedDataUrl);
  closeCameraModal();
}

function importGridFromDataUrl(dataUrl){
  const img = new Image();
  img.onload = () => {
    const w = img.naturalWidth;
    const h = img.naturalHeight;
    camCanvasEl.width = w;
    camCanvasEl.height = h;
    const ctx = camCanvasEl.getContext("2d");
    ctx.drawImage(img, 0, 0, w, h);

    const { data } = ctx.getImageData(0, 0, w, h);

    // centered crop to reduce background impact
    const cropX = Math.floor(w * 0.10);
    const cropY = Math.floor(h * 0.12);
    const cropW = Math.floor(w * 0.80);
    const cropH = Math.floor(h * 0.76);

    function idx(px, py){ return (py * w + px) * 4; }

    function sampleCell(r, c){
      // sample a few points inside the cell
      const x0 = cropX + Math.floor((c + 0.15) * cropW / cols);
      const x1 = cropX + Math.floor((c + 0.85) * cropW / cols);
      const y0 = cropY + Math.floor((r + 0.20) * cropH / rows);
      const y1 = cropY + Math.floor((r + 0.80) * cropH / rows);

      const pts = [
        [x0, y0],
        [x1, y0],
        [Math.floor((x0+x1)/2), Math.floor((y0+y1)/2)],
        [x0, y1],
        [x1, y1]
      ];

      let satSum = 0;
      let lumSum = 0;
      for(const [x,y] of pts){
        const i = idx(Math.max(0, Math.min(w-1, x)), Math.max(0, Math.min(h-1, y)));
        const R = data[i]/255, G = data[i+1]/255, B = data[i+2]/255;
        const maxv = Math.max(R,G,B);
        const minv = Math.min(R,G,B);
        const lum = (maxv + minv) * 0.5;
        const sat = (maxv === 0) ? 0 : (maxv - minv) / maxv; // simple saturation proxy
        satSum += sat;
        lumSum += lum;
      }
      const sat = satSum / pts.length;
      const lum = lumSum / pts.length;

      // heuristic: colored if reasonably saturated and not near-white
      return (sat > 0.18) && (lum < 0.92);
    }

    pushUndo();
    notesByRow = Array.from({length: rows}, () => []);
    occ = Array.from({length: rows}, () => Array(cols).fill(null));
    nextId = 1;

    for(let r=0;r<rows;r++){
      for(let c=0;c<cols;c++){
        if(sampleCell(r,c)){
          if(canPlace(r, c, 1)) placeNote(r, c, 1);
        }
      }
    }

    redrawAllNotes();
  };
  img.src = dataUrl;
}


/* -------------------- INIT -------------------- */
/* -------------------- LAYOUT MANAGER -------------------- */
/* One source of truth:
   - Internal layout is computed in *stage coordinates* (CSS --stageW/--stageH).
   - The whole stage is then scaled to fit the *visible* viewport (VisualViewport on iOS).
   - All triggers funnel through scheduleLayout() so DevTools refresh / iOS URL-bar changes can't create competing layouts. */
(function(){
  const root = document.documentElement;
  const viewportEl = document.getElementById('viewport');
  const pageEl = document.getElementById('page');
  if(!pageEl) return;

  let __ready = false;
  let __stable = 0;
  let __lastVW = 0, __lastVH = 0;
  function __reveal(){
    if(__ready) return;
    __ready = true;

    // Ensure we are at top-left to prevent any offX / scroll-restoration offsets (iOS can restore scroll subtly)
    try{ window.scrollTo(0, 0); }catch(e){}
    try{ if(viewportEl){ viewportEl.scrollTop = 0; viewportEl.scrollLeft = 0; } }catch(e){}

    // First pass with the latest VisualViewport values
    try{ __ksSyncViewportVars(); }catch(e){}
    try{ fitToViewport(); }catch(e){}

    root.classList.remove('js-loading');
    root.classList.add('js-ready');

    // Double-pass: re-run after visibility changes are actually painted
    requestAnimationFrame(() => {
      try{ fitToViewport(); }catch(e){}
      try{ scheduleLayout(); }catch(e){}
      // One last safety pass for slow iOS UI settling
      setTimeout(() => { try{ scheduleLayout(); }catch(e){} }, 150);
    });
  }

  let __stabilityRaf = 0;
  // Improved stability polling to wait for iOS UI (safe-area / address bar) to settle
  function __ksPollStability(){
    if(__ready) return;
    const vv = window.visualViewport;
    const vw = vv ? vv.width : window.innerWidth;
    const vh = vv ? vv.height : window.innerHeight;

    if (Math.abs(vw - __lastVW) < 0.5 && Math.abs(vh - __lastVH) < 0.5) {
      __stable++;
    } else {
      __stable = 0;
      __lastVW = vw;
      __lastVH = vh;
    }

    // Increased to 5 stable frames (~80-100ms) to ensure iOS safe-area/address bar is settled
    if(__stable >= 5){
      __reveal();
    }else{
      __stabilityRaf = requestAnimationFrame(__ksPollStability);
    }
  }
  // Hard fallback in case of unexpected errors.
  setTimeout(__reveal, 900);

  function applyStageFit(){
    const { vw, vh, offX, offY } = __ksViewport();
    const { stageW, stageH } = __ksStageSize();

    // In scaled mode we respect safe-area padding on #viewport (iPhone notch / home bar).
    // Measure its paddings once per pass.
    let padL = 0, padR = 0, padT = 0, padB = 0;
    if(viewportEl){
      const cs = getComputedStyle(viewportEl);
      padL = parseFloat(cs.paddingLeft)  || 0;
      padR = parseFloat(cs.paddingRight) || 0;
      padT = parseFloat(cs.paddingTop)   || 0;
      padB = parseFloat(cs.paddingBottom)|| 0;
    }

    const usableW = Math.max(0, vw - padL - padR);
    const usableH = Math.max(0, vh - padT - padB);

    // Only enter scaled mode if the stage cannot fit at 1:1.
    const shouldScale = (usableW < stageW) || (usableH < stageH);

    if(!shouldScale){
      // Desktop / large screens: leave layout exactly as-is.
      root.classList.remove('stageScaled','tabletScaled');
      pageEl.style.transform = '';
      pageEl.style.width = '';
      pageEl.style.height = '';
      pageEl.style.minWidth = '';
      pageEl.style.minHeight = '';
      return;
    }

    // Scale UP/DOWN to fit (iOS-first)
    // On iPhone in landscape, the stage is often height-limited even though we have spare width.
    // The current design leaves some "dead" vertical padding, so we can safely treat the stage as a bit shorter
    // *only for the fit math* to let it scale up and use more width.
    const phoneish = Math.min(vw, vh) < 520;           // iPhone-ish devices
    const landscape = vw > vh;
    const fitStageH = (phoneish && landscape) ? Math.max(1, stageH - 90) : stageH;

    const s = Math.min(usableW / stageW, usableH / fitStageH);

    // Center in the *visual viewport* (not just the padded safe-area box),
    // but clamp so we never clip into the safe-area paddings.
    const targetTx = offX + (vw - stageW * s) / 2;
    const minTx = offX + padL;
    const maxTx = offX + (vw - padR) - stageW * s;
    const tx = Math.min(maxTx, Math.max(minTx, targetTx));

    // Vertical placement: scale uses fitStageH (a slightly reduced height in iPhone-landscape),
// but translation should center using the *real* stage height so we don't drift downward.
const freeYTrue = usableH - stageH * s;

// When the scaled stage is taller than the usable area (freeYTrue < 0), pin to the top
// so the controls/play buttons stay visible below the browser toolbar — the bottom overflows
// (which is fine since the bottom has less-critical content like the drum panel).
// When there's room, center vertically but clamp to safe-area paddings.
const targetTy = freeYTrue >= 0
  ? offY + padT + (freeYTrue) / 2
  : offY + padT;
const minTy = offY + padT;
// maxTy must never go below minTy — if the stage overflows, we accept bottom overflow.
const maxTyRaw = offY + (vh - padB) - stageH * s;
const maxTy = Math.max(minTy, maxTyRaw);
const ty = Math.min(maxTy, Math.max(minTy, targetTy));

root.classList.add('stageScaled');
    root.classList.remove('tabletScaled');

    // Freeze the element box to stage size so internal layout never reflows.
    pageEl.style.width = stageW + 'px';
    pageEl.style.height = stageH + 'px';
    pageEl.style.minWidth = stageW + 'px';
    pageEl.style.minHeight = stageH + 'px';

    pageEl.style.transform = `translate(${tx}px, ${ty}px) scale(${s})`;

    // Keep the "viewport" scroller pinned (no accidental scrollbars after refresh)
    if(viewportEl){
      try{ viewportEl.scrollTop = 0; viewportEl.scrollLeft = 0; }catch(e){}
    }
  }

  let raf = 0;
  function layoutPass(){
    // Sync the fixed #viewport box to the visible viewport (prevents the 1–3px iPhone landscape scroll).
    try{ __ksSyncViewportVars(); }catch(e){}
    // Compute internal layout in unscaled coordinates
    const prev = pageEl.style.transform;
    pageEl.style.transform = '';
    try{
      fitToViewport();
      buildGrid();
      positionRobotLogo();
    }catch(e){
      console.error('layoutPass failed', e);
    }
    pageEl.style.transform = prev;

    // Now scale & center the stage
    try{ applyStageFit(); }catch(e){ console.error('applyStageFit failed', e); }
    // Reveal only after the visible viewport is stable for several frames (iOS address bar / safe-area settling)
    if(!__ready){
      try{ if(__stabilityRaf) cancelAnimationFrame(__stabilityRaf); }catch(e){}
      __stabilityRaf = requestAnimationFrame(__ksPollStability);
    }
  }

  function scheduleLayout(){
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(layoutPass);
  }

  // Export for other code paths (init, etc.)
  window.scheduleLayout = scheduleLayout;

  const trigger = () => scheduleLayout();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', trigger, {once:true});
  else scheduleLayout();

  window.addEventListener('resize', trigger, {passive:true});
  window.addEventListener('orientationchange', () => setTimeout(trigger, 60), {passive:true});
  if(window.visualViewport){
    window.visualViewport.addEventListener('resize', trigger, {passive:true});
  }
  window.addEventListener('load', trigger, {once:true});

  // One extra pass after fonts settle
  setTimeout(trigger, 120);

  // iOS Safari can still allow a tiny rubber-band scroll even with overflow hidden.
  // When we are in stageScaled mode (no scrolling intended), block touchmove to eliminate that wiggle.
  document.addEventListener('touchmove', (e) => {
    if(!root.classList.contains('stageScaled')) return;
    // Allow native interaction on form controls if any.
    const t = e.target;
    if(t && (t.closest && t.closest('input, textarea, select, option, button'))) return;
    e.preventDefault();
  }, { passive: false });
})();


function init(){
  if (window.scheduleLayout) window.scheduleLayout();
setInstrument("piano");
  updateTempoBox();
  setPlayheadWobbleFromTempo(tempo);
  if (window.scheduleLayout) { requestAnimationFrame(window.scheduleLayout); setTimeout(window.scheduleLayout, 120); }

  // Two-pass layout: compute once, then again after paint/fonts to avoid misalignment when opened in a small window.
  requestAnimationFrame(() => {
    fitToViewport(); positionRobotLogo();
    requestAnimationFrame(() => { fitToViewport(); positionRobotLogo();  });
  });
}

// Layout init must be independent of auth and run on DOMContentLoaded.
(function(){
  const run = () => { try{ init(); }catch(e){ console.error('init failed', e); } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, {once:true});
  else run();
})();
/* -------------------- OPTION A EXPORTS --------------------
   Keep inline onclick handlers working (play/stop/tempo/etc) while still providing
   a structured, manager-friendly namespace at window.KidSequencer.
   This is intentionally additive: UI + behaviour remain exactly the same.
*/

// Inline-handler globals (used by existing HTML attributes)
window.play = play;
window.stop = stop;
window.clearGrid = clearGrid;
window.undo = undo;
window.openCameraModal = openCameraModal;
window.closeCameraModal = closeCameraModal;
window.camCapture = camCapture;
window.camImport = camImport;
window.tempoUp = tempoUp;
window.tempoDown = tempoDown;
window.logout = logout;

// Organised namespace for maintenance/debugging (optional)
window.KidSequencer = {
  State: {
    get tempo(){ return tempo; },
    set tempo(v){ tempo = v; updateTempoBox(); setPlayheadWobbleFromTempo(tempo); },
    get instrument(){ return instrument; },
    set instrument(v){ setInstrument(v); },
    get isLoggedIn(){ return isLoggedIn; }
  },
  UI: {
    fitToViewport,
    positionRobotLogo,
    updateTempoBox,
    updateLoginLinks,
    applyLockState,
    showLockNudge,
    hideLockNudgeSoon,
    setPlayheadWobbleFromTempo
  },
  Audio: {
    ensureAudioRunning,
    stopAllAudioNow,
    primeAudioOnce,
    setInstrument,
    playInstrument
  },
  Sequencer: {
    play,
    stop,
    clearGrid,
    undo,
    buildGrid,
    buildTools,
    redrawAllNotes
  },
  Camera: {
    openCameraModal,
    closeCameraModal,
    camCapture,
    camImport
  },
  Auth: { logout }
};

})();
/* OPTION A ORGANISATION END */
