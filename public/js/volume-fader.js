/* Shadow-DOM encapsulated master volume fader */
(function(){
  class SeqVolumeFader extends HTMLElement{
    connectedCallback(){
      if(this.shadowRoot) return;
      const sr = this.attachShadow({mode:'open'});
      sr.innerHTML = `
<style>
/* ── host resets ─────────────────────────────────────────────────────────── */
:host{
  display: block;
  width: 100%;
  /* match the instrument button width — no extra column width needed */
  --instBtnSize: 58px;
  --instGap: 10px;
}

/* ── outer row: single centred column, no side readout ───────────────────── */
.seqFaderRow{
  width: 100%;
  display: flex;
  justify-content: center;
  /* top gap matches the gap between instrument buttons */
  margin-top: var(--instGap);
}

/* ── fader panel ─────────────────────────────────────────────────────────── */
/*
  Height fills from just below the last instBtn all the way to the bottom
  of the sequencer grid, matching the grid's bottom edge.

  Grid height  = cell*8 + gap*7
  Used above   = 4 buttons + 3 gaps  (instBtnSize*4 + instGap*3)
  Remaining    = grid height - above
  We subtract the panel's own vertical padding (10px top + 10px bottom)
  so the track + badge fill the interior neatly.
*/
.seqFaderPanel{
  width: var(--instBtnSize);
  height: calc(
    (var(--cell, 46px) * 8 + var(--gap, 4px) * 7)
    - (var(--instBtnSize) * 4 + var(--instGap) * 3)
    - var(--instGap)          /* the margin-top we added above */
  );
  border-radius: 18px;
  border: 4px solid #1d1d1d;
  background: #ffffff;
  box-shadow: 0 8px 0 rgba(0,0,0,0.07);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  /* top padding = a little breathing room; bottom padding = space for badge */
  padding: 10px 4px 8px;
  position: relative;
}

/* ── track area — fills all space above the badge ────────────────────────── */
.seqTrackArea{
  position: relative;
  flex: 1 1 0;              /* take all remaining height */
  width: var(--instBtnSize);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

/* ── track line ──────────────────────────────────────────────────────────── */
.seqTrack{
  position: relative;
  width: 3px;
  height: 100%;
  background: transparent;
  overflow: visible;
}
.seqTrack::before{
  content: "";
  position: absolute;
  left: 50%;
  top: 0;
  transform: translateX(-50%);
  width: 3px;
  height: 100%;
  border-radius: 999px;
  background: #0f0f0f;
  pointer-events: none;
}

/* ── tick marks ──────────────────────────────────────────────────────────── */
.seqIncTicks{
  position: absolute;
  left: 50%;
  top: 8px;
  bottom: 8px;
  width: 6px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  pointer-events: none;
  opacity: 0.55;
}
.seqIncTicks .t{
  width: 4px;
  height: 2px;
  background: #0f0f0f;
  border-radius: 2px;
}
.seqIncTicks .t:first-of-type,
.seqIncTicks .t:last-of-type{ visibility: hidden; }

/* ── end-stop caps ───────────────────────────────────────────────────────── */
.seqCaps{
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  height: 100%;
  width: 9px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  pointer-events: none;
}
.seqCap{
  display: block;
  width: 9px;
  height: 9px;
  border-radius: 999px;
  border: 2px solid #1d1d1d;
  background: #fff;
  box-shadow: 0 2px 0 rgba(0,0,0,0.05);
}

/* ── fader knob ──────────────────────────────────────────────────────────── */
.seqKnob{
  position: absolute;
  left: 50%;
  transform: translate(-50%, -50%);
  width: calc(var(--instBtnSize) - 12px);
  height: 16px;
  border-radius: 11px;
  border: 3px solid #1d1d1d;
  background: #ffffff;
  box-shadow:
    0 5px 0 rgba(0,0,0,0.07),
    inset 0 2px 0 rgba(255,255,255,0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.seqKnobStripe{
  width: 70%;
  height: 7px;
  border-radius: 999px;
  border: 3px solid rgba(29,29,29,0.70);
  background: rgba(216,240,255,0.75);
  box-shadow: inset 0 2px 0 rgba(255,255,255,0.55);
}

/* ── volume badge — sits below the track, inside the panel ──────────────── */
/*
  A small circle at the bottom of the panel showing the current value.
  No "VOL" label — the context is obvious, and the circle keeps it tidy.
*/
.seqBadge{
  flex: 0 0 auto;
  margin-top: 6px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid rgba(29,29,29,0.18);
  background: #f0f5ff;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.seqBadge .num{
  font-family: "Fredoka","Trebuchet MS", Arial, sans-serif;
  font-weight: 900;
  font-size: 13px;
  color: #1f2a44;
  line-height: 1;
  letter-spacing: -0.5px;
}

/* ── hidden range input (handles a11y / keyboard) ────────────────────────── */
.seqVolRange{
  position: absolute;
  left: 50%;
  top: 0;
  transform: translateX(-50%) rotate(-90deg);
  transform-origin: center;
  width: calc(100% - 6px);
  height: 28px;
  opacity: 0;
  pointer-events: none;
  cursor: pointer;
  z-index: 20;
}
.seqVolRange:focus{ outline: none; }
</style>

<div class="seqFaderRow">
  <div class="seqFaderPanel" aria-label="Master volume fader">

    <!-- track + knob -->
    <div class="seqTrackArea" id="seqTrackArea">
      <div class="seqTrack"></div>

      <input id="seqVolRange" class="seqVolRange"
             type="range" min="0" max="10" step="0.01" value="10"
             aria-label="Master volume"/>

      <div class="seqIncTicks" aria-hidden="true">
        <div class="t"></div><div class="t"></div><div class="t"></div>
        <div class="t"></div><div class="t"></div><div class="t"></div>
        <div class="t"></div><div class="t"></div>
      </div>

      <div class="seqCaps" aria-hidden="true">
        <div class="seqCap"></div>
        <div class="seqCap"></div>
      </div>

      <div class="seqKnob" id="seqKnob"
           role="slider" aria-valuemin="0" aria-valuemax="10"
           aria-valuenow="10" tabindex="-1">
        <div class="seqKnobStripe"></div>
      </div>
    </div>

    <!-- inline number badge at the bottom of the panel -->
    <div class="seqBadge" aria-label="Volume level">
      <span class="num" id="seqVolNum">10</span>
    </div>

  </div>
</div>
`;
      const area = sr.getElementById('seqTrackArea');
      const range = sr.getElementById('seqVolRange');
      const knob = sr.getElementById('seqKnob');
      const num  = sr.getElementById('seqVolNum');
      if(!area || !range || !knob || !num) return;

      function ensureAudio(){
        try{
          if(typeof window.getAudio === 'function'){
            const a = window.getAudio();
            try{ if(a && a.state === 'suspended') a.resume(); }catch(_){}
          }
        }catch(_){}
      }
      // DJ equal-power taper: maps linear fader position (0..1) → gain (0..1)
      function taperGain(t){ return t <= 0 ? 0 : Math.pow(t, 2.0); }

      // Smoothed gain setter — 8ms ramp eliminates zipper noise / crackle
      const RAMP_TIME = 0.008;
      function setMasterGain(t){
        const mg = (typeof window.masterGain !== 'undefined' ? window.masterGain :
                   (typeof masterGain !== 'undefined' ? masterGain : null));
        const ctx = (typeof window.audioCtx !== 'undefined' ? window.audioCtx : null);
        if(!mg || !mg.gain) return;
        const targetGain = taperGain(t);
        if(ctx && ctx.state === 'running'){
          const now = ctx.currentTime;
          mg.gain.cancelScheduledValues(now);
          mg.gain.setValueAtTime(mg.gain.value, now);
          mg.gain.linearRampToValueAtTime(targetGain, now + RAMP_TIME);
        } else {
          mg.gain.value = targetGain;
        }
      }
      function clamp(n,min,max){ return Math.max(min, Math.min(max,n)); }

      function getMetrics(){
        // When #page is scaled via CSS transform (iPhone landscape “stageScaled”),
        // getBoundingClientRect() is in *scaled* pixels, but style.top uses *local* pixels.
        const rect = area.getBoundingClientRect();           // scaled px
        const localH = area.clientHeight || area.offsetHeight || rect.height || 1; // unscaled px
        const scaleY = (rect.height / localH) || 1;

        const knobH = knob.offsetHeight || (parseFloat(getComputedStyle(knob).height) || 16);
        const half = knobH / 2;

        const minC = half;            // knob center at top end-stop
        const maxC = localH - half;   // knob center at bottom end-stop
        return { rect, localH, scaleY, minC, maxC };
      }

      function layoutFromRange(){
        const m = getMetrics();
        const t = clamp((parseFloat(range.value) || 0) / 10, 0, 1); // 0..1 (0 bottom, 1 top)
        const y = m.maxC - (m.maxC - m.minC) * t;                  // center position in local px
        knob.style.top = y + 'px';
        num.textContent = String(Math.round(t * 10));
      }

      const setFromClientY=(clientY)=>{
        const m = getMetrics();
        // Convert pointer Y from scaled viewport pixels to local (unscaled) element pixels
        const localY = (clientY - m.rect.top) / m.scaleY;

        const yRaw = localY - (clickOnKnob ? pointerOffset : 0);
        const yy = clamp(yRaw, m.minC, m.maxC);

        const t = (m.maxC - yy) / (m.maxC - m.minC); // 0..1
        range.value = String(t * 10);

        setMasterGain(t);
        layoutFromRange();
      };


      // Ensure audio on first interaction
      range.addEventListener('pointerdown', ensureAudio, {passive:true});
      range.addEventListener('input', ()=>{
        const v = parseFloat(range.value)/10;
        setMasterGain(v);
        layoutFromRange();
      });

      // pointer dragging (no-jump: keep value until user actually drags)
      let dragging=false;
      let moved=false;
      let startX=0, startY=0;
      let pointerOffset=0;
      let clickOnKnob=false;


      const onPointerDown=(e)=>{
        dragging=true;
        moved=false;
        startX=e.clientX; startY=e.clientY;
        clickOnKnob=!!(e.target && e.target.closest && e.target.closest('.seqKnob'));
        const m = getMetrics();
        // compute where the knob center currently is (in *local* area coords) to preserve relative grab point
        const t0 = clamp((parseFloat(range.value) || 10) / 10, 0, 1);
        const knobY = m.maxC - (m.maxC - m.minC) * t0;
        const localY = (e.clientY - m.rect.top) / m.scaleY;
        pointerOffset = localY - knobY;

        area.setPointerCapture(e.pointerId);
        ensureAudio();

        // If user clicks the *track* (not the knob), allow an immediate jump to that position.
        if(!clickOnKnob){
          setFromClientY(e.clientY);
        }
      };

      const onPointerMove=(e)=>{
        if(!dragging) return;

        // Don't change value until the user actually drags a few pixels (prevents first-click jump)
        if(!moved){
          const dx=Math.abs(e.clientX-startX);
          const dy=Math.abs(e.clientY-startY);
          if(dx<3 && dy<3) return;
          moved=true;
        }
        setFromClientY(e.clientY);
      };

      const onPointerUp=()=>{
        dragging=false;
        moved=false;
      };

      area.addEventListener('pointerdown', onPointerDown);
      area.addEventListener('pointermove', onPointerMove);
      area.addEventListener('pointerup', onPointerUp);
      area.addEventListener('pointercancel', onPointerUp);

      // initial layout
      requestAnimationFrame(layoutFromRange);
      setTimeout(layoutFromRange, 50);
    }
  }
  customElements.define('seq-volume-fader', SeqVolumeFader);
})();
