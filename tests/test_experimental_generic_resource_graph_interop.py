from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from opensmell.experimental.generic_graph import (
    GenericResource,
    GenericResourceGraph,
    ResourceTypeRegistry,
    create_default_resource_type_registry,
    generic_graph_from_dict,
    generic_graph_to_dict,
)
from opensmell.experimental.resources import Stimulus


ROOT = Path(__file__).resolve().parents[1]

VECTORS_PATH = (
    ROOT
    / "examples"
    / "generic_resource_graph_interop_vectors.json"
)

EXPECTED_VECTOR_SET = (
    "org.opensmell.experimental.generic-resource-graph.interop-vectors"
)
EXPECTED_VECTOR_VERSION = "0.1"
EXPECTED_GRAPH_FORMAT = (
    "org.opensmell.experimental.generic-resource-graph"
)
EXPECTED_GRAPH_VERSION = "0.1"

EXPECTED_VECTOR_NAMES = (
    "known_version_0_1",
    "known_version_0_2",
    "unknown_future_version",
    "unknown_resource_type",
    "legacy_rfc0007_resource",
    "mixed_graph",
    "extensions_and_unicode",
)

INTEROP_RESOURCE_TYPE = "org.example.interop.resource"


@dataclass
class InteropResourceV01:
    id: str
    value: int
    label: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class InteropResourceV02:
    id: str
    value: int
    label: str
    extra: dict[str, Any] = field(default_factory=dict)


def _parse_interop_resource(
    value: Any,
    *,
    expected_version: str,
    python_type: type[InteropResourceV01] | type[InteropResourceV02],
) -> InteropResourceV01 | InteropResourceV02:
    assert isinstance(value, dict)
    assert value.get("type") == INTEROP_RESOURCE_TYPE
    assert value.get("type_version") == expected_version

    resource_id = value.get("id")
    resource_value = value.get("value")
    label = value.get("label")

    if not isinstance(resource_id, str) or not resource_id:
        raise ValueError("interop resource id must be a non-empty string")
    if not isinstance(resource_value, int) or isinstance(resource_value, bool):
        raise TypeError("interop resource value must be an integer")
    if not isinstance(label, str) or not label:
        raise ValueError("interop resource label must be a non-empty string")

    extra = {
        key: item
        for key, item in value.items()
        if key not in {"type", "type_version", "id", "value", "label"}
    }

    return python_type(
        id=resource_id,
        value=resource_value,
        label=label,
        extra=extra,
    )


def parse_v01(value: Any) -> InteropResourceV01:
    resource = _parse_interop_resource(
        value,
        expected_version="0.1",
        python_type=InteropResourceV01,
    )
    assert isinstance(resource, InteropResourceV01)
    return resource


def parse_v02(value: Any) -> InteropResourceV02:
    resource = _parse_interop_resource(
        value,
        expected_version="0.2",
        python_type=InteropResourceV02,
    )
    assert isinstance(resource, InteropResourceV02)
    return resource


def _serialize_interop_resource(
    resource: InteropResourceV01 | InteropResourceV02,
    *,
    version: str,
) -> dict[str, Any]:
    result = dict(resource.extra)
    result.update({
        "type": INTEROP_RESOURCE_TYPE,
        "type_version": version,
        "id": resource.id,
        "value": resource.value,
        "label": resource.label,
    })
    return result


def serialize_v01(resource: InteropResourceV01) -> dict[str, Any]:
    return _serialize_interop_resource(resource, version="0.1")


def serialize_v02(resource: InteropResourceV02) -> dict[str, Any]:
    return _serialize_interop_resource(resource, version="0.2")


def create_interop_registry() -> ResourceTypeRegistry:
    registry = create_default_resource_type_registry()

    registry.register(
        INTEROP_RESOURCE_TYPE,
        InteropResourceV01,
        parse_v01,
        serialize_v01,
        resource_type_version="0.1",
    )
    registry.register(
        INTEROP_RESOURCE_TYPE,
        InteropResourceV02,
        parse_v02,
        serialize_v02,
        resource_type_version="0.2",
    )

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


def vector_graph(name: str) -> dict[str, Any]:
    graph = vectors_by_name()[name]["graph"]
    assert isinstance(graph, dict)
    return graph


