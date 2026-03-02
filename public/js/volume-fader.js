/* Shadow-DOM encapsulated master volume fader */
(function(){
  class SeqVolumeFader extends HTMLElement{
    connectedCallback(){
      if(this.shadowRoot) return;
      const sr = this.attachShadow({mode:'open'});
      sr.innerHTML = `
<style>
:host{ display:block; width:100%; }
/* -------------------- MASTER VOLUME FADER (UI ONLY) -------------------- */
    :host{ --instBtnSize: 58px; --instGap: 10px; }

    /* Give the right column enough width for fader + VOL box */
    :host{ --rightW: 150px; }

    .seqFaderRow{
      width: 100%;
      position: relative;
      display:flex;
      align-items:flex-end;
      justify-content:center; /* center the fader itself */
      margin-top: 6px;
      padding-bottom: 2px;
    }

    .seqFaderPanel{
      width: var(--instBtnSize);
      border-radius: 18px;
      border: 3px solid #1d1d1d; /* thinner */
      background:#ffffff;
      box-shadow: 0 6px 0 rgba(0,0,0,0.05);
      display:flex;
      align-items:center;
      justify-content:center;
      padding: 6px 4px;
    }

    .seqTrackArea{
      position: relative;
      /* Much shorter, while still ending at grid bottom */
      height: calc((var(--cell) * 8 + var(--gap) * 7) - (4 * var(--instBtnSize) + 3 * var(--instGap)) - 70px);
      width: var(--instBtnSize);
      display:flex;
      align-items:center;
      justify-content:center;
    }

    .seqTrack{
      position: relative;
      width: 3px;      /* just enough to host the line */
      height: 100%;
      border: none;    /* remove surrounding shape */
      background: transparent;
      box-shadow: none;
      overflow: visible;
    }

    
    .seqTrack:before{
      content:"";
      position:absolute;
      left:50%;
      top:0;
      transform: translateX(-50%);
      width: 3px; /* thin central line */
      height: 100%;
      border-radius: 999px;
      background:#0f0f0f;
      opacity: 1;
      pointer-events:none;
    }
.seqIncTicks{
      position:absolute;
      left: 50%;          /* left edge sits on the track center line */
      margin-left: 0;
      top: 10px;          /* inset to match the visible track between caps */
      bottom: 10px;
      height: auto;
      width: 6px;         /* small container */
      display:flex;
      flex-direction: column;
      justify-content: space-between; /* evenly space 8 ticks */
      pointer-events:none;
      opacity: 0.95;
    }
    .seqIncTicks .t{
      width: 4px;   /* one third as long */
      height: 2px;
      background:#0f0f0f;
      border-radius: 2px;
    }
    
    .seqIncTicks .t:first-of-type,
    .seqIncTicks .t:last-of-type{ visibility:hidden; }

    .seqCaps{
      position:absolute;
      left: 50%;
      transform: translateX(-50%);
      height: 100%;
      width: 9px;
      display:flex;
      flex-direction: column;
      justify-content: space-between;
      align-items: center; /* ensure caps are centered on the track line */
      pointer-events:none;
    }
    .seqCap{
      display:block;
      width: 9px;
      height: 9px;
      border-radius: 999px;
      border: 2px solid #1d1d1d;
      background:#fff;
      box-shadow: 0 2px 0 rgba(0,0,0,0.05);
    }

    .seqKnob{
      position:absolute;
      left: 50%;
      transform: translate(-50%, -50%);
      width: calc(var(--instBtnSize) - 10px); /* slightly narrower than sound buttons */
      height: 16px;              /* thinner */
      border-radius: 11px;
      border: 3px solid #1d1d1d; /* thin outline */
      background:#ffffff;
      box-shadow:
        0 5px 0 rgba(0,0,0,0.05),
        inset 0 2px 0 rgba(255,255,255,0.85);
      display:flex;
      align-items:center;
      justify-content:center;
      pointer-events:none;
    }

    .seqKnobStripe{
      width: 70%;
      height: 7px;
      border-radius: 999px;
      border: 3px solid rgba(29,29,29,0.70);
      background: rgba(216,240,255,0.75);
      box-shadow: inset 0 2px 0 rgba(255,255,255,0.55);
    }

    .seqReadout{
      position:absolute;
      left: 50%;
      transform: translateX(calc(var(--instBtnSize) / 2 + 10px)); /* sits to the right without shifting fader */
      bottom: 2px;
      width: 40px;
      height: 40px;
      border-radius: 12px;
      border: 3px solid #1d1d1d;
      background:#ffffff;
      box-shadow: 0 6px 0 rgba(0,0,0,0.05);
      display:flex;
      align-items:center;
      justify-content:center;
      flex-direction: column;
      gap: 2px;
      padding: 4px;
      flex: 0 0 auto;
    }
    .seqReadout .small{
      font-family: "Fredoka","Trebuchet MS", Arial, sans-serif;
      font-weight: 800;
      font-size: 9px;
      color: rgba(31,42,68,0.70);
      letter-spacing: 0.4px;
      line-height: 1;
    }
    .seqReadout .num{
      font-family: "Fredoka","Trebuchet MS", Arial, sans-serif;
      font-weight: 900;
      font-size: 16px;
      color:#1f2a44;
      line-height: 1;
      text-shadow:
        0 2px 0 rgba(255,255,255,0.9),
        0 4px 0 rgba(0,0,0,0.08);
    }
    /* ---------------------------------------------------------------------- */

  
    /* --- Master volume fader interaction --- */
    .seqTrackArea{ position: relative; }
    .seqVolRange{
      position:absolute;
      left: 50%;
      top: 0;
      transform: translateX(-50%) rotate(-90deg);
      transform-origin: center;
      width: calc(100% - 6px); /* matches track height after rotation */
      height: 28px;
      opacity: 0; /* invisible */
      pointer-events: none; /* prevent range click-jump; we handle clicks/drags ourselves */
      cursor: pointer;
      z-index: 20;
    }
    /* prevent default focus ring from shifting layout */
    .seqVolRange:focus{ outline: none; }


    /* --------------------
</style>
<div class="seqFaderRow" >
            <div class="seqFaderPanel" aria-label="Master volume fader (UI)">
              <div class="seqTrackArea" id="seqTrackArea">
                <div class="seqTrack"></div>

                
                <input id="seqVolRange" class="seqVolRange" type="range" min="0" max="10" step="0.01" value="10" aria-label="Master volume" />
<div class="seqIncTicks" aria-hidden="true">
                  <div class="t"></div>
                  <div class="t"></div>
                  <div class="t"></div>
                  <div class="t"></div>
                  <div class="t"></div>
                  <div class="t"></div>
                  <div class="t"></div>
                  <div class="t"></div>
                </div>

                <div class="seqCaps" aria-hidden="true">
                  <div class="seqCap"></div>
                  <div class="seqCap"></div>
                </div>

                <div class="seqKnob" id="seqKnob" role="slider" aria-valuemin="0" aria-valuemax="10" aria-valuenow="8" tabindex="-1">
                  <div class="seqKnobStripe"></div>
                </div>
              </div>
            </div>

            <div class="seqReadout" aria-label="Volume display">
              <div class="small">VOL</div>
              <div class="num" id="seqVolNum">10</div>
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
      function setMasterGain(v){
        // Prefer global masterGain exposed on window; fall back to any globally accessible masterGain
        const mg = (typeof window.masterGain !== 'undefined' ? window.masterGain :
                   (typeof masterGain !== 'undefined' ? masterGain : null));
        if(mg && mg.gain && typeof mg.gain.value === 'number'){
          mg.gain.value = v;
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
