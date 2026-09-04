"""RFC-0010 Annotation interoperability tests.

These tests exercise the experimental Annotation resource through the real
RFC-0008 GenericResourceGraph infrastructure.

The language-independent golden vectors cover:

- Molecule and Annotation resources transported together;
- Annotation subjects resolved through ResourceGraph references;
- unresolved Annotation subjects;
- unknown Annotation schemes;
- unknown future Annotation resource versions;
- Annotation resources targeting unknown resource types;
- mixed known and unknown resources;
- extension and Unicode preservation.

Unknown resource types and unknown resource type versions must remain
transportable through RFC-0008 GenericResource fallback behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from opensmell.experimental.annotation import (
    ANNOTATION_RESOURCE_TYPE,
    ANNOTATION_RESOURCE_TYPE_VERSION,
    Annotation,
    register_annotation_resource_type,
)
from opensmell.experimental.generic_graph import (
    GenericResource,
    GenericResourceGraph,
    ResourceTypeRegistry,
    create_default_resource_type_registry,
    generic_graph_from_dict,
    generic_graph_to_dict,
)
from opensmell.experimental.molecule import (
    MOLECULE_RESOURCE_TYPE,
    MOLECULE_RESOURCE_TYPE_VERSION,
    Molecule,
    register_molecule_resource_type,
)


ROOT = Path(__file__).resolve().parents[1]

VECTORS_PATH = (
    ROOT
    / "examples"
    / "annotation_resource_graph_interop_vectors.json"
)

EXPECTED_VECTOR_SET = (
    "org.opensmell.experimental.annotation-resource-graph.interop-vectors"
)
EXPECTED_VECTOR_VERSION = "0.1"
EXPECTED_GRAPH_FORMAT = (
    "org.opensmell.experimental.generic-resource-graph"
)
EXPECTED_GRAPH_VERSION = "0.1"

EXPECTED_VECTOR_NAMES = (
    "molecule_and_annotation",
    "unresolved_annotation_subject",
    "unknown_annotation_scheme",
    "unknown_future_annotation_version",
    "unknown_resource_with_annotation",
    "mixed_molecule_annotation_unknown_and_future",
    "extensions_and_unicode",
)


def create_annotation_interop_registry() -> ResourceTypeRegistry:
    registry = create_default_resource_type_registry()

    register_molecule_resource_type(
        registry
    )
    register_annotation_resource_type(
        registry
    )

    return registry


def load_vector_document() -> dict[str, Any]:
    with VECTORS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        value = json.load(file)

    assert isinstance(
        value,
        dict,
    )

    return value


def vectors_by_name() -> dict[str, dict[str, Any]]:
    document = load_vector_document()

    vectors = document["vectors"]

    assert isinstance(
        vectors,
        list,
    )

    result: dict[str, dict[str, Any]] = {}

    for vector in vectors:
        assert isinstance(
            vector,
            dict,
        )

        name = vector["name"]

        assert isinstance(
            name,
            str,
        )
        assert name
        assert name not in result

        result[name] = vector

    return result


def vector_graph(
    name: str,
) -> dict[str, Any]:
    graph = vectors_by_name()[
        name
    ]["graph"]

    assert isinstance(
        graph,
        dict,
    )

    return graph


def test_interop_vector_document_metadata() -> None:
    document = load_vector_document()

    assert (
        document["vector_set"]
        == EXPECTED_VECTOR_SET
    )
    assert (
        document["version"]
        == EXPECTED_VECTOR_VERSION
    )
    assert (
        document["resource_graph_format"]
        == EXPECTED_GRAPH_FORMAT
    )
    assert (
        document["resource_graph_version"]
        == EXPECTED_GRAPH_VERSION
    )


def test_interop_vector_names_are_stable() -> None:
    assert (
        tuple(vectors_by_name())
        == EXPECTED_VECTOR_NAMES
    )


@pytest.mark.parametrize(
    "name",
    EXPECTED_VECTOR_NAMES,
)
def test_interop_vectors_parse_with_real_generic_graph_model(
    name: str,
) -> None:
    graph = generic_graph_from_dict(
        vector_graph(name),
        registry=create_annotation_interop_registry(),
    )

    assert isinstance(
        graph,
        GenericResourceGraph,
    )


@pytest.mark.parametrize(
    "name",
    EXPECTED_VECTOR_NAMES,
)
def test_interop_vectors_are_stable_after_python_roundtrip(
    name: str,
) -> None:
    graph_data = vector_graph(
        name
    )

    registry = (
        create_annotation_interop_registry()
    )

    graph = generic_graph_from_dict(
        graph_data,
        registry=registry,
    )

    serialized = generic_graph_to_dict(
        graph,
        registry=registry,
    )

    assert serialized == graph_data


def test_molecule_and_annotation_dispatch_to_typed_resources() -> None:
    graph = generic_graph_from_dict(
        vector_graph(
            "molecule_and_annotation"
        ),
        registry=create_annotation_interop_registry(),
    )

    assert len(graph.resources) == 2

    molecule = graph.resources[0]
    annotation = graph.resources[1]

    assert isinstance(
        molecule,
        Molecule,
    )
    assert isinstance(
        annotation,
        Annotation,
    )

    assert molecule.id == "molecule-1"
    assert annotation.id == "annotation-1"

    assert (
        annotation.subject.resource_id
        == molecule.id
    )


def test_annotation_subject_resolves_to_molecule() -> None:
    graph = generic_graph_from_dict(
        vector_graph(
            "molecule_and_annotation"
        ),
        registry=create_annotation_interop_registry(),
    )

    annotation = graph.resources[1]

    assert isinstance(
        annotation,
        Annotation,
    )

    resolved = graph.resolve(
        annotation.subject
    )

    assert isinstance(
        resolved,
        Molecule,
    )
    assert resolved.id == "molecule-1"


def test_unresolved_annotation_subject_is_valid() -> None:
    graph = generic_graph_from_dict(
        vector_graph(
            "unresolved_annotation_subject"
        ),
        registry=create_annotation_interop_registry(),
    )

    annotation = graph.resources[0]

    assert isinstance(
        annotation,
        Annotation,
    )

    assert (
        annotation.subject.resource_id
        == "molecule-not-in-graph"
    )

    assert (
        graph.resolve(
            annotation.subject
        )
        is None
    )


def test_unknown_annotation_scheme_remains_typed_annotation() -> None:
    graph = generic_graph_from_dict(
        vector_graph(
            "unknown_annotation_scheme"
        ),
        registry=create_annotation_interop_registry(),
    )

    molecule = graph.resources[0]
    annotation = graph.resources[1]

    assert isinstance(
        molecule,
        Molecule,
    )
    assert isinstance(
        annotation,
        Annotation,
    )

    assert (
        annotation.scheme.id
        == "org.example.future.annotation-scheme"
    )
    assert (
        annotation.scheme.version
        == "999"
    )
    assert (
        annotation.data[
            "future_payload"
        ]["enabled"]
        is True
    )

    assert (
        graph.resolve(
            annotation.subject
        )
        is molecule
    )


def test_unknown_future_annotation_version_falls_back_to_generic_resource() -> None:
    graph = generic_graph_from_dict(
        vector_graph(
            "unknown_future_annotation_version"
        ),
        registry=create_annotation_interop_registry(),
    )

    molecule = graph.resources[0]
    future_annotation = graph.resources[1]

    assert isinstance(
        molecule,
        Molecule,
    )

    assert isinstance(
        future_annotation,
        GenericResource,
    )

    assert (
        future_annotation.type
        == ANNOTATION_RESOURCE_TYPE
    )
    assert (
        future_annotation.type_version
        == "99.0"
    )
    assert (
        future_annotation.id
        == "annotation-future"
    )

    assert (
        future_annotation.data[
            "subject"
        ]["resource_id"]
        == "molecule-future-annotation"
    )

    assert (
        future_annotation.data[
            "new_field_from_future"
        ]["preserve_me"]
        is True
    )


def test_unknown_resource_can_be_subject_of_typed_annotation() -> None:
    graph = generic_graph_from_dict(
        vector_graph(
            "unknown_resource_with_annotation"
        ),
        registry=create_annotation_interop_registry(),
    )

    unknown_resource = graph.resources[0]
    annotation = graph.resources[1]

    assert isinstance(
        unknown_resource,
        GenericResource,
    )
    assert isinstance(
        annotation,
        Annotation,
    )

    assert (
        unknown_resource.type
        == "org.example.future.sensor"
    )

    resolved = graph.resolve(
        annotation.subject
    )

    assert resolved is unknown_resource


def test_mixed_graph_dispatches_each_resource_independently() -> None:
    graph = generic_graph_from_dict(
        vector_graph(
            "mixed_molecule_annotation_unknown_and_future"
        ),
        registry=create_annotation_interop_registry(),
    )

    assert len(graph.resources) == 4

    assert isinstance(
        graph.resources[0],
        Molecule,
    )
    assert isinstance(
        graph.resources[1],
        Annotation,
    )
    assert isinstance(
        graph.resources[2],
        GenericResource,
    )
    assert isinstance(
        graph.resources[3],
        GenericResource,
    )

    assert (
        graph.resources[2].type
        == "org.example.unknown-resource"
    )

    assert (
        graph.resources[3].type
        == ANNOTATION_RESOURCE_TYPE
    )
    assert (
        graph.resources[3].type_version
        == "99.0"
    )

    assert (
        graph.extra[
            "graph_extension"
        ]["purpose"]
        == "RFC-0010 interoperability"
    )


def test_mixed_graph_annotation_resolves_to_molecule() -> None:
    graph = generic_graph_from_dict(
        vector_graph(
            "mixed_molecule_annotation_unknown_and_future"
        ),
        registry=create_annotation_interop_registry(),
    )

    molecule = graph.resources[0]
    annotation = graph.resources[1]

    assert isinstance(
        molecule,
        Molecule,
    )
    assert isinstance(
        annotation,
        Annotation,
    )

    resolved = graph.resolve(
        annotation.subject
    )

    assert resolved is molecule


def test_mixed_graph_preserves_annotation_reference_scheme_and_extensions() -> None:
    graph_data = vector_graph(
        "mixed_molecule_annotation_unknown_and_future"
    )

    registry = (
        create_annotation_interop_registry()
    )

    graph = generic_graph_from_dict(
        graph_data,
        registry=registry,
    )

    serialized = generic_graph_to_dict(
        graph,
        registry=registry,
    )

    assert serialized == graph_data

    annotation = serialized[
        "resources"
    ][1]

    assert (
        annotation[
            "subject"
        ][
            "relationship_extension"
        ]
        == "primary-subject"
    )

    assert (
        annotation[
            "scheme"
        ][
            "vocabulary_extension"
        ]
        == "odornet-12"
    )

    assert (
        annotation[
            "provenance"
        ][
            "source"
        ]
        == "interop-test"
    )


def test_extensions_and_unicode_survive_python_roundtrip() -> None:
    graph_data = vector_graph(
        "extensions_and_unicode"
    )

    registry = (
        create_annotation_interop_registry()
    )

    graph = generic_graph_from_dict(
        graph_data,
        registry=registry,
    )

    serialized = generic_graph_to_dict(
        graph,
        registry=registry,
    )

    assert serialized == graph_data

    molecule = serialized[
        "resources"
    ][0]

    annotation = serialized[
        "resources"
    ][1]

    assert (
        molecule["id"]
        == "molécule-日本語-🧪"
    )

    assert (
        annotation["id"]
        == "аннотация-🌸"
    )

    assert (
        annotation[
            "subject"
        ][
            "reference_extension"
        ]
        == "référence-参照"
    )

    assert (
        annotation[
            "scheme"
        ][
            "scheme_extension"
        ]
        == "éèê-日本語"
    )

    assert (
        annotation[
            "data"
        ][
            "description"
        ]
        == "café-香り-🌹"
    )

    assert (
        annotation[
            "annotation_extension"
        ][
            "russian"
        ]
        == "запах"
    )

    assert (
        serialized[
            "unicode_graph_extension"
        ]
        == "éèê-日本語-🚀"
    )


def test_registered_contracts_are_exact() -> None:
    registry = (
        create_annotation_interop_registry()
    )

    molecule_handler = (
        registry.handler_for_resource_type(
            MOLECULE_RESOURCE_TYPE,
            MOLECULE_RESOURCE_TYPE_VERSION,
        )
    )

    annotation_handler = (
        registry.handler_for_resource_type(
            ANNOTATION_RESOURCE_TYPE,
            ANNOTATION_RESOURCE_TYPE_VERSION,
        )
    )

    assert molecule_handler is not None
    assert annotation_handler is not None

    assert (
        molecule_handler.python_type
        is Molecule
    )
    assert (
        annotation_handler.python_type
        is Annotation
    )

    assert (
        registry.handler_for_resource_type(
            ANNOTATION_RESOURCE_TYPE,
            "99.0",
        )
        is None
    )