"use strict";

const fs = require("fs");
const path = require("path");

const INPUT_PATH = path.join(
    "examples",
    "resource_graph_interop_vectors.json"
);

const OUTPUT_PATH = path.join(
    "examples",
    "resource_graph_interop_vectors_js.json"
);

const EXPECTED_VECTOR_SET =
    "org.opensmell.experimental.resource-graph.interop-vectors";

const EXPECTED_VECTOR_VERSION = "0.1";

const EXPECTED_GRAPH_FORMAT =
    "org.opensmell.experimental.resource-graph";

const EXPECTED_GRAPH_VERSION = "0.1";


function fail(message) {
    throw new Error(message);
}


function requireObject(value, name) {
    if (
        value === null ||
        typeof value !== "object" ||
        Array.isArray(value)
    ) {
        fail(`${name} must be an object`);
    }

    return value;
}


function requireArray(value, name) {
    if (!Array.isArray(value)) {
        fail(`${name} must be an array`);
    }

    return value;
}


function requireEqual(actual, expected, name) {
    if (actual !== expected) {
        fail(
            `${name}: expected ${JSON.stringify(expected)}, ` +
            `got ${JSON.stringify(actual)}`
        );
    }
}


function getVector(document, name) {
    const vector = document.vectors.find(
        (candidate) => candidate.name === name
    );

    if (!vector) {
        fail(`missing vector: ${name}`);
    }

    return vector;
}


function getResources(vector) {
    const graph = requireObject(
        vector.graph,
        `${vector.name}.graph`
    );

    requireEqual(
        graph.format,
        EXPECTED_GRAPH_FORMAT,
        `${vector.name}.graph.format`
    );

    requireEqual(
        graph.version,
        EXPECTED_GRAPH_VERSION,
        `${vector.name}.graph.version`
    );

    return requireArray(
        graph.resources,
        `${vector.name}.graph.resources`
    );
}


function findResource(resources, type) {
    const resource = resources.find(
        (candidate) => candidate.type === type
    );

    if (!resource) {
        fail(`missing resource type: ${type}`);
    }

    return resource;
}


function findObservation(resources) {
    return findResource(resources, "observation");
}


function verifyBasicGraph(document) {
    const vector = getVector(document, "basic_graph");
    const resources = getResources(vector);

    requireEqual(
        resources.length,
        3,
        "basic_graph resource count"
    );

    const stimulus = findResource(resources, "stimulus");

    const target = findResource(
        resources,
        "observation_target"
    );

    const observation = findObservation(resources);

    requireEqual(
        observation.stimulus.resource_id,
        stimulus.id,
        "basic_graph observation stimulus reference"
    );

    requireEqual(
        observation.target.resource_id,
        target.id,
        "basic_graph observation target reference"
    );

    requireEqual(
        observation.results.length,
        1,
        "basic_graph result count"
    );

    requireEqual(
        observation.results[0].data.value,
        42.5,
        "basic_graph result value"
    );
}


function verifyUnicode(document) {
    const vector = getVector(document, "unicode");
    const resources = getResources(vector);

    const stimulus = findResource(resources, "stimulus");
    const observation = findObservation(resources);

    requireEqual(
        stimulus.identifiers[0].value,
        "café-香り-🌹",
        "unicode external identifier"
    );

    requireEqual(
        stimulus.conditions[0].value,
        "Crème brûlée — ваниль — 香り 🌹",
        "unicode condition"
    );

    requireEqual(
        stimulus.unicode_extension,
        "éèê-日本語-🚀",
        "unicode extension"
    );

    const data = observation.results[0].data;

    requireEqual(data.label, "café", "unicode Latin value");
    requireEqual(data.japanese, "香り", "unicode Japanese value");
    requireEqual(data.russian, "запах", "unicode Cyrillic value");
    requireEqual(data.emoji, "🌹", "unicode emoji value");
}


