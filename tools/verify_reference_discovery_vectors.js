"use strict";

/**
 * Independent JavaScript interoperability verifier for RFC-0011
 * Structural Reference Discovery and Graph Navigation.
 *
 * This verifier intentionally does not use the Python implementation.
 * It implements only the resource knowledge needed by these portable vectors.
 *
 * Unknown resources and unknown future resource versions are transportable
 * but structurally opaque.
 */

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const VECTORS_PATH = path.join(
    ROOT,
    "examples",
    "reference_discovery_interop_vectors.json"
);

const EXPECTED_VECTOR_SET =
    "org.opensmell.experimental.reference-discovery.interop-vectors";
const EXPECTED_VECTOR_VERSION = "0.1";
const GRAPH_FORMAT =
    "org.opensmell.experimental.generic-resource-graph";
const GRAPH_VERSION = "0.1";

const MOLECULE_TYPE = "org.opensmell.molecule";
const MOLECULE_VERSION = "0.1";
const ANNOTATION_TYPE = "org.opensmell.annotation";
const ANNOTATION_VERSION = "0.1";

const EXPECTED_VECTOR_NAMES = [
    "annotation_to_molecule",
    "unresolved_annotation_subject",
    "unknown_resource_is_opaque",
    "future_annotation_version_is_opaque",
    "multiple_annotations_preserve_graph_order",
    "opaque_payloads_do_not_create_edges",
    "unicode_ids_and_reference_extensions",
];

