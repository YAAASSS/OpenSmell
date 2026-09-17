"use strict";
// Static assets only. No graph parsing, uploads, Python, SDK or device access.
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const assets = new Map([
  ["/", ["index.html", "text/html; charset=utf-8"]],
  ["/index.html", ["index.html", "text/html; charset=utf-8"]],
  ["/style.css", ["style.css", "text/css; charset=utf-8"]],
  ["/reader.js", ["reader.js", "text/javascript; charset=utf-8"]],
  ["/app.js", ["app.js", "text/javascript; charset=utf-8"]],
  ["/logo-full.png", ["../../docs/images/OpenSmell_Official_Logo_Full.png", "image/png"]],
  ["/logo-small.png", ["../../docs/images/OpenSmell_Official_Logo_Small.png", "image/png"]],
]);
function createServer() {
  return http.createServer((request, response) => {
    if (!["GET", "HEAD"].includes(request.method)) { response.writeHead(405, {Allow: "GET, HEAD"}); response.end(); return; }
    const asset = assets.get(request.url.split("?")[0]);
    if (!asset) { response.writeHead(404); response.end("Not found"); return; }
    const data = fs.readFileSync(path.join(__dirname, asset[0]));
    response.writeHead(200, {
      "Content-Type": asset[1], "Content-Length": data.length, "X-Content-Type-Options": "nosniff",
      "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
      "Cache-Control": "no-store",
    });
    response.end(request.method === "HEAD" ? undefined : data);
  });
}
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.includes("--help")) { console.log("Usage: node apps/graph_viewer_js/server.cjs [--port 8766]\nServes static assets on 127.0.0.1. File inspection runs only in the browser."); }
  else {
    const port = args.length === 0 ? 8766 : args.length === 2 && args[0] === "--port" ? Number(args[1]) : NaN;
    if (!Number.isInteger(port) || port < 0 || port > 65535) { console.error("Invalid port. Use --port with an integer from 0 to 65535."); process.exitCode = 1; }
    else { const server = createServer(); server.on("error", error => { console.error(error.message); process.exitCode = 1; }); server.listen(port, "127.0.0.1", () => console.log(`JavaScript Graph Reader: http://127.0.0.1:${server.address().port}`)); }
  }
}
module.exports = {createServer};
