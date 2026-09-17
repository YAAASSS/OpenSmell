"use strict";
const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const vm = require("node:vm");
const reader = require("../apps/graph_viewer_js/reader.js");
const {createServer} = require("../apps/graph_viewer_js/server.cjs");
const root = path.join(__dirname, "..");
const bytes = name => new Uint8Array(fs.readFileSync(path.join(root, `examples/multisource_${name}.osmell`)));
const document = name => JSON.parse(Buffer.from(bytes(name)).toString("utf8"));
const encoded = value => new TextEncoder().encode(typeof value === "string" ? value : JSON.stringify(value));
const inspect = value => reader.inspectBytes(encoded(value));
const hash = value => crypto.createHash("sha256").update(value).digest("hex");

// Independent source expectations, not computed by the reader under test.
const states = ["animalic&ambery", "sweety&gourmand", "floral", "fruity&vegetable", "pungent&disagreeable", "green&herbal", "nutty", "woody&mossy", "resinous&balsamic", "cooked", "odorless", "spice"];
const examples = [
  {name: "beta_pinene", key: "WTARULDDTDQWMU-IUCAKERBSA-N", present: ["green&herbal", "woody&mossy", "resinous&balsamic"], unknown: [], ratings: {intensity: 100, pleasantness: 100, familiarity: 99, sweet: 46, fruit: 8, spices: 54, warm: 62, decayed: 31, wood: 97, grass: 86, flower: 1}},
  {name: "diphenyl_ether", key: "USIUVYZYUHIAEV-UHFFFAOYSA-N", present: ["floral", "green&herbal"], unknown: ["sweety&gourmand", "pungent&disagreeable"], ratings: {intensity: 95, pleasantness: 2, familiarity: 0, wood: 15, grass: 18, flower: 47, chemical: 1}},
];
for (const example of examples) test(`independent interpretation and byte transfer: ${example.name}`, async () => {
  const original = bytes(example.name), result = await reader.inspectBytes(original, `${example.name}.osmell`), report = result.report;
  assert.equal(report.status, "inspected");
  assert.equal(report.molecules[0].identifiers.find(item => item.scheme === "pubchem.inchikey").value, example.key);
  assert.equal(report.annotations[0].source.name.text, "OdorNet");
  assert.equal(report.observations[0].source.name.text, "Keller/Vosshall");
  assert.deepEqual(Object.fromEntries(report.annotations[0].entries.map(item => [item.value, item.state])), Object.fromEntries(states.map(name => [name, example.present.includes(name) ? "present" : example.unknown.includes(name) ? "unknown" : "absent"])));
  const actual = Object.fromEntries(report.observations[0].groups[0].entries.map(item => [item.property, item.value.text]));
  assert.deepEqual(actual, Object.fromEntries(Object.entries(example.ratings).map(([key, value]) => [key, String(value)])));
  for (const item of report.observations[0].groups[0].entries) {
    assert.equal(item.min.text, "0"); assert.equal(item.max.text, "100"); assert.equal(item.unit.presence, "missing");
  }
  assert.equal(report.references.length, 4); assert.ok(report.references.every(item => item.resolved));
  const molecule = report.molecules[0].id;
  assert.equal(report.references.find(item => item.field === "subject").target_id, molecule);
  assert.equal(report.references.find(item => item.field === "source").target_id, molecule);
  assert.equal(report.file.sha256, hash(original)); assert.deepEqual(result.copyBytes(), original);
  const copy = result.copyBytes(); copy[0] = 0; original[0] = 0;
  assert.equal(hash(result.copyBytes()), report.file.sha256);
});

