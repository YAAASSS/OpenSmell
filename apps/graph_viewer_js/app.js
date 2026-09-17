"use strict";

// All file-derived content is text. No innerHTML, Python API, fetch or serial API.
const $ = id => document.getElementById(id);
let revision = 0, current = null;
const visibleText = value => String(value).replace(/[\uD800-\uDFFF]/gu, unit => `\\u${unit.charCodeAt(0).toString(16).padStart(4, "0")}`);
const node = (tag, text) => { const element = document.createElement(tag); if (text !== undefined) element.textContent = visibleText(text); return element; };
function table(headers, rows) {
  const element = node("table"), head = node("thead"), titles = node("tr"), body = node("tbody");
  for (const title of headers) { const th = node("th", title); th.scope = "col"; titles.append(th); }
  head.append(titles); element.append(head, body);
  for (const values of rows) { const row = node("tr"); for (const value of values) row.append(node("td", value)); body.append(row); }
  return element;
}
function list(id, values) { $(id).replaceChildren(...values.map(value => node("li", value))); }
function showReport(report) {
  $("welcome").hidden = true; $("inspection").hidden = false;
  $("file-name").textContent = visibleText(report.file.name);
  $("file-meta").textContent = `${report.file.byte_length.toLocaleString("en-US")} bytes · UTF-8 BOM ${report.file.utf8_bom ? "present and preserved" : "absent"}`;
  $("file-hash").textContent = report.file.sha256;
  $("format").textContent = `Format: ${report.format?.text || "Not available"} · Version: ${report.version?.text || "Not available"}`;
  for (const id of ["molecules", "annotations", "observations", "references", "resources", "provenance"]) $(id).replaceChildren();
  for (const molecule of report.molecules) {
    $("molecules").append(node("h2", molecule.label.presence === "value" ? molecule.label.text : "Molecule"));
    const fields = node("dl");
    for (const [key, value] of [["Resource ID", molecule.id], ["SMILES", molecule.smiles.text], ...molecule.identifiers.map(item => [item.scheme, item.value])]) fields.append(node("dt", key), node("dd", value));
    $("molecules").append(fields);
  }
  if (!report.molecules.length) $("molecules").append(node("p", "No interpreted molecular identity."));
  for (const branch of report.annotations) {
    const source = node("p", branch.source.name.text); source.className = "source-label";
    $("annotations").append(source, table(["Category", "State"], branch.entries.map(item => [item.value, item.state])));
    const label = node("p", `Annotation ${branch.id}`); label.className = "resource-label"; $("annotations").append(label);
  }
  if (!report.annotations.length) $("annotations").append(node("p", "No interpreted categorical branch."));
  for (const branch of report.observations) {
    const source = node("p", branch.source.name.text); source.className = "source-label";
    $("observations").append(source);
    for (const group of branch.groups) $("observations").append(table(["Measurement", "Value", "Scale", "Unit"], group.entries.map(item => [item.property, item.value.text, item.scale.presence === "value" ? `${item.min.text} – ${item.max.text}` : item.scale.text, item.unit.text])));
    const label = node("p", `Observation ${branch.id}`); label.className = "resource-label"; $("observations").append(label);
  }
  if (!report.observations.length) $("observations").append(node("p", "No interpreted quantitative branch."));
  $("inspection-summary").textContent = `${report.resources.filter(item => item.status === "recognized").length} recognized resources · ${report.resources.filter(item => item.status === "opaque").length} opaque · ${report.resources.filter(item => item.status === "invalid").length} invalid. Checks apply only to the listed profile.`;
  $("diagnostics").replaceChildren(...report.diagnostics.map(item => { const entry = node("li", `${item.severity.toUpperCase()} · ${item.code}${item.path ? ` · ${item.path}` : ""}: ${item.message}`); entry.dataset.severity = item.severity; return entry; }));
  list("checks", report.checks); list("limits", report.limits);
  const resourceAnchors = new Map(report.resources.map((item, index) => [item.id, `resource-${index}`]));
  for (const ref of report.references) {
    const entry = node("div"); entry.className = "reference";
    const target = node(ref.resolved ? "a" : "span", ref.target_id);
    if (ref.resolved) target.href = `#${resourceAnchors.get(ref.target_id)}`;
    target.addEventListener("click", () => { $("resources").parentElement.open = true; });
    entry.append(node("strong", `${ref.source_id} · ${ref.field} → `), target, node("span", ref.resolved ? ` · resolved (${ref.target_kind})` : " · unresolved"));
    $("references").append(entry);
  }
  if (!report.references.length) $("references").append(node("p", "No known structural references discovered."));
  for (const item of report.resources) {
    const entry = node("div", `${item.id} · ${item.type} · type_version: ${item.type_version.text} · ${item.status}`);
    entry.id = resourceAnchors.get(item.id); entry.className = "resource"; $("resources").append(entry);
  }
  for (const branch of [...report.molecules, ...report.annotations, ...report.observations]) {
    const detail = node("details"); detail.append(node("summary", `Declared source · ${branch.id}`));
    detail.append(node("pre", branch.source.provenance_json ?? "Provenance not provided"));
    if (branch.source.context_json !== null) detail.append(node("pre", branch.source.context_json));
    $("provenance").append(detail);
  }
}
function reset() {
  current = null; $("download-copy").disabled = true; $("download-report").disabled = true;
  $("inspection").hidden = true; $("welcome").hidden = false; $("error").hidden = true; $("error").textContent = "";
}
async function openFile(file) {
  const requested = ++revision;
  reset();
  if (!file) { $("status").textContent = "Choose a graph file to begin."; return; }
  $("status").textContent = "Reading file and calculating SHA-256 in JavaScript…";
  try {
    if (file.size > OpenSmellReader.LIMIT) throw new Error("File too large. Maximum: 1,048,576 bytes (1 MiB), including any UTF-8 BOM.");
    const inspection = await OpenSmellReader.inspectBytes(new Uint8Array(await file.arrayBuffer()), file.name);
    if (requested !== revision) return;
    current = inspection; showReport(inspection.report);
    const rejected = inspection.report.status === "rejected";
    $("download-copy").disabled = rejected; $("download-report").disabled = false;
    $("status").textContent = rejected ? "Import rejected. Review the diagnostics; no transferable copy is active."
      : inspection.report.status === "partial" ? "Partial inspection. Review the limits; the original bytes are available to transfer."
      : "Listed checks completed. The original bytes are ready to transfer.";
    if (rejected) { $("error").textContent = inspection.report.diagnostics.filter(item => item.severity === "error").map(item => item.message).join(" "); $("error").hidden = false; }
  } catch (error) {
    if (requested !== revision) return;
    $("error").textContent = error.message; $("error").hidden = false; $("status").textContent = "Import failed. Choose another file to try again.";
  }
}
function download(bytes, name, type) {
  const url = URL.createObjectURL(new Blob([bytes], {type}));
  const anchor = node("a"); anchor.href = url; anchor.download = name;
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function basename(name) { return name.replace(/\.[^.]*$/, "").replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_").slice(0, 100) || "graph"; }
$("open-file").addEventListener("click", () => $("file-input").click());
$("file-input").addEventListener("change", async event => { const file = event.target.files[0]; event.target.value = ""; await openFile(file); });
$("download-copy").addEventListener("click", () => { if (current && current.report.status !== "rejected") download(current.copyBytes(), `${basename(current.report.file.name)}-transfer.osmell`, "application/octet-stream"); });
$("download-report").addEventListener("click", () => { if (current) download(JSON.stringify(current.report, null, 2) + "\n", `${basename(current.report.file.name)}-inspection.json`, "application/json"); });
