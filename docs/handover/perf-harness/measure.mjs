// CDP harness: real headless Chrome, real input events, CPU throttling as an iPad proxy.
// Usage: node measure.mjs <cpuThrottle> <tapsPerSec> <seconds> [instrument] [url-suffix]
import { spawn } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const throttle = +(process.argv[2] || 1);
const tapsPerSec = +(process.argv[3] || 8);
const seconds = +(process.argv[4] || 6);
const instr = process.argv[5] || 'btnPiano';
const urlSuffix = process.argv[6] || '';
const port = 9300 + Math.floor(Math.random() * 500);
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const userDir = mkdtempSync(join(tmpdir(), 'kseq-cdp-'));

const chrome = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${userDir}`,
  '--autoplay-policy=no-user-gesture-required', '--window-size=1600,900', '--hide-scrollbars',
  '--no-first-run', '--no-default-browser-check', 'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
async function getWs() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json`);
      const j = await r.json();
      const p = j.find(t => t.type === 'page');
      if (p) return p.webSocketDebuggerUrl;
    } catch {}
    await sleep(250);
  }
  throw new Error('no devtools');
}

const wsUrl = await getWs();
const ws = new WebSocket(wsUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map();
ws.addEventListener('message', (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } });
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, (d) => d.error ? rej(new Error(method + ': ' + JSON.stringify(d.error))) : res(d.result)); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJs = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 400)); return r.result.value; };

await send('Page.enable'); await send('Runtime.enable'); await send('Performance.enable');
await send('Page.navigate', { url: `http://localhost:3000/${process.env.PAGE || 'index.html'}?audiodebug=1${urlSuffix}` });
await sleep(4000);
if (throttle > 1) await send('Emulation.setCPUThrottlingRate', { rate: throttle });

// page-side helpers
await evalJs(`(() => {
  window.__lt = []; try { new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lt.push(Math.round(e.duration)); }).observe({entryTypes:['longtask']}); } catch(e) {}
  window.__panel = () => { const els = Array.from(document.querySelectorAll('pre')).filter(p => /worst tick late/.test(p.textContent)); return els.length ? els[els.length-1].textContent : 'no panel'; };
  return true; })()`);

const cellPos = async (r, c) => evalJs(`(() => { const cs = document.querySelectorAll('#sequencer .cell'); const b = cs[${r}*16+${c}].getBoundingClientRect(); return [b.left + b.width/2, b.top + b.height/2]; })()`);
const click = async (x, y) => { await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 }); await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 }); };
const clickSel = async (sel) => { const [x, y] = await evalJs(`(() => { const b = document.querySelector(${JSON.stringify(sel)}).getBoundingClientRect(); return [b.left+b.width/2, b.top+b.height/2]; })()`); await click(x, y); };

if (process.env.INJECT_CSS) await evalJs(`(() => { const s = document.createElement('style'); s.textContent = ${JSON.stringify(process.env.INJECT_CSS)}; document.head.appendChild(s); return true; })()`);
if (process.env.INJECT_JS) await evalJs(`(() => { ${process.env.INJECT_JS}; return true; })()`);
await clickSel('#' + instr).catch(() => {});
// seed a small tune, then press play
for (const [r, c] of [[2,0],[4,2],[5,4],[3,6],[4,8],[2,10],[5,12],[3,14]]) { const [x, y] = await cellPos(r, c); await click(x, y); }
if (process.env.FILL) {            // fill N of the 128 cells before play (unmeasured), e.g. FILL=128
  const n = +process.env.FILL; const fillOrder = [];
  for (let r = 0; r < 8; r++) for (let c = 0; c < 16; c++) fillOrder.push([r, c]);
  for (let i = 0; i < n; i++) { const [r, c] = fillOrder[(i * 5) % 128]; const [x, y] = await cellPos(r, c); await click(x, y); }
}
if (!process.env.NOPLAY) await clickSel('button[aria-label="Play"]');
await sleep(2500);

