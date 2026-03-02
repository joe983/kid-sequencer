// Safety: remove any legacy rotate/sideways prompt overlays (older cached HTML/CSS versions)
    (function(){
      try{
        const el = document.getElementById('rotatePrompt');
        if(el) el.remove();
        const legacy = ['turn your device sideways', 'turn your device', 'rotate your device'];
        const nodes = Array.from(document.querySelectorAll('body *'));
        for(const n of nodes){
          const t = (n && n.textContent) ? n.textContent.toLowerCase().trim() : '';
          if(!t) continue;
          if(legacy.some(s => t.includes(s))){
            // Hide rather than remove to avoid layout reflow surprises
            n.style.display = 'none';
          }
        }
      }catch(e){}
    })();
