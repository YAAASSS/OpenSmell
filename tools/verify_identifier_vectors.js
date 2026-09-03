"use strict";

/*
 * OpenSmell RFC-0006 cross-language interoperability experiment.
 *
 * Independent JavaScript implementation of the experimental deterministic
 * Resource ID algorithm.
 *
 * No external dependencies are required.
 *
 * This implementation deliberately does NOT copy Python's json.dumps().
 * Instead, it implements the currently tested OpenSmell identity structure
 * explicitly so that Python is not part of the protocol definition.
 *
 * Experimental only. Not normative OpenSmell 0.1.
 */

const crypto = require("crypto");


const OPENSMELL_EXPERIMENTAL_NAMESPACE =
    "7f0f1d72-83c7-4f57-a1f6-4bc43bb26e58";


function uuidToBytes(uuid) {
    const hex = uuid.replace(/-/g, "");

    if (!/^[0-9a-f]{32}$/.test(hex)) {
        throw new Error(
            "namespace must use canonical lowercase UUID representation"
        );
    }

    return Buffer.from(hex, "hex");
}


function bytesToUuid(bytes) {
    const hex = Buffer.from(bytes).toString("hex");

    return [
        hex.slice(0, 8),
        hex.slice(8, 12),
        hex.slice(12, 16),
        hex.slice(16, 20),
        hex.slice(20, 32),
    ].join("-");
}


function uuid5(namespaceUuid, name) {
    if (typeof name !== "string" || name.length === 0) {
        throw new Error("name must be a non-empty string");
    }

    const namespaceBytes = uuidToBytes(namespaceUuid);
    const nameBytes = Buffer.from(name, "utf8");

    const hash = crypto
        .createHash("sha1")
        .update(namespaceBytes)
        .update(nameBytes)
        .digest();

    const bytes = Buffer.from(hash.subarray(0, 16));

    // RFC 9562 UUID version field: version 5.
    bytes[6] = (bytes[6] & 0x0f) | 0x50;

    // RFC 9562 variant field: 10xx....
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    return bytesToUuid(bytes);
}


function validateNonEmptyString(value, fieldName) {
    if (typeof value !== "string" || value.length === 0) {
        throw new Error(
            `${fieldName} must be a non-empty string`
        );
    }
}


function validateSourceIdentity(sourceIdentity) {
    if (typeof sourceIdentity === "string") {
        if (sourceIdentity.length === 0) {
            throw new Error(
                "source identity must be a non-empty string"
            );
        }

        return;
    }

    if (
        sourceIdentity === null ||
        Array.isArray(sourceIdentity) ||
        typeof sourceIdentity !== "object"
    ) {
        throw new Error(
            "source identity must be a non-empty string " +
            "or an object of non-empty string keys and values"
        );
    }

    const keys = Object.keys(sourceIdentity);

    if (keys.length === 0) {
        throw new Error(
            "structured source identity must not be empty"
        );
    }

    for (const key of keys) {
        validateNonEmptyString(
            key,
            "structured source identity key"
        );

        validateNonEmptyString(
            sourceIdentity[key],
            "structured source identity value"
        );
    }
}


/*
 * JSON string serialization.
 *
 * JSON.stringify() is used only for individual strings.
 *
 * Object ordering is handled explicitly below rather than relying on
 * JavaScript object insertion order.
 */
function jsonString(value) {
    return JSON.stringify(value);
}


function canonicalSourceIdentity(sourceIdentity) {
    validateSourceIdentity(sourceIdentity);

    if (typeof sourceIdentity === "string") {
        return jsonString(sourceIdentity);
    }

    const keys = Object.keys(sourceIdentity).sort();

    const members = keys.map((key) => {
        return (
            jsonString(key) +
            ":" +
            jsonString(sourceIdentity[key])
        );
    });

    return "{" + members.join(",") + "}";
}


function canonicalGenerationName(
    dataset,
    resourceType,
    sourceIdentity
) {
    validateNonEmptyString(
        dataset,
        "dataset"
    );

    validateNonEmptyString(
        resourceType,
        "resource_type"
    );

    const identity =
        canonicalSourceIdentity(sourceIdentity);

    /*
     * Top-level key order is deliberately fixed to match the current
     * experimental canonical ordering:
     *
     * dataset
     * resource_type
     * source_identity
     */
    return (
        "{" +
        '"dataset":' +
        jsonString(dataset) +
        "," +
        '"resource_type":' +
        jsonString(resourceType) +
        "," +
        '"source_identity":' +
        identity +
        "}"
    );
}


function deterministicResourceIdFromSource(
    dataset,
    resourceType,
    sourceIdentity
) {
    const name = canonicalGenerationName(
        dataset,
        resourceType,
        sourceIdentity
    );

    return uuid5(
        OPENSMELL_EXPERIMENTAL_NAMESPACE,
        name
    );
}


