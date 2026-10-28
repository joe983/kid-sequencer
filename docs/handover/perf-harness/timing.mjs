// Scheduler timing check: hook every source start(), play, optionally add main-thread jank,
// then report grid error, lead distribution, first-sound latency and stop behaviour.
// Usage: node timing.mjs <page> <jankMs> [jankEveryMs]
import { spawn } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const page = process.argv[2] || 'index.html';
const jank = +(process.argv[3] || 0);
const every = +(process.argv[4] || 700);
const port = 9600 + Math.floor(Math.random() * 90);
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'kseq-t-'))}`, '--window-size=1600,900', '--autoplay-policy=no-user-gesture-required', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
let wsUrl; for (let i = 0; i < 60 && !wsUrl; i++) { try { const j = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); const p = j.find(t => t.type === 'page'); if (p) wsUrl = p.webSocketDebuggerUrl; } catch {} if (!wsUrl) await sleep(250); }
const ws = new WebSocket(wsUrl); await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pend = new Map();
ws.addEventListener('message', m => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id); } });
const send = (method, params = {}) => new Promise((res) => { const i = ++id; pend.set(i, d => res(d.result || d.error)); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (e) => { const r = await send('Runtime.evaluate', { expression: e, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) return 'EXC ' + JSON.stringify(r.exceptionDetails).slice(0, 300); return r.result?.value; };
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate', { url: `http://localhost:3000/${page}${page.includes('?') ? '&' : '?'}audiodebug=1` });
await sleep(4500);
const out = await ev(`(async () => {
  const log = window.__starts = [];
  for (const P of [AudioBufferSourceNode.prototype, OscillatorNode.prototype]) {
    const orig = P.start;
    P.start = function(when, ...rest) { try { log.push({ when: when || 0, now: this.context.currentTime, w: performance.now() }); } catch(e){} return orig.call(this, when, ...rest); };
  }
  const cells = document.querySelectorAll('#sequencer .cell');
  for (const [r, c] of [[2,0],[4,2],[5,4],[3,6],[4,8],[2,10],[5,12],[3,14]]) cells[r*16 + c].click();
  await new Promise(r => setTimeout(r, 300));
  const tempo = +document.getElementById('tempoBox').textContent;
  const tPlay = performance.now();
  document.querySelector('button[aria-label="Play"]').click();
  const busy = (ms) => { const e = performance.now() + ms; while (performance.now() < e) {} };
  let iv = null;
  if (${jank}) setTimeout(() => { iv = setInterval(() => busy(${jank}), ${every}); }, 1500);
  await new Promise(r => setTimeout(r, 8000));
  if (iv) clearInterval(iv);
  const panel = (Array.from(document.querySelectorAll('pre')).find(p => /worst tick late/.test(p.textContent)) || {}).textContent || '';
  // stop and see whether anything new is STARTED after the stop
  const nBefore = log.length;
  const stopA = audioCtx.currentTime;
  window.stop();
  await new Promise(r => setTimeout(r, 600));
  const startedAfterStop = log.slice(nBefore).length;
  return { tempo, tPlay, stopA, startedAfterStop, panelLine: (panel.split('\\n').find(l => /worst tick late/.test(l)) || '').trim(), log: log.slice(0, nBefore) };
})()`);
if (typeof out === 'string') { console.log(out); chrome.kill(); process.exit(1); }
const stepDur = 60 / out.tempo / 4;
// group onsets into steps: distinct 'when' values (rounded to 0.5 ms)
const whens = [...new Set(out.log.map(l => Math.round(l.when * 2000) / 2000))].sort((a, b) => a - b);
const t0 = whens[0];
// swing in the techno pattern moves odd 16ths by 0.08 of a step: assign each onset to nearest step and measure error vs even/odd grid
let maxErr = 0, n = 0; const errs = [];
for (const w of whens) {
  const k = Math.round((w - t0) / stepDur);
  const ideal = t0 + k * stepDur;
  let e = Math.abs(w - ideal);
  const eSw = Math.abs(w - (ideal + 0.08 * stepDur));
  e = Math.min(e, eSw);
  errs.push(e); if (e > maxErr) maxErr = e; n++;
}
if (process.env.DUMP) {
  const rows = whens.map((w, i) => { const k = Math.round((w - t0) / stepDur); const ideal = t0 + k * stepDur; const d = (w - ideal) * 1000; const calls = out.log.filter(l => Math.round(l.when * 2000) / 2000 === w); return `#${i} k=${k} dev=${d.toFixed(2)}ms calls=${calls.length} schedLead=${((calls[0].when - calls[0].now) * 1000).toFixed(0)}ms`; });
  console.log(rows.slice(0, 24).join('\n'));
}
// leads: when - currentTime at the call, first second vs rest
const firstW = out.log[0].w;
const leads = out.log.map(l => ({ dt: l.w - firstW, lead: (l.when - l.now) * 1000 }));
const early = leads.filter(l => l.dt < 400).map(l => l.lead);
const steady = leads.filter(l => l.dt > 1000).map(l => l.lead);
const pct = (a, p) => { const s = [...a].sort((x, y) => x - y); return s.length ? +s[Math.min(s.length - 1, Math.floor(p * s.length))].toFixed(0) : null; };
console.log(JSON.stringify({
  page, jank, tempo: out.tempo, onsets: n,
  gridErrMaxMs: +(maxErr * 1000).toFixed(2),
  firstSoundAfterPlayClickMs: +((out.log[0].w - out.tPlay) + (out.log[0].when - out.log[0].now) * 1000).toFixed(0),
  leadFirst400ms: { min: pct(early, 0), median: pct(early, 0.5), max: pct(early, 0.99) },
  leadSteady: { p01: pct(steady, 0.01), median: pct(steady, 0.5), max: pct(steady, 0.99) },
  startedAfterStop: out.startedAfterStop,
  panel: out.panelLine,
}));
chrome.kill(); process.exit(0);