function verifyNegativeZero(document) {
    const vector = getVector(document, "negative_zero");
    const resources = getResources(vector);
    const observation = findObservation(resources);

    const value = observation.results[0].data.value;

    if (!Object.is(value, -0)) {
        fail("negative_zero value was not preserved as -0");
    }
}


function verifyUnresolvedReferences(document) {
    const vector = getVector(
        document,
        "unresolved_references"
    );

    const resources = getResources(vector);

    const stimulus = findResource(resources, "stimulus");
    const observation = findObservation(resources);

    requireEqual(
        stimulus.source.resource_id,
        "88888888-8888-4888-8888-888888888888",
        "unresolved source reference"
    );

    requireEqual(
        observation.target.resource_id,
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "unresolved target reference"
    );

    const ids = new Set(
        resources.map((resource) => resource.id)
    );

    if (ids.has(stimulus.source.resource_id)) {
        fail("unresolved source unexpectedly resolves");
    }

    if (ids.has(observation.target.resource_id)) {
        fail("unresolved target unexpectedly resolves");
    }
}


function verifyExtensionsAndUnknownScheme(document) {
    const vector = getVector(
        document,
        "extensions_and_unknown_scheme"
    );

    const graph = requireObject(
        vector.graph,
        "extensions_and_unknown_scheme.graph"
    );

    const resources = getResources(vector);

    requireEqual(
        graph.graph_extension.producer,
        "OpenSmell interoperability test",
        "graph extension"
    );

    const stimulus = findResource(resources, "stimulus");

    const target = findResource(
        resources,
        "observation_target"
    );

    const observation = findObservation(resources);

    requireEqual(
        stimulus.future_stimulus_field.enabled,
        true,
        "stimulus extension"
    );

    requireEqual(
        stimulus.future_stimulus_field.nested.value,
        123,
        "nested stimulus extension"
    );

    requireEqual(
        stimulus.conditions[0].condition_extension.origin,
        "interop-test",
        "condition extension"
    );

    requireEqual(
        target.future_target_field.length,
        3,
        "target extension"
    );

    const result = observation.results[0];

    requireEqual(
        result.scheme.id,
        "org.example.future.result-scheme",
        "unknown Result scheme ID"
    );

    requireEqual(
        result.scheme.version,
        "9.7",
        "unknown Result scheme version"
    );

    requireEqual(
        result.scheme.scheme_extension,
        "preserve-me",
        "ResultScheme extension"
    );

    requireEqual(
        result.result_extension,
        true,
        "Result extension"
    );

    requireEqual(
        result.data.arbitrary.nested[2],
        3,
        "opaque Result data"
    );

    requireEqual(
        observation.context.protocol,
        "future-protocol",
        "observation context"
    );

    requireEqual(
        observation.future_observation_field.answer,
        42,
        "observation extension"
    );
}


function verifyMultipleResults(document) {
    const vector = getVector(document, "multiple_results");
    const resources = getResources(vector);
    const observation = findObservation(resources);

    requireEqual(
        observation.results.length,
        3,
        "multiple_results result count"
    );

    const schemes = observation.results.map(
        (result) => result.scheme.id
    );

    requireEqual(
        schemes[0],
        "org.opensmell.experimental.observation.categories",
        "multiple_results first scheme"
    );

    requireEqual(
        schemes[1],
        "org.opensmell.perceptual.measurements",
        "multiple_results second scheme"
    );

    requireEqual(
        schemes[2],
        "org.example.unknown",
        "multiple_results unknown scheme"
    );

    requireEqual(
        observation.results[0].data.state,
        "present",
        "categorical Result data"
    );

    requireEqual(
        observation.results[1].data.measurements[0].value,
        75.0,
        "perceptual Result data"
    );

    requireEqual(
        observation.results[2].data.opaque,
        "preserve this",
        "unknown Result data"
    );
}


