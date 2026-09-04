"use strict";

/**
 * Independent JavaScript verifier for the portable RFC-0010
 * Annotation 0.1 conformance vectors.
 *
 * This verifier intentionally does not depend on the Python
 * implementation or on the experimental JSON Schema.
 *
 * Its purpose is to demonstrate that the language-independent
 * conformance vectors describe a contract that can be implemented
 * independently in another language.
 */

const fs = require("fs");
const path = require("path");


const ROOT = path.resolve(__dirname, "..");

const VECTOR_PATH = path.join(
    ROOT,
    "examples",
    "annotation_conformance_vectors.json"
);

const EXPECTED_FORMAT =
    "org.opensmell.experimental.annotation-conformance";

const EXPECTED_VERSION = "0.1";

const ANNOTATION_RESOURCE_TYPE =
    "org.opensmell.annotation";

const ANNOTATION_RESOURCE_TYPE_VERSION =
    "0.1";

const EXPECTED_VECTOR_COUNT = 44;
const EXPECTED_VALID_COUNT = 12;
const EXPECTED_INVALID_COUNT = 32;
const EXPECTED_PRESERVATION_COUNT = 12;


function loadJson(filePath) {
    return JSON.parse(
        fs.readFileSync(
            filePath,
            "utf8"
        )
    );
}


function isObject(value) {
    return (
        typeof value === "object"
        && value !== null
        && !Array.isArray(value)
    );
}


function isNonEmptyString(value) {
    return (
        typeof value === "string"
        && value.length > 0
    );
}


function isValidReference(value) {
    if (!isObject(value)) {
        return false;
    }

    return isNonEmptyString(
        value.resource_id
    );
}


function isValidScheme(value) {
    if (!isObject(value)) {
        return false;
    }

    if (!isNonEmptyString(value.id)) {
        return false;
    }

    if (!isNonEmptyString(value.version)) {
        return false;
    }

    return true;
}


function isValidAnnotation(resource) {
    if (!isObject(resource)) {
        return false;
    }

    if (
        resource.type
        !== ANNOTATION_RESOURCE_TYPE
    ) {
        return false;
    }

    if (
        resource.type_version
        !== ANNOTATION_RESOURCE_TYPE_VERSION
    ) {
        return false;
    }

    if (!isNonEmptyString(resource.id)) {
        return false;
    }

    if (!isValidReference(resource.subject)) {
        return false;
    }

    if (!isValidScheme(resource.scheme)) {
        return false;
    }

    if (!isObject(resource.data)) {
        return false;
    }

    return true;
}


function deepCloneJson(value) {
    return JSON.parse(
        JSON.stringify(value)
    );
}


/**
 * Simulate an independent parse/serialize transport round trip.
 *
 * Known fields are reconstructed explicitly.
 * Unknown extension fields are copied back so that preservation
 * behavior is tested independently from the Python serializer.
 */
function roundTripAnnotation(resource) {
    if (!isValidAnnotation(resource)) {
        throw new Error(
            "Cannot round-trip invalid Annotation resource."
        );
    }

    const recovered = {};

    for (const [key, value] of Object.entries(resource)) {
        if (
            key !== "type"
            && key !== "type_version"
            && key !== "id"
            && key !== "subject"
            && key !== "scheme"
            && key !== "data"
        ) {
            recovered[key] = deepCloneJson(value);
        }
    }

    recovered.type =
        ANNOTATION_RESOURCE_TYPE;

    recovered.type_version =
        ANNOTATION_RESOURCE_TYPE_VERSION;

    recovered.id =
        resource.id;

    recovered.subject = {};

    for (
        const [key, value]
        of Object.entries(resource.subject)
    ) {
        if (key !== "resource_id") {
            recovered.subject[key] =
                deepCloneJson(value);
        }
    }

    recovered.subject.resource_id =
        resource.subject.resource_id;

    recovered.scheme = {};

    for (
        const [key, value]
        of Object.entries(resource.scheme)
    ) {
        if (
            key !== "id"
            && key !== "version"
        ) {
            recovered.scheme[key] =
                deepCloneJson(value);
        }
    }

    recovered.scheme.id =
        resource.scheme.id;

    recovered.scheme.version =
        resource.scheme.version;

    recovered.data =
        deepCloneJson(resource.data);

    return recovered;
}