for (const [name, mutate, code] of [
  ["duplicate IDs", graph => graph.resources.push({...graph.resources[0]}), "duplicate_id"],
  ["empty ID", graph => { graph.resources[0].id = ""; }, "invalid_content"],
  ["numeric ID", graph => { graph.resources[0].id = 15; }, "invalid_content"],
  ["unresolved subject", graph => { graph.resources[1].subject.resource_id = "missing"; }, "invalid_content"],
  ["wrong target type", graph => { graph.resources[4].target.resource_id = graph.resources[0].id; }, "invalid_content"],
  ["invalid state", graph => { graph.resources[1].data.annotations[0].state = "maybe"; }, "invalid_content"],
  ["string rating", graph => { graph.resources[4].results[0].data.measurements[0].value = "95"; }, "invalid_content"],
  ["inverted scale", graph => { graph.resources[4].results[0].data.measurements[0].scale = {min: 100, max: 0}; }, "invalid_content"],
  ["out-of-range rating", graph => { graph.resources[4].results[0].data.measurements[0].value = 101; }, "invalid_content"],
  ["null type version", graph => { graph.resources[0].type_version = null; }, "invalid_content"],
]) test(`reject ${name} without providing a transferable copy`, async () => {
  const graph = document("diphenyl_ether"); mutate(graph);
  const result = await inspect(graph);
  assert.equal(result.report.status, "rejected"); assert.ok(result.report.diagnostics.some(item => item.code === code));
  assert.throws(() => result.copyBytes(), /rejected/);
});

test("unknown resources, future versions, schemes and arbitrary reference-looking fields stay opaque", async () => {
  const graph = document("diphenyl_ether");
  graph.resources.push({id: "future", type: "custom", type_version: "9", payload: {resource_id: "nonexistent"}});
  graph.resources.push({id: "future-annotation", type: "org.opensmell.annotation", type_version: "9", subject: {resource_id: "nonexistent"}});
  graph.resources.push({id: "future-stimulus", type: "stimulus", type_version: "0.1", source: {resource_id: "nonexistent"}});
  graph.resources[0].extension = {resource_id: "also-nonexistent"};
  graph.resources[4].results.push({scheme: {id: "future", version: "9"}, data: {reference: {resource_id: "not-a-reference"}}});
  const original = encoded(graph), result = await reader.inspectBytes(original);
  assert.equal(result.report.status, "partial");
  assert.equal(result.report.resources.filter(item => item.status === "opaque").length, 3);
  assert.equal(result.report.references.length, 4);
  assert.ok(result.report.diagnostics.some(item => item.code === "opaque_scheme"));
  assert.deepEqual(result.copyBytes(), original);
});

test("references into an opaque target resolve without interpreting it", async () => {
  const graph = document("beta_pinene"); graph.resources[0].type_version = "future";
  const result = await inspect(graph);
  assert.equal(result.report.status, "partial"); assert.equal(result.report.molecules.length, 0);
  assert.equal(result.report.references.filter(item => item.target_kind === "opaque").length, 2);
});

test("zero, missing/null value, scale and unit remain distinguishable", async () => {
  const graph = document("diphenyl_ether"), measurements = graph.resources[4].results[0].data.measurements;
  measurements.push({property: "null-case", value: null, scale: null, unit: null}, {property: "missing-case"});
  const result = await inspect(graph), rows = result.report.observations[0].groups[0].entries;
  assert.equal(result.report.status, "partial");
  assert.equal(rows.find(item => item.property === "familiarity").value.text, "0");
  for (const key of ["value", "scale", "unit"]) {
    assert.equal(rows.at(-2)[key].presence, "null"); assert.equal(rows.at(-1)[key].presence, "missing");
  }
});

test("unsafe and extreme JSON numbers, negative zero, Unicode and extensions are exact in transfers", async () => {
  const base = JSON.stringify(document("diphenyl_ether"));
  const tokens = '[9007199254740993,-0,1e400,1e-400,0.123456789012345678901,1.0]';
  const text = base.slice(0, -1) + ',"unknown":{"resource_id":"not-an-edge","unicode":"é🧪漢字","numbers":' + tokens + '}}';
  const original = encoded(text), result = await reader.inspectBytes(original);
  assert.equal(result.report.status, "partial");
  assert.equal(result.report.diagnostics.filter(item => item.code === "numeric_limit").length, 5);
  assert.equal(result.report.references.length, 4); assert.deepEqual(result.copyBytes(), original);
  const knownNumber = base.replace('"value":95', '"value":9007199254740993');
  const known = await inspect(knownNumber);
  assert.equal(known.report.observations[0].groups[0].entries[0].value.text, "9007199254740993");
  assert.ok(known.report.diagnostics.some(item => item.code === "numeric_limit"));
});

