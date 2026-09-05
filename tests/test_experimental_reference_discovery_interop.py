"""RFC-0011 portable structural reference discovery interoperability tests.

These tests use language-independent JSON vectors and the real RFC-0008,
RFC-0009, RFC-0010, and RFC-0011 experimental Python implementation.

The vectors intentionally distinguish structural References from Reference-like
JSON stored in opaque payloads and extensions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from opensmell.experimental.annotation import (
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
    Molecule,
    register_molecule_resource_type,
)
from opensmell.experimental.reference_discovery import (
    ReferenceIndex,
    build_reference_index,
    discover_graph_references,
)


ROOT = Path(__file__).resolve().parents[1]
VECTORS_PATH = ROOT / "examples" / "reference_discovery_interop_vectors.json"

EXPECTED_VECTOR_SET = (
    "org.opensmell.experimental.reference-discovery.interop-vectors"
)
EXPECTED_VECTOR_VERSION = "0.1"
EXPECTED_GRAPH_FORMAT = "org.opensmell.experimental.generic-resource-graph"
EXPECTED_GRAPH_VERSION = "0.1"

EXPECTED_VECTOR_NAMES = (
    "annotation_to_molecule",
    "unresolved_annotation_subject",
    "unknown_resource_is_opaque",
    "future_annotation_version_is_opaque",
    "multiple_annotations_preserve_graph_order",
    "opaque_payloads_do_not_create_edges",
    "unicode_ids_and_reference_extensions",
)


def create_interop_registry() -> ResourceTypeRegistry:
    registry = create_default_resource_type_registry()
    register_molecule_resource_type(registry)
    register_annotation_resource_type(registry)
    return registry


def load_vector_document() -> dict[str, Any]:
    with VECTORS_PATH.open("r", encoding="utf-8") as file:
        value = json.load(file)
    assert isinstance(value, dict)
    return value


def vectors_by_name() -> dict[str, dict[str, Any]]:
    document = load_vector_document()
    vectors = document["vectors"]
    assert isinstance(vectors, list)

    result: dict[str, dict[str, Any]] = {}
    for vector in vectors:
        assert isinstance(vector, dict)
        name = vector["name"]
        assert isinstance(name, str)
        assert name
        assert name not in result
        result[name] = vector
    return result


def vector(name: str) -> dict[str, Any]:
    return vectors_by_name()[name]


def parse_vector_graph(name: str) -> GenericResourceGraph:
    graph_data = vector(name)["graph"]
    assert isinstance(graph_data, dict)
    return generic_graph_from_dict(
        graph_data,
        registry=create_interop_registry(),
    )


def expected_pairs(name: str) -> list[tuple[str, str]]:
    edges = vector(name)["expected_edges"]
    assert isinstance(edges, list)
    return [
        (edge["source_id"], edge["target_id"])
        for edge in edges
    ]


def discovered_pairs(graph: GenericResourceGraph) -> list[tuple[str, str]]:
    return [
        (edge.source_id, edge.reference.resource_id)
        for edge in discover_graph_references(graph)
    ]


def index_pairs(index: ReferenceIndex) -> list[tuple[str, str]]:
    return [
        (edge.source_id, edge.reference.resource_id)
        for edge in index.references()
    ]


def test_vector_document_metadata() -> None:
    document = load_vector_document()
    assert document["vector_set"] == EXPECTED_VECTOR_SET
    assert document["version"] == EXPECTED_VECTOR_VERSION
    assert document["resource_graph_format"] == EXPECTED_GRAPH_FORMAT
    assert document["resource_graph_version"] == EXPECTED_GRAPH_VERSION


def test_vector_names_are_stable() -> None:
    assert tuple(vectors_by_name()) == EXPECTED_VECTOR_NAMES


@pytest.mark.parametrize("name", EXPECTED_VECTOR_NAMES)
def test_vectors_parse_with_real_generic_graph(name: str) -> None:
    graph = parse_vector_graph(name)
    assert isinstance(graph, GenericResourceGraph)


@pytest.mark.parametrize("name", EXPECTED_VECTOR_NAMES)
def test_vectors_roundtrip_without_transport_changes(name: str) -> None:
    graph_data = vector(name)["graph"]
    registry = create_interop_registry()
    graph = generic_graph_from_dict(graph_data, registry=registry)
    recovered = generic_graph_to_dict(graph, registry=registry)
    assert recovered == graph_data


@pytest.mark.parametrize("name", EXPECTED_VECTOR_NAMES)
def test_direct_discovery_matches_portable_expected_edges(name: str) -> None:
    graph = parse_vector_graph(name)
    assert discovered_pairs(graph) == expected_pairs(name)


@pytest.mark.parametrize("name", EXPECTED_VECTOR_NAMES)
def test_reference_index_matches_portable_expected_edges(name: str) -> None:
    graph = parse_vector_graph(name)
    index = build_reference_index(graph)
    assert index_pairs(index) == expected_pairs(name)


@pytest.mark.parametrize("name", EXPECTED_VECTOR_NAMES)
def test_resolved_and_unresolved_counts_match(name: str) -> None:
    graph = parse_vector_graph(name)
    index = build_reference_index(graph)
    item = vector(name)

    assert len(index.resolved()) == item["expected_resolved"]
    assert len(index.unresolved()) == item["expected_unresolved"]
    assert len(index) == len(item["expected_edges"])


@pytest.mark.parametrize("name", EXPECTED_VECTOR_NAMES)
def test_outgoing_navigation_matches_expected_edges(name: str) -> None:
    graph = parse_vector_graph(name)
    index = build_reference_index(graph)

    expected = expected_pairs(name)
    source_ids = [resource.id for resource in graph.resources]

    for source_id in source_ids:
        actual = [
            (edge.source_id, edge.reference.resource_id)
            for edge in index.references_from(source_id)
        ]
        wanted = [
            pair for pair in expected
            if pair[0] == source_id
        ]
        assert actual == wanted


@pytest.mark.parametrize("name", EXPECTED_VECTOR_NAMES)
def test_incoming_navigation_matches_expected_edges(name: str) -> None:
    graph = parse_vector_graph(name)
    index = build_reference_index(graph)

    expected = expected_pairs(name)
    target_ids = list(dict.fromkeys(target for _, target in expected))

    for target_id in target_ids:
        actual = [
            (edge.source_id, edge.reference.resource_id)
            for edge in index.references_to(target_id)
        ]
        wanted = [
            pair for pair in expected
            if pair[1] == target_id
        ]
        assert actual == wanted


def test_annotation_and_molecule_dispatch_are_typed() -> None:
    graph = parse_vector_graph("annotation_to_molecule")
    assert isinstance(graph.resources[0], Molecule)
    assert isinstance(graph.resources[1], Annotation)


def test_unknown_resource_is_generic_and_contributes_no_edges() -> None:
    graph = parse_vector_graph("unknown_resource_is_opaque")
    assert isinstance(graph.resources[1], GenericResource)
    assert discovered_pairs(graph) == []


def test_future_annotation_version_is_generic_and_contributes_no_edges() -> None:
    graph = parse_vector_graph("future_annotation_version_is_opaque")
    future = graph.resources[1]
    assert isinstance(future, GenericResource)
    assert future.type == "org.opensmell.annotation"
    assert future.type_version == "99.0"
    assert discovered_pairs(graph) == []


def test_opaque_payloads_create_no_false_edges() -> None:
    graph = parse_vector_graph("opaque_payloads_do_not_create_edges")
    assert discovered_pairs(graph) == [
        ("annotation-real", "molecule-real")
    ]


def test_reference_extensions_survive_discovery() -> None:
    graph = parse_vector_graph("unicode_ids_and_reference_extensions")
    edges = discover_graph_references(graph)

    assert len(edges) == 1
    assert edges[0].reference.resource_id == "molécule-日本語-🧪"
    assert edges[0].reference.extra["note"] == "référence-参照"


def test_unresolved_target_is_queryable_by_incoming_index() -> None:
    graph = parse_vector_graph("unresolved_annotation_subject")
    index = ReferenceIndex(graph)

    incoming = index.references_to("missing-resource")
    assert len(incoming) == 1
    assert incoming[0].source_id == "annotation-unresolved"
    assert index.resolve(incoming[0]) is None


def test_multiple_annotations_preserve_discovery_order() -> None:
    graph = parse_vector_graph("multiple_annotations_preserve_graph_order")
    assert discovered_pairs(graph) == [
        ("annotation-b", "molecule-b"),
        ("annotation-a", "molecule-a"),
        ("annotation-missing", "missing-z"),
    ]