function jsonEquivalent(left, right) {
    if (left === right) {
        return true;
    }

    if (
        typeof left !== typeof right
    ) {
        return false;
    }

    if (
        left === null
        || right === null
    ) {
        return false;
    }

    if (
        Array.isArray(left)
        || Array.isArray(right)
    ) {
        if (
            !Array.isArray(left)
            || !Array.isArray(right)
        ) {
            return false;
        }

        if (
            left.length
            !== right.length
        ) {
            return false;
        }

        for (
            let index = 0;
            index < left.length;
            index += 1
        ) {
            if (
                !jsonEquivalent(
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
        typeof left === "object"
    ) {
        const leftKeys =
            Object.keys(left).sort();

        const rightKeys =
            Object.keys(right).sort();

        if (
            leftKeys.length
            !== rightKeys.length
        ) {
            return false;
        }

        for (
            let index = 0;
            index < leftKeys.length;
            index += 1
        ) {
            if (
                leftKeys[index]
                !== rightKeys[index]
            ) {
                return false;
            }
        }

        for (const key of leftKeys) {
            if (
                !jsonEquivalent(
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


function fail(message) {
    console.error(
        `FAIL: ${message}`
    );

    process.exitCode = 1;
}


function main() {
    const document =
        loadJson(VECTOR_PATH);

    if (!isObject(document)) {
        throw new Error(
            "Conformance document must be an object."
        );
    }

    if (
        document.format
        !== EXPECTED_FORMAT
    ) {
        throw new Error(
            `Unexpected conformance format: ${document.format}`
        );
    }

    if (
        document.version
        !== EXPECTED_VERSION
    ) {
        throw new Error(
            `Unexpected conformance version: ${document.version}`
        );
    }

    if (!Array.isArray(document.vectors)) {
        throw new Error(
            "Conformance document must contain a vectors array."
        );
    }

    const vectors =
        document.vectors;

    if (
        vectors.length
        !== EXPECTED_VECTOR_COUNT
    ) {
        throw new Error(
            `Expected ${EXPECTED_VECTOR_COUNT} vectors, found ${vectors.length}.`
        );
    }

    const names =
        new Set();

    let validCount = 0;
    let invalidCount = 0;
    let validationPassed = 0;
    let validationFailed = 0;

    let preservationCount = 0;
    let preservationPassed = 0;
    let preservationFailed = 0;

    for (const vector of vectors) {
        if (!isObject(vector)) {
            fail(
                "Vector is not an object."
            );
            validationFailed += 1;
            continue;
        }

        const name =
            vector.name;

        if (!isNonEmptyString(name)) {
            fail(
                "Vector has an invalid name."
            );
            validationFailed += 1;
            continue;
        }

        if (names.has(name)) {
            fail(
                `${name}: duplicate vector name`
            );
            validationFailed += 1;
            continue;
        }

        names.add(name);

        if (
            typeof vector.valid
            !== "boolean"
        ) {
            fail(
                `${name}: valid must be boolean`
            );
            validationFailed += 1;
            continue;
        }

        if (
            !Object.prototype.hasOwnProperty.call(
                vector,
                "resource"
            )
        ) {
            fail(
                `${name}: resource is missing`
            );
            validationFailed += 1;
            continue;
        }

        if (vector.valid) {
            validCount += 1;
        } else {
            invalidCount += 1;
        }

        const actual =
            isValidAnnotation(
                vector.resource
            );

        if (
            actual
            === vector.valid
        ) {
            validationPassed += 1;
        } else {
            validationFailed += 1;

            fail(
                `${name}: expected valid=${vector.valid}, got ${actual}`
            );
        }

        if (
            Object.prototype.hasOwnProperty.call(
                vector,
                "preserve"
            )
        ) {
            if (
                typeof vector.preserve
                !== "boolean"
            ) {
                preservationFailed += 1;

                fail(
                    `${name}: preserve must be boolean`
                );

                continue;
            }

            if (
                vector.preserve
                && !vector.valid
            ) {
                preservationFailed += 1;

                fail(
                    `${name}: preserve=true requires valid=true`
                );

                continue;
            }
        }

        if (vector.preserve === true) {
            preservationCount += 1;

            try {
                const recovered =
                    roundTripAnnotation(
                        vector.resource
                    );

                if (
                    jsonEquivalent(
                        recovered,
                        vector.resource
                    )
                ) {
                    preservationPassed += 1;
                } else {
                    preservationFailed += 1;

                    fail(
                        `${name}: round trip did not preserve the resource`
                    );
                }
            } catch (error) {
                preservationFailed += 1;

                fail(
                    `${name}: preservation threw ${error.message}`
                );
            }
        }
    }

    if (
        validCount
        !== EXPECTED_VALID_COUNT
    ) {
        fail(
            `Expected ${EXPECTED_VALID_COUNT} valid vectors, found ${validCount}.`
        );
    }

    if (
        invalidCount
        !== EXPECTED_INVALID_COUNT
    ) {
        fail(
            `Expected ${EXPECTED_INVALID_COUNT} invalid vectors, found ${invalidCount}.`
        );
    }

    if (
        preservationCount
        !== EXPECTED_PRESERVATION_COUNT
    ) {
        fail(
            `Expected ${EXPECTED_PRESERVATION_COUNT} preservation vectors, found ${preservationCount}.`
        );
    }

    console.log(
        `Annotation validation conformance: ${validationPassed} passed, ${validationFailed} failed`
    );

    console.log(
        `Annotation preservation conformance: ${preservationPassed} passed, ${preservationFailed} failed`
    );

    console.log(
        `Vectors: ${vectors.length} total, ${validCount} valid, ${invalidCount} invalid`
    );

    if (
        validationFailed === 0
        && preservationFailed === 0
        && process.exitCode !== 1
    ) {
        console.log(
            "SUCCESS: independent JavaScript Annotation verifier agrees with the portable RFC-0010 conformance vectors."
        );
    }
}


main();