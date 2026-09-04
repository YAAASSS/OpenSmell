"use strict";

/**
 * Independent JavaScript interoperability verifier for RFC-0010
 * Annotation resources transported through an RFC-0008 GenericResourceGraph.
 *
 * This verifier intentionally does not use the Python implementation.
 *
 * It verifies that the language-independent golden vectors preserve:
 *
 * - Molecule 0.1 resources;
 * - Annotation 0.1 resources;
 * - subject references;
 * - unknown Annotation schemes;
 * - unknown resource types;
 * - unknown future Annotation resource versions;
 * - graph/resource/reference/scheme extensions;
 * - Unicode data.
 */

const fs = require("fs");
const path = require("path");


const ROOT = path.resolve(__dirname, "..");

const VECTORS_PATH = path.join(
    ROOT,
    "examples",
    "annotation_resource_graph_interop_vectors.json"
);

const EXPECTED_VECTOR_SET =
    "org.opensmell.experimental.annotation-resource-graph.interop-vectors";

const EXPECTED_VECTOR_VERSION = "0.1";

const GRAPH_FORMAT =
    "org.opensmell.experimental.generic-resource-graph";

const GRAPH_VERSION = "0.1";

const MOLECULE_TYPE =
    "org.opensmell.molecule";

const MOLECULE_VERSION = "0.1";

const ANNOTATION_TYPE =
    "org.opensmell.annotation";

const ANNOTATION_VERSION = "0.1";

const EXPECTED_VECTOR_NAMES = [
    "molecule_and_annotation",
    "unresolved_annotation_subject",
    "unknown_annotation_scheme",
    "unknown_future_annotation_version",
    "unknown_resource_with_annotation",
    "mixed_molecule_annotation_unknown_and_future",
    "extensions_and_unicode",
];


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