for (const bom of [false, true]) for (const size of [reader.LIMIT - 1, reader.LIMIT, reader.LIMIT + 1]) test(`inclusive byte limit ${size}, BOM=${bom}`, async () => {
  const graph = JSON.stringify(document("diphenyl_ether"));
  const prefix = (bom ? "\ufeff" : "") + graph.slice(0, -1) + ',"padding":"é🧪';
  const text = prefix + " ".repeat(size - Buffer.byteLength(prefix + '"}')) + '"}';
  const input = encoded(text); assert.equal(input.length, size);
  if (size > reader.LIMIT) await assert.rejects(reader.inspectBytes(input), /1,048,576/);
  else { const result = await reader.inspectBytes(input); assert.equal(result.report.file.utf8_bom, bom); assert.deepEqual(result.copyBytes(), input); }
});

for (const [name, input, code] of [
  ["invalid UTF-8", new Uint8Array([0xc3, 0x28]), "invalid_utf8"],
  ["invalid JSON", encoded('{"format":'), "invalid_json"],
  ["Core document", encoded({format: "opensmell", version: "0.1", odor: {}}), "unsupported_format"],
  ["future graph version", encoded({...document("beta_pinene"), version: "2"}), "unsupported_format"],
  ["duplicate JSON key", encoded('{"format":"a","format":"b"}'), "duplicate_json_key"],
  ["excessive depth", encoded("[".repeat(70) + "0" + "]".repeat(70)), "reading_limit"],
]) test(`clear diagnostic for ${name}`, async () => {
  const result = await reader.inspectBytes(input);
  assert.equal(result.report.status, "rejected"); assert.ok(result.report.diagnostics.some(item => item.code === code));
});

test("escaped lone surrogate is reported and preserved", async () => {
  const graph = JSON.stringify(document("beta_pinene"));
  const input = encoded(graph.slice(0, -1) + ',"extension":"\\ud800"}');
  const result = await reader.inspectBytes(input);
  assert.ok(result.report.diagnostics.some(item => item.code === "unicode_limit")); assert.deepEqual(result.copyBytes(), input);
});

