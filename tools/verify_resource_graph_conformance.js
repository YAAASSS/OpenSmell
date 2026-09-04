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
 * Valid vectors may additionally declare:
 *
 *   preserve: true
 *
 * For those vectors, this verifier also performs an independent JavaScript
 * parse/serialize round-trip and requires the complete document to be
 * preserved.
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

const EXPECTED_VECTOR_COUNT = 57;
const EXPECTED_VALID_VECTOR_COUNT = 12;
const EXPECTED_INVALID_VECTOR_COUNT = 45;
const EXPECTED_PRESERVATION_VECTOR_COUNT = 2;


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


function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
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

    if (!hasOwn(value, "value")) {
        return false;
    }

    if (
        hasOwn(value, "unit") &&
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

    if (!hasOwn(value, "data")) {
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

    if (hasOwn(resource, "source")) {
        if (
            resource.source !== null &&
            !validateReference(resource.source)
        ) {
            return false;
        }
    }

    if (hasOwn(resource, "identifiers")) {
        if (!validateIdentifiers(resource.identifiers)) {
            return false;
        }
    }

    if (hasOwn(resource, "conditions")) {
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

    if (hasOwn(resource, "identifiers")) {
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

    if (!hasOwn(resource, "stimulus")) {
        return false;
    }

    if (!validateReference(resource.stimulus)) {
        return false;
    }

    if (hasOwn(resource, "target")) {
        if (
            resource.target !== null &&
            !validateReference(resource.target)
        ) {
            return false;
        }
    }

    if (hasOwn(resource, "results")) {
        if (!validateResults(resource.results)) {
            return false;
        }
    }

    if (hasOwn(resource, "context")) {
        if (!isObject(resource.context)) {
            return false;
        }
    }

    if (hasOwn(resource, "identifiers")) {
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

    if (!hasOwn(resource, "type")) {
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

    if (!hasOwn(document, "resources")) {
        return false;
    }

    if (!Array.isArray(document.resources)) {
        return false;
    }

    return document.resources.every(validateResource);
}


/*
 * JSON-compatible deep clone.
 *
 * This deliberately preserves members that the experimental JavaScript
 * implementation does not understand. That behavior is what the
 * preservation vectors are intended to verify.
 */
function cloneJsonValue(value) {
    if (
        value === null ||
        typeof value === "string" ||
        typeof value === "boolean" ||
        typeof value === "number"
    ) {
        return value;
    }

    if (Array.isArray(value)) {
        return value.map(cloneJsonValue);
    }

    if (isObject(value)) {
        const result = {};

        for (const [key, nestedValue] of Object.entries(value)) {
            result[key] = cloneJsonValue(nestedValue);
        }

        return result;
    }

    throw new Error(
        `Unsupported non-JSON value: ${String(value)}`
    );
}


/*
 * Minimal independent JavaScript ResourceGraph parse/serialize path.
 *
 * It is intentionally separate from the Python implementation.
 * Unknown JSON members are retained rather than discarded.
 */
function parseGraph(document) {
    if (!validateGraph(document)) {
        throw new Error(
            "Cannot parse invalid ResourceGraph document."
        );
    }

    return cloneJsonValue(document);
}


function serializeGraph(graph) {
    if (!validateGraph(graph)) {
        throw new Error(
            "Cannot serialize invalid ResourceGraph document."
        );
    }

    return cloneJsonValue(graph);
}


/*
 * Compare JSON-compatible values semantically.
 *
 * Object member ordering is irrelevant. Array ordering remains significant.
 */
function jsonDeepEqual(left, right) {
    if (left === right) {
        return true;
    }

    if (Array.isArray(left) || Array.isArray(right)) {
        if (!Array.isArray(left) || !Array.isArray(right)) {
            return false;
        }

        if (left.length !== right.length) {
            return false;
        }

        for (
            let index = 0;
            index < left.length;
            index += 1
        ) {
            if (!jsonDeepEqual(left[index], right[index])) {
                return false;
            }
        }

        return true;
    }

    if (isObject(left) || isObject(right)) {
        if (!isObject(left) || !isObject(right)) {
            return false;
        }

        const leftKeys = Object.keys(left);
        const rightKeys = Object.keys(right);

        if (leftKeys.length !== rightKeys.length) {
            return false;
        }

        for (const key of leftKeys) {
            if (!hasOwn(right, key)) {
                return false;
            }

            if (!jsonDeepEqual(left[key], right[key])) {
                return false;
            }
        }

        return true;
    }

    return false;
}


function loadVectors() {
    const text = fs.readFileSync(
        VECTORS_PATH,
        "utf8"
    );

    const document = JSON.parse(text);

    if (!isObject(document)) {
        throw new Error(
            "Conformance vector file must contain an object."
        );
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
        throw new Error(
            "Conformance vector file must contain vectors[]."
        );
    }

    return document.vectors;
}


function verifyVectorShape(vector) {
    if (!isObject(vector)) {
        throw new Error(
            "Conformance vector must be an object."
        );
    }

    const allowedKeys = new Set([
        "document",
        "name",
        "preserve",
        "valid",
    ]);

    const requiredKeys = [
        "document",
        "name",
        "valid",
    ];

    for (const key of Object.keys(vector)) {
        if (!allowedKeys.has(key)) {
            throw new Error(
                `${String(vector.name)}: ` +
                `invalid vector field ${key}.`
            );
        }
    }

    for (const key of requiredKeys) {
        if (!hasOwn(vector, key)) {
            throw new Error(
                `${String(vector.name)}: ` +
                `missing vector field ${key}.`
            );
        }
    }

    if (!isNonEmptyString(vector.name)) {
        throw new Error(
            "Conformance vector name must be non-empty."
        );
    }

    if (typeof vector.valid !== "boolean") {
        throw new Error(
            `${vector.name}: valid must be a boolean.`
        );
    }

    if (
        hasOwn(vector, "preserve") &&
        typeof vector.preserve !== "boolean"
    ) {
        throw new Error(
            `${vector.name}: preserve must be a boolean.`
        );
    }

    if (
        vector.preserve === true &&
        vector.valid !== true
    ) {
        throw new Error(
            `${vector.name}: ` +
            "preserve=true requires valid=true."
        );
    }
}


function verifyPreservation(vector) {
    const parsed = parseGraph(vector.document);
    const serialized = serializeGraph(parsed);

    return jsonDeepEqual(
        serialized,
        vector.document
    );
}


function main() {
    const vectors = loadVectors();

    if (vectors.length !== EXPECTED_VECTOR_COUNT) {
        throw new Error(
            `Expected ${EXPECTED_VECTOR_COUNT} ` +
            `conformance vectors, found ${vectors.length}.`
        );
    }

    const names = new Set();

    let validCount = 0;
    let invalidCount = 0;
    let preservationCount = 0;

    let validationPassed = 0;
    let preservationPassed = 0;

    let failed = 0;


    for (const vector of vectors) {
        verifyVectorShape(vector);

        if (names.has(vector.name)) {
            throw new Error(
                `Duplicate conformance vector name: ` +
                `${vector.name}`
            );
        }

        names.add(vector.name);


        if (vector.valid === true) {
            validCount += 1;
        } else {
            invalidCount += 1;
        }


        if (vector.preserve === true) {
            preservationCount += 1;
        }


        const actual = validateGraph(
            vector.document
        );


        if (actual === vector.valid) {
            console.log(
                `PASS validation ${vector.name}`
            );

            validationPassed += 1;
        } else {
            console.error(
                `FAIL validation ${vector.name}: ` +
                `expected valid=${vector.valid}, ` +
                `got valid=${actual}`
            );

            failed += 1;

            /*
             * Do not attempt a preservation round-trip
             * if structural validation already failed.
             */
            continue;
        }


        if (vector.preserve === true) {
            if (verifyPreservation(vector)) {
                console.log(
                    `PASS preservation ${vector.name}`
                );

                preservationPassed += 1;
            } else {
                console.error(
                    `FAIL preservation ${vector.name}: ` +
                    "JavaScript round-trip changed the document"
                );

                failed += 1;
            }
        }
    }


    if (
        validCount !==
        EXPECTED_VALID_VECTOR_COUNT
    ) {
        throw new Error(
            `Expected ${EXPECTED_VALID_VECTOR_COUNT} ` +
            `valid vectors, found ${validCount}.`
        );
    }


    if (
        invalidCount !==
        EXPECTED_INVALID_VECTOR_COUNT
    ) {
        throw new Error(
            `Expected ${EXPECTED_INVALID_VECTOR_COUNT} ` +
            `invalid vectors, found ${invalidCount}.`
        );
    }


    if (
        preservationCount !==
        EXPECTED_PRESERVATION_VECTOR_COUNT
    ) {
        throw new Error(
            `Expected ${EXPECTED_PRESERVATION_VECTOR_COUNT} ` +
            `preservation vectors, ` +
            `found ${preservationCount}.`
        );
    }


    console.log("");

    console.log(
        "ResourceGraph validation conformance: " +
        `${validationPassed} passed, ` +
        `${EXPECTED_VECTOR_COUNT - validationPassed} failed`
    );

    console.log(
        "ResourceGraph preservation conformance: " +
        `${preservationPassed} passed, ` +
        `${preservationCount - preservationPassed} failed`
    );


    if (failed !== 0) {
        process.exitCode = 1;
        return;
    }


    console.log(
        "SUCCESS: JavaScript agrees with all portable " +
        "conformance vectors and preserves all " +
        "preservation vectors."
    );
}


main();