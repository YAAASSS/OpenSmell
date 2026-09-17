/* Independent, deliberately limited JavaScript inspection. No Python or network.
 * Wire dispatch/reference rules follow the existing portable verifiers in
 * tools/verify_{multisource_beta_pinene_interop,reference_discovery_vectors}.js.
 * Those historical fixture verifiers remain unchanged and run separately.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.OpenSmellReader = api;
})(globalThis, function () {
  "use strict";
  const LIMIT = 1_048_576;
  const FORMAT = "org.opensmell.experimental.generic-resource-graph";
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
  const string = value => typeof value === "string" && value.length > 0;
  const pointer = (base, key) => `${base}/${String(key).replace(/~/g, "~0").replace(/\//g, "~1")}`;
  class InspectionError extends Error {
    constructor(code, path, message) { super(message); this.code = code; this.path = path; }
  }
  function requireValue(condition, path, message) {
    if (!condition) throw new InspectionError("invalid_content", path, message);
  }

  // JSON.parse checks syntax. This second pass records original token spans,
  // detects duplicate object keys, and never uses rounded numbers for display.
  function scan(text, diagnostic) {
    const spans = new Map(), limitedNumbers = new Set();
    let index = 0;
    const space = () => { while (/\s/.test(text[index] || "x")) index++; };
    function quoted() {
      const start = index++;
      while (text[index] !== '"') {
        if (text[index] === "\\") index++;
        index++;
      }
      index++;
      return JSON.parse(text.slice(start, index));
    }
    function visit(path, depth) {
      if (depth > 64) throw new InspectionError("reading_limit", path, "JSON nesting exceeds the reader limit of 64 levels.");
      space();
      const start = index;
      if (text[index] === "{") {
        index++; space();
        const keys = new Set();
        while (text[index] !== "}") {
          const key = quoted(); space(); index++;
          if (keys.has(key)) throw new InspectionError("duplicate_json_key", pointer(path, key), "Duplicate JSON object key; interpretation would be ambiguous.");
          keys.add(key); visit(pointer(path, key), depth + 1); space();
          if (text[index] !== ",") break;
          index++; space();
        }
        index++;
      } else if (text[index] === "[") {
        index++; space();
        let item = 0;
        while (text[index] !== "]") {
          visit(pointer(path, item++), depth + 1); space();
          if (text[index] !== ",") break;
          index++; space();
        }
        index++;
      } else if (text[index] === '"') {
        const value = quoted();
        // Escaped unpaired surrogates are legal JSON, but not scalar Unicode.
        if (/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(value)) {
          diagnostic("warning", "unicode_limit", path, "Unpaired Unicode surrogate: display uses its JSON escape; original bytes remain intact.");
        }
      } else {
        while (index < text.length && !/[\s,\]}]/.test(text[index])) index++;
        const token = text.slice(start, index);
        if (/^-?\d/.test(token)) {
          const number = Number(token);
          if (!Number.isSafeInteger(number) || !/^-?\d+(?:\.0+)?$/.test(token) || Object.is(number, -0)) {
            limitedNumbers.add(path);
            diagnostic("warning", "numeric_limit", path,
              "Number retained as its original JSON token. Exact-decimal/range interpretation is not performed for non-integral, exponent, unsafe, extreme or negative-zero tokens.");
          }
        }
      }
      spans.set(path, [start, index]);
    }
    visit("", 0);
    return {spans, limitedNumbers};
  }

  const CHECKS = [
    "Inclusive 1,048,576-byte file limit (including a UTF-8 BOM).",
    "Fatal UTF-8 decoding, JSON syntax, duplicate keys, maximum nesting of 64.",
    "Generic ResourceGraph 0.1 envelope; nonempty resource IDs/types; unique IDs; optional nonempty type_version.",
    "Exact recognized type/version dispatch; limited fields and the two supported result schemes.",
    "Only Annotation.subject, Stimulus.source, Observation.stimulus and Observation.target references.",
    "Safe-integer measurement ranges when an explicit usable scale is supplied; other numeric tokens reported verbatim.",
  ];
  const LIMITS = [
    "A limited reader developed in the OpenSmell project, not third-party certification or a complete SDK implementation.",
    "Unknown types, versions, schemes and extensions are preserved as bytes; their meaning is not validated.",
    "Provenance and identity labels are declarations in the file, not verified chemical identity or source authenticity.",
    "No scientific equivalence between categorical annotations and perceptual measurements is inferred.",
    "The original-byte download is not JSON reserialization, editing, or proof of lossless JSON.stringify.",
    "No hardware access, mapping, Python analysis or network upload occurs in this reader.",
  ];

  function analyze(text, report) {
    const diagnostic = (severity, code, path, message) => report.diagnostics.push({severity, code, path, message});
    let graph;
    try { graph = JSON.parse(text); }
    catch { throw new InspectionError("invalid_json", "", "Invalid JSON. The file cannot be interpreted."); }
    const {spans, limitedNumbers} = scan(text, diagnostic);
    const raw = path => {
      const span = spans.get(path);
      return span ? text.slice(...span) : null;
    };
    const field = (parent, key, base) => {
      if (!object(parent) || !own(parent, key)) return {presence: "missing", text: "Not provided"};
      const value = parent[key], path = pointer(base, key);
      if (value === null) return {presence: "null", text: "Explicit null"};
      let display = typeof value === "string" ? value : raw(path);
      if (typeof value === "string" && /[\uD800-\uDFFF]/u.test(value.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/gu, ""))) display = raw(path);
      return {presence: "value", text: display, json: raw(path)};
    };
    const source = (resource, path) => ({
      name: field(resource.provenance?.source, "name", `${path}/provenance/source`),
      provenance_json: raw(`${path}/provenance`),
      context_json: raw(`${path}/context`),
    });
    requireValue(object(graph), "", "The graph must be a JSON object.");
    report.format = field(graph, "format", ""); report.version = field(graph, "version", "");
    if (graph.format !== FORMAT || graph.version !== "0.1") {
      throw new InspectionError("unsupported_format", "/format", "Unsupported format/version. This reader supports experimental Generic ResourceGraph 0.1, not Core documents or other graph formats.");
    }
    requireValue(Array.isArray(graph.resources), "/resources", "resources must be an array.");
    const byId = new Map();
    for (const [index, resource] of graph.resources.entries()) {
      const path = `/resources/${index}`;
      requireValue(object(resource), path, "A resource must be an object.");
      requireValue(string(resource.id), `${path}/id`, "Resource id must be a nonempty string (not necessarily a UUID).");
      requireValue(string(resource.type), `${path}/type`, "Resource type must be a nonempty string.");
      requireValue(!own(resource, "type_version") || string(resource.type_version), `${path}/type_version`, "type_version must be a nonempty string when present.");
      if (byId.has(resource.id)) throw new InspectionError("duplicate_id", `${path}/id`, `Duplicate resource id: ${resource.id}`);
      const kind = resource.type === "org.opensmell.molecule" && resource.type_version === "0.1" ? "molecule"
        : resource.type === "org.opensmell.annotation" && resource.type_version === "0.1" ? "annotation"
        : ["stimulus", "observation_target", "observation"].includes(resource.type) && !own(resource, "type_version") ? resource.type : "opaque";
      const item = {id: resource.id, type: resource.type, type_version: field(resource, "type_version", path), kind, status: kind === "opaque" ? "opaque" : "recognized", path};
      report.resources.push(item); byId.set(resource.id, item);
    }
    function identifiers(resource, path) {
      if (!own(resource, "identifiers")) return [];
      requireValue(Array.isArray(resource.identifiers), `${path}/identifiers`, "identifiers must be an array.");
      return resource.identifiers.map((identifier, index) => {
        requireValue(object(identifier) && string(identifier.scheme) && string(identifier.value), `${path}/identifiers/${index}`, "An identifier needs nonempty scheme and value strings.");
        return {scheme: identifier.scheme, value: identifier.value};
      });
    }
    function reference(resource, name, path, optional, expected) {
      if (optional && (!own(resource, name) || resource[name] === null)) return;
      const ref = resource[name], location = pointer(path, name);
      requireValue(object(ref) && string(ref.resource_id), location, "A structural reference must contain a nonempty resource_id.");
      const target = byId.get(ref.resource_id);
      report.references.push({source_id: resource.id, field: name, target_id: ref.resource_id, resolved: Boolean(target), target_kind: target?.kind || null});
      requireValue(Boolean(target), location, `Unresolved reference: ${ref.resource_id}`);
      if (target.kind === "opaque") diagnostic("warning", "opaque_target", location, "The reference resolves, but the target type/version is not interpreted.");
      else if (expected) requireValue(target.kind === expected, location, `This reader's observation path requires a ${expected} target.`);
    }
    function scheme(value, path) {
      requireValue(object(value) && string(value.id) && string(value.version), path, "A scheme needs nonempty id and version strings.");
      return value;
    }
    for (const [index, resource] of graph.resources.entries()) {
      const item = report.resources[index], path = item.path;
      try {
        if (item.kind === "opaque") {
          diagnostic("warning", "opaque_resource", path, "Resource type/version not interpreted. Its original bytes are preserved; payload and references are not checked.");
        } else if (item.kind === "molecule") {
          const ids = identifiers(resource, path);
          requireValue(resource.smiles == null || string(resource.smiles), `${path}/smiles`, "smiles must be nonempty text when provided.");
          requireValue(string(resource.smiles) || ids.length > 0, path, "Molecule needs SMILES or at least one external identifier.");
          report.molecules.push({id: item.id, label: field(resource.pubchem, "title", `${path}/pubchem`), smiles: field(resource, "smiles", path), identifiers: ids, source: source(resource, path)});
        } else if (item.kind === "annotation") {
          reference(resource, "subject", path, false);
          const selected = scheme(resource.scheme, `${path}/scheme`);
          requireValue(object(resource.data), `${path}/data`, "Annotation data must be an object.");
          if (selected.id !== "org.opensmell.semantic.annotations" || selected.version !== "0.1") {
            diagnostic("warning", "opaque_scheme", `${path}/scheme`, "Annotation scheme/version not interpreted; no categorical meaning is inferred.");
            continue;
          }
          requireValue(Array.isArray(resource.data.annotations), `${path}/data/annotations`, "annotations must be an array.");
          const entries = resource.data.annotations.map((entry, offset) => {
            const location = `${path}/data/annotations/${offset}`;
            requireValue(object(entry) && string(entry.value), location, "An annotation requires a nonempty value string.");
            requireValue(["present", "absent", "unknown"].includes(entry.state), `${location}/state`, "State must be present, absent or unknown; it is never filled in.");
            requireValue(!own(entry, "language") || entry.language === null || string(entry.language), `${location}/language`, "language must be nonempty text or null when provided.");
            return {value: entry.value, state: entry.state, language: field(entry, "language", location)};
          });
          report.annotations.push({id: item.id, subject: resource.subject.resource_id, source: source(resource, path), entries});
        } else if (item.kind === "stimulus") {
          reference(resource, "source", path, true);
          identifiers(resource, path);
          report.stimuli.push({id: item.id, source: field(resource, "source", path), conditions: field(resource, "conditions", path)});
        } else if (item.kind === "observation_target") {
          report.targets.push({id: item.id, identifiers: identifiers(resource, path)});
        } else if (item.kind === "observation") {
          reference(resource, "stimulus", path, false, "stimulus");
          reference(resource, "target", path, true, "observation_target");
          requireValue(Array.isArray(resource.results), `${path}/results`, "Observation results must be an array.");
          const groups = [];
          for (const [offset, result] of resource.results.entries()) {
            const location = `${path}/results/${offset}`;
            requireValue(object(result), location, "A result must be an object.");
            const selected = scheme(result.scheme, `${location}/scheme`);
            requireValue(object(result.data), `${location}/data`, "Result data must be an object.");
            if (selected.id !== "org.opensmell.perceptual.measurements" || selected.version !== "0.1") {
              diagnostic("warning", "opaque_scheme", `${location}/scheme`, "Result scheme/version not interpreted; its payload is preserved, not validated.");
              continue;
            }
            requireValue(Array.isArray(result.data.measurements), `${location}/data/measurements`, "measurements must be an array.");
            const entries = result.data.measurements.map((measurement, index) => {
              const p = `${location}/data/measurements/${index}`;
              requireValue(object(measurement) && string(measurement.property), p, "Measurement property must be a nonempty string.");
              requireValue(!own(measurement, "value") || measurement.value === null || typeof measurement.value === "number", `${p}/value`, "A displayed quantitative value must be a number, null or missing.");
              const scale = measurement.scale;
              requireValue(scale == null || object(scale), `${p}/scale`, "Scale must be an object, null or missing.");
              for (const key of ["min", "max"]) requireValue(!object(scale) || !own(scale, key) || scale[key] === null || typeof scale[key] === "number", `${p}/scale/${key}`, "A scale bound must be numeric, null or missing.");
              requireValue(!own(measurement, "unit") || measurement.unit === null || string(measurement.unit), `${p}/unit`, "Unit must be nonempty text, null or missing.");
              const fields = [`${p}/value`, `${p}/scale/min`, `${p}/scale/max`];
              if (typeof measurement.value !== "number" || !object(scale) || typeof scale.min !== "number" || typeof scale.max !== "number") {
                diagnostic("warning", "unavailable_measurement", p, "Value or explicit min/max scale is missing/null. Shown as supplied; no range check or normalization performed.");
              } else if (!fields.some(key => limitedNumbers.has(key))) {
                requireValue(scale.min < scale.max, `${p}/scale`, "Scale minimum must be less than maximum.");
                requireValue(measurement.value >= scale.min && measurement.value <= scale.max, `${p}/value`, "Measurement is outside its declared scale.");
              }
              return {property: measurement.property, value: field(measurement, "value", p), unit: field(measurement, "unit", p), scale: field(measurement, "scale", p), min: field(scale, "min", `${p}/scale`), max: field(scale, "max", `${p}/scale`)};
            });
            groups.push({result_index: offset, entries});
          }
          report.observations.push({id: item.id, stimulus: resource.stimulus.resource_id, target: field(resource, "target", path), source: source(resource, path), groups});
        }
      } catch (error) {
        if (!(error instanceof InspectionError)) throw error;
        item.status = "invalid";
        diagnostic("error", error.code, error.path, error.message);
      }
    }
    for (const ref of report.references) {
      if (byId.get(ref.target_id)?.status === "invalid") diagnostic("error", "invalid_target", ref.source_id, `Reference ${ref.field} points to an invalid recognized resource.`);
    }
    if (!report.molecules.length || !report.annotations.length || !report.observations.length) diagnostic("warning", "incomplete_branches", "/resources", "This file does not expose all of the recognized molecule, annotation and observation branches.");
    diagnostic("info", "scope", "", "Listed checks only. Unknown fields, source declarations, chemistry and opaque payload meanings are not validated.");
  }

  async function inspectBytes(input, name = "graph.osmell") {
    if (!(input instanceof Uint8Array)) throw new TypeError("Expected file bytes as Uint8Array.");
    if (input.byteLength > LIMIT) throw new InspectionError("file_too_large", "", "File too large. Maximum: 1,048,576 bytes (1 MiB), including any UTF-8 BOM.");
    const bytes = Uint8Array.from(input); // Private snapshot; callers cannot alter downloads.
    const hash = Array.from(new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", bytes)), value => value.toString(16).padStart(2, "0")).join("");
    const bom = bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf;
    const report = {tool: "OpenSmell JavaScript Graph Reader", report_version: "application-specific 0.1", file: {name, byte_length: bytes.length, sha256: hash, utf8_bom: bom}, status: "inspected", checks: [...CHECKS], limits: [...LIMITS], diagnostics: [], resources: [], references: [], molecules: [], annotations: [], observations: [], stimuli: [], targets: []};
    try {
      let text;
      try { text = new TextDecoder("utf-8", {fatal: true, ignoreBOM: true}).decode(bytes); }
      catch { throw new InspectionError("invalid_utf8", "", "Invalid UTF-8. No replacement characters were inserted; the file was not interpreted."); }
      analyze(bom ? text.slice(1) : text, report);
    } catch (error) {
      if (!(error instanceof InspectionError)) throw error;
      report.diagnostics.push({severity: "error", code: error.code, path: error.path, message: error.message});
    }
    if (report.diagnostics.some(item => item.severity === "error")) report.status = "rejected";
    else if (report.diagnostics.some(item => item.severity === "warning")) report.status = "partial";
    return {report, copyBytes() {
      if (report.status === "rejected") throw new Error("No transfer is available for a rejected inspection.");
      return Uint8Array.from(bytes);
    }};
  }
  return {LIMIT, FORMAT, inspectBytes};
});