const metric = async () => Object.fromEntries((await send('Performance.getMetrics')).metrics.map(m => [m.name, m.value]));
// optional trace of the measured window (env TRACE=1): sum durations by event name on the renderer main thread
const traceEvents = [];
if (process.env.TRACE) {
  ws.addEventListener('message', (m) => { const d = JSON.parse(m.data); if (d.method === 'Tracing.dataCollected') traceEvents.push(...d.params.value); });
  await send('Tracing.start', { traceConfig: { includedCategories: ['devtools.timeline', 'disabled-by-default-devtools.timeline', 'blink', 'cc', 'gpu'], recordMode: 'recordAsMuchAsPossible' } });
}
if (process.env.DUMPANIM) {
  const tally = await evalJs(`(async () => {
    const t = {};
    for (let i = 0; i < 60; i++) {
      for (const a of document.getAnimations()) {
        const tg = a.effect && a.effect.target; if (!tg) continue;
        const nm = (a.animationName || ('transition:' + (a.transitionProperty || '?')));
        const who = (tg.id ? '#' + tg.id : '') + (typeof tg.className === 'string' && tg.className ? '.' + tg.className.trim().split(/\\s+/).slice(0, 2).join('.') : tg.tagName);
        const k = nm + ' @ ' + who + (a.pseudoElement ? a.pseudoElement : '');
        t[k] = (t[k] || 0) + 1;
      }
      await new Promise(r => setTimeout(r, 35));
    }
    return Object.entries(t).sort((a, b) => b[1] - a[1]).slice(0, 18).map(([k, v]) => k + '  x' + v);
  })()`);
  console.log('ANIMATIONS seen while playing (sample count over 60 samples):\n  ' + tally.join('\n  '));
}
const m0 = await metric();
const ps0 = await evalJs(`(() => { const p = audioCtx.playbackStats; return p ? JSON.parse(JSON.stringify(p)) : null; })()`);
await evalJs('window.__lt.length = 0; true');

// tap burst: fill cells in a scattered order, tapsPerSec per second, for `seconds`
const order = []; for (let c = 0; c < 16; c++) for (let r = 0; r < 8; r++) order.push([r, (c * 7) % 16]);
const total = Math.floor(tapsPerSec * seconds);
const t0 = Date.now();
for (let i = 0; i < total; i++) {
  const [r, c] = order[(i * 5) % order.length];
  const [x, y] = await cellPos(r, c);
  await click(x, y);
  const wait = t0 + ((i + 1) * 1000) / tapsPerSec - Date.now();
  if (wait > 0) await sleep(wait);
}
if (total === 0) await sleep(seconds * 1000);
await sleep(800);
const m1 = await metric();
const ps1 = await evalJs(`(() => { const p = audioCtx.playbackStats; return p ? JSON.parse(JSON.stringify(p)) : null; })()`);
const lt = await evalJs('window.__lt.slice()');
const panel = await evalJs('window.__panel()');
const notes = await evalJs(`document.querySelectorAll('#sequencer .noteBlock').length`);
const d = (k) => +(((m1[k] || 0) - (m0[k] || 0)) * 1000).toFixed(0);
const wall = (m1.Timestamp - m0.Timestamp) * 1000;
const line = panel.split('\n').find(l => /worst tick late/.test(l)) || panel;
console.log(JSON.stringify({
  throttle, tapsPerSec, seconds, instr, taps: total, notesInGrid: notes,
  mainThreadBusyPct: +((d('TaskDuration') / wall) * 100).toFixed(1),
  scriptMs: d('ScriptDuration'), layoutMs: d('LayoutDuration'), styleMs: d('RecalcStyleDuration'), layouts: m1.LayoutCount - m0.LayoutCount,
  longtasks: lt.length ? lt : 0,
  underrunEvents: ps0 && ps1 ? ps1.underrunEvents - ps0.underrunEvents : 'n/a',
  schedulerLine: line.trim(),
}, null, 1));
if (process.env.TRACE) {
  const done = new Promise(r => { const h = (m) => { const d = JSON.parse(m.data); if (d.method === 'Tracing.tracingComplete') { ws.removeEventListener('message', h); r(); } }; ws.addEventListener('message', h); });
  await send('Tracing.end'); await done;
  const mainTid = (() => { const nm = traceEvents.find(e => e.ph === 'M' && e.name === 'thread_name' && e.args && e.args.name === 'CrRendererMain'); return nm ? nm.tid : null; })();
  const sums = {};
  for (const e of traceEvents) { if (e.ph !== 'X' || !e.dur) continue; if (mainTid && e.tid !== mainTid) continue; sums[e.name] = (sums[e.name] || 0) + e.dur / 1000; }
  const top = Object.entries(sums).filter(([k]) => !/^(RunTask|ThreadControllerImpl::RunTask|ThreadControllerImpl::DoWork|SequenceManager.*|TimerFire|EventDispatch)$/.test(k)).sort((a, b) => b[1] - a[1]).slice(0, 16).map(([k, v]) => k + ': ' + v.toFixed(0) + 'ms');
  console.log('TRACE main-thread top events (ms over ' + wall.toFixed(0) + 'ms wall):\n  ' + top.join('\n  '));
}
await send('Browser.close').catch(() => {});
chrome.kill();
process.exit(0);
