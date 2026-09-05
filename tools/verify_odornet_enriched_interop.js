"use strict";

/**
 * Independent JavaScript verifier for the real enriched OdorNet
 * interoperability demonstration.
 *
 * Pipeline under test:
 *
 *   enriched OdorNet CSV
 *       -> OpenSmell Python adapter
 *       -> GenericResourceGraph JSON
 *       -> independent JavaScript consumer
 *
 * This verifier intentionally does not use the Python implementation.
 *
 * It verifies:
 *
 * - GenericResourceGraph format and version;
 * - Molecule 0.1 resource recognition;
 * - Annotation 0.1 resource recognition;
 * - Annotation subject resolution;
 * - SMILES preservation;
 * - PubChem InChIKey preservation;
 * - all 12 OdorNet semantic states;
 * - JSON round-trip preservation.
 *
 * The default input is:
 *
 *   examples/odornet_enriched_interop.json
 *
 * A different input document can be supplied with:
 *
 *   node tools/verify_odornet_enriched_interop.js --input file.json
 *
 * This is experimental and non-normative.
 */

const fs = require("fs");
const path = require("path");


const ROOT = path.resolve(__dirname, "..");

const DEFAULT_INPUT_PATH = path.join(
    ROOT,
    "examples",
    "odornet_enriched_interop.json"
);


const INTEROP_TEST =
    "org.opensmell.experimental.odornet-enriched.interop";

const INTEROP_VERSION = "0.1";

const GRAPH_FORMAT =
    "org.opensmell.experimental.generic-resource-graph";

const GRAPH_VERSION = "0.1";

const MOLECULE_TYPE =
    "org.opensmell.molecule";

const MOLECULE_VERSION = "0.1";

const ANNOTATION_TYPE =
    "org.opensmell.annotation";

const ANNOTATION_VERSION = "0.1";

const SEMANTIC_SCHEME =
    "org.opensmell.semantic.annotations";

const SEMANTIC_SCHEME_VERSION = "0.1";

const PUBCHEM_INCHIKEY_SCHEME =
    "pubchem.inchikey";

const ODORNET_LABELS = [
    "animalic&ambery",
    "sweety&gourmand",
    "floral",
    "fruity&vegetable",
    "pungent&disagreeable",
    "green&herbal",
    "nutty",
    "woody&mossy",
    "resinous&balsamic",
    "cooked",
    "odorless",
    "spice",
];

const VALID_STATES = new Set([
    "present",
    "absent",
    "unknown",
]);


function isObject(value) {
    return (
        typeof value === "object"
        && value !== null
        && !Array.isArray(value)
    );
}


function hasOwn(value, key) {
    return Object.prototype.hasOwnProperty.call(
        value,
        key
    );
}


function isNonEmptyString(value) {
    return (
        typeof value === "string"
        && value.length > 0
    );
}


function cloneJson(value) {
    if (
        value === null
        || typeof value === "string"
        || typeof value === "boolean"
        || typeof value === "number"
    ) {
        return value;
    }

    if (Array.isArray(value)) {
        return value.map(
            cloneJson
        );
    }

    if (isObject(value)) {
        const result = {};

        for (
            const [key, item]
            of Object.entries(value)
        ) {
            result[key] =
                cloneJson(item);
        }

        return result;
    }

    throw new Error(
        `Unsupported JSON value: ${String(value)}`
    );
}


function deepEqual(left, right) {
    if (left === right) {
        return true;
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

        return left.every(
            (item, index) =>
                deepEqual(
                    item,
                    right[index]
                )
        );
    }

    if (
        isObject(left)
        || isObject(right)
    ) {
        if (
            !isObject(left)
            || !isObject(right)
        ) {
            return false;
        }

        const leftKeys =
            Object.keys(left);

        const rightKeys =
            Object.keys(right);

        if (
            leftKeys.length
            !== rightKeys.length
        ) {
            return false;
        }

        return leftKeys.every(
            (key) =>
                hasOwn(right, key)
                && deepEqual(
                    left[key],
                    right[key]
                )
        );
    }

    return false;
}


