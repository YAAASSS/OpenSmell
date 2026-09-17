"use strict";

// Exercise the real UI import handler with WHATWG File/TextDecoder and DOM doubles.
// No browser, HTTP server, transport or physical device is used by this test.
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const {test} = require("node:test");
const vm = require("node:vm");

const root = join(__dirname, "..");
const script = readFileSync(join(root, "apps/local_demo/static/app.js"), "utf8");
const fixture = JSON.parse(readFileSync(join(root, "examples/multisource_beta_pinene.osmell"), "utf8"));
const limit = 1_048_576;

function graphFile(size, {bom = false, token = "a"} = {}) {
  const prefix = (bom ? "\ufeff" : "") + JSON.stringify(fixture).slice(0, -1) + ',"import_test":"';
  const suffix = '"}';
  const escaped = JSON.stringify(token).slice(1, -1);
  const budget = size - Buffer.byteLength(prefix + suffix);
  const width = Buffer.byteLength(escaped);
  const text = prefix + escaped.repeat(Math.floor(budget / width)) + " ".repeat(budget % width) + suffix;
  const file = new File([text], "import.osmell", {type: "application/json"});
  assert.equal(file.size, size);
  assert.deepEqual(JSON.parse(text.replace(/^\ufeff/, "")).resources, fixture.resources);
  return {file, text};
}

function ui() {
  const elements = new Map();
  function element(selector) {
    if (!elements.has(selector)) elements.set(selector, {
      listeners: {}, hidden: true, textContent: "", value: "5",
      addEventListener(event, handler) { this.listeners[event] = handler; },
      getAttribute() { return null; },
      classList: {add() {}},
    });
    return elements.get(selector);
  }
  const captured = [], requests = [];
  let cleared = 0;
  const context = vm.createContext({
    document: {querySelector: element, querySelectorAll: () => []},
    crypto: {randomUUID: () => "browser-import-test-client"},
    TextDecoder, TypeError, AbortController,
    hardware: {clearPreview() { cleared++; }},
    fetch: async (path, options) => { requests.push({path, payload: JSON.parse(options.body)}); },
    captured,
  });
  vm.runInContext(script, context);
  // Capture the source at the calculation boundary; Python tests cover HTTP and mapping.
  vm.runInContext("calculate = async () => { captured.push(source); };", context);
  return {
    captured, requests, element,
    get cleared() { return cleared; },
    async import(file) {
      const target = {files: [file], value: "selected"};
      await element("#file-input").listeners.change({target});
      assert.equal(target.value, "");
    },
  };
}

for (const bom of [false, true]) {
  for (const size of [limit - 1, limit, limit + 1]) {
    test(`UI UTF-8 boundary ${size} bytes, BOM=${bom}`, async () => {
      const app = ui();
      const {file, text} = graphFile(size, {bom, token: 'é🧪\\"'});
      await app.import(file);
      assert.ok(app.cleared > 0);
      assert.equal(app.requests[0].path, "/api/preview/invalidate");
      assert.equal(app.requests[0].payload.revision, 1);
      if (size <= limit) {
        assert.equal(app.captured.length, 1);
        assert.equal(app.captured[0].text, text);
        assert.equal(Buffer.byteLength(app.captured[0].text), file.size);
        assert.equal(app.captured[0].text.startsWith("\ufeff"), bom);
        // JSON transport preserves the BOM and all multibyte/source escaping.
        assert.equal(JSON.parse(JSON.stringify(app.captured[0])).text, text);
      } else {
        assert.equal(app.captured.length, 0);
        assert.equal(app.element("#error").hidden, false);
        assert.equal(app.element("#error").textContent,
          "File too large: the limit is 1 MiB (1,048,576 bytes).");
        await app.import(graphFile(limit).file);
        assert.equal(app.captured.length, 1);
        assert.equal(app.requests[1].payload.revision, 2);
      }
    });
  }
}

test("UI refuses invalid UTF-8 instead of replacing bytes", async () => {
  const app = ui();
  await app.import(new File([new Uint8Array([0xff])], "invalid.osmell"));
  assert.equal(app.captured.length, 0);
  assert.equal(app.element("#error").textContent, "Invalid encoding: a UTF-8 JSON file is required.");
});

test("A late file read cannot restore an import invalidated by a larger file", async () => {
  const app = ui();
  const slow = graphFile(8192).file;
  const buffer = await slow.arrayBuffer();
  let release;
  const pendingBuffer = new Promise((resolve) => { release = resolve; });
  const pending = app.import({size: slow.size, name: slow.name, arrayBuffer: () => pendingBuffer});
  await app.import(graphFile(limit + 1).file);
  release(buffer);
  await pending;
  assert.equal(app.captured.length, 0);
  assert.match(app.element("#error").textContent, /File too large/);
  await app.import(graphFile(limit).file);
  assert.equal(app.captured.length, 1);
});
