/*
  Firebase (modular) is OPTIONAL.

  Goals:
  - Never crash or block the rest of the app if Firebase fails to load.
  - Avoid CORS issues when opening this file directly via file:// (skip Firebase in that case).
  - No reliance on any global `firebase` namespace.
*/
(async () => {
  const isHttp = location.protocol === 'http:' || location.protocol === 'https:';
  if(!isHttp){
    console.info('[Auth] Skipping Firebase in file:// mode (open via a local server or deploy to test auth).');
    return;
  }

  try{
    // Try to use your existing firebase-init module (recommended in your project structure).
    // It should export `auth` (and optionally `app`).
    let auth = null;

    try{
      const initMod = await import('./js/firebase-init.js');
      auth = initMod.auth || null;

      // Provide a safe sign-out hook for the non-module code.
      if(auth){
        const { signOut } = await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js');
        window.__doFirebaseSignOut = () => signOut(auth);
      }
    }catch(e){
      console.warn('[Auth] Could not import ./js/firebase-init.js. Auth will stay disabled.', e);
      return;
    }

    if(!auth){
      console.warn('[Auth] `auth` export not found in ./js/firebase-init.js. Auth will stay disabled.');
      return;
    }

    const { onAuthStateChanged } = await import('https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js');

    onAuthStateChanged(auth, (user) => {
      // Keep this lightweight and non-blocking.
      // Your existing UI/login flow can read sessionStorage flags as before.
      console.log('[Auth] User:', user ? user.email : 'none');
    });
  }catch(e){
    console.warn('[Auth] Firebase disabled (non-fatal):', e);
  }
})();