function verifyDocument(document) {
    requireObject(document, "vector document");

    requireEqual(
        document.vector_set,
        EXPECTED_VECTOR_SET,
        "vector_set"
    );

    requireEqual(
        document.version,
        EXPECTED_VECTOR_VERSION,
        "vector version"
    );

    requireEqual(
        document.resource_graph_format,
        EXPECTED_GRAPH_FORMAT,
        "declared ResourceGraph format"
    );

    requireEqual(
        document.resource_graph_version,
        EXPECTED_GRAPH_VERSION,
        "declared ResourceGraph version"
    );

    requireArray(document.vectors, "vectors");

    requireEqual(
        document.vectors.length,
        6,
        "vector count"
    );

    const checks = [
        ["basic_graph", verifyBasicGraph],
        ["unicode", verifyUnicode],
        ["negative_zero", verifyNegativeZero],
        [
            "unresolved_references",
            verifyUnresolvedReferences,
        ],
        [
            "extensions_and_unknown_scheme",
            verifyExtensionsAndUnknownScheme,
        ],
        [
            "multiple_results",
            verifyMultipleResults,
        ],
    ];

    for (const [name, check] of checks) {
        check(document);
        console.log(`  PASS  ${name}`);
    }
}


function writeJavaScriptRoundTrip(document) {
    /*
     * Intentionally parse and re-serialize using the native JavaScript
     * JSON implementation.
     *
     * This is not a byte-for-byte copy. The goal is to prove that the
     * ResourceGraph representation survives an independent JSON runtime.
     */
    const serialized = JSON.stringify(
        document,
        null,
        2
    );

    fs.writeFileSync(
        OUTPUT_PATH,
        serialized + "\n",
        "utf8"
    );
}


function verifyWrittenDocument() {
    const raw = fs.readFileSync(
        OUTPUT_PATH,
        "utf8"
    );

    const document = JSON.parse(raw);

    /*
     * JSON.stringify(-0) produces "0".
     *
     * This is an important cross-runtime behavior. Therefore we do not
     * incorrectly claim that JavaScript preserves the IEEE-754 sign of
     * negative zero through JSON serialization.
     *
     * Python will verify semantic equivalence separately, with this
     * known JSON limitation handled explicitly.
     */
    return document;
}


function main() {
    const raw = fs.readFileSync(
        INPUT_PATH,
        "utf8"
    );

    const document = JSON.parse(raw);

    console.log(
        "OpenSmell ResourceGraph JavaScript interoperability verification"
    );

    console.log("=".repeat(72));

    console.log(`Input  : ${INPUT_PATH}`);
    console.log(`Vectors: ${document.vectors.length}`);
    console.log();

    verifyDocument(document);

    console.log();
    console.log(
        "Writing JavaScript re-serialized interoperability vectors..."
    );

    writeJavaScriptRoundTrip(document);

    const rewritten = verifyWrittenDocument();

    requireEqual(
        rewritten.vector_set,
        EXPECTED_VECTOR_SET,
        "rewritten vector_set"
    );

    requireEqual(
        rewritten.vectors.length,
        6,
        "rewritten vector count"
    );

    console.log(`Output : ${OUTPUT_PATH}`);
    console.log();

    /*
     * Demonstrate the JSON negative-zero behavior explicitly.
     */
    const originalNegativeZero =
        getVector(document, "negative_zero")
            .graph.resources
            .find(
                (resource) =>
                    resource.type === "observation"
            )
            .results[0]
            .data
            .value;

    const rewrittenNegativeZero =
        getVector(rewritten, "negative_zero")
            .graph.resources
            .find(
                (resource) =>
                    resource.type === "observation"
            )
            .results[0]
            .data
            .value;

    requireEqual(
        Object.is(originalNegativeZero, -0),
        true,
        "input negative-zero sign"
    );

    requireEqual(
        Object.is(rewrittenNegativeZero, 0),
        true,
        "JavaScript JSON negative-zero normalization"
    );

    console.log(
        "  INFO  JavaScript JSON serialization normalizes -0 to 0"
    );

    console.log();
    console.log("SUCCESS");

    console.log(
        "JavaScript parsed, verified, and re-serialized all Python-generated ResourceGraph vectors."
    );
}


main();