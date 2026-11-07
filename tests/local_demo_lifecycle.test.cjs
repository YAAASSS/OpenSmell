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

function evidenceHarness() {
  const elements = new Map();
  const $ = key => {
    if (!elements.has(key)) elements.set(key, {value:'', addEventListener() {}, replaceChildren() {}});
    return elements.get(key);
  };
  const downloads = [];
  const blobs = [];
  const context = vm.createContext({$, number:new Intl.NumberFormat('en'), field() {}, node() {},
    setInterval() {}, setTimeout(fn) { fn(); }, Blob,
    URL: {createObjectURL(blob) { blobs.push(blob); return 'blob:test'; }, revokeObjectURL() {}},
    document: {querySelectorAll:() => [], createElement() { return {click() { downloads.push({name:this.download, href:this.href}); }}; }},
    fetch: async () => ({ok:true, json:async () => ({available:true, connection:'disconnected'})}),
  });
  vm.runInContext(fs.readFileSync('apps/local_demo/static/hardware.js','utf8') + '\nthis.ui = hardware;',context);
  return {context, $, downloads, blobs};
}

test('evidence download contains the correlated snapshot and stays available after disconnect', async () => {
  const {context, $, downloads, blobs} = evidenceHarness();
  await new Promise(resolve => setImmediate(resolve));
  context.ui.render({available:true, connection:'disconnected', evidence_id:'report-a'});
  assert.equal($('#download-evidence').disabled, false);
  const report = {report_id:'report-a', execution:{state:'unknown'}, exchanges:[], omitted_events:0, source:{document:{unknown_extension:'preserved'}}};
  context.ui.request = async path => { assert.match(path, /report_id=report-a$/); return report; };
  await context.ui.evidence(true);
  assert.equal(downloads[0].name,'opensmell-evidence-report-a.json');
  assert.deepEqual(JSON.parse(await blobs[0].text()), report);
  assert.match($('#evidence-message').textContent, /unknown/);
  assert.equal($('#evidence-details').open, true);
});

test('late evidence cannot download or display a different execution', async () => {
  const {context, $, downloads} = evidenceHarness();
  await new Promise(resolve => setImmediate(resolve));
  context.ui.render({available:true, connection:'disconnected', evidence_id:'old'});
  let resolve;
  context.ui.request = () => new Promise(r => {resolve=r;});
  const pending = context.ui.evidence(true);
  context.ui.render({available:true, connection:'disconnected', evidence_id:'new'});
  resolve({report_id:'old', execution:{state:'completed'}, exchanges:[], omitted_events:0});
  await pending;
  assert.equal(downloads.length,0);
  assert.equal($('#evidence-json').textContent,'');
});