function deepCloneJson(value) {
    return JSON.parse(
        JSON.stringify(value)
    );
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


function parseMolecule(resource) {
    if (!isObject(resource)) {
        throw new Error(
            "Molecule must be an object."
        );
    }

    if (
        resource.type !== MOLECULE_TYPE
        || resource.type_version !== MOLECULE_VERSION
    ) {
        throw new Error(
            "Not a Molecule 0.1 resource."
        );
    }

    if (!isNonEmptyString(resource.id)) {
        throw new Error(
            "Molecule id must be a non-empty string."
        );
    }

    const hasSmiles =
        Object.prototype.hasOwnProperty.call(
            resource,
            "smiles"
        );

    const hasIdentifiers =
        Object.prototype.hasOwnProperty.call(
            resource,
            "identifiers"
        );

    if (
        !hasSmiles
        && !hasIdentifiers
    ) {
        throw new Error(
            "Molecule requires smiles or identifiers."
        );
    }

    if (
        hasSmiles
        && !isNonEmptyString(resource.smiles)
    ) {
        throw new Error(
            "Molecule smiles must be a non-empty string."
        );
    }

    if (
        hasIdentifiers
        && !Array.isArray(resource.identifiers)
    ) {
        throw new Error(
            "Molecule identifiers must be an array."
        );
    }

    return {
        kind: "molecule",
        raw: deepCloneJson(resource),
    };
}


function parseAnnotation(resource) {
    if (!isObject(resource)) {
        throw new Error(
            "Annotation must be an object."
        );
    }

    if (
        resource.type !== ANNOTATION_TYPE
        || resource.type_version !== ANNOTATION_VERSION
    ) {
        throw new Error(
            "Not an Annotation 0.1 resource."
        );
    }

    if (!isNonEmptyString(resource.id)) {
        throw new Error(
            "Annotation id must be a non-empty string."
        );
    }

    if (
        !isObject(resource.subject)
        || !isNonEmptyString(
            resource.subject.resource_id
        )
    ) {
        throw new Error(
            "Annotation subject must contain a non-empty resource_id."
        );
    }

    if (
        !isObject(resource.scheme)
        || !isNonEmptyString(
            resource.scheme.id
        )
        || !isNonEmptyString(
            resource.scheme.version
        )
    ) {
        throw new Error(
            "Annotation scheme must contain non-empty id and version."
        );
    }

    if (!isObject(resource.data)) {
        throw new Error(
            "Annotation data must be an object."
        );
    }

    return {
        kind: "annotation",
        raw: deepCloneJson(resource),
    };
}


function parseGenericResource(resource) {
    if (!isObject(resource)) {
        throw new Error(
            "Generic resource must be an object."
        );
    }

    if (!isNonEmptyString(resource.type)) {
        throw new Error(
            "Generic resource type must be a non-empty string."
        );
    }

    if (!isNonEmptyString(resource.id)) {
        throw new Error(
            "Generic resource id must be a non-empty string."
        );
    }

    if (
        Object.prototype.hasOwnProperty.call(
            resource,
            "type_version"
        )
        && !isNonEmptyString(
            resource.type_version
        )
    ) {
        throw new Error(
            "Generic resource type_version must be a non-empty string when present."
        );
    }

    return {
        kind: "generic",
        raw: deepCloneJson(resource),
    };
}


function parseResource(resource) {
    if (
        isObject(resource)
        && resource.type === MOLECULE_TYPE
        && resource.type_version === MOLECULE_VERSION
    ) {
        return parseMolecule(resource);
    }

    if (
        isObject(resource)
        && resource.type === ANNOTATION_TYPE
        && resource.type_version === ANNOTATION_VERSION
    ) {
        return parseAnnotation(resource);
    }

    return parseGenericResource(resource);
}


function parseGraph(graph) {
    if (!isObject(graph)) {
        throw new Error(
            "Graph must be an object."
        );
    }

    if (graph.format !== GRAPH_FORMAT) {
        throw new Error(
            "Unexpected graph format."
        );
    }

    if (graph.version !== GRAPH_VERSION) {
        throw new Error(
            "Unexpected graph version."
        );
    }

    if (!Array.isArray(graph.resources)) {
        throw new Error(
            "Graph resources must be an array."
        );
    }

    const resources =
        graph.resources.map(parseResource);

    const ids = new Set();

    for (const resource of resources) {
        const id = resource.raw.id;

        if (ids.has(id)) {
            throw new Error(
                `Duplicate resource id: ${id}`
            );
        }

        ids.add(id);
    }

    return {
        resources,
        raw: deepCloneJson(graph),
    };
}


function serializeGraph(parsedGraph) {
    const result = {};

    for (
        const [key, value]
        of Object.entries(parsedGraph.raw)
    ) {
        if (
            key !== "format"
            && key !== "version"
            && key !== "resources"
        ) {
            result[key] =
                deepCloneJson(value);
        }
    }

    result.format = GRAPH_FORMAT;
    result.version = GRAPH_VERSION;

    result.resources =
        parsedGraph.resources.map(
            (resource) =>
                deepCloneJson(resource.raw)
        );

    return result;
}


function resourceById(
    parsedGraph,
    resourceId
) {
    for (
        const resource
        of parsedGraph.resources
    ) {
        if (
            resource.raw.id
            === resourceId
        ) {
            return resource;
        }
    }

    return null;
}


function fail(message) {
    console.error(
        `FAIL: ${message}`
    );

    process.exitCode = 1;
}


function main() {
    const document =
        loadJson(VECTORS_PATH);

    if (!isObject(document)) {
        throw new Error(
            "Interop vector document must be an object."
        );
    }

    if (
        document.vector_set
        !== EXPECTED_VECTOR_SET
    ) {
        throw new Error(
            "Unexpected interop vector set."
        );
    }

    if (
        document.version
        !== EXPECTED_VECTOR_VERSION
    ) {
        throw new Error(
            "Unexpected interop vector version."
        );
    }

    if (
        document.resource_graph_format
        !== GRAPH_FORMAT
    ) {
        throw new Error(
            "Unexpected declared graph format."
        );
    }

    if (
        document.resource_graph_version
        !== GRAPH_VERSION
    ) {
        throw new Error(
            "Unexpected declared graph version."
        );
    }

    if (!Array.isArray(document.vectors)) {
        throw new Error(
            "Interop document must contain vectors."
        );
    }

    if (
        document.vectors.length
        !== EXPECTED_VECTOR_NAMES.length
    ) {
        throw new Error(
            `Expected ${EXPECTED_VECTOR_NAMES.length} vectors, found ${document.vectors.length}.`
        );
    }

    let roundTripPassed = 0;
    let roundTripFailed = 0;
    let behaviorPassed = 0;
    let behaviorFailed = 0;

    for (
        let index = 0;
        index < document.vectors.length;
        index += 1
    ) {
        const vector =
            document.vectors[index];

        const expectedName =
            EXPECTED_VECTOR_NAMES[index];

        if (
            !isObject(vector)
            || vector.name !== expectedName
        ) {
            fail(
                `Vector ${index} expected name ${expectedName}.`
            );

            continue;
        }

        try {
            const parsed =
                parseGraph(vector.graph);

            const recovered =
                serializeGraph(parsed);

            if (
                jsonEquivalent(
                    recovered,
                    vector.graph
                )
            ) {
                roundTripPassed += 1;
            } else {
                roundTripFailed += 1;

                fail(
                    `${vector.name}: graph round trip changed the vector`
                );
            }

            if (
                vector.name
                === "molecule_and_annotation"
            ) {
                const annotation =
                    resourceById(
                        parsed,
                        "annotation-1"
                    );

                if (
                    annotation !== null
                    && annotation.kind === "annotation"
                    && resourceById(
                        parsed,
                        annotation.raw.subject.resource_id
                    )?.kind === "molecule"
                ) {
                    behaviorPassed += 1;
                } else {
                    behaviorFailed += 1;

                    fail(
                        `${vector.name}: Annotation subject did not resolve to Molecule`
                    );
                }
            }

            if (
                vector.name
                === "unresolved_annotation_subject"
            ) {
                const annotation =
                    resourceById(
                        parsed,
                        "annotation-unresolved"
                    );

                if (
                    annotation !== null
                    && annotation.kind === "annotation"
                    && resourceById(
                        parsed,
                        annotation.raw.subject.resource_id
                    ) === null
                ) {
                    behaviorPassed += 1;
                } else {
                    behaviorFailed += 1;

                    fail(
                        `${vector.name}: unresolved subject behavior is incorrect`
                    );
                }
            }

            if (
                vector.name
                === "unknown_annotation_scheme"
            ) {
                const annotation =
                    resourceById(
                        parsed,
                        "annotation-unknown-scheme"
                    );

                if (
                    annotation !== null
                    && annotation.kind === "annotation"
                    && annotation.raw.scheme.id
                        === "org.example.future.annotation-scheme"
                    && annotation.raw.scheme.version
                        === "999"
                ) {
                    behaviorPassed += 1;
                } else {
                    behaviorFailed += 1;

                    fail(
                        `${vector.name}: unknown Scheme was not preserved`
                    );
                }
            }

            if (
                vector.name
                === "unknown_future_annotation_version"
            ) {
                const futureAnnotation =
                    resourceById(
                        parsed,
                        "annotation-future"
                    );

                if (
                    futureAnnotation !== null
                    && futureAnnotation.kind === "generic"
                    && futureAnnotation.raw.type
                        === ANNOTATION_TYPE
                    && futureAnnotation.raw.type_version
                        === "99.0"
                    && futureAnnotation.raw
                        .new_field_from_future
                        .preserve_me === true
                ) {
                    behaviorPassed += 1;
                } else {
                    behaviorFailed += 1;

                    fail(
                        `${vector.name}: future Annotation did not fall back to generic transport`
                    );
                }
            }

            if (
                vector.name
                === "unknown_resource_with_annotation"
            ) {
                const unknown =
                    resourceById(
                        parsed,
                        "future-sensor-1"
                    );

                const annotation =
                    resourceById(
                        parsed,
                        "annotation-future-sensor"
                    );

                if (
                    unknown !== null
                    && unknown.kind === "generic"
                    && annotation !== null
                    && annotation.kind === "annotation"
                    && resourceById(
                        parsed,
                        annotation.raw.subject.resource_id
                    ) === unknown
                ) {
                    behaviorPassed += 1;
                } else {
                    behaviorFailed += 1;

                    fail(
                        `${vector.name}: Annotation did not target the unknown resource correctly`
                    );
                }
            }

            if (
                vector.name
                === "mixed_molecule_annotation_unknown_and_future"
            ) {
                const kinds =
                    parsed.resources.map(
                        (resource) =>
                            resource.kind
                    );

                const expectedKinds = [
                    "molecule",
                    "annotation",
                    "generic",
                    "generic",
                ];

                if (
                    jsonEquivalent(
                        kinds,
                        expectedKinds
                    )
                ) {
                    behaviorPassed += 1;
                } else {
                    behaviorFailed += 1;

                    fail(
                        `${vector.name}: incorrect mixed resource dispatch`
                    );
                }
            }

            if (
                vector.name
                === "extensions_and_unicode"
            ) {
                const annotation =
                    resourceById(
                        parsed,
                        "аннотация-🌸"
                    );

                if (
                    annotation !== null
                    && annotation.kind === "annotation"
                    && annotation.raw.data.description
                        === "café-香り-🌹"
                    && annotation.raw
                        .annotation_extension
                        .russian === "запах"
                    && parsed.raw
                        .unicode_graph_extension
                        === "éèê-日本語-🚀"
                ) {
                    behaviorPassed += 1;
                } else {
                    behaviorFailed += 1;

                    fail(
                        `${vector.name}: Unicode/extensions were not preserved`
                    );
                }
            }
        } catch (error) {
            roundTripFailed += 1;
            behaviorFailed += 1;

            fail(
                `${vector.name}: ${error.message}`
            );
        }
    }

    console.log(
        `Annotation ResourceGraph round trips: ${roundTripPassed} passed, ${roundTripFailed} failed`
    );

    console.log(
        `Annotation ResourceGraph behaviors: ${behaviorPassed} passed, ${behaviorFailed} failed`
    );

    if (
        roundTripFailed === 0
        && behaviorFailed === 0
        && roundTripPassed
            === EXPECTED_VECTOR_NAMES.length
        && behaviorPassed
            === EXPECTED_VECTOR_NAMES.length
        && process.exitCode !== 1
    ) {
        console.log(
            "SUCCESS: independent JavaScript implementation preserves all RFC-0010 Annotation ResourceGraph interoperability vectors."
        );
    }
}


main();