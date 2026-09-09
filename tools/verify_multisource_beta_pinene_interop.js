#!/usr/bin/env node
"use strict";

/*
 * Independent JavaScript interoperability verifier for the OpenSmell
 * multi-source beta-pinene example.
 *
 * This verifier intentionally does not import the Python implementation.
 * It validates the actual serialized wire representation used by the
 * current GenericResourceGraph fixture, follows its references, checks
 * the OdorNet semantic annotation and Keller/Vosshall perceptual result,
 * then reserializes the graph for a Python round-trip check.
 */

const fs = require("fs");
const path = require("path");

const inputPath =
  process.argv[2] || path.join("examples", "multisource_beta_pinene.osmell");
const outputPath =
  process.argv[3] || path.join("examples", "multisource_beta_pinene_js.json");

function fail(message) {
  console.error(`FAIL ${message}`);
  process.exit(1);
}

function pass(message) {
  console.log(`PASS ${message}`);
}

function requireCondition(condition, message) {
  if (!condition) {
    fail(message);
  }
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function findOne(resources, type) {
  const matches = resources.filter((resource) => resource.type === type);
  requireCondition(
    matches.length === 1,
    `expected exactly one ${type}, found ${matches.length}`
  );
  return matches[0];
}

function getReferenceId(value, label) {
  requireCondition(isObject(value), `${label} must be an object reference`);
  requireCondition(
    typeof value.resource_id === "string" && value.resource_id.length > 0,
    `${label}.resource_id must be a non-empty string`
  );
  return value.resource_id;
}

function buildMeasurementMap(result) {
  requireCondition(isObject(result), "observation result must be an object");
  requireCondition(
    isObject(result.scheme),
    "observation result scheme must be an object"
  );
  requireCondition(
    result.scheme.id === "org.opensmell.perceptual.measurements",
    "unexpected perceptual measurement scheme id"
  );
  requireCondition(
    result.scheme.version === "0.1",
    "unexpected perceptual measurement scheme version"
  );
  requireCondition(
    isObject(result.data),
    "observation result data must be an object"
  );
  requireCondition(
    Array.isArray(result.data.measurements) &&
      result.data.measurements.length > 0,
    "measurements must be a non-empty array"
  );

  const measurements = new Map();

  for (const measurement of result.data.measurements) {
    requireCondition(isObject(measurement), "measurement must be an object");
    requireCondition(
      typeof measurement.property === "string" &&
        measurement.property.length > 0,
      "measurement property must be a non-empty string"
    );
    requireCondition(
      typeof measurement.value === "number" &&
        Number.isFinite(measurement.value),
      `measurement ${measurement.property} value must be finite`
    );
    requireCondition(
      isObject(measurement.scale),
      `measurement ${measurement.property} scale missing`
    );
    requireCondition(
      typeof measurement.scale.min === "number" &&
        Number.isFinite(measurement.scale.min),
      `measurement ${measurement.property} scale minimum invalid`
    );
    requireCondition(
      typeof measurement.scale.max === "number" &&
        Number.isFinite(measurement.scale.max),
      `measurement ${measurement.property} scale maximum invalid`
    );
    requireCondition(
      measurement.scale.min < measurement.scale.max,
      `measurement ${measurement.property} scale invalid`
    );
    requireCondition(
      measurement.value >= measurement.scale.min &&
        measurement.value <= measurement.scale.max,
      `measurement ${measurement.property} outside scale`
    );
    requireCondition(
      !measurements.has(measurement.property),
      `duplicate measurement property ${measurement.property}`
    );

    measurements.set(measurement.property, measurement);
  }

  return measurements;
}

let raw;
try {
  raw = fs.readFileSync(inputPath, "utf8");
} catch (error) {
  fail(`cannot read ${inputPath}: ${error.message}`);
}

let graph;
try {
  graph = JSON.parse(raw);
} catch (error) {
  fail(`invalid JSON: ${error.message}`);
}

requireCondition(isObject(graph), "graph root must be an object");
requireCondition(
  graph.format === "org.opensmell.experimental.generic-resource-graph",
  "unexpected graph format"
);
requireCondition(graph.version === "0.1", "unexpected graph version");
requireCondition(Array.isArray(graph.resources), "resources must be an array");
requireCondition(
  graph.resources.length === 5,
  `expected 5 resources, found ${graph.resources.length}`
);
pass("generic graph envelope and five-resource fixture");

const byId = new Map();

for (const resource of graph.resources) {
  requireCondition(isObject(resource), "every resource must be an object");
  requireCondition(
    typeof resource.id === "string" && resource.id.length > 0,
    "every resource must have a non-empty id"
  );
  requireCondition(
    typeof resource.type === "string" && resource.type.length > 0,
    `resource ${resource.id} must have a non-empty type`
  );
  requireCondition(
    !byId.has(resource.id),
    `duplicate resource id ${resource.id}`
  );
  byId.set(resource.id, resource);
}
pass("resource identifiers are unique");

/*
 * Important interoperability detail:
 *
 * Molecule and Annotation use namespaced experimental resource type names.
 * The RFC-0007 resource family keeps its established serialized type names:
 *   stimulus
 *   observation_target
 *   observation
 *
 * JavaScript validates those actual wire names rather than Python class names.
 */
const molecule = findOne(graph.resources, "org.opensmell.molecule");
const annotation = findOne(graph.resources, "org.opensmell.annotation");
const stimulus = findOne(graph.resources, "stimulus");
const target = findOne(graph.resources, "observation_target");
const observation = findOne(graph.resources, "observation");
pass(
  "Molecule, Annotation, Stimulus, ObservationTarget and Observation present"
);

requireCondition(
  typeof molecule.smiles === "string" && molecule.smiles.length > 0,
  "molecule SMILES missing"
);
requireCondition(
  Array.isArray(molecule.identifiers),
  "molecule identifiers must be an array"
);

const inchikeyIdentifier = molecule.identifiers.find(
  (identifier) =>
    isObject(identifier) &&
    identifier.scheme === "pubchem.inchikey" &&
    typeof identifier.value === "string"
);

requireCondition(
  Boolean(inchikeyIdentifier),
  "PubChem InChIKey identifier missing"
);
requireCondition(
  inchikeyIdentifier.value === "WTARULDDTDQWMU-IUCAKERBSA-N",
  "unexpected beta-pinene InChIKey"
);
pass("shared beta-pinene molecular identity");

const annotationSubjectId = getReferenceId(
  annotation.subject,
  "annotation.subject"
);
requireCondition(
  annotationSubjectId === molecule.id,
  "OdorNet annotation must directly reference the Molecule"
);
requireCondition(isObject(annotation.scheme), "annotation scheme missing");
requireCondition(
  annotation.scheme.id === "org.opensmell.semantic.annotations",
  "unexpected annotation scheme"
);
requireCondition(
  annotation.scheme.version === "0.1",
  "unexpected annotation scheme version"
);
requireCondition(
  isObject(annotation.data),
  "annotation data must be an object"
);
requireCondition(
  Array.isArray(annotation.data.annotations),
  "semantic annotations must be an array"
);
requireCondition(
  annotation.data.annotations.length === 12,
  `expected 12 OdorNet annotations, found ${annotation.data.annotations.length}`
);

const semanticStates = new Map();

for (const entry of annotation.data.annotations) {
  requireCondition(
    isObject(entry),
    "semantic annotation entry must be an object"
  );
  requireCondition(
    typeof entry.value === "string" && entry.value.length > 0,
    "semantic annotation value must be a non-empty string"
  );
  requireCondition(
    ["present", "absent", "unknown"].includes(entry.state),
    `invalid semantic state for ${entry.value}`
  );
  requireCondition(
    !semanticStates.has(entry.value),
    `duplicate semantic annotation ${entry.value}`
  );
  semanticStates.set(entry.value, entry.state);
}

requireCondition(
  semanticStates.get("floral") === "absent",
  "floral state must be absent"
);
requireCondition(
  semanticStates.get("green&herbal") === "present",
  "green&herbal state must be present"
);
requireCondition(
  semanticStates.get("woody&mossy") === "present",
  "woody&mossy state must be present"
);
pass("all 12 OdorNet semantic states preserved");

const stimulusSourceId = getReferenceId(stimulus.source, "stimulus.source");
requireCondition(
  stimulusSourceId === molecule.id,
  "Keller/Vosshall Stimulus must reference the same Molecule"
);
pass("OdorNet and Keller/Vosshall branches converge on the same Molecule");

const observationStimulusId = getReferenceId(
  observation.stimulus,
  "observation.stimulus"
);
const observationTargetId = getReferenceId(
  observation.target,
  "observation.target"
);

requireCondition(
  observationStimulusId === stimulus.id,
  "Observation must reference the Keller/Vosshall Stimulus"
);
requireCondition(
  observationTargetId === target.id,
  "Observation must reference the ObservationTarget"
);
requireCondition(
  byId.has(observationStimulusId),
  "Observation stimulus reference unresolved"
);
requireCondition(
  byId.has(observationTargetId),
  "Observation target reference unresolved"
);
requireCondition(
  byId.has(stimulusSourceId),
  "Stimulus source reference unresolved"
);
requireCondition(
  byId.has(annotationSubjectId),
  "Annotation subject reference unresolved"
);
pass("all cross-resource references resolve");

requireCondition(
  Array.isArray(observation.results) && observation.results.length > 0,
  "Observation must contain results"
);

const perceptualResult = observation.results.find(
  (result) =>
    isObject(result) &&
    isObject(result.scheme) &&
    result.scheme.id === "org.opensmell.perceptual.measurements" &&
    result.scheme.version === "0.1"
);

requireCondition(
  Boolean(perceptualResult),
  "perceptual measurement result missing"
);

const measurements = buildMeasurementMap(perceptualResult);

for (const [property, expected] of [
  ["flower", 1],
  ["grass", 86],
  ["wood", 97],
]) {
  requireCondition(
    measurements.has(property),
    `${property} measurement missing`
  );

  const measurement = measurements.get(property);

  requireCondition(
    measurement.value === expected,
    `${property} expected ${expected}, found ${measurement.value}`
  );
  requireCondition(
    measurement.scale.min === 0 && measurement.scale.max === 100,
    `${property} expected explicit 0..100 scale`
  );
}
pass(
  "Keller/Vosshall flower=1, grass=86 and wood=97 measurements preserved"
);

let reserialized;
try {
  reserialized = JSON.stringify(graph, null, 2) + "\n";
} catch (error) {
  fail(`cannot reserialize graph: ${error.message}`);
}

try {
  fs.writeFileSync(outputPath, reserialized, "utf8");
} catch (error) {
  fail(`cannot write ${outputPath}: ${error.message}`);
}

pass(`JavaScript reserialization written to ${outputPath}`);
console.log(
  "Multi-source beta-pinene interoperability: 8 passed, 0 failed"
);