function requireObject(
    value,
    message
) {
    if (!isObject(value)) {
        throw new Error(message);
    }

    return value;
}


function requireNonEmptyString(
    value,
    message
) {
    if (!isNonEmptyString(value)) {
        throw new Error(message);
    }

    return value;
}


function parseArgs(argv) {
    let inputPath =
        DEFAULT_INPUT_PATH;

    for (
        let index = 0;
        index < argv.length;
        index += 1
    ) {
        const argument =
            argv[index];

        if (
            argument === "--input"
        ) {
            if (
                index + 1
                >= argv.length
            ) {
                throw new Error(
                    "--input requires a file path"
                );
            }

            inputPath =
                path.resolve(
                    argv[index + 1]
                );

            index += 1;
            continue;
        }

        throw new Error(
            `unknown argument: ${argument}`
        );
    }

    return {
        inputPath,
    };
}


function validateGraph(graph) {
    requireObject(
        graph,
        "graph must be an object"
    );

    if (
        graph.format
        !== GRAPH_FORMAT
    ) {
        throw new Error(
            "unexpected GenericResourceGraph format"
        );
    }

    if (
        graph.version
        !== GRAPH_VERSION
    ) {
        throw new Error(
            "unexpected GenericResourceGraph version"
        );
    }

    if (
        !Array.isArray(
            graph.resources
        )
    ) {
        throw new Error(
            "graph.resources must be an array"
        );
    }

    const ids = new Set();

    for (
        const resource
        of graph.resources
    ) {
        requireObject(
            resource,
            "graph resource must be an object"
        );

        requireNonEmptyString(
            resource.type,
            "resource.type must be a non-empty string"
        );

        requireNonEmptyString(
            resource.id,
            "resource.id must be a non-empty string"
        );

        if (
            hasOwn(
                resource,
                "type_version"
            )
        ) {
            requireNonEmptyString(
                resource.type_version,
                "resource.type_version must be a non-empty string"
            );
        }

        if (
            ids.has(
                resource.id
            )
        ) {
            throw new Error(
                `duplicate resource id: ${resource.id}`
            );
        }

        ids.add(
            resource.id
        );
    }
}


function resourceById(
    graph,
    resourceId
) {
    for (
        const resource
        of graph.resources
    ) {
        if (
            resource.id
            === resourceId
        ) {
            return resource;
        }
    }

    return null;
}


function requireMolecule(
    graph,
    expected
) {
    const molecule =
        resourceById(
            graph,
            expected.molecule_id
        );

    if (
        molecule === null
    ) {
        throw new Error(
            "expected Molecule resource was not found"
        );
    }

    if (
        molecule.type
        !== MOLECULE_TYPE
        || molecule.type_version
        !== MOLECULE_VERSION
    ) {
        throw new Error(
            "expected resource is not a Molecule 0.1"
        );
    }

    if (
        molecule.smiles
        !== expected.smiles
    ) {
        throw new Error(
            "Molecule SMILES was not preserved"
        );
    }

    if (
        !Array.isArray(
            molecule.identifiers
        )
    ) {
        throw new Error(
            "Molecule identifiers must be an array"
        );
    }

    return molecule;
}


function verifyPubChemInChIKey(
    molecule,
    expected
) {
    const expectedValue =
        expected.pubchem_inchikey;

    const identifiers =
        molecule.identifiers.filter(
            (identifier) =>
                isObject(identifier)
                && identifier.scheme
                    === PUBCHEM_INCHIKEY_SCHEME
        );

    if (
        expectedValue === null
    ) {
        if (
            identifiers.length !== 0
        ) {
            throw new Error(
                "unexpected PubChem InChIKey identifier"
            );
        }

        return;
    }

    if (
        !isNonEmptyString(
            expectedValue
        )
    ) {
        throw new Error(
            "expected.pubchem_inchikey must be a non-empty string or null"
        );
    }

    if (
        identifiers.length !== 1
    ) {
        throw new Error(
            "expected exactly one PubChem InChIKey identifier"
        );
    }

    if (
        identifiers[0].value
        !== expectedValue
    ) {
        throw new Error(
            "PubChem InChIKey value was not preserved"
        );
    }
}