const vectors = [
    {
        name: "Burton atomic target",

        dataset: "burton_2022",

        resourceType: "target",

        sourceIdentity: "113L_038",

        canonical:
            '{"dataset":"burton_2022",' +
            '"resource_type":"target",' +
            '"source_identity":"113L_038"}',

        uuid:
            "f485e819-2af5-502a-9489-4554ec11716c",
    },

    {
        name: "Burton composite observation",

        dataset: "burton_2022",

        resourceType: "observation",

        sourceIdentity: {
            stimulus: "1001_3.12e-13",
            target: "111L_001",
        },

        canonical:
            '{"dataset":"burton_2022",' +
            '"resource_type":"observation",' +
            '"source_identity":{' +
            '"stimulus":"1001_3.12e-13",' +
            '"target":"111L_001"' +
            '}}',

        uuid:
            "6136624f-5105-52f1-875e-53a177ef2134",
    },

    {
        name: "Composite delimiter boundary A",

        dataset: "dataset",

        resourceType: "observation",

        sourceIdentity: {
            stimulus: "a|b",
            target: "c",
        },
    },

    {
        name: "Composite delimiter boundary B",

        dataset: "dataset",

        resourceType: "observation",

        sourceIdentity: {
            stimulus: "a",
            target: "b|c",
        },
    },

    {
        name: "Unicode Latin",

        dataset: "dataset",

        resourceType: "target",

        sourceIdentity: "café",
    },

    {
        name: "Unicode CJK",

        dataset: "dataset",

        resourceType: "target",

        sourceIdentity: "咖啡",
    },

    {
        name: "Quote",

        dataset: "dataset",

        resourceType: "target",

        sourceIdentity: 'abc"def',
    },

    {
        name: "Backslash",

        dataset: "dataset",

        resourceType: "target",

        sourceIdentity: "abc\\def",
    },
];


function run() {
    console.log(
        "OpenSmell RFC-0006 Python <-> JavaScript interoperability"
    );

    console.log(
        "=".repeat(72)
    );

    console.log(
        `Namespace: ${OPENSMELL_EXPERIMENTAL_NAMESPACE}`
    );

    console.log();

    let failures = 0;

    const results = [];

    for (const vector of vectors) {
        const canonical =
            canonicalGenerationName(
                vector.dataset,
                vector.resourceType,
                vector.sourceIdentity
            );

        const uuid =
            deterministicResourceIdFromSource(
                vector.dataset,
                vector.resourceType,
                vector.sourceIdentity
            );

        let canonicalOk = true;
        let uuidOk = true;

        if (
            vector.canonical !== undefined &&
            canonical !== vector.canonical
        ) {
            canonicalOk = false;
            failures += 1;
        }

        if (
            vector.uuid !== undefined &&
            uuid !== vector.uuid
        ) {
            uuidOk = false;
            failures += 1;
        }

        results.push({
            ...vector,
            generatedCanonical: canonical,
            generatedUuid: uuid,
        });

        console.log(vector.name);
        console.log("-".repeat(72));

        console.log(
            `Canonical : ${canonical}`
        );

        console.log(
            `UUID      : ${uuid}`
        );

        if (vector.canonical !== undefined) {
            console.log(
                `Canonical vector: ${
                    canonicalOk ? "PASS" : "FAIL"
                }`
            );
        }

        if (vector.uuid !== undefined) {
            console.log(
                `UUID vector     : ${
                    uuidOk ? "PASS" : "FAIL"
                }`
            );
        }

        console.log();
    }


    /*
     * Explicitly verify that delimiter-boundary cases remain distinct.
     */
    const boundaryA = results.find(
        (item) =>
            item.name ===
            "Composite delimiter boundary A"
    );

    const boundaryB = results.find(
        (item) =>
            item.name ===
            "Composite delimiter boundary B"
    );

    const boundariesDistinct =
        boundaryA.generatedCanonical !==
            boundaryB.generatedCanonical &&
        boundaryA.generatedUuid !==
            boundaryB.generatedUuid;

    console.log(
        "Structural boundary test"
    );

    console.log(
        "-".repeat(72)
    );

    console.log(
        "Composite identities remain distinct: " +
        (boundariesDistinct ? "YES" : "NO")
    );

    if (!boundariesDistinct) {
        failures += 1;
    }

    console.log();


    /*
     * Verify object insertion order independence.
     */
    const orderA = {
        stimulus: "1001_3.12e-13",
        target: "111L_001",
    };

    const orderB = {
        target: "111L_001",
        stimulus: "1001_3.12e-13",
    };

    const orderNameA =
        canonicalGenerationName(
            "burton_2022",
            "observation",
            orderA
        );

    const orderNameB =
        canonicalGenerationName(
            "burton_2022",
            "observation",
            orderB
        );

    const orderUuidA =
        deterministicResourceIdFromSource(
            "burton_2022",
            "observation",
            orderA
        );

    const orderUuidB =
        deterministicResourceIdFromSource(
            "burton_2022",
            "observation",
            orderB
        );

    const orderIndependent =
        orderNameA === orderNameB &&
        orderUuidA === orderUuidB;

    console.log(
        "Object ordering test"
    );

    console.log(
        "-".repeat(72)
    );

    console.log(
        "Insertion order does not affect identity: " +
        (orderIndependent ? "YES" : "NO")
    );

    if (!orderIndependent) {
        failures += 1;
    }

    console.log();


    /*
     * UTF-8 visibility test.
     */
    const unicodeName =
        canonicalGenerationName(
            "dataset",
            "target",
            "咖啡"
        );

    const unicodeBytes =
        Buffer.from(
            unicodeName,
            "utf8"
        );

    console.log(
        "UTF-8 test"
    );

    console.log(
        "-".repeat(72)
    );

    console.log(
        `Canonical : ${unicodeName}`
    );

    console.log(
        `UTF-8 hex : ${unicodeBytes.toString("hex")}`
    );

    console.log();


    console.log(
        "Result"
    );

    console.log(
        "=".repeat(72)
    );

    if (failures > 0) {
        console.log(
            `FAILED: ${failures} interoperability check(s) failed.`
        );

        process.exitCode = 1;
        return;
    }

    console.log("SUCCESS");

    console.log();

    console.log(
        "JavaScript independently reproduced the current " +
        "experimental OpenSmell canonical generation and UUIDv5 vectors."
    );
}


run();