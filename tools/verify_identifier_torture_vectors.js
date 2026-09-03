"use strict";

/*
 * OpenSmell RFC-0006 Unicode / JSON escaping interoperability test.
 *
 * Verifies Python-generated vectors using an independent JavaScript
 * implementation.
 *
 * Experimental only.
 */

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");


const NAMESPACE =
    "7f0f1d72-83c7-4f57-a1f6-4bc43bb26e58";


function uuidToBytes(uuid) {
    const hex = uuid.replace(/-/g, "");

    if (!/^[0-9a-f]{32}$/.test(hex)) {
        throw new Error("Invalid namespace UUID");
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


function uuid5(namespace, name) {
    const hash = crypto
        .createHash("sha1")
        .update(uuidToBytes(namespace))
        .update(Buffer.from(name, "utf8"))
        .digest();

    const bytes = Buffer.from(
        hash.subarray(0, 16)
    );

    bytes[6] =
        (bytes[6] & 0x0f) | 0x50;

    bytes[8] =
        (bytes[8] & 0x3f) | 0x80;

    return bytesToUuid(bytes);
}


function jsonString(value) {
    return JSON.stringify(value);
}


function canonicalSourceIdentity(value) {
    if (typeof value === "string") {
        return jsonString(value);
    }

    const keys = Object.keys(value).sort();

    return (
        "{" +
        keys
            .map(
                (key) =>
                    jsonString(key) +
                    ":" +
                    jsonString(value[key])
            )
            .join(",") +
        "}"
    );
}


function canonicalGenerationName(
    dataset,
    resourceType,
    sourceIdentity
) {
    return (
        "{" +
        '"dataset":' +
        jsonString(dataset) +
        "," +
        '"resource_type":' +
        jsonString(resourceType) +
        "," +
        '"source_identity":' +
        canonicalSourceIdentity(
            sourceIdentity
        ) +
        "}"
    );
}


const vectorsPath = path.join(
    __dirname,
    "..",
    "examples",
    "identifier_torture_vectors.json"
);

const vectors = JSON.parse(
    fs.readFileSync(
        vectorsPath,
        "utf8"
    )
);


console.log(
    "OpenSmell RFC-0006 Python <-> JavaScript torture test"
);

console.log(
    "=".repeat(72)
);

let failures = 0;


for (const vector of vectors) {
    const canonical =
        canonicalGenerationName(
            vector.dataset,
            vector.resource_type,
            vector.source_identity
        );

    const utf8Hex =
        Buffer.from(
            canonical,
            "utf8"
        ).toString("hex");

    const uuid =
        uuid5(
            NAMESPACE,
            canonical
        );

    const canonicalPass =
        canonical === vector.canonical;

    const utf8Pass =
        utf8Hex === vector.utf8_hex;

    const uuidPass =
        uuid === vector.uuid;

    console.log();
    console.log(vector.name);
    console.log("-".repeat(72));

    console.log(
        "Canonical : " +
        (canonicalPass ? "PASS" : "FAIL")
    );

    console.log(
        "UTF-8    : " +
        (utf8Pass ? "PASS" : "FAIL")
    );

    console.log(
        "UUID     : " +
        (uuidPass ? "PASS" : "FAIL")
    );

    if (
        !canonicalPass ||
        !utf8Pass ||
        !uuidPass
    ) {
        failures += 1;

        console.log();
        console.log(
            "Python canonical:"
        );

        console.log(
            JSON.stringify(vector.canonical)
        );

        console.log(
            "JavaScript canonical:"
        );

        console.log(
            JSON.stringify(canonical)
        );

        console.log(
            "Python UTF-8:"
        );

        console.log(
            vector.utf8_hex
        );

        console.log(
            "JavaScript UTF-8:"
        );

        console.log(
            utf8Hex
        );

        console.log(
            "Python UUID:"
        );

        console.log(
            vector.uuid
        );

        console.log(
            "JavaScript UUID:"
        );

        console.log(
            uuid
        );
    }
}


console.log();
console.log(
    "Unicode normalization distinction"
);

console.log(
    "-".repeat(72)
);

const nfc = vectors.find(
    (vector) =>
        vector.name === "Latin NFC"
);

const decomposed = vectors.find(
    (vector) =>
        vector.name ===
        "Latin decomposed NFD-like"
);

const normalizationDistinct =
    nfc.uuid !== decomposed.uuid;

console.log(
    "NFC and decomposed source identities remain distinct: " +
    (
        normalizationDistinct
            ? "YES"
            : "NO"
    )
);

if (!normalizationDistinct) {
    failures += 1;
}


console.log();
console.log("Result");
console.log(
    "=".repeat(72)
);

if (failures > 0) {
    console.log(
        `FAILED: ${failures} vector(s) failed.`
    );

    process.exitCode = 1;
} else {
    console.log("SUCCESS");
    console.log();

    console.log(
        "Python and JavaScript produced identical canonical text, " +
        "UTF-8 octets, and UUIDv5 Resource IDs for every torture vector."
    );
}