function requireAnnotation(
    graph,
    expected
) {
    const annotation =
        resourceById(
            graph,
            expected.annotation_id
        );

    if (
        annotation === null
    ) {
        throw new Error(
            "expected Annotation resource was not found"
        );
    }

    if (
        annotation.type
        !== ANNOTATION_TYPE
        || annotation.type_version
        !== ANNOTATION_VERSION
    ) {
        throw new Error(
            "expected resource is not an Annotation 0.1"
        );
    }

    requireObject(
        annotation.subject,
        "Annotation subject must be an object"
    );

    requireNonEmptyString(
        annotation.subject.resource_id,
        "Annotation subject.resource_id must be a non-empty string"
    );

    requireObject(
        annotation.scheme,
        "Annotation scheme must be an object"
    );

    if (
        annotation.scheme.id
        !== SEMANTIC_SCHEME
        || annotation.scheme.version
        !== SEMANTIC_SCHEME_VERSION
    ) {
        throw new Error(
            "unexpected semantic Annotation scheme"
        );
    }

    requireObject(
        annotation.data,
        "Annotation data must be an object"
    );

    return annotation;
}


function verifySubjectResolution(
    graph,
    molecule,
    annotation
) {
    if (
        annotation.subject.resource_id
        !== molecule.id
    ) {
        throw new Error(
            "Annotation subject does not reference Molecule"
        );
    }

    const resolved =
        resourceById(
            graph,
            annotation.subject.resource_id
        );

    if (
        resolved !== molecule
    ) {
        throw new Error(
            "Annotation subject did not resolve to Molecule"
        );
    }
}


function verifySemanticStates(
    annotation,
    expected
) {
    const annotations =
        annotation.data.annotations;

    if (
        !Array.isArray(
            annotations
        )
    ) {
        throw new Error(
            "Annotation data.annotations must be an array"
        );
    }

    if (
        annotations.length
        !== ODORNET_LABELS.length
    ) {
        throw new Error(
            `expected ${ODORNET_LABELS.length} semantic annotations, `
            + `found ${annotations.length}`
        );
    }

    const expectedStates =
        requireObject(
            expected.semantic_states,
            "expected.semantic_states must be an object"
        );

    const expectedStateKeys =
        Object.keys(
            expectedStates
        );

    if (
        expectedStateKeys.length
        !== ODORNET_LABELS.length
    ) {
        throw new Error(
            "expected.semantic_states must contain exactly "
            + `${ODORNET_LABELS.length} entries`
        );
    }

    const seen = new Set();

    for (
        let index = 0;
        index < annotations.length;
        index += 1
    ) {
        const item =
            annotations[index];

        requireObject(
            item,
            `semantic annotation ${index} must be an object`
        );

        const expectedLabel =
            ODORNET_LABELS[index];

        if (
            item.value
            !== expectedLabel
        ) {
            throw new Error(
                `semantic annotation ${index} `
                + `expected value ${expectedLabel}, `
                + `found ${String(item.value)}`
            );
        }

        if (
            item.language
            !== "en"
        ) {
            throw new Error(
                `${expectedLabel}: expected language en`
            );
        }

        if (
            !VALID_STATES.has(
                item.state
            )
        ) {
            throw new Error(
                `${expectedLabel}: invalid semantic state`
            );
        }

        if (
            !hasOwn(
                expectedStates,
                expectedLabel
            )
        ) {
            throw new Error(
                `${expectedLabel}: expected state is missing`
            );
        }

        if (
            item.state
            !== expectedStates[
                expectedLabel
            ]
        ) {
            throw new Error(
                `${expectedLabel}: expected state `
                + `${expectedStates[expectedLabel]}, `
                + `found ${item.state}`
            );
        }

        if (
            seen.has(
                expectedLabel
            )
        ) {
            throw new Error(
                `duplicate semantic annotation: ${expectedLabel}`
            );
        }

        seen.add(
            expectedLabel
        );
    }

    for (
        const label
        of ODORNET_LABELS
    ) {
        if (
            !seen.has(label)
        ) {
            throw new Error(
                `missing semantic annotation: ${label}`
            );
        }
    }
}


