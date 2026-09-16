"use strict";

const $ = (selector) => document.querySelector(selector);
const number = new Intl.NumberFormat("en-US", {maximumSignificantDigits: 15});
const level = new Intl.NumberFormat("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 20});
let source = null;
let requestId = 0;
let activeRequest = null;
const previewClientId = crypto.randomUUID();

function invalidateServerPreview(revision) {
  // Monotonic revisions make late invalidations harmless. No hardware I/O.
  fetch("/api/preview/invalidate", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({client_id: previewClientId, revision}),
  }).catch(() => {});
}

function invalidatePreview() {
  ++requestId;
  activeRequest?.abort();
  hardware.clearPreview();
  invalidateServerPreview(requestId);
}

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function display(value) {
  if (value === undefined) return "Not provided";
  if (value === null) return "Not specified (null)";
  if (value === "") return "Empty string";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function raw(value) {
  return node("pre", value === undefined ? "Not provided" : JSON.stringify(value, null, 2));
}

function field(list, label, value) {
  list.append(node("dt", label), node("dd", display(value)));
}

function sourceName(resource) {
  return display(resource?.provenance?.source?.name);
}

function renderData(data) {
  const molecule = data.molecule;
  $("#molecule-title").textContent = display(molecule.pubchem?.title ?? data.stimulus.source_label ?? molecule.id);
  const fields = $("#molecule-fields");
  fields.replaceChildren();
  field(fields, "SMILES", molecule.smiles);
  field(fields, "InChIKey", molecule.identifiers?.find((item) => item.scheme === "pubchem.inchikey")?.value);
  field(fields, "Resource ID", molecule.id);
  $("#graph-meta").textContent = `${data.document.resources.length} resources · Declared identity match: ${display(data.document.identity_basis)}`;
  $("#semantic-source").textContent = [...new Set(data.annotations.map(sourceName))].join(" / ");
  $("#perceptual-source").textContent = sourceName(data.observation);

  const annotations = $("#annotations");
  annotations.replaceChildren();
  for (const annotation of data.annotations) {
    if (data.annotations.length > 1) annotations.append(node("p", annotation.id, "group-label"));
    const items = annotation.data.annotations;
    if (!Array.isArray(items)) {
      annotations.append(node("p", "Annotation list not provided.", "footnote"), raw(annotation.data));
      continue;
    }
    if (!items.length) annotations.append(node("p", "Empty annotation list.", "footnote"));
    for (const item of items) {
      if (!item || typeof item !== "object" || Array.isArray(item)) { annotations.append(raw(item)); continue; }
      const row = node("div", undefined, "annotation-row");
      const name = node("span", display(item.value));
      name.title = `Language: ${display(item.language)}`;
      const state = new Map([["present", "Present"], ["absent", "Absent"], ["unknown", "Unknown"]]).get(item.state) ?? display(item.state);
      row.append(name, node("span", state, `state ${["present", "absent", "unknown"].includes(item.state) ? item.state : ""}`));
      annotations.append(row);
    }
  }

  const measurements = $("#measurements");
  measurements.replaceChildren();
  for (const result of data.observation.results) {
    measurements.append(node("p", `${result.scheme.id} · ${result.scheme.version}`, "group-label"));
    const items = result.data.measurements;
    if (!Array.isArray(items)) {
      measurements.append(node("p", "Measurement list not provided.", "footnote"), raw(result.data));
      continue;
    }
    const table = node("table", undefined, "measurements");
    const head = node("thead");
    const headers = node("tr");
    for (const title of ["Property", "Value / scale"]) {
      const th = node("th", title); th.scope = "col"; headers.append(th);
    }
    head.append(headers);
    const body = node("tbody");
    for (const item of items) {
      if (!item || typeof item !== "object" || Array.isArray(item)) { measurements.append(raw(item)); continue; }
      const row = node("tr");
      const value = node("td", typeof item.value === "number" ? number.format(item.value) : display(item.value));
      const scale = item.scale;
      value.append(node("small", scale && typeof scale === "object" ? `${display(scale.min)} → ${display(scale.max)}` : `Scale: ${display(scale)}`));
      if ("unit" in item) value.append(node("small", `Unit: ${display(item.unit)}`));
      row.append(node("td", display(item.property)), value);
      body.append(row);
    }
    table.append(head, body);
    measurements.append(table);
  }
  renderProvenance(data);
  $("#graph-json").textContent = JSON.stringify(data.document, null, 2);
}

function renderProvenance(data) {
  const container = $("#provenance");
  container.replaceChildren();
  const metadata = node("article", undefined, "provenance-card");
  metadata.append(node("h3", "Identity match & context"));
  const list = node("dl", undefined, "identity");
  field(list, "Identity", data.document.identity_basis);
  field(list, "Shared key", data.document.shared_inchikey);
  field(list, "Conditions", data.stimulus.conditions);
  field(list, "Target", data.target?.identifiers);
  field(list, "Context", data.observation.context);
  metadata.append(list);
  container.append(metadata);
  for (const resource of data.document.resources) {
    const article = node("article", undefined, "provenance-card");
    article.append(node("h3", resource.type));
    const fields = node("dl", undefined, "identity");
    field(fields, "Resource ID", resource.id);
    field(fields, "Source", resource.provenance?.source);
    field(fields, "Record", resource.provenance?.record);
    field(fields, "Derivation", resource.provenance?.derivation);
    article.append(fields);
    const details = node("details");
    details.append(node("summary", "View the full resource"), raw(resource));
    article.append(details);
    container.append(article);
  }
}

function renderPlan(data) {
  const chosen = data.policy;
  const plan = data.plans[chosen];
  const channels = [...new Set(Object.values(data.bindings).flat().map((binding) => binding.channel)
    .concat(Object.values(data.plans).flatMap((item) => item.commands.map((command) => command.channel))))].sort((a, b) => a - b);
  const commands = new Map(plan.commands.map((command) => [command.channel, command.intensity]));
  $("#plan-title").textContent = chosen === "semantic" ? "Semantic plan" : "Perceptual plan";
  const leds = $("#led-preview");
  leds.replaceChildren();
  for (const channel of channels) {
    const exists = commands.has(channel);
    const item = node("div", undefined, `led-item${exists ? "" : " omitted"}`);
    const circle = node("div", undefined, "led-circle");
    circle.setAttribute("aria-hidden", "true");
    if (exists) {
      const light = node("span", undefined, "led-light");
      light.style.setProperty("--level", commands.get(channel));
      circle.append(light);
    }
    item.append(circle, node("span", `Channel ${channel}`, "channel-label"), node("b", exists ? level.format(commands.get(channel)) : "No command", exists ? "" : "no-command"));
    leds.append(item);
  }
  $("#plan-count").textContent = `${plan.commands.length} command${plan.commands.length === 1 ? "" : "s"} in the plan`;
  $("#plan-duration").textContent = `${number.format(plan.duration)} s`;
  const comparison = $("#comparison-body");
  comparison.replaceChildren();
  for (const channel of channels) {
    const row = node("tr");
    const label = node("th", String(channel)); label.scope = "row";
    row.append(label);
    for (const policy of ["semantic", "perceptual"]) {
      const command = data.plans[policy].commands.find((item) => item.channel === channel);
      row.append(node("td", command ? level.format(command.intensity) : "No command", `${command ? "" : "no-command "}${chosen === policy ? "selected" : ""}`));
    }
    comparison.append(row);
  }
  $("#plan-json").textContent = JSON.stringify(plan, null, 2);
  const rules = $("#rules-content");
  rules.replaceChildren();
  for (const binding of data.bindings[chosen]) {
    const rule = chosen === "semantic" ? `${binding.descriptor} present → channel ${binding.channel} at ${level.format(binding.intensity)}` : `${binding.property} → channel ${binding.channel}`;
    rules.append(node("p", rule, "rule-line"));
  }
  rules.append(node("p", chosen === "semantic" ? "Only descriptors marked as present and mapped to a channel produce a command. All others produce no command." : "The mapper normalizes each measurement using its declared scale: (value − min) / (max − min). Measurements without a usable value or scale are skipped."));
}

function showError(message) {
  $("#error").textContent = message;
  $("#error").hidden = false;
  $("#workspace").classList.add("hardware-only");
  hardware.clearPreview();
  $("#welcome").hidden = false;
  $("#request-status").textContent = "Error · no preview displayed. Open the demo or import another file.";
}

async function calculate() {
  if (!source) return;
  const currentId = ++requestId;
  hardware.clearPreview();
  activeRequest?.abort();
  activeRequest = new AbortController();
  $("#calculated-preview").hidden = true;
  const duration = $("#duration").value.trim() === "" ? null : Number($("#duration").value);
  if (duration === null || !Number.isFinite(duration) || duration <= 0) {
    invalidateServerPreview(currentId);
    $("#duration-error").textContent = "Enter a finite duration greater than zero, in seconds, then recalculate.";
    $("#duration-error").hidden = false;
    $("#duration").setAttribute("aria-invalid", "true");
    $("#workspace").setAttribute("aria-busy", "false");
    $("#request-status").textContent = "Invalid duration · correct the duration to preview the plan.";
    return;
  }
  $("#duration-error").hidden = true;
  $("#duration").removeAttribute("aria-invalid");
  $("#error").hidden = true;
  $("#request-status").textContent = "Calculating with the OpenSmell mappers…";
  $("#workspace").setAttribute("aria-busy", "true");
  $("#file-name").textContent = source.name;
  $("#file-meta").textContent = source.source === "fixture" ? "examples/multisource_beta_pinene.osmell · local file" : "Imported file · processed in memory on this computer";
  try {
    const response = await fetch("/api/preview", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({...source, duration, policy: $("input[name=policy]:checked").value,
        client_id: previewClientId, revision: currentId}),
      signal: activeRequest.signal,
    });
    const result = await response.json();
    if (currentId !== requestId) return;
    if (!response.ok) throw new Error(result.error || "Calculation failed.");
    renderData(result);
    renderPlan(result);
    $("#calculated-preview").hidden = false;
    $("#workspace").classList.remove("hardware-only");
    hardware.setPreview(result.preview_ticket);
    $("#welcome").hidden = true;
    $("#request-status").textContent = "Preview calculated · two plans available · previewing does not send commands";
  } catch (error) {
    if (currentId !== requestId || error.name === "AbortError") return;
    showError(error instanceof TypeError ? "The local server is not responding. Restart python -m apps.local_demo, then open the demo." : error.message);
  } finally {
    if (currentId === requestId) $("#workspace").setAttribute("aria-busy", "false");
  }
}

