#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const {inspectBytes, LIMIT} = require("./index.cjs");

function readBounded(filename) {
  const fd = fs.openSync(filename, "r");
  try {
    const buffer = Buffer.alloc(LIMIT + 1);
    let used = 0, count;
    while (used < buffer.length && (count = fs.readSync(fd, buffer, used, buffer.length - used, null)) > 0) used += count;
    return buffer.subarray(0, used);
  } finally { fs.closeSync(fd); }
}

async function main(args) {
  if (args.length === 1 && args[0] === "--help") {
    console.log("Usage: opensmell-inspect-js FILE [--copy NEW_FILE]");
    console.log("Offline experimental graph inspection. Exit: 0 inspected, 3 partial, 1 rejected, 2 I/O/usage.");
    return 0;
  }
  if (![1, 3].includes(args.length) || args[0].startsWith("--") ||
      (args.length === 3 && (args[1] !== "--copy" || !args[2]))) {
    console.error(JSON.stringify({status: "error", error: "Use --help for usage."}));
    return 2;
  }
  try {
    const result = await inspectBytes(readBounded(args[0]), args[0]);
    if (result.report.status !== "rejected" && args.length === 3)
      fs.writeFileSync(args[2], result.copyBytes(), {flag: "wx"});
    console.log(JSON.stringify(result.report, null, 2));
    return result.report.status === "rejected" ? 1 : result.report.status === "partial" ? 3 : 0;
  } catch (error) {
    console.error(JSON.stringify({status: "error", error: {code: error.code || "inspection_error", message: error.message}}));
    return error.code === "file_too_large" ? 1 : 2;
  }
}
if (require.main === module) main(process.argv.slice(2)).then(code => { process.exitCode = code; });
module.exports = {main};
