/* Tap-feedback (micro press + blue glow) for primary action buttons */
(function(){
  function isDisabled(btn){
    if(!btn) return true;
    if(btn.disabled) return true;
    const ad = (btn.getAttribute('aria-disabled') || '').toLowerCase();
    if(ad === 'true') return true;
    if(btn.classList.contains('disabled')) return true;
    return false;
  }

  function flash(btn){
    if(isDisabled(btn)) return;
    const now = performance.now();
    if(btn.__tapFlashAt && (now - btn.__tapFlashAt) < 220) return;
    btn.__tapFlashAt = now;
    // restart animation
    btn.classList.remove('tapFlash');
    // force reflow
    void btn.offsetWidth;
    btn.classList.add('tapFlash');
    clearTimeout(btn.__tapFlashT);
    btn.__tapFlashT = setTimeout(() => btn.classList.remove('tapFlash'), 220);
  }

  function wire(){
    const selectors = [
      'button[aria-label="Play"]',
      'button[aria-label="Stop"]',
      'button[aria-label="Clear"]',
      'button[aria-label="Undo"]',
      '#cameraBtn',
      'button[aria-label="Scan"]'
    ];
    const btns = selectors.flatMap(sel => Array.from(document.querySelectorAll(sel)));
    const uniq = Array.from(new Set(btns)).filter(Boolean);

    uniq.forEach(btn => {
      // pointerdown gives immediate feedback on touch + mouse.
      btn.addEventListener('pointerdown', (e) => {
        // ignore right-click / non-primary mouse
        if(e.pointerType === 'mouse' && e.button !== 0) return;
        flash(btn);
      }, {passive:true});

      // keyboard accessibility (Enter/Space)
      btn.addEventListener('keydown', (e) => {
        if(e.key === 'Enter' || e.key === ' ') flash(btn);
      });
    });
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