def test_interop_vector_document_metadata() -> None:
    document = load_vector_document()
    assert document["vector_set"] == EXPECTED_VECTOR_SET
    assert document["version"] == EXPECTED_VECTOR_VERSION
    assert document["resource_graph_format"] == EXPECTED_GRAPH_FORMAT
    assert document["resource_graph_version"] == EXPECTED_GRAPH_VERSION


def test_interop_vector_names_are_stable() -> None:
    assert tuple(vectors_by_name()) == EXPECTED_VECTOR_NAMES


@pytest.mark.parametrize("name", EXPECTED_VECTOR_NAMES)
def test_interop_vectors_parse_with_real_generic_graph_model(
    name: str,
) -> None:
    graph = generic_graph_from_dict(
        vector_graph(name),
        registry=create_interop_registry(),
    )
    assert isinstance(graph, GenericResourceGraph)


@pytest.mark.parametrize("name", EXPECTED_VECTOR_NAMES)
def test_interop_vectors_are_stable_after_python_roundtrip(
    name: str,
) -> None:
    graph_data = vector_graph(name)
    registry = create_interop_registry()
    graph = generic_graph_from_dict(graph_data, registry=registry)
    serialized = generic_graph_to_dict(graph, registry=registry)
    assert serialized == graph_data


def test_registered_versions_dispatch_to_distinct_python_types() -> None:
    registry = create_interop_registry()

    graph_01 = generic_graph_from_dict(
        vector_graph("known_version_0_1"),
        registry=registry,
    )
    graph_02 = generic_graph_from_dict(
        vector_graph("known_version_0_2"),
        registry=registry,
    )

    assert isinstance(graph_01.resources[0], InteropResourceV01)
    assert isinstance(graph_02.resources[0], InteropResourceV02)


def test_unknown_future_version_falls_back_to_generic_resource() -> None:
    registry = create_interop_registry()
    graph = generic_graph_from_dict(
        vector_graph("unknown_future_version"),
        registry=registry,
    )

    resource = graph.resources[0]
    assert isinstance(resource, GenericResource)
    assert resource.type == INTEROP_RESOURCE_TYPE
    assert resource.type_version == "99.0"
    assert resource.data["future_payload"]["enabled"] is True


def test_unknown_resource_type_falls_back_to_generic_resource() -> None:
    graph = generic_graph_from_dict(
        vector_graph("unknown_resource_type"),
        registry=create_interop_registry(),
    )

    resource = graph.resources[0]
    assert isinstance(resource, GenericResource)
    assert resource.type == "org.example.future.sensor-array"
    assert resource.type_version == "7"
    assert resource.data["channels"] == [0.1, 0.2, 0.3]


def test_legacy_rfc0007_resource_remains_unversioned_and_typed() -> None:
    registry = create_interop_registry()
    graph = generic_graph_from_dict(
        vector_graph("legacy_rfc0007_resource"),
        registry=registry,
    )

    resource = graph.resources[0]
    assert isinstance(resource, Stimulus)

    serialized = generic_graph_to_dict(graph, registry=registry)
    assert "type_version" not in serialized["resources"][0]


def test_mixed_graph_dispatches_each_resource_independently() -> None:
    registry = create_interop_registry()
    graph = generic_graph_from_dict(
        vector_graph("mixed_graph"),
        registry=registry,
    )

    assert isinstance(graph.resources[0], Stimulus)
    assert isinstance(graph.resources[1], InteropResourceV01)
    assert isinstance(graph.resources[2], GenericResource)
    assert isinstance(graph.resources[3], GenericResource)

    assert graph.extra["graph_extension"]["producer"] == (
        "OpenSmell RFC-0008 interoperability test"
    )


def test_extensions_and_unicode_survive_python_roundtrip() -> None:
    registry = create_interop_registry()
    graph_data = vector_graph("extensions_and_unicode")
    graph = generic_graph_from_dict(graph_data, registry=registry)
    serialized = generic_graph_to_dict(graph, registry=registry)

    assert serialized == graph_data
    assert serialized["unicode_graph_extension"] == "éèê-日本語-🚀"
    assert serialized["resources"][0]["label"] == "café-香り-🌹"
    assert (
        serialized["resources"][0]["resource_extension"]["russian"]
        == "запах"
    )
    assert serialized["resources"][1]["type_version"] == "β1"
