import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../integration/electron/boot.js', import.meta.url), 'utf8');

function events(object = {}) {
  const listeners = new Map();
  object.addEventListener = (type, fn) => {
    if (!listeners.has(type)) listeners.set(type, new Set());
    listeners.get(type).add(fn);
  };
  object.removeEventListener = (type, fn) => listeners.get(type)?.delete(fn);
  object.emit = (type, event = {}) => [...(listeners.get(type) || [])].forEach(fn => fn(event));
  return object;
}

function element() {
  return {
    children: [], style: {}, dataset: {}, classList: { remove() {} },
    appendChild(child) { child.parentNode = this; this.children.push(child); },
    remove() {
      this.parentNode.children = this.parentNode.children.filter(child => child !== this);
      this.parentNode = null;
    }
  };
}

function boot(options = {}) {
  const storage = options.storage || new Map();
  const timers = new Map();
  let nextTimer = 0;
  const document = events({
    readyState: options.loading ? 'loading' : 'complete',
    documentElement: element(), head: element(), body: element(), createElement: element
  });
  const context = events({
    document,
    codexStartupBoot: { eligible: options.eligible ?? true, sessionId: options.session || 'one' },
    __DSH_STARTUP__: { enabled: options.enabled ?? true },
    sessionStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
    matchMedia: () => ({ matches: options.reduced || false }),
    setTimeout: fn => { timers.set(++nextTimer, fn); return nextTimer; },
    clearTimeout: id => timers.delete(id)
  });
  context.window = context;
  vm.createContext(context);
  vm.runInContext(source, context);
  return { context, document, timers, storage };
}

test('non-primary windows and disabled config do not create an overlay', () => {
  for (const options of [{ eligible: false }, { enabled: false }]) {
    const { document, timers } = boot(options);
    assert.equal(document.body.children.length, 0);
    assert.equal(document.documentElement.dataset.codexStartupPending, undefined);
    assert.equal(timers.size, 0);
  }
});

test('a session plays once; another process session can play again', () => {
  const first = boot();
  assert.equal(first.document.body.children.length, 1);
  const again = boot({ storage: first.storage });
  assert.equal(again.document.body.children.length, 0);
  const another = boot({ storage: first.storage, session: 'two' });
  assert.equal(another.document.body.children.length, 1);
});

test('script load failure removes the cover and unlocks scrolling', () => {
  const { context, document, timers } = boot();
  document.head.children[0].onerror();
  assert.equal(document.body.children.length, 0);
  assert.equal(document.documentElement.style.overflow, '');
  assert.equal(document.documentElement.dataset.codexStartupPending, undefined);
  assert.equal(context.__DSH_STARTUP_SKIP__, true);
  assert.equal(timers.size, 0);
});

test('initialization timeout fails open', () => {
  const { context, document, timers } = boot();
  [...timers.values()][0]();
  assert.equal(document.body.children.length, 0);
  assert.equal(context.__DSH_STARTUP_SKIP__, true);
});

test('Escape before DOMContentLoaded cannot create a delayed overlay', () => {
  const { context, document } = boot({ loading: true });
  document.emit('keydown', { key: 'Escape' });
  document.emit('DOMContentLoaded');
  assert.equal(document.body.children.length, 0);
  assert.equal(document.head.children.length, 0);
  assert.equal(context.__DSH_STARTUP_SKIP__, true);
});

test('Escape during script loading blocks late revival', () => {
  const { context, document } = boot();
  const script = document.head.children[0];
  document.emit('keydown', { key: 'Escape' });
  context.__DSH_STARTUP_API__ = { skip() {} };
  script.onload();
  assert.equal(document.body.children.length, 0);
  assert.equal(document.documentElement.dataset.codexStartupPending, undefined);
  assert.equal(context.__DSH_STARTUP_SKIP__, true);
});

test('loaded runtime owns Escape; completion releases only the overlay', () => {
  const { context, document, timers } = boot();
  const appRoot = element();
  document.body.appendChild(appRoot);
  let skipped = 0;
  context.__DSH_STARTUP_API__ = { skip() { skipped++; } };
  document.head.children[0].onload();
  assert.equal(timers.size, 0);
  document.emit('keydown', { key: 'Escape' });
  assert.equal(skipped, 1);
  context.emit('dsh-startup:done');
  assert.deepEqual(document.body.children, [appRoot]);
});

test('reduced motion uses fast automatic playback', () => {
  const { context } = boot({ reduced: true });
  assert.equal(context.__DSH_STARTUP__.requireInteraction, false);
  assert.equal(context.__DSH_STARTUP__.speed, 3);
});
