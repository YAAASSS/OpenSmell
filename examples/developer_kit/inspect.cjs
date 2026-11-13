"use strict";
// Installed package only; this file has no repository-relative imports.
const fs = require("node:fs");
const {inspectBytes} = require("@opensmell/graph-reader");
(async () => {
  const result = await inspectBytes(fs.readFileSync(process.argv[2]), process.argv[2]);
  if (result.report.status === "rejected") throw Error(JSON.stringify(result.report.diagnostics));
  fs.writeFileSync(process.argv[3], result.copyBytes(), {flag: "wx"});
  console.log(JSON.stringify(result.report));
})().catch(error => { console.error(error); process.exitCode = 1; });
