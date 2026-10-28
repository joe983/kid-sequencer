// Screenshot the beat-badge flash frozen at fixed points, for a before/after look.
// Usage: node shot.mjs <page> <outPrefix> [reduce]
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const page = process.argv[2] || 'index.html';   // not bare '/': it once loaded with 0 beat badges (script timing)
const outPrefix = process.argv[3];
const reduce = process.argv[4] === 'reduce';
const port = 9800 + Math.floor(Math.random() * 150);
const userDir = mkdtempSync(join(tmpdir(), 'kseq-shot-'));
const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${userDir}`,
  '--window-size=1600,900', '--hide-scrollbars', '--no-first-run', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
let wsUrl;
for (let i = 0; i < 60 && !wsUrl; i++) { try { const j = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); const p = j.find(t => t.type === 'page'); if (p) wsUrl = p.webSocketDebuggerUrl; } catch {} if (!wsUrl) await sleep(250); }
const ws = new WebSocket(wsUrl); await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pend = new Map();
ws.addEventListener('message', m => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id); } });
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pend.set(i, d => d.error ? rej(new Error(JSON.stringify(d.error))) : res(d.result)); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (e) => { const r = await send('Runtime.evaluate', { expression: e, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 300)); return r.result.value; };

await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1600, height: 900, deviceScaleFactor: 2, mobile: false });
if (reduce) await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
const errs = [];
ws.addEventListener('message', m => { const d = JSON.parse(m.data); if (d.method === 'Runtime.exceptionThrown') errs.push(d.params.exceptionDetails.exception?.description?.slice(0, 200)); if (d.method === 'Runtime.consoleAPICalled' && /error|warn/.test(d.params.type)) errs.push(d.params.type + ': ' + d.params.args.map(a => a.value ?? a.description ?? '').join(' ').slice(0, 300)); });
await send('Runtime.enable');
await send('Page.navigate', { url: `http://localhost:3000/${page}` });
let nb = 0;
for (let i = 0; i < 40 && !nb; i++) { await sleep(250); nb = await ev(`document.querySelectorAll('.beatBadge').length`); }
console.log('badges', nb, 'errors', JSON.stringify(errs));
await sleep(800);
const clip = await ev(`(() => {
  document.documentElement.style.setProperty('--beatFlash', '1000ms');
  const b = Array.from(document.querySelectorAll('.beatBadge'));
  b[0].classList.add('beatOne');            // strong beat (3/4 styling) on badge 1
  for (const i of [0, 1]) { b[i].classList.remove('beatOn'); void b[i].offsetWidth; b[i].classList.add('beatOn'); }
  const r1 = b[0].getBoundingClientRect(), r2 = b[2].getBoundingClientRect();
  return { x: r1.left - 30, y: r1.top - 30, width: (r2.right - r1.left) + 60, height: r1.height + 60, scale: 1 };
})()`);
for (const t of [0, 550, 900]) {
  await ev(`(() => { for (const a of document.getAnimations()) { const tg = a.effect && a.effect.target; if (tg && tg.classList && tg.classList.contains('beatBadge')) { a.pause(); a.currentTime = ${t}; } } return true; })()`);
  await sleep(150);
  const { data } = await send('Page.captureScreenshot', { format: 'png', clip });
  writeFileSync(`${outPrefix}-${t}.png`, Buffer.from(data, 'base64'));
}
console.log('ok', JSON.stringify(clip));
await send('Browser.close').catch(() => {}); chrome.kill(); process.exit(0);
