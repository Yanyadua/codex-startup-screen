/* Unofficial Codex integration; the animation is a sibling of React's root. */
(function () {
  const info = window.codexStartupBoot;
  if (!info || !info.eligible || window.__DSH_STARTUP__?.enabled === false) return;
  const key = 'codex-startup-personal:' + info.sessionId;
  try {
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, '1');
  } catch { /* Private browsing may disable storage. */ }
  const html = document.documentElement;
  html.dataset.codexStartupPending = '1';
  let root = null, script = null, timer = null, released = false;
  function release() {
    released = true;
    // A late script completion must not bring the overlay back after Esc.
    window.__DSH_STARTUP_SKIP__ = true;
    delete html.dataset.codexStartupPending;
    if (root?.parentNode) root.remove();
    if (script?.parentNode) script.remove();
    html.classList.remove('dsu-lock');
    html.style.overflow = '';
    if (document.body) document.body.style.overflow = '';
    document.removeEventListener('keydown', escapeGuard, true);
    document.removeEventListener('DOMContentLoaded', start);
    if (timer) clearTimeout(timer);
  }
  function escapeGuard(event) {
    if (event.key !== 'Escape') return;
    if (window.__DSH_STARTUP_API__) window.__DSH_STARTUP_API__.skip();
    else release();
  }
  function start() {
    if (released) return;
    root = document.createElement('div');
    root.id = 'dsh-startup-root';
    root.className = 'dsu-boot';
    root.style.cssText = 'position:fixed;inset:0;background:#000;z-index:2147483000';
    document.body.appendChild(root);
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
      window.__DSH_STARTUP__.requireInteraction = false;
      window.__DSH_STARTUP__.speed = 3;
    }
    script = document.createElement('script');
    script.src = './codex-startup/splash.js';
    window.__DSH_STARTUP_SCRIPT_URL__ = './codex-startup/splash.js';
    script.onload = () => {
      if (released) return;
      if (!window.__DSH_STARTUP_API__) { release(); return; }
      clearTimeout(timer);
      delete html.dataset.codexStartupPending;
    };
    script.onerror = release;
    document.head.appendChild(script);
  }
  document.addEventListener('keydown', escapeGuard, true);
  window.addEventListener('dsh-startup:done', release, { once: true });
  timer = setTimeout(() => { if (!window.__DSH_STARTUP_API__) release(); }, 8000);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
