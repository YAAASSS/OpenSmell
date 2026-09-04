"use strict";

/*
 * OpenSmell experimental ResourceGraph portable conformance verifier.
 *
 * This verifier intentionally does not depend on the Python implementation.
 * It consumes:
 *
 *   examples/resource_graph_conformance_vectors.json
 *
 * and independently checks the structural rules represented by the
 * experimental ResourceGraph 0.1 JSON Schema.
 *
 * This is an interoperability/conformance experiment. It is not a normative
 * OpenSmell implementation.
 */

const fs = require("fs");
const path = require("path");


const ROOT = path.resolve(__dirname, "..");

const VECTORS_PATH = path.join(
    ROOT,
    "examples",
    "resource_graph_conformance_vectors.json"
);

const VECTOR_FORMAT =
    "org.opensmell.experimental.resource-graph-conformance";

const VECTOR_VERSION = "0.1";

const GRAPH_FORMAT =
    "org.opensmell.experimental.resource-graph";

const GRAPH_VERSION = "0.1";


function isObject(value) {
    return (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value)
    );
}


function isNonEmptyString(value) {
    return typeof value === "string" && value.length > 0;
}


function validateReference(value) {
    if (!isObject(value)) {
        return false;
    }

    return isNonEmptyString(value.resource_id);
}


function validateExternalIdentifier(value) {
    if (!isObject(value)) {
        return false;
    }

    return (
        isNonEmptyString(value.scheme) &&
        isNonEmptyString(value.value)
    );
}


function validateCondition(value) {
    if (!isObject(value)) {
        return false;
    }

    if (!isNonEmptyString(value.property)) {
        return false;
    }

    if (!Object.prototype.hasOwnProperty.call(value, "value")) {
        return false;
    }

    if (
        Object.prototype.hasOwnProperty.call(value, "unit") &&
        !isNonEmptyString(value.unit)
    ) {
        return false;
    }

    return true;
}


function validateResultScheme(value) {
    if (!isObject(value)) {
        return false;
    }

    return (
        isNonEmptyString(value.id) &&
        isNonEmptyString(value.version)
    );
}


function validateResult(value) {
    if (!isObject(value)) {
        return false;
    }

    if (!validateResultScheme(value.scheme)) {
        return false;
    }

    if (!Object.prototype.hasOwnProperty.call(value, "data")) {
        return false;
    }

    if (!isObject(value.data)) {
        return false;
    }

    return true;
}


function validateIdentifiers(value) {
    if (!Array.isArray(value)) {
        return false;
    }

    return value.every(validateExternalIdentifier);
}


function validateConditions(value) {
    if (!Array.isArray(value)) {
        return false;
    }

    return value.every(validateCondition);
}


function validateResults(value) {
    if (!Array.isArray(value)) {
        return false;
    }

    return value.every(validateResult);
}


function validateStimulus(resource) {
    if (!isNonEmptyString(resource.id)) {
        return false;
    }

    if (resource.type !== "stimulus") {
        return false;
    }

    if (Object.prototype.hasOwnProperty.call(resource, "source")) {
        if (
            resource.source !== null &&
            !validateReference(resource.source)
        ) {
            return false;
        }
    }

    if (Object.prototype.hasOwnProperty.call(resource, "identifiers")) {
        if (!validateIdentifiers(resource.identifiers)) {
            return false;
        }
    }

    if (Object.prototype.hasOwnProperty.call(resource, "conditions")) {
        if (!validateConditions(resource.conditions)) {
            return false;
        }
    }

    return true;
}


function validateObservationTarget(resource) {
    if (!isNonEmptyString(resource.id)) {
        return false;
    }

    if (resource.type !== "observation_target") {
        return false;
    }

    if (Object.prototype.hasOwnProperty.call(resource, "identifiers")) {
        if (!validateIdentifiers(resource.identifiers)) {
            return false;
        }
    }

    return true;
}


