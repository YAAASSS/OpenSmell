"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const INPUT_PATH = path.join(
    ROOT,
    "examples",
    "generic_resource_graph_interop_vectors.json"
);
const OUTPUT_PATH = path.join(
    ROOT,
    "examples",
    "generic_resource_graph_interop_vectors_js.json"
);

const VECTOR_SET =
    "org.opensmell.experimental.generic-resource-graph.interop-vectors";
const VECTOR_VERSION = "0.1";
const GRAPH_FORMAT =
    "org.opensmell.experimental.generic-resource-graph";
const GRAPH_VERSION = "0.1";
const INTEROP_RESOURCE_TYPE = "org.example.interop.resource";
const KNOWN_VERSIONS = new Set(["0.1", "0.2"]);

function isObject(value) {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function nonEmptyString(value) {
    return typeof value === "string" && value.length > 0;
}

function clone(value) {
    if (
        value === null ||
        typeof value === "string" ||
        typeof value === "boolean" ||
        typeof value === "number"
    ) {
        return value;
    }

    if (Array.isArray(value)) {
        return value.map(clone);
    }

    if (isObject(value)) {
        const result = {};

        for (const [key, item] of Object.entries(value)) {
            result[key] = clone(item);
        }

        return result;
    }

    throw new Error(
        `Unsupported JSON value: ${String(value)}`
    );
}

function validateResource(resource) {
    return (
        isObject(resource) &&
        nonEmptyString(resource.type) &&
        nonEmptyString(resource.id) &&
        (
            !hasOwn(resource, "type_version") ||
            nonEmptyString(resource.type_version)
        )
    );
}

function validateGraph(graph) {
    return (
        isObject(graph) &&
        graph.format === GRAPH_FORMAT &&
        graph.version === GRAPH_VERSION &&
        Array.isArray(graph.resources) &&
        graph.resources.every(validateResource)
    );
}

function classifyResource(resource) {
    if (
        resource.type === "stimulus" &&
        !hasOwn(resource, "type_version")
    ) {
        return "legacy";
    }

    if (
        resource.type === INTEROP_RESOURCE_TYPE &&
        KNOWN_VERSIONS.has(resource.type_version)
    ) {
        return `known:${resource.type_version}`;
    }

    return "generic";
}

function roundTripGraph(graph) {
    if (!validateGraph(graph)) {
        throw new Error(
            "Invalid Generic ResourceGraph golden vector."
        );
    }

    const result = clone(graph);

    for (const resource of result.resources) {
        classifyResource(resource);
    }

    return result;
}

function deepEqual(left, right) {
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

        if (left.length !== right.length) {
            return false;
        }

        return left.every(
            (item, index) =>
                deepEqual(item, right[index])
        );
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

        const leftKeys = Object.keys(left);
        const rightKeys = Object.keys(right);

        if (leftKeys.length !== rightKeys.length) {
            return false;
        }

        return leftKeys.every(
            (key) =>
                hasOwn(right, key) &&
                deepEqual(left[key], right[key])
        );
    }

    return false;
}

function main() {
    const document = JSON.parse(
        fs.readFileSync(
            INPUT_PATH,
            "utf8"
        )
    );

    if (!isObject(document)) {
        throw new Error(
            "Vector document must be an object."
        );
    }

    if (document.vector_set !== VECTOR_SET) {
        throw new Error(
            "Unexpected vector_set."
        );
    }

    if (document.version !== VECTOR_VERSION) {
        throw new Error(
            "Unexpected vector version."
        );
    }

    if (
        document.resource_graph_format !==
        GRAPH_FORMAT
    ) {
        throw new Error(
            "Unexpected graph format."
        );
    }

    if (
        document.resource_graph_version !==
        GRAPH_VERSION
    ) {
        throw new Error(
            "Unexpected graph version."
        );
    }

    if (!Array.isArray(document.vectors)) {
        throw new Error(
            "vectors must be an array."
        );
    }

    const output = clone(document);

    let passed = 0;

    for (
        let index = 0;
        index < document.vectors.length;
        index += 1
    ) {
        const vector =
            document.vectors[index];

        if (
            !isObject(vector) ||
            !nonEmptyString(vector.name) ||
            !isObject(vector.graph)
        ) {
            throw new Error(
                `Invalid vector at index ${index}.`
            );
        }

        const roundTripped =
            roundTripGraph(vector.graph);

        if (
            !deepEqual(
                roundTripped,
                vector.graph
            )
        ) {
            throw new Error(
                `${vector.name}: ` +
                "JavaScript round-trip changed graph."
            );
        }

        output.vectors[index].graph =
            roundTripped;

        console.log(
            `PASS ${vector.name}`
        );

        passed += 1;
    }

    fs.writeFileSync(
        OUTPUT_PATH,
        JSON.stringify(
            output,
            null,
            2
        ) + "\n",
        "utf8"
    );

    console.log("");

    console.log(
        `SUCCESS: ${passed} Generic ResourceGraph ` +
        "interoperability vectors " +
        "round-tripped in JavaScript."
    );

    console.log(
        `Wrote ${path.relative(
            ROOT,
            OUTPUT_PATH
        )}`
    );
}

main();