"use strict";
// Pack/install in a fresh consumer with no registry, scripts or repository imports.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const cp = require("node:child_process");
const root = path.resolve(__dirname, "..");
const work = fs.mkdtempSync(path.join(os.tmpdir(), "opensmell-js-sdk-"));
const npm = process.platform === "win32" ? "npm.cmd" : "npm";

function run(command, args, cwd, expected = 0) {
  const result = cp.spawnSync(command, args, {cwd, encoding: "utf8", timeout: 120000});
  if (result.error || result.status !== expected)
    throw Error(JSON.stringify({command, args, status: result.status, error: result.error?.message,
                                stdout: result.stdout, stderr: result.stderr}));
  return result.stdout;
}
try {
  const packed = JSON.parse(run(npm, ["pack", "--ignore-scripts", "--json", "--pack-destination", work],
                               path.join(root, "packages/javascript")))[0];
  const files = packed.files.map(item => item.path).sort();
  assert.deepEqual(files, ["LICENSE", "README.md", "cli.cjs", "index.cjs", "index.d.ts",
                           "index.mjs", "package.json", "reader.cjs"].sort());
  const archive = path.join(work, packed.filename);
  fs.writeFileSync(path.join(work, "package.json"), '{"private":true,"type":"module"}');
  run(npm, ["install", "--offline", "--ignore-scripts", "--no-audit", "--no-fund",
            "--package-lock=false", archive], work);
  for (const name of ["beta_pinene", "diphenyl_ether"])
    fs.copyFileSync(path.join(root, "examples/multisource_" + name + ".osmell"),
                    path.join(work, name + ".osmell"));

  const common = [
    'const assert = require("node:assert/strict");',
    'const fs = require("node:fs");',
    'const crypto = require("node:crypto");',
    'const reader = require("@opensmell/graph-reader");',
    'assert.ok(require.resolve("@opensmell/graph-reader").startsWith(process.cwd()));',
    'const original = fs.readFileSync("beta_pinene.osmell");',
    '(async () => {',
    ' const value = await reader.inspectBytes(original);',
    ' assert.equal(value.report.status, "inspected");',
    ' assert.equal(value.report.references.length, 4);',
    ' assert.equal(value.report.file.sha256, crypto.createHash("sha256").update(original).digest("hex"));',
    ' const first = value.copyBytes(); first[0] = 0;',
    ' assert.deepEqual(Buffer.from(value.copyBytes()), original);',
    ' fs.writeFileSync("beta-transfer.osmell", value.copyBytes());',
    ' const bad = await reader.inspectBytes(Buffer.from("{"));',
    ' bad.report.status = "inspected"; assert.throws(() => bad.copyBytes());',
    ' await assert.rejects(reader.inspectBytes(new Uint8Array(reader.LIMIT + 1)));',
    '})().catch(error => {console.error(error); process.exitCode = 1;});'
  ].join('\n');
  fs.writeFileSync(path.join(work, "consumer.cjs"), common);
  run(process.execPath, ["consumer.cjs"], work);
  fs.writeFileSync(path.join(work, "consumer.mjs"), [
    'import assert from "node:assert/strict";',
    'import fs from "node:fs";',
    'import reader, {inspectBytes} from "@opensmell/graph-reader";',
    'assert.equal(reader.inspectBytes, inspectBytes);',
    'const raw = fs.readFileSync("diphenyl_ether.osmell");',
    'const result = await inspectBytes(raw);',
    'assert.equal(result.report.status, "inspected");',
    'assert.equal(result.report.references.length, 4);',
    'fs.writeFileSync("diphenyl-transfer.osmell", result.copyBytes());'
  ].join('\n'));
  run(process.execPath, ["consumer.mjs"], work);

  const cli = process.platform === "win32" ?
    path.join(work, "node_modules/@opensmell/graph-reader/cli.cjs") :
    path.join(work, "node_modules/.bin/opensmell-inspect-js");
  function command(args, expected = 0) {
    return process.platform === "win32" ? run(process.execPath, [cli, ...args], work, expected) :
                                         run(cli, args, work, expected);
  }
  const report = JSON.parse(command(["beta_pinene.osmell", "--copy", "cli-copy.osmell"]));
  assert.equal(report.status, "inspected");
  command(["beta_pinene.osmell", "--copy", "cli-copy.osmell"], 2);
  command(["beta_pinene.osmell", "--copy", "beta_pinene.osmell"], 2);
  command(["--help"]);
  command([], 2);
  fs.writeFileSync(path.join(work, "bad.osmell"), '{"format":"x","format":"x"}');
  assert.equal(JSON.parse(command(["bad.osmell", "--copy", "not-created.osmell"], 1)).status, "rejected");
  assert.equal(fs.existsSync(path.join(work, "not-created.osmell")), false);
  fs.writeFileSync(path.join(work, "large.osmell"), Buffer.alloc(1048577, 32));
  command(["large.osmell"], 1);
  fs.writeFileSync(path.join(work, "opaque.osmell"),
    '{"format":"org.opensmell.experimental.generic-resource-graph","version":"0.1","resources":[{"id":"x","type":"future","type_version":"9","unknown":{"value":123}}]}');
  assert.equal(JSON.parse(command(["opaque.osmell", "--copy", "opaque-copy.osmell"], 3)).status, "partial");
  assert.deepEqual(fs.readFileSync(path.join(work, "opaque.osmell")), fs.readFileSync(path.join(work, "opaque-copy.osmell")));
  assert.deepEqual(fs.readFileSync(path.join(work, "beta_pinene.osmell")), fs.readFileSync(path.join(work, "beta-transfer.osmell")));
  assert.deepEqual(fs.readFileSync(path.join(work, "beta_pinene.osmell")), fs.readFileSync(path.join(work, "cli-copy.osmell")));
  assert.deepEqual(fs.readFileSync(path.join(work, "diphenyl_ether.osmell")), fs.readFileSync(path.join(work, "diphenyl-transfer.osmell")));

  // Optionally retain only exchanged bytes for a Python-side check in the same workflow.
  if (process.argv[2]) {
    const output = path.resolve(process.argv[2]);
    fs.mkdirSync(output, {recursive: true});
    for (const name of ["beta-transfer.osmell", "diphenyl-transfer.osmell"]) {
      const target = path.join(output, name);
      fs.writeFileSync(target, fs.readFileSync(path.join(work, name)), {flag: "wx"});
    }
  }
  console.log(JSON.stringify({result: "passed", package: packed.name, version: packed.version,
                             files, consumer: "fresh offline install", modules: ["CommonJS", "ESM"],
                             cli: "installed bin", original_bytes_preserved: true, physical_access: false}));
} finally { fs.rmSync(work, {recursive: true, force: true}); }