function validateObservation(resource) {
    if (!isNonEmptyString(resource.id)) {
        return false;
    }

    if (resource.type !== "observation") {
        return false;
    }

    if (!Object.prototype.hasOwnProperty.call(resource, "stimulus")) {
        return false;
    }

    if (!validateReference(resource.stimulus)) {
        return false;
    }

    if (Object.prototype.hasOwnProperty.call(resource, "target")) {
        if (
            resource.target !== null &&
            !validateReference(resource.target)
        ) {
            return false;
        }
    }

    if (Object.prototype.hasOwnProperty.call(resource, "results")) {
        if (!validateResults(resource.results)) {
            return false;
        }
    }

    if (Object.prototype.hasOwnProperty.call(resource, "context")) {
        if (!isObject(resource.context)) {
            return false;
        }
    }

    if (Object.prototype.hasOwnProperty.call(resource, "identifiers")) {
        if (!validateIdentifiers(resource.identifiers)) {
            return false;
        }
    }

    return true;
}


function validateResource(resource) {
    if (!isObject(resource)) {
        return false;
    }

    if (!Object.prototype.hasOwnProperty.call(resource, "type")) {
        return false;
    }

    switch (resource.type) {
        case "stimulus":
            return validateStimulus(resource);

        case "observation_target":
            return validateObservationTarget(resource);

        case "observation":
            return validateObservation(resource);

        default:
            return false;
    }
}


function validateGraph(document) {
    if (!isObject(document)) {
        return false;
    }

    if (document.format !== GRAPH_FORMAT) {
        return false;
    }

    if (document.version !== GRAPH_VERSION) {
        return false;
    }

    if (!Object.prototype.hasOwnProperty.call(document, "resources")) {
        return false;
    }

    if (!Array.isArray(document.resources)) {
        return false;
    }

    return document.resources.every(validateResource);
}


function loadVectors() {
    const text = fs.readFileSync(VECTORS_PATH, "utf8");
    const document = JSON.parse(text);

    if (!isObject(document)) {
        throw new Error("Conformance vector file must contain an object.");
    }

    if (document.format !== VECTOR_FORMAT) {
        throw new Error(
            `Unexpected vector format: ${String(document.format)}`
        );
    }

    if (document.version !== VECTOR_VERSION) {
        throw new Error(
            `Unexpected vector version: ${String(document.version)}`
        );
    }

    if (!Array.isArray(document.vectors)) {
        throw new Error("Conformance vector file must contain vectors[].");
    }

    return document.vectors;
}


function verifyVectorShape(vector) {
    if (!isObject(vector)) {
        throw new Error("Conformance vector must be an object.");
    }

    const keys = Object.keys(vector).sort();
    const expectedKeys = ["document", "name", "valid"];

    if (JSON.stringify(keys) !== JSON.stringify(expectedKeys)) {
        throw new Error(
            `Invalid vector fields: ${JSON.stringify(keys)}`
        );
    }

    if (!isNonEmptyString(vector.name)) {
        throw new Error("Conformance vector name must be non-empty.");
    }

    if (typeof vector.valid !== "boolean") {
        throw new Error(
            `${vector.name}: valid must be a boolean.`
        );
    }
}


function main() {
    const vectors = loadVectors();

    if (vectors.length !== 55) {
        throw new Error(
            `Expected 55 conformance vectors, found ${vectors.length}.`
        );
    }

    const names = new Set();

    let passed = 0;
    let failed = 0;

    for (const vector of vectors) {
        verifyVectorShape(vector);

        if (names.has(vector.name)) {
            throw new Error(
                `Duplicate conformance vector name: ${vector.name}`
            );
        }

        names.add(vector.name);

        const actual = validateGraph(vector.document);

        if (actual === vector.valid) {
            console.log(`PASS ${vector.name}`);
            passed += 1;
        } else {
            console.error(
                `FAIL ${vector.name}: ` +
                `expected valid=${vector.valid}, ` +
                `got valid=${actual}`
            );
            failed += 1;
        }
    }

    console.log("");
    console.log(
        `ResourceGraph conformance: ${passed} passed, ${failed} failed`
    );

    if (failed !== 0) {
        process.exitCode = 1;
        return;
    }

    console.log(
        "SUCCESS: JavaScript agrees with all portable conformance vectors."
    );
}


main();