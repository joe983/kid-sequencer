/* Layout Debug Mode
   - Turn on with ?debug=1 (or ?debug) in the URL.
   - Shows outlines, viewport size, and highlights overflowing elements.
*/
(function(){
  const params = new URLSearchParams(window.location.search);
  const debugOn = params.has('debug') && params.get('debug') !== '0';
  if(!debugOn) return;

  document.body.classList.add('debug');

  const infoEl = document.getElementById('debug-info');
  const setInfo = () => {
    if(!infoEl) return;
    // innerWidth/innerHeight are CSS pixels of the visual viewport
    infoEl.textContent = `${window.innerWidth} × ${window.innerHeight}`;
  };

  const markOverflow = () => {
    // Remove previous marks
    document.querySelectorAll('.overflow-check').forEach(el => el.classList.remove('overflow-check'));
    // Mark elements that overflow their own box
    document.querySelectorAll('body *').forEach(el => {
      try{
        if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1){
          el.classList.add('overflow-check');
        }
      }catch(e){}
    });
  };

  window.addEventListener('resize', () => {
    setInfo();
    // allow layout to settle
    requestAnimationFrame(markOverflow);
    setTimeout(markOverflow, 60);
  });

  document.addEventListener('DOMContentLoaded', () => {
    setInfo();
    requestAnimationFrame(markOverflow);
    setTimeout(markOverflow, 60);
  });
})();
