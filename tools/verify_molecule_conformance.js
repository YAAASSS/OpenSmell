"use strict";

/*
 * OpenSmell experimental Molecule 0.1 portable conformance verifier.
 *
 * This verifier intentionally does not depend on the Python implementation.
 *
 * It consumes:
 *
 *   examples/molecule_conformance_vectors.json
 *
 * and independently checks the structural and resource-specific rules defined
 * by the experimental Molecule 0.1 contract in RFC-0009.
 *
 * Valid vectors may additionally declare:
 *
 *   preserve: true
 *
 * For those vectors, this verifier performs an independent JavaScript
 * parse/serialize round-trip and requires the complete resource to be
 * preserved.
 *
 * Preservation is deliberately separate from validity. A valid resource may
 * have a serialized form that an implementation normalizes. Such a vector
 * should not declare preserve=true.
 *
 * This verifier checks Molecule 0.1 conformance, not generic RFC-0008
 * transport validity.
 *
 * In particular, an unknown future Molecule version may be invalid for this
 * specific 0.1 contract while remaining transportable as an RFC-0008
 * GenericResource.
 */

const fs = require("fs");
const path = require("path");


const ROOT = path.resolve(
    __dirname,
    ".."
);

const VECTORS_PATH = path.join(
    ROOT,
    "examples",
    "molecule_conformance_vectors.json"
);

const VECTOR_FORMAT =
    "org.opensmell.experimental.molecule-conformance";

const VECTOR_VERSION = "0.1";

const MOLECULE_TYPE =
    "org.opensmell.molecule";

const MOLECULE_VERSION = "0.1";

const EXPECTED_VECTOR_COUNT = 37;
const EXPECTED_VALID_VECTOR_COUNT = 10;
const EXPECTED_INVALID_VECTOR_COUNT = 27;
const EXPECTED_PRESERVATION_VECTOR_COUNT = 9;


function isObject(value) {
    return (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value)
    );
}


function isNonEmptyString(value) {
    return (
        typeof value === "string" &&
        value.length > 0
    );
}


function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(
        value,
        key
    );
}


function validateExternalIdentifier(identifier) {
    if (!isObject(identifier)) {
        return false;
    }

    if (!hasOwn(identifier, "scheme")) {
        return false;
    }

    if (!isNonEmptyString(identifier.scheme)) {
        return false;
    }

    if (!hasOwn(identifier, "value")) {
        return false;
    }

    if (!isNonEmptyString(identifier.value)) {
        return false;
    }

    return true;
}


/*
 * Molecule 0.1 validation.
 *
 * This deliberately does not validate chemical SMILES syntax.
 *
 * The Molecule transport contract treats SMILES as an opaque non-empty
 * string. Chemical parsing, canonicalization and equivalence are outside the
 * scope of RFC-0009.
 */
function validateMolecule(resource) {
    if (!isObject(resource)) {
        return false;
    }

    if (
        resource.type !==
        MOLECULE_TYPE
    ) {
        return false;
    }

    if (
        resource.type_version !==
        MOLECULE_VERSION
    ) {
        return false;
    }

    if (!hasOwn(resource, "id")) {
        return false;
    }

    if (!isNonEmptyString(resource.id)) {
        return false;
    }

    const hasSmiles =
        hasOwn(resource, "smiles");

    if (
        hasSmiles &&
        !isNonEmptyString(resource.smiles)
    ) {
        return false;
    }

    const hasIdentifiers =
        hasOwn(resource, "identifiers");

    if (hasIdentifiers) {
        if (!Array.isArray(resource.identifiers)) {
            return false;
        }

        if (
            !resource.identifiers.every(
                validateExternalIdentifier
            )
        ) {
            return false;
        }
    }

    const hasChemicalIdentity =
        hasSmiles ||
        (
            hasIdentifiers &&
            resource.identifiers.length > 0
        );

    if (!hasChemicalIdentity) {
        return false;
    }

    return true;
}


/*
 * JSON-compatible deep clone.
 *
 * Unknown extension members are intentionally preserved.
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
        return value.map(
            cloneJsonValue
        );
    }

    if (isObject(value)) {
        const result = {};

        for (
            const [key, nestedValue]
            of Object.entries(value)
        ) {
            result[key] =
                cloneJsonValue(
                    nestedValue
                );
        }

        return result;
    }

    throw new Error(
        `Unsupported non-JSON value: ${String(value)}`
    );
}


/*
 * Minimal independent Molecule parse/serialize path.
 *
 * This is deliberately not a JavaScript implementation of the Python class.
 * It only implements the portable contract needed for conformance and
 * preservation testing.
 */
function parseMolecule(resource) {
    if (!validateMolecule(resource)) {
        throw new Error(
            "Cannot parse invalid Molecule 0.1 resource."
        );
    }

    return cloneJsonValue(
        resource
    );
}


