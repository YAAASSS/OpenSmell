const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

test('lifecycle UI shows correlated terminal states and gates Stop by capabilities', async () => {
  const elements = new Map();
  const $ = key => {
    if (!elements.has(key)) elements.set(key, {value: '', addEventListener() {}, replaceChildren() {}});
    return elements.get(key);
  };
  const requests = [];
  const context = vm.createContext({$, number: new Intl.NumberFormat('en'), field() {},
    node() {}, setInterval() {}, document: {querySelectorAll: () => []},
    fetch: async (path, options) => { requests.push({path, options}); return {ok: true, json: async () => ({available: true, connection: 'disconnected'})}; },
  });
  vm.runInContext(fs.readFileSync('apps/local_demo/static/hardware.js', 'utf8') + '\nthis.ui = hardware;', context);
  await new Promise(resolve => setImmediate(resolve));
  const state = {available: true, simulated: true, connection: 'connected',
    lifecycle_capabilities: {stop: true}, execution: {state: 'running', duration: 5, execution_id: 'run-2', observation: {state: 'running', execution_id: 'run-2'}}};
  context.ui.render(state);
  assert.equal($('#stop-device').disabled, false);
  assert.equal($('#stop-device').hidden, false);
  assert.match($('#hardware-heading').textContent, /Software simulator/);
  await context.ui.action('stop');
  const stop = requests.find(r => r.path.endsWith('/stop'));
  assert.deepEqual(JSON.parse(stop.options.body), {execution_id: 'run-2'});
  for (const terminal of ['completed', 'stopped', 'unknown']) {
    context.ui.render({...state, execution: {...state.execution, state: terminal}});
    assert.equal($('#stop-device').disabled, true);
    assert.match($('#execution-heading').textContent.toLowerCase(), new RegExp(terminal));
  }
  context.ui.render({...state, simulated: false, lifecycle_capabilities: null});
  assert.equal($('#stop-device').hidden, true);
});