function ui() {
  const elements = new Map(), blobs = [], clicks = [];
  class Element {
    constructor(tag = "div") { this.tag = tag; this.children = []; this.listeners = {}; this.dataset = {}; this.value = ""; this.hidden = true; this.disabled = true; }
    set innerHTML(value) { throw new Error("Untrusted HTML rendering is forbidden"); }
    set textContent(value) { this.text = String(value); this.children = []; }
    get textContent() { return (this.text || "") + this.children.map(child => child.textContent).join(""); }
    append(...children) { for (const child of children) { child.parentElement = this; this.children.push(child); } }
    replaceChildren(...children) { this.children = []; this.text = ""; this.append(...children); }
    addEventListener(name, handler) { this.listeners[name] = handler; }
    click() { clicks.push(this); return this.listeners.click?.(); }
    remove() {}
  }
  const element = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const context = vm.createContext({document: {getElementById: element, createElement: tag => new Element(tag), body: new Element("body")}, OpenSmellReader: reader, Uint8Array, Blob, URL: {createObjectURL(blob) { blobs.push(blob); return "blob:test"; }, revokeObjectURL() {}}, setTimeout: callback => callback(), console});
  vm.runInContext(fs.readFileSync(path.join(root, "apps/graph_viewer_js/app.js"), "utf8"), context);
  return {element, blobs, clicks, async import(file) { const target = {files: file ? [file] : [], value: "selected"}; await element("file-input").listeners.change({target}); assert.equal(target.value, ""); }};
}
test("real UI handler: downloads original bytes and separate report; rejects, clears and recovers", async () => {
  const app = ui(), original = bytes("diphenyl_ether");
  await app.import(new File([original], "diphenyl.osmell"));
  assert.equal(app.element("download-copy").disabled, false);
  app.element("download-copy").click(); assert.deepEqual(new Uint8Array(await app.blobs[0].arrayBuffer()), original);
  app.element("download-report").click(); const report = JSON.parse(await app.blobs[1].text());
  assert.equal(report.file.sha256, hash(original)); assert.notEqual(await app.blobs[1].text(), Buffer.from(original).toString("utf8"));
  await app.import(new File(['{"format":"core"}'], "bad.osmell"));
  assert.equal(app.element("download-copy").disabled, true);
  app.element("download-copy").click(); assert.equal(app.blobs.length, 2);
  assert.match(app.element("error").textContent, /Unsupported/);
  await app.import(new File([original], "recovered.osmell"));
  assert.equal(app.element("download-copy").disabled, false); assert.equal(app.element("error").hidden, true);
});
test("late file read cannot restore a previous import after an oversize failure", async () => {
  const app = ui(); let resolve;
  const pending = app.import({name: "old.osmell", size: 12, arrayBuffer: () => new Promise(done => { resolve = done; })});
  await app.import({name: "large.osmell", size: reader.LIMIT + 1, arrayBuffer() { throw new Error("Oversize file must not be read"); }});
  resolve(bytes("beta_pinene").buffer); await pending;
  assert.equal(app.element("download-copy").disabled, true); assert.equal(app.element("inspection").hidden, true);
  assert.match(app.element("error").textContent, /too large/);
  await app.import(new File([bytes("beta_pinene")], "new.osmell")); assert.equal(app.element("download-copy").disabled, false);
});
test("file text, names and IDs are rendered as data, never executable HTML", async () => {
  const app = ui(), graph = document("beta_pinene"), payload = '<img src=x onerror="alert(1)">';
  graph.resources[0].pubchem.title = payload; graph.resources[1].data.annotations[0].value = payload;
  graph.resources[0].id = payload;
  graph.resources[1].subject.resource_id = payload; graph.resources[2].source.resource_id = payload;
  graph.resources[1].data.annotations[1].value = "escaped-\ud800";
  await app.import(new File([JSON.stringify(graph)], payload + ".osmell"));
  assert.match(app.element("molecules").textContent, /<img/); assert.match(app.element("annotations").textContent, /<img/);
  assert.equal(app.element("file-name").textContent, payload + ".osmell");
  assert.match(app.element("annotations").textContent, /escaped-\\ud800/);
  assert.ok(app.element("references").children.every(entry => entry.children[1].href.startsWith("#resource-")));
});

test("static server serves official logos and denies analysis APIs, uploads and arbitrary paths", async () => {
  const server = createServer(); await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    const page = await fetch(base); assert.equal(page.status, 200); assert.match(page.headers.get("content-security-policy"), /connect-src 'none'/);
    for (const [route, file] of [["logo-full.png", "OpenSmell_Official_Logo_Full.png"], ["logo-small.png", "OpenSmell_Official_Logo_Small.png"]]) {
      const response = await fetch(`${base}/${route}`); assert.equal(hash(new Uint8Array(await response.arrayBuffer())), hash(fs.readFileSync(path.join(root, "docs/images", file))));
    }
    for (const route of ["/api/preview", "/.git/config", "/examples/multisource_beta_pinene.osmell"]) assert.equal((await fetch(base + route)).status, 404);
    assert.equal((await fetch(base + "/", {method: "POST", body: "no uploads"})).status, 405);
  } finally { await new Promise(resolve => server.close(resolve)); }
});