function serializeMolecule(molecule) {
    if (!validateMolecule(molecule)) {
        throw new Error(
            "Cannot serialize invalid Molecule 0.1 resource."
        );
    }

    return cloneJsonValue(
        molecule
    );
}


/*
 * Compare JSON-compatible values semantically.
 *
 * Object member ordering is irrelevant.
 * Array ordering remains significant.
 */
function jsonDeepEqual(left, right) {
    if (left === right) {
        return true;
    }

    if (
        Array.isArray(left) ||
        Array.isArray(right)
    ) {
        if (
            !Array.isArray(left) ||
            !Array.isArray(right)
        ) {
            return false;
        }

        if (
            left.length !==
            right.length
        ) {
            return false;
        }

        for (
            let index = 0;
            index < left.length;
            index += 1
        ) {
            if (
                !jsonDeepEqual(
                    left[index],
                    right[index]
                )
            ) {
                return false;
            }
        }

        return true;
    }

    if (
        isObject(left) ||
        isObject(right)
    ) {
        if (
            !isObject(left) ||
            !isObject(right)
        ) {
            return false;
        }

        const leftKeys =
            Object.keys(left);

        const rightKeys =
            Object.keys(right);

        if (
            leftKeys.length !==
            rightKeys.length
        ) {
            return false;
        }

        for (const key of leftKeys) {
            if (!hasOwn(right, key)) {
                return false;
            }

            if (
                !jsonDeepEqual(
                    left[key],
                    right[key]
                )
            ) {
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

    const document =
        JSON.parse(text);

    if (!isObject(document)) {
        throw new Error(
            "Conformance vector file must contain an object."
        );
    }

    if (
        document.format !==
        VECTOR_FORMAT
    ) {
        throw new Error(
            `Unexpected vector format: ${String(document.format)}`
        );
    }

    if (
        document.version !==
        VECTOR_VERSION
    ) {
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
        "name",
        "valid",
        "resource",
        "preserve",
    ]);

    const requiredKeys = [
        "name",
        "valid",
        "resource",
    ];

    for (
        const key
        of Object.keys(vector)
    ) {
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

    if (
        typeof vector.valid !==
        "boolean"
    ) {
        throw new Error(
            `${vector.name}: valid must be a boolean.`
        );
    }

    if (
        hasOwn(vector, "preserve") &&
        typeof vector.preserve !==
        "boolean"
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
    const parsed =
        parseMolecule(
            vector.resource
        );

    const serialized =
        serializeMolecule(
            parsed
        );

    return jsonDeepEqual(
        serialized,
        vector.resource
    );
}


function main() {
    const vectors =
        loadVectors();

    if (
        vectors.length !==
        EXPECTED_VECTOR_COUNT
    ) {
        throw new Error(
            `Expected ${EXPECTED_VECTOR_COUNT} ` +
            `conformance vectors, found ${vectors.length}.`
        );
    }

    const names =
        new Set();

    let validCount = 0;
    let invalidCount = 0;
    let preservationCount = 0;

    let validationPassed = 0;
    let preservationPassed = 0;

    let failed = 0;

    for (const vector of vectors) {
        verifyVectorShape(
            vector
        );

        if (names.has(vector.name)) {
            throw new Error(
                "Duplicate conformance vector name: " +
                `${vector.name}`
            );
        }

        names.add(
            vector.name
        );

        if (vector.valid === true) {
            validCount += 1;
        } else {
            invalidCount += 1;
        }

        if (
            vector.preserve === true
        ) {
            preservationCount += 1;
        }

        const actual =
            validateMolecule(
                vector.resource
            );

        if (
            actual ===
            vector.valid
        ) {
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

            continue;
        }

        if (
            vector.preserve === true
        ) {
            if (
                verifyPreservation(
                    vector
                )
            ) {
                console.log(
                    `PASS preservation ${vector.name}`
                );

                preservationPassed += 1;
            } else {
                console.error(
                    `FAIL preservation ${vector.name}: ` +
                    "JavaScript round-trip changed the resource"
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
            "preservation vectors, " +
            `found ${preservationCount}.`
        );
    }

    console.log("");

    console.log(
        "Molecule 0.1 validation conformance: " +
        `${validationPassed} passed, ` +
        `${EXPECTED_VECTOR_COUNT - validationPassed} failed`
    );

    console.log(
        "Molecule 0.1 preservation conformance: " +
        `${preservationPassed} passed, ` +
        `${preservationCount - preservationPassed} failed`
    );

    if (failed !== 0) {
        process.exitCode = 1;
        return;
    }

    console.log(
        "SUCCESS: JavaScript agrees with all portable " +
        "Molecule 0.1 conformance vectors and preserves all " +
        "preservation vectors."
    );
}


main();