function verifyRoundTrip(graph) {
    const serialized =
        JSON.stringify(graph);

    const recovered =
        JSON.parse(serialized);

    if (
        !deepEqual(
            recovered,
            graph
        )
    ) {
        throw new Error(
            "JavaScript JSON round-trip changed the graph"
        );
    }
}


function main() {
    const args =
        parseArgs(
            process.argv.slice(2)
        );

    const document =
        JSON.parse(
            fs.readFileSync(
                args.inputPath,
                "utf8"
            )
        );

    requireObject(
        document,
        "interop document must be an object"
    );

    if (
        document.interop_test
        !== INTEROP_TEST
    ) {
        throw new Error(
            "unexpected interop_test"
        );
    }

    if (
        document.version
        !== INTEROP_VERSION
    ) {
        throw new Error(
            "unexpected interop document version"
        );
    }

    const expected =
        requireObject(
            document.expected,
            "expected must be an object"
        );

    requireNonEmptyString(
        expected.molecule_id,
        "expected.molecule_id must be a non-empty string"
    );

    requireNonEmptyString(
        expected.annotation_id,
        "expected.annotation_id must be a non-empty string"
    );

    requireNonEmptyString(
        expected.smiles,
        "expected.smiles must be a non-empty string"
    );

    const graph =
        requireObject(
            document.graph,
            "graph must be an object"
        );

    validateGraph(
        graph
    );

    if (
        graph.resources.length
        !== 2
    ) {
        throw new Error(
            "expected exactly two graph resources"
        );
    }

    const molecule =
        requireMolecule(
            graph,
            expected
        );

    const annotation =
        requireAnnotation(
            graph,
            expected
        );

    verifyPubChemInChIKey(
        molecule,
        expected
    );

    verifySubjectResolution(
        graph,
        molecule,
        annotation
    );

    verifySemanticStates(
        annotation,
        expected
    );

    verifyRoundTrip(
        graph
    );

    console.log(
        "OpenSmell enriched OdorNet JavaScript interoperability verifier"
    );

    console.log(
        "=============================================================="
    );

    console.log("");

    console.log(
        `Input: ${args.inputPath}`
    );

    console.log("");

    console.log(
        "PASS GenericResourceGraph format/version"
    );

    console.log(
        "PASS Molecule 0.1 recognition"
    );

    console.log(
        "PASS SMILES preservation"
    );

    console.log(
        "PASS PubChem InChIKey preservation"
    );

    console.log(
        "PASS Annotation 0.1 recognition"
    );

    console.log(
        "PASS Annotation subject resolution"
    );

    console.log(
        `PASS ${ODORNET_LABELS.length} OdorNet semantic states`
    );

    console.log(
        "PASS JavaScript graph round-trip preservation"
    );

    console.log("");

    console.log(
        "Molecule ID: "
        + molecule.id
    );

    console.log(
        "Annotation ID: "
        + annotation.id
    );

    console.log(
        "SMILES: "
        + molecule.smiles
    );

    console.log(
        "PubChem InChIKey: "
        + String(
            expected.pubchem_inchikey
        )
    );

    console.log("");

    console.log(
        "SUCCESS: independent JavaScript consumer understood the "
        + "real OpenSmell ResourceGraph generated from enriched OdorNet."
    );
}


main();