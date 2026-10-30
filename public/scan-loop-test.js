/* Live-loop fixtures for the worksheet scanner, run from scan-tests.html.

   The other fixtures call the pipeline one frame at a time; these drive the REAL
   live loop (openCameraModal → _scanTick → lock → _processScanFrame) with a fake
   camera, because the bugs they exist for live in the loop, not the pipeline:

   - refusedLock: a frame that locked on three times and then failed the grid
     check STOPPED the loop for good, so the scanner sat on "Point the camera at
     your worksheet" until the camera was closed and reopened (in class,
     2026-10-28). Phase 1 shows a sheet that locks but must fail the grid check
     (missing bottom-left mark — a tool icon stands in); phase 2 a good sheet,
     which must then be read.
   - slowReport / gaveupReport: a hunt that never scans reports itself, carries
     the reason, never a photo, fits the Firestore rule, and says it only once.
   - hint: the status pill says why it isn't locking.

   Reports go to Scan.reportSink here, never to Firestore. Returns an array of
   { name, pass, detail }. */
async function scanLoopTests(app, makeSheet, CELLS, OVER){
  const W = app.contentWindow, D = app.contentDocument;
  const S = W.KidSequencer.Scan, G = S.SHEET_GEOMETRY["kidseq:main"];
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const modal = D.getElementById("camModal");
  const isOpen = () => modal.classList.contains("show");
  // What the status pill actually SAYS — not the attribute behind it (an attr()
  // pointed at the wrong element once rendered an empty pill with the attribute set).
  const pill = () => {
    const c = W.getComputedStyle(modal.querySelector(".camStage"), "::after").content || "";
    return c.replace(/^["']|["']$/g, "");
  };
  const out = [];

  // An embedded/background pane can freeze rAF; the loop runs on it.
  W.requestAnimationFrame = cb => W.setTimeout(() => cb(W.performance.now()), 16);
  W.cancelAnimationFrame = id => W.clearTimeout(id);
  try{ W.KidSequencer.Sequencer.buildGrid(); }catch(e){}

  const reports = [];
  S.reportSink = r => reports.push(r);

  const cv = D.createElement("canvas");
  cv.width = 420; cv.height = 315;
  const g = cv.getContext("2d");
  const show = img => g.putImageData(img, 0, 0);
  const realGUM = W.navigator.mediaDevices && W.navigator.mediaDevices.getUserMedia;
  // keep frames flowing — a static canvas stream may stop delivering
  const pump = W.setInterval(() => { g.fillStyle = "rgba(255,255,255,0.004)"; g.fillRect(0, 0, 1, 1); }, 60);
  const openWith = async img => {
    show(img);
    const stream = cv.captureStream(15);
    W.navigator.mediaDevices.getUserMedia = async () => stream;
    await W.openCameraModal();
    return stream;
  };
  const close = stream => { if(isOpen()) W.closeCameraModal(); stream.getTracks().forEach(t => t.stop()); };

  try{
    /* ---- refusedLock ---- */
    const bad  = makeSheet(S, G, { cells: CELLS, drop: 3 });
    const good = makeSheet(S, G, { cells: CELLS });
    const probe = S.diagnose(bad, "kidseq:main");
    if(probe.verdict !== "grid-misregistered"){
      out.push({ name: "loop · refused lock", pass: false,
                 detail: "fixture: bad sheet gave " + probe.verdict + ", not grid-misregistered" });
    }else{
      let st = await openWith(bad);
      // Locks on the bad sheet, refused by the grid check, over and over. The pill
      // alternates "Hold steady…" with the hint, so sample it rather than once.
      const said = new Set();
      for(let i = 0; i < 30; i++){ await wait(100); said.add(pill()); }
      const hintSeen = said.has("Show corners") ? "Show corners"
                     : [...said].join(" | ");
      show(good);
      for(let i = 0; i < 40 && isOpen(); i++) await wait(150);
      const stillOpen = isOpen();
      close(st);
      out.push({ name: "loop · refused lock", pass: !stillOpen,
                 detail: stillOpen ? "loop stopped after the refused lock: good sheet never read"
                                   : "good sheet read after a refused lock" });
      out.push({ name: "loop · hint on refused lock", pass: hintSeen === "Show corners",
                 detail: "pill said: " + (hintSeen || "(nothing)") });
      out.push({ name: "loop · scan that succeeds sends nothing", pass: reports.length === 0,
                 detail: reports.length + " report(s)" });
    }

    /* ---- slowReport ---- */
    reports.length = 0;
    S.reportSlowMs = 1500;
    const over = makeSheet(S, G, { cells: CELLS, quad: OVER, bg: "#2a2a2a" });
    let st = await openWith(over);
    await wait(2600);
    const hint = pill();
    close(st);                       // must NOT send a second ("gaveup") report
    await wait(100);
    let r = null; try{ r = JSON.parse(reports[0]); }catch(e){}
    const okShape = !!r && r.kind === "scan" && r.trigger === "slow" && r.ticks > 0 &&
                    r.tally && Object.keys(r.records || {}).length > 0;
    const noPhoto = reports.every(s => !/data:image|jpeg|base64/i.test(s));
    out.push({ name: "loop · slow hunt reports itself", pass: okShape,
               detail: r ? ("trigger " + r.trigger + ", tally " + JSON.stringify(r.tally) + ", hint " + r.hint) : "no report" });
    out.push({ name: "loop · report fits the rule, no photo", pass: noPhoto && reports.every(s => s.length <= 9000),
               detail: reports.map(s => s.length + " chars").join(", ") || "none" });
    out.push({ name: "loop · one report per hunt", pass: reports.length === 1,
               detail: reports.length + " report(s)" });
    out.push({ name: "loop · overflow hint", pass: hint === "Move Back",
               detail: "pill said: " + (hint || "(nothing)") });

    /* ---- gaveupReport ---- */
    reports.length = 0;
    S.reportSlowMs = 600000;
    st = await openWith(over);
    await wait(5600);                // past the 5 s "gave up" floor
    close(st);
    await wait(100);
    r = null; try{ r = JSON.parse(reports[0]); }catch(e){}
    out.push({ name: "loop · closing without a scan reports", pass: !!r && r.trigger === "gaveup" && reports.length === 1,
               detail: r ? ("trigger " + r.trigger + ", " + r.secs + " s") : "no report" });

    /* ---- debug mode reports every scan (owner 2026-10-29: a /02 sheet "never
       locked on" and left no report, so nothing showed what happened) ---- */
    S.debug = true;
    try{
      reports.length = 0;
      st = await openWith(good);
      for(let i = 0; i < 40 && isOpen(); i++) await wait(150);
      close(st);
      r = null; try{ r = JSON.parse(reports[0]); }catch(e){}
      const ok = !!r && r.trigger === "ok" && !!r.read && r.read.sheet === "main" && r.read.here === true &&
                 r.read.notes === "0:0+1 3:5+1 7:12+1";
      out.push({ name: "loop · debug: a good scan reports what it read", pass: ok && reports.length === 1,
                 detail: r ? (r.trigger + " " + JSON.stringify(r.read)) : "no report" });

      reports.length = 0;
      st = await openWith(over);
      await wait(900);
      close(st);                    // well under the 5 s floor a normal opening needs
      await wait(100);
      r = null; try{ r = JSON.parse(reports[0]); }catch(e){}
      out.push({ name: "loop · debug: a short hunt still reports", pass: !!r && r.trigger === "gaveup",
                 detail: r ? ("trigger " + r.trigger + ", camera open " + r.openSecs + " s") : "no report" });

      /* A camera that gives no picture: play() never settled and the loop never
         started, so this failure could never report. Now it starts anyway and
         every pictureless frame is tallied. */
      reports.length = 0;
      S.reportSlowMs = 1500;
      W.navigator.mediaDevices.getUserMedia = async () => new W.MediaStream();
      await W.openCameraModal();
      await wait(2200);
      if(isOpen()) W.closeCameraModal();
      await wait(100);
      r = null; try{ r = JSON.parse(reports[0]); }catch(e){}
      out.push({ name: "loop · no camera picture still reports", pass: !!r && r.tally && r.tally["no-frame"] > 0,
                 detail: r ? ("trigger " + r.trigger + ", tally " + JSON.stringify(r.tally)) : "no report" });
    }finally{
      S.debug = false;
      S.reportSlowMs = 0;
    }
  }finally{
    W.clearInterval(pump);
    S.reportSink = null;
    S.reportSlowMs = 0;              // back to the default
    if(realGUM) W.navigator.mediaDevices.getUserMedia = realGUM;
  }
  return out;
}
