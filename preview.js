window.__DSH_STARTUP_SCRIPT_URL__ = 'lib/splash.js';

// Preview only. This page does not connect to, authenticate, or modify Codex.
const params = new URLSearchParams(location.search);
if(params.get('auto')==='1') window.__DSH_STARTUP__.requireInteraction=false;
if(params.get('fast')==='1') window.__DSH_STARTUP__.speed=3;
if(matchMedia('(prefers-reduced-motion: reduce)').matches){window.__DSH_STARTUP__.requireInteraction=false;window.__DSH_STARTUP__.speed=3;}
if(params.get('quiet')==='1') window.__DSH_STARTUP__.sound=false;
const status = document.getElementById('result');
window.__codexPreviewEvidence = {rootReplaced:false,overlaySurvived:false,done:false};
// Simulate the real app's createRoot(...).render(...) replacing #root.
setTimeout(()=>{document.getElementById('root').replaceChildren(document.createElement('span')); window.__codexPreviewEvidence.rootReplaced=true;window.__codexPreviewEvidence.overlaySurvived=!!document.getElementById('dsh-startup-root');},800);
window.addEventListener('dsh-startup:done',()=>{window.__codexPreviewEvidence.done=true;status.hidden=false;document.getElementById('root').textContent='';});
document.getElementById('replay').addEventListener('click',()=>location.reload());
document.getElementById('auto').addEventListener('click',()=>{const u=new URL(location.href);u.searchParams.set('auto','1');location.href=u.href;});
