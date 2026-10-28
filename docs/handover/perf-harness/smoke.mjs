// Smoke test views: load, tap cells, play, tempo up mid-play, stop. Report errors + scheduler stats.
import { spawn } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const urls = process.argv.slice(2);
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
for (const path of urls) {
  const port = 9500 + Math.floor(Math.random() * 90);
  const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'kseq-sm-'))}`, '--window-size=1600,900', '--autoplay-policy=no-user-gesture-required', 'about:blank'], { stdio: 'ignore' });
  let wsUrl; for (let i = 0; i < 60 && !wsUrl; i++) { try { const j = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); const p = j.find(t => t.type === 'page'); if (p) wsUrl = p.webSocketDebuggerUrl; } catch {} if (!wsUrl) await sleep(250); }
  const ws = new WebSocket(wsUrl); await new Promise(r => ws.addEventListener('open', r, { once: true }));
  let id = 0; const pend = new Map(); const errs = [];
  ws.addEventListener('message', m => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id); } if (d.method === 'Runtime.exceptionThrown') errs.push('EXC ' + (d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text).slice(0, 220)); if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errs.push('console.error ' + d.params.args.map(a => a.value ?? a.description ?? '').join(' ').slice(0, 220)); });
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pend.set(i, d => res(d.result || d.error)); ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async (e) => { const r = await send('Runtime.evaluate', { expression: e, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) return 'EXC ' + JSON.stringify(r.exceptionDetails).slice(0, 300); return r.result?.value; };
  await send('Page.enable'); await send('Runtime.enable');
  const sep = path.includes('?') ? '&' : '?';
  await send('Page.navigate', { url: `http://localhost:3000/${path}${sep}audiodebug=1` });
  await sleep(5000);
  const res = await ev(`(async () => {
    const cells = Array.from(document.querySelectorAll('#sequencer .cell'));
    const cols = cells.length ? Math.round(cells.length / document.querySelectorAll('.noteLayer').length) : 0;
    for (let i = 0; i < Math.min(6, cells.length); i++) cells[(i * 7) % cells.length].click();
    const notes = document.querySelectorAll('#sequencer .noteBlock').length;
    const playBtn = document.querySelector('button[aria-label="Play"]');
    if (playBtn) playBtn.click();
    await new Promise(r => setTimeout(r, 2500));
    const up = document.getElementById('tempoUpBtn');
    const t0 = document.getElementById('tempoBox') ? document.getElementById('tempoBox').textContent : '-';
    if (up && up.offsetParent) for (let i = 0; i < 4; i++) { up.click(); await new Promise(r => setTimeout(r, 150)); }
    await new Promise(r => setTimeout(r, 2500));
    const t1 = document.getElementById('tempoBox') ? document.getElementById('tempoBox').textContent : '-';
    const ph = document.getElementById('playhead');
    const playheadMoved = ph ? ph.style.transform : '-';
    const panel = (Array.from(document.querySelectorAll('pre')).find(p => /worst tick late/.test(p.textContent)) || {}).textContent || '';
    if (typeof window.stop === 'function') window.stop();
    return { cells: cells.length, cols, notes, tempo: t0 + '->' + t1, playheadMoved, ctx: window.audioCtx ? window.audioCtx.state : 'none', panel: (panel.split('\\n').find(l => /worst tick late/.test(l)) || '').trim() };
  })()`);
  console.log(path.padEnd(22), JSON.stringify(res), errs.length ? '\n   ERRORS: ' + errs.join(' | ') : '');
  chrome.kill();
}
process.exit(0);