function loadJson(filePath) {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function isObject(value) {
    return (
        typeof value === "object"
        && value !== null
        && !Array.isArray(value)
    );
}

function isNonEmptyString(value) {
    return typeof value === "string" && value.length > 0;
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function validateGenericResource(resource) {
    assert(isObject(resource), "Resource must be an object.");
    assert(isNonEmptyString(resource.type), "Resource type must be non-empty.");
    assert(isNonEmptyString(resource.id), "Resource id must be non-empty.");

    if (Object.prototype.hasOwnProperty.call(resource, "type_version")) {
        assert(
            isNonEmptyString(resource.type_version),
            "Resource type_version must be non-empty when present."
        );
    }
}

function validateMolecule(resource) {
    validateGenericResource(resource);
    assert(
        resource.type === MOLECULE_TYPE
        && resource.type_version === MOLECULE_VERSION,
        "Not a Molecule 0.1 resource."
    );

    const hasSmiles =
        Object.prototype.hasOwnProperty.call(resource, "smiles");
    const hasIdentifiers =
        Object.prototype.hasOwnProperty.call(resource, "identifiers");

    assert(
        hasSmiles || hasIdentifiers,
        "Molecule requires smiles or identifiers."
    );

    if (hasSmiles) {
        assert(
            isNonEmptyString(resource.smiles),
            "Molecule smiles must be non-empty."
        );
    }

    if (hasIdentifiers) {
        assert(
            Array.isArray(resource.identifiers),
            "Molecule identifiers must be an array."
        );
    }
}

function validateAnnotation(resource) {
    validateGenericResource(resource);
    assert(
        resource.type === ANNOTATION_TYPE
        && resource.type_version === ANNOTATION_VERSION,
        "Not an Annotation 0.1 resource."
    );
    assert(
        isObject(resource.subject)
        && isNonEmptyString(resource.subject.resource_id),
        "Annotation subject must contain a non-empty resource_id."
    );
    assert(
        isObject(resource.scheme)
        && isNonEmptyString(resource.scheme.id)
        && isNonEmptyString(resource.scheme.version),
        "Annotation scheme must contain non-empty id and version."
    );
    assert(
        isObject(resource.data),
        "Annotation data must be an object."
    );
}

function resourceKind(resource) {
    if (
        resource.type === MOLECULE_TYPE
        && resource.type_version === MOLECULE_VERSION
    ) {
        validateMolecule(resource);
        return "molecule";
    }

    if (
        resource.type === ANNOTATION_TYPE
        && resource.type_version === ANNOTATION_VERSION
    ) {
        validateAnnotation(resource);
        return "annotation";
    }

    validateGenericResource(resource);
    return "generic";
}

function validateGraph(graph) {
    assert(isObject(graph), "Graph must be an object.");
    assert(graph.format === GRAPH_FORMAT, "Unexpected graph format.");
    assert(graph.version === GRAPH_VERSION, "Unexpected graph version.");
    assert(Array.isArray(graph.resources), "Graph resources must be an array.");

    const ids = new Set();

    for (const resource of graph.resources) {
        resourceKind(resource);
        assert(
            !ids.has(resource.id),
            `Duplicate resource id: ${resource.id}`
        );
        ids.add(resource.id);
    }
}

function discoverResourceReferences(resource) {
    const kind = resourceKind(resource);

    if (kind === "annotation") {
        return [resource.subject];
    }

    /*
     * Molecule declares no structural References.
     * Generic resources are deliberately opaque.
     */
    return [];
}

function discoverGraphReferences(graph) {
    const edges = [];

    for (const resource of graph.resources) {
        const references = discoverResourceReferences(resource);

        for (const reference of references) {
            edges.push({
                source_id: resource.id,
                target_id: reference.resource_id,
            });
        }
    }

    return edges;
}

function buildResourceMap(graph) {
    const result = new Map();

    for (const resource of graph.resources) {
        result.set(resource.id, resource);
    }

    return result;
}

function partitionEdges(graph, edges) {
    const resources = buildResourceMap(graph);
    const resolved = [];
    const unresolved = [];

    for (const edge of edges) {
        if (resources.has(edge.target_id)) {
            resolved.push(edge);
        } else {
            unresolved.push(edge);
        }
    }

    return { resolved, unresolved };
}

function referencesFrom(edges, sourceId) {
    return edges.filter(
        (edge) => edge.source_id === sourceId
    );
}

function referencesTo(edges, targetId) {
    return edges.filter(
        (edge) => edge.target_id === targetId
    );
}

function jsonEquivalent(left, right) {
    return JSON.stringify(left) === JSON.stringify(right);
}

function fail(message) {
    console.error(`FAIL: ${message}`);
    process.exitCode = 1;
}

function main() {
    const document = loadJson(VECTORS_PATH);

    assert(isObject(document), "Vector document must be an object.");
    assert(
        document.vector_set === EXPECTED_VECTOR_SET,
        "Unexpected vector set."
    );
    assert(
        document.version === EXPECTED_VECTOR_VERSION,
        "Unexpected vector version."
    );
    assert(
        document.resource_graph_format === GRAPH_FORMAT,
        "Unexpected declared graph format."
    );
    assert(
        document.resource_graph_version === GRAPH_VERSION,
        "Unexpected declared graph version."
    );
    assert(Array.isArray(document.vectors), "Vectors must be an array.");
    assert(
        document.vectors.length === EXPECTED_VECTOR_NAMES.length,
        "Unexpected vector count."
    );

    let discoveryPassed = 0;
    let discoveryFailed = 0;
    let navigationPassed = 0;
    let navigationFailed = 0;

    for (let index = 0; index < document.vectors.length; index += 1) {
        const vector = document.vectors[index];
        const expectedName = EXPECTED_VECTOR_NAMES[index];

        try {
            assert(
                isObject(vector) && vector.name === expectedName,
                `Vector ${index} expected name ${expectedName}.`
            );

            validateGraph(vector.graph);

            const edges = discoverGraphReferences(vector.graph);

            if (jsonEquivalent(edges, vector.expected_edges)) {
                discoveryPassed += 1;
            } else {
                discoveryFailed += 1;
                fail(
                    `${vector.name}: discovered edges differ from portable expectations`
                );
            }

            const partition = partitionEdges(vector.graph, edges);

            let navigationOk =
                partition.resolved.length === vector.expected_resolved
                && partition.unresolved.length === vector.expected_unresolved;

            for (const edge of vector.expected_edges) {
                const outgoing = referencesFrom(edges, edge.source_id);
                const incoming = referencesTo(edges, edge.target_id);

                navigationOk =
                    navigationOk
                    && outgoing.some(
                        (candidate) =>
                            candidate.source_id === edge.source_id
                            && candidate.target_id === edge.target_id
                    )
                    && incoming.some(
                        (candidate) =>
                            candidate.source_id === edge.source_id
                            && candidate.target_id === edge.target_id
                    );
            }

            if (navigationOk) {
                navigationPassed += 1;
            } else {
                navigationFailed += 1;
                fail(
                    `${vector.name}: navigation/resolution behavior is incorrect`
                );
            }
        } catch (error) {
            discoveryFailed += 1;
            navigationFailed += 1;
            fail(`${expectedName}: ${error.message}`);
        }
    }

    console.log(
        `RFC-0011 discovery vectors: ${discoveryPassed} passed, ${discoveryFailed} failed`
    );
    console.log(
        `RFC-0011 navigation behaviors: ${navigationPassed} passed, ${navigationFailed} failed`
    );

    if (
        discoveryFailed === 0
        && navigationFailed === 0
        && discoveryPassed === EXPECTED_VECTOR_NAMES.length
        && navigationPassed === EXPECTED_VECTOR_NAMES.length
        && process.exitCode !== 1
    ) {
        console.log(
            "SUCCESS: independent JavaScript implementation agrees with all RFC-0011 portable reference-discovery vectors."
        );
    }
}

main();