$("#load-demo").addEventListener("click", () => {
  source = {source: "fixture", name: "multisource_beta_pinene.osmell"};
  // Reopening the fixture also recovers from an invalid duration.
  $("#duration").value = "5";
  calculate();
});
$("#import-file").addEventListener("click", () => $("#file-input").click());
$("#file-input").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const importId = ++requestId;
  activeRequest?.abort();
  hardware.clearPreview();
  invalidateServerPreview(importId);
  source = null;
  try {
    if (file.size > 1024 * 1024) throw new Error("File too large: the limit is 1 MiB.");
    const text = new TextDecoder("utf-8", {fatal: true}).decode(await file.arrayBuffer());
    if (importId !== requestId) return;
    source = {source: "file", name: file.name, text};
    if ($("#duration").getAttribute("aria-invalid") === "true") $("#duration").value = "5";
    await calculate();
  } catch (error) {
    if (importId === requestId) showError(error instanceof TypeError ? "Invalid encoding: a UTF-8 JSON file is required." : error.message);
  } finally {
    event.target.value = "";
  }
});
$("#duration-form").addEventListener("submit", (event) => { event.preventDefault(); calculate(); });
$("#duration").addEventListener("change", calculate);
$("#duration").addEventListener("input", () => {
  invalidatePreview();
  $("#calculated-preview").hidden = true;
  $("#workspace").setAttribute("aria-busy", "false");
  $("#request-status").textContent = "Duration changed · recalculate to display the planned commands.";
});
$("#policy-picker").addEventListener("change", calculate);

function chooseTab(tab) {
  document.querySelectorAll("[data-tab]").forEach((button) => {
    const active = button === tab;
    button.setAttribute("aria-selected", active);
    button.tabIndex = active ? 0 : -1;
    $(`#panel-${button.dataset.tab}`).hidden = !active;
  });
}
const tabs = [...document.querySelectorAll("[data-tab]")];
tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => chooseTab(tab));
  tab.addEventListener("keydown", (event) => {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); chooseTab(tabs[next]); tabs[next].focus(); }
  });
});
