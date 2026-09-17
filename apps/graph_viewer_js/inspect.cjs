"use strict";
// Offline companion for reproducible tests: same independent JS reader as the UI.
const fs = require("node:fs");
const {inspectBytes} = require("./reader.js");
async function main() {
  const [input, copy, report, ...extra] = process.argv.slice(2);
  if (!input || !copy || !report || extra.length) throw new Error("Usage: node apps/graph_viewer_js/inspect.cjs INPUT COPY.osmell REPORT.json");
  const paths = [input, copy, report].map(value => require("node:path").resolve(value));
  if (new Set(paths).size !== 3) throw new Error("Input, copy and report must be separate files.");
  const inspection = await inspectBytes(new Uint8Array(fs.readFileSync(input)), require("node:path").basename(input));
  fs.writeFileSync(report, JSON.stringify(inspection.report, null, 2) + "\n", {flag: "wx"});
  if (inspection.report.status === "rejected") throw new Error("Inspection rejected. See the report; no copy was written.");
  fs.writeFileSync(copy, inspection.copyBytes(), {flag: "wx"});
  console.log(`${inspection.report.file.sha256}  ${copy}`);
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
