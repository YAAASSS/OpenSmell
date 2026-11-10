const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

test('lifecycle UI shows correlated terminal states and gates Stop by capabilities', async () => {
  const elements = new Map();
  const $ = key => {
    if (!elements.has(key)) elements.set(key, {value: '', addEventListener() {}, replaceChildren() {}, append() {}});
    return elements.get(key);
  };
  const requests = [];
  const context = vm.createContext({$, number: new Intl.NumberFormat('en'), field() {},
    node() { return {}; }, setInterval() {}, document: {querySelectorAll: () => []},
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
  context.ui.render({...state, software_adapter: {executable: '<custom & command>', expected_device_id: 'my-device'}});
  assert.equal($('#hardware-heading').textContent, 'Software adapter · experimental');
  assert.match($('#software-selection').textContent, /<custom & command>/);
  assert.match($('#software-selection').textContent, /my-device/);
  assert.equal($('#serial-port').value, 'SOFTWARE');
  assert.equal($('#serial-port').disabled, true);
  assert.equal($('#refresh-ports').disabled, true);
  assert.equal($('#execution-heading').textContent, 'Adapter running');
  assert.match($('#simulation-note').textContent, /Not sandboxed/);
  await context.ui.action('connect');
  const connect = requests.find(r => r.path.endsWith('/connect'));
  assert.deepEqual(JSON.parse(connect.options.body), {port: 'SOFTWARE'});
});

function evidenceHarness() {
  const elements = new Map();
  const $ = key => {
    if (!elements.has(key)) elements.set(key, {value:'', addEventListener() {}, replaceChildren() {}, append() {}});
    return elements.get(key);
  };
  const downloads = [];
  const blobs = [];
  const context = vm.createContext({$, number:new Intl.NumberFormat('en'), field() {}, node() { return {}; },
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


test('history selection exports an older report and ignores a late response after selection changes', async () => {
  const {context, $, downloads, blobs} = evidenceHarness();
  await new Promise(resolve => setImmediate(resolve));
  const state = {available:true, connection:'disconnected', evidence_id:'new', evidence_history:{reports:[{report_id:'new', state:'unknown'}, {report_id:'old', state:'completed'}], evicted_reports:2}};
  context.ui.render(state);
  context.ui.selectedEvidence = 'old';
  context.ui.render(state);
  assert.equal($('#evidence-history').value, 'old');
  assert.match($('#evidence-retention').textContent, /2 evicted/);
  const report = {report_id:'old', execution:{state:'completed'}, exchanges:[], omitted_events:0};
  context.ui.request = async path => {assert.match(path, /report_id=old$/); return report;};
  await context.ui.evidence(true);
  assert.deepEqual(JSON.parse(await blobs[0].text()), report);
  let resolve;
  context.ui.request = () => new Promise(r => {resolve=r;});
  const pending = context.ui.evidence(true);
  context.ui.selectedEvidence = 'new';
  resolve(report);
  await pending;
  assert.equal(downloads.length, 1);
});


test('history bundle downloads all returned snapshots without issuing commands', async () => {
  const {context, $, downloads, blobs} = evidenceHarness();
  await new Promise(resolve => setImmediate(resolve));
  const bundle = {reports:[{report_id:'a'}, {report_id:'b'}], retention:{evicted_reports:3}};
  context.ui.request = async path => {assert.equal(path, '/api/hardware/evidence-history'); return bundle;};
  await context.ui.downloadHistory();
  assert.deepEqual(JSON.parse(await blobs[0].text()), bundle);
  assert.equal(downloads[0].name, 'opensmell-execution-history.json');
  assert.match($('#evidence-message').textContent, /3 evicted/);
});
