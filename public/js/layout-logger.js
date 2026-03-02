/* ==================== LAYOUT DEBUG LOGGER ====================
   Captures layout, scroll, pan, resize, and overflow diagnostics.
   Sends to Firestore collection "zoomDebug".
   Disable with ?logLayout=0 in the URL.
   ============================================================= */
(async () => {
  const params = new URLSearchParams(window.location.search);
  if (params.get('logLayout') === '0') return;

  const isHttp = location.protocol === 'http:' || location.protocol === 'https:';
  if (!isHttp) { console.info('[LayoutDebug] Skipping in file:// mode'); return; }

  // --- Firebase setup: reuse existing app or create, then sign in anonymously ---
  let db = null;
  try {
    const { initializeApp, getApps, getApp } = await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js');
    const { getFirestore, collection, addDoc } = await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js');
    const { getAuth, signInAnonymously } = await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js');

    // Reuse the default app if it exists (from firebase-init.js), otherwise create one
    let app;
    try { app = getApp(); } catch(_) {
      app = initializeApp({
        apiKey: "AIzaSyBokU1u4hJIxZ0Y4U9BxQreI3hnxEJzuwc",
        authDomain: "kid-sequencer.firebaseapp.com",
        projectId: "kid-sequencer",
        storageBucket: "kid-sequencer.firebasestorage.app",
        messagingSenderId: "715996068165",
        appId: "1:715996068165:web:84e127454cb9bb0c35a62c"
      });
    }

    // Sign in anonymously so Firestore rules allow writes
    const auth = getAuth(app);
    try { await signInAnonymously(auth); } catch(e) { console.warn('[LayoutDebug] Anon auth failed:', e); }

    db = getFirestore(app);
    window.__layoutDebugFirestore = { db, collection, addDoc };
    console.log('[LayoutDebug] Logger ready');
  } catch (e) {
    console.warn('[LayoutDebug] Firestore init failed, logging to console only:', e);
  }

  // --- Session & state ---
  const sessionId = 'LD-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6);
  let seq = 0;
  const buffer = [];
  let flushTimer = null;
  const FLUSH_INTERVAL = 3000;
  const MAX_BUFFER = 50;

  // --- Snapshot helper ---
  function snap() {
    const root = document.documentElement;
    const vp = document.getElementById('viewport');
    const pg = document.getElementById('page');
    const vv = window.visualViewport;

    const vpRect = vp ? vp.getBoundingClientRect() : {};
    const pgRect = pg ? pg.getBoundingClientRect() : {};

    return {
      // Visual viewport
      vvW: vv ? Math.round(vv.width) : null,
      vvH: vv ? Math.round(vv.height) : null,
      vvOX: vv ? Math.round(vv.offsetLeft) : null,
      vvOY: vv ? Math.round(vv.offsetTop) : null,
      vvS: vv ? +vv.scale.toFixed(3) : null,
      // window
      iW: window.innerWidth,
      iH: window.innerHeight,
      oW: window.outerWidth,
      oH: window.outerHeight,
      dpr: +window.devicePixelRatio.toFixed(2),
      // #viewport element
      vpSL: vp ? vp.scrollLeft : null,
      vpST: vp ? vp.scrollTop : null,
      vpSW: vp ? vp.scrollWidth : null,
      vpSH: vp ? vp.scrollHeight : null,
      vpCW: vp ? vp.clientWidth : null,
      vpCH: vp ? vp.clientHeight : null,
      // #page element
      pgW: pgRect.width ? Math.round(pgRect.width) : null,
      pgH: pgRect.height ? Math.round(pgRect.height) : null,
      pgL: pgRect.left !== undefined ? Math.round(pgRect.left) : null,
      pgT: pgRect.top !== undefined ? Math.round(pgRect.top) : null,
      pgTransform: pg ? pg.style.transform || 'none' : null,
      // Mode flags
      scaled: root.classList.contains('stageScaled'),
      tablet: root.classList.contains('tabletScaled'),
      // CSS vars
      stageW: parseInt(getComputedStyle(root).getPropertyValue('--stageW')) || null,
      stageH: parseInt(getComputedStyle(root).getPropertyValue('--stageH')) || null,
      cell: parseInt(getComputedStyle(root).getPropertyValue('--cell')) || null,
      // Overflow detection
      vpOverflowX: vp ? (vp.scrollWidth > vp.clientWidth + 2) : null,
      vpOverflowY: vp ? (vp.scrollHeight > vp.clientHeight + 2) : null,
      // Screen orientation
      orient: screen.orientation ? screen.orientation.type : (window.orientation !== undefined ? window.orientation : null),
    };
  }

  // --- Log entry ---
  function logEntry(event, extra) {
    const entry = {
      seq: seq++,
      t: Date.now(),
      event,
      ...snap(),
      ...(extra || {})
    };
    buffer.push(entry);
    console.log('[LayoutDebug]', event, entry);

    if (buffer.length >= MAX_BUFFER) flush();
    else scheduleFlush();
  }

  function scheduleFlush() {
    if (flushTimer) return;
    flushTimer = setTimeout(flush, FLUSH_INTERVAL);
  }

  async function flush() {
    clearTimeout(flushTimer);
    flushTimer = null;
    if (buffer.length === 0) return;

    const entries = buffer.splice(0);
    if (!db) return; // console-only mode

    try {
      const { collection, addDoc } = window.__layoutDebugFirestore;
      await addDoc(collection(db, 'zoomDebug'), {
        sessionId,
        ts: Date.now(),
        ua: navigator.userAgent,
        entries
      });
    } catch (e) {
      console.warn('[LayoutDebug] Flush failed:', e);
      // Put entries back
      buffer.unshift(...entries);
    }
  }

  // Flush on page hide
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush();
  });
  window.addEventListener('pagehide', flush);

  // --- Hook into layout events ---

  // 1. PAGE LOAD
  logEntry('PAGE-LOAD', { url: location.href });

  // 2. Resize
  let resizeTimeout = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => logEntry('resize'), 150);
  }, { passive: true });

  // 3. VisualViewport resize
  if (window.visualViewport) {
    let vvTimeout = null;
    window.visualViewport.addEventListener('resize', () => {
      clearTimeout(vvTimeout);
      vvTimeout = setTimeout(() => logEntry('vv-resize'), 150);
    }, { passive: true });

    window.visualViewport.addEventListener('scroll', () => {
      logEntry('vv-scroll');
    }, { passive: true });
  }

  // 4. Orientation change
  window.addEventListener('orientationchange', () => {
    setTimeout(() => logEntry('orient-change'), 200);
  }, { passive: true });

  // 5. Viewport scroll (the #viewport element)
  const vpEl = document.getElementById('viewport');
  if (vpEl) {
    let scrollTimeout = null;
    vpEl.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => logEntry('vp-scroll'), 100);
    }, { passive: true });
  }

  // 6. Monitor applyStageFit by patching scheduleLayout
  const origSchedule = window.scheduleLayout;
  if (origSchedule) {
    let layoutCount = 0;
    window.scheduleLayout = function() {
      layoutCount++;
      const lc = layoutCount;
      origSchedule.apply(this, arguments);
      // Log after the rAF fires
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          logEntry('layout-pass', { layoutN: lc });
        });
      });
    };
  }

  // 7. Drag-to-pan tracking
  if (vpEl) {
    let panStart = null;
    vpEl.addEventListener('pointerdown', (e) => {
      // Only log non-interactive pans (background drags)
      const el = e.target;
      if (el && el.closest && el.closest('button, a, input, select, textarea, .tool, .instBtn, .cell, .drumMiniBtn, .drumStyleBtn, seq-volume-fader')) return;
      panStart = { x: e.clientX, y: e.clientY, sl: vpEl.scrollLeft, st: vpEl.scrollTop, t: Date.now() };
    }, { passive: true });

    window.addEventListener('pointerup', () => {
      if (panStart) {
        const dx = vpEl.scrollLeft - panStart.sl;
        const dy = vpEl.scrollTop - panStart.st;
        const dt = Date.now() - panStart.t;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
          logEntry('pan-end', { panDX: dx, panDY: dy, panDT: dt });
        }
        panStart = null;
      }
    }, { passive: true });
  }

  // 8. Periodic idle snapshot (every 10s)
  setInterval(() => {
    logEntry('idle-snap');
  }, 10000);

  // 9. Touch event tracking (for diagnosing mobile scroll issues)
  let touchCount = 0;
  document.addEventListener('touchstart', (e) => {
    touchCount++;
    if (touchCount <= 5 || touchCount % 10 === 0) {
      logEntry('touch-start', {
        touches: e.touches.length,
        tX: Math.round(e.touches[0].clientX),
        tY: Math.round(e.touches[0].clientY),
        touchN: touchCount
      });
    }
  }, { passive: true });

  // 10. Overflow scanner (runs after each layout pass)
  function scanOverflows() {
    const problems = [];
    const els = document.querySelectorAll('#page, #viewport, #topBar, #mainLayout, #tools, #sequencerShell, #rightCol, #contentWrap, #drumPanel');
    els.forEach(el => {
      const id = el.id || el.className;
      if (el.scrollWidth > el.clientWidth + 2) {
        problems.push({ id, dir: 'X', scroll: el.scrollWidth, client: el.clientWidth });
      }
      if (el.scrollHeight > el.clientHeight + 2) {
        problems.push({ id, dir: 'Y', scroll: el.scrollHeight, client: el.clientHeight });
      }
    });
    if (problems.length > 0) {
      logEntry('overflow-detected', { overflows: problems });
    }
  }

  // Run overflow scan after initial layout and periodically
  setTimeout(scanOverflows, 2000);
  setInterval(scanOverflows, 15000);

  // 11. Log when stageScaled/tabletScaled class changes
  const observer = new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.attributeName === 'class') {
        const cl = document.documentElement.className;
        logEntry('class-change', { htmlClass: cl });
      }
    }
  });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

  // Expose for manual use in console
  window.__layoutDebug = { logEntry, flush, snap, sessionId };
  console.log('[LayoutDebug] Session:', sessionId, '— call __layoutDebug.snap() or __layoutDebug.logEntry("test") from console. Disable with ?logLayout=0');
})();
