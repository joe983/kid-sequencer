/* === Drag-to-pan viewport === */
(function(){
  const viewport = document.getElementById('viewport');
  const page = document.getElementById('page');
  if(!viewport || !page) return;

  // Lock "stage" size once (the first time the page loads at a good size)
  function lockStageOnce(){
    if(page.dataset.stageLocked === "1") return;

    // Use scrollWidth/scrollHeight for intrinsic content size.
    // This preserves your full-screen layout as the baseline.
    const w = Math.ceil(page.scrollWidth);
    const h = Math.ceil(page.scrollHeight);

    if(w > 0) page.style.minWidth = w + "px";
    if(h > 0) page.style.minHeight = h + "px";

    page.dataset.stageLocked = "1";
  }

  // Run after layout settles
  window.addEventListener('load', () => {
    requestAnimationFrame(lockStageOnce);
    setTimeout(lockStageOnce, 50);
  });

  // Cursor hints
  document.body.classList.add('can-pan');

  // Drag to pan (mouse / pointer)
  let dragging = false;
  let startX = 0, startY = 0;
  let startLeft = 0, startTop = 0;
  let pointerId = null;

  // Disable drag-to-pan while interacting with the volume fader (Shadow DOM)
  let panBlockedByFader = false;
  const faderHost = document.getElementById('masterVolUI');
  if(faderHost){
    faderHost.addEventListener('pointerenter', () => { panBlockedByFader = true; });
    faderHost.addEventListener('pointerleave', () => { panBlockedByFader = false; });
  }
  function eventHitsFader(ev){
    const path = ev.composedPath ? ev.composedPath() : [];
    return path.some(n => n && n.tagName && String(n.tagName).toLowerCase() === 'seq-volume-fader');
  }

  function isInteractive(el){
    return !!el.closest('button, a, input, select, textarea, label, [role="button"], [onclick], .tool, .instBtn, .cell, .drawer, .knob, .handle, .slider');
  }

  function onDown(e){
    // Left mouse / primary touch only
    if(e.button !== undefined && e.button !== 0) return;
    if(panBlockedByFader || eventHitsFader(e)) return;
    if(isInteractive(e.target)) return;

    dragging = true;
    pointerId = e.pointerId ?? null;
    startX = e.clientX;
    startY = e.clientY;
    startLeft = viewport.scrollLeft;
    startTop = viewport.scrollTop;

    document.body.classList.add('dragging-pan');
    try{ if(pointerId !== null) viewport.setPointerCapture(pointerId); }catch(_){}
    e.preventDefault();
  }

  function onMove(e){
    if(!dragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    viewport.scrollLeft = startLeft - dx;
    viewport.scrollTop  = startTop  - dy;
    e.preventDefault();
  }

  function onUp(){
    if(!dragging) return;
    dragging = false;
    document.body.classList.remove('dragging-pan');
    pointerId = null;
  }

  viewport.addEventListener('pointerdown', onDown, {passive:false});
  viewport.addEventListener('pointermove', onMove, {passive:false});
  window.addEventListener('pointerup', onUp);
  window.addEventListener('pointercancel', onUp);
})();
