"use strict";
const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const core = require("../packages/javascript");
const legacy = require("../apps/graph_viewer_js/reader.js");
const {createServer} = require("../apps/graph_viewer_js/server.cjs");
const source = path.join(__dirname, "../packages/javascript/reader.cjs");

test("legacy repository import and ESM share the SDK engine", async () => {
  assert.equal(legacy.inspectBytes, core.inspectBytes);
  const esm = await import("../packages/javascript/index.mjs");
  assert.equal(esm.inspectBytes, core.inspectBytes);
  assert.equal(esm.default, core);
});

test("changing a rejected report cannot enable original-byte transfer", async () => {
  const result = await core.inspectBytes(new TextEncoder().encode('{"format":"bad"}'));
  assert.equal(result.report.status, "rejected");
  result.report.status = "inspected";
  assert.throws(() => result.copyBytes(), /No transfer/);
});

test("demo endpoint serves the same browser engine", async () => {
  const server = createServer();
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  try {
    const result = await fetch("http://127.0.0.1:" + server.address().port + "/reader.js");
    assert.equal(result.status, 200);
    assert.equal(await result.text(), fs.readFileSync(source, "utf8"));
    const context = vm.createContext({Uint8Array, TextDecoder, crypto: require("node:crypto").webcrypto});
    vm.runInContext(fs.readFileSync(source, "utf8"), context);
    assert.equal(typeof context.OpenSmellReader.inspectBytes, "function");
    const raw = new Uint8Array(fs.readFileSync(path.join(__dirname, "../examples/multisource_beta_pinene.osmell")));
    assert.equal((await context.OpenSmellReader.inspectBytes(raw)).report.status, "inspected");
  } finally { await new Promise(resolve => server.close(resolve)); }
});
