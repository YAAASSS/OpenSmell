from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opensmell.experimental.generic_graph import (
    ResourceTypeRegistry,
    create_default_resource_type_registry,
    generic_graph_from_dict,
    generic_graph_to_dict,
)


ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = (
    ROOT
    / "examples"
    / "generic_resource_graph_interop_vectors_js.json"
)

EXPECTED_VECTOR_SET = (
    "org.opensmell.experimental.generic-resource-graph.interop-vectors"
)

EXPECTED_VECTOR_VERSION = "0.1"

EXPECTED_GRAPH_FORMAT = (
    "org.opensmell.experimental.generic-resource-graph"
)

EXPECTED_GRAPH_VERSION = "0.1"

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
    if not isinstance(value, dict):
        raise TypeError(
            "interop resource must be an object"
        )

    if value.get("type") != INTEROP_RESOURCE_TYPE:
        raise ValueError(
            "unexpected interop resource type"
        )

    if value.get("type_version") != expected_version:
        raise ValueError(
            "unexpected interop resource type_version"
        )

    resource_id = value.get("id")
    resource_value = value.get("value")
    label = value.get("label")

    if (
        not isinstance(resource_id, str)
        or not resource_id
    ):
        raise ValueError(
            "interop resource id must be a non-empty string"
        )

    if (
        not isinstance(resource_value, int)
        or isinstance(resource_value, bool)
    ):
        raise TypeError(
            "interop resource value must be an integer"
        )

    if (
        not isinstance(label, str)
        or not label
    ):
        raise ValueError(
            "interop resource label must be a non-empty string"
        )

    extra = {
        key: item
        for key, item in value.items()
        if key
        not in {
            "type",
            "type_version",
            "id",
            "value",
            "label",
        }
    }

    return python_type(
        id=resource_id,
        value=resource_value,
        label=label,
        extra=extra,
    )


def parse_v01(
    value: Any,
) -> InteropResourceV01:
    resource = _parse_interop_resource(
        value,
        expected_version="0.1",
        python_type=InteropResourceV01,
    )

    if not isinstance(
        resource,
        InteropResourceV01,
    ):
        raise TypeError(
            "0.1 parser returned unexpected resource type"
        )

    return resource


def parse_v02(
    value: Any,
) -> InteropResourceV02:
    resource = _parse_interop_resource(
        value,
        expected_version="0.2",
        python_type=InteropResourceV02,
    )

    if not isinstance(
        resource,
        InteropResourceV02,
    ):
        raise TypeError(
            "0.2 parser returned unexpected resource type"
        )

    return resource


def _serialize_interop_resource(
    resource: InteropResourceV01 | InteropResourceV02,
    *,
    version: str,
) -> dict[str, Any]:
    result = dict(resource.extra)

    result.update(
        {
            "type": INTEROP_RESOURCE_TYPE,
            "type_version": version,
            "id": resource.id,
            "value": resource.value,
            "label": resource.label,
        }
    )

    return result


def serialize_v01(
    resource: InteropResourceV01,
) -> dict[str, Any]:
    return _serialize_interop_resource(
        resource,
        version="0.1",
    )


def serialize_v02(
    resource: InteropResourceV02,
) -> dict[str, Any]:
    return _serialize_interop_resource(
        resource,
        version="0.2",
    )


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


def main() -> int:
    with INPUT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        document = json.load(file)

    if not isinstance(document, dict):
        raise TypeError(
            "vector document must be an object"
        )

    if (
        document.get("vector_set")
        != EXPECTED_VECTOR_SET
    ):
        raise ValueError(
            "unexpected vector_set"
        )

    if (
        document.get("version")
        != EXPECTED_VECTOR_VERSION
    ):
        raise ValueError(
            "unexpected vector version"
        )

    if (
        document.get("resource_graph_format")
        != EXPECTED_GRAPH_FORMAT
    ):
        raise ValueError(
            "unexpected resource graph format"
        )

    if (
        document.get("resource_graph_version")
        != EXPECTED_GRAPH_VERSION
    ):
        raise ValueError(
            "unexpected resource graph version"
        )

    vectors = document.get("vectors")

    if not isinstance(vectors, list):
        raise TypeError(
            "vectors must be a list"
        )

    registry = create_interop_registry()

    for vector in vectors:
        if not isinstance(vector, dict):
            raise TypeError(
                "vector must be an object"
            )

        name = vector.get("name")
        graph_data = vector.get("graph")

        if (
            not isinstance(name, str)
            or not name
        ):
            raise ValueError(
                "vector name must be a non-empty string"
            )

        if not isinstance(graph_data, dict):
            raise TypeError(
                f"{name}: graph must be an object"
            )

        graph = generic_graph_from_dict(
            graph_data,
            registry=registry,
        )

        serialized = generic_graph_to_dict(
            graph,
            registry=registry,
        )

        if serialized != graph_data:
            raise AssertionError(
                f"{name}: Python changed the "
                "JavaScript round-trip output"
            )

        print(
            f"PASS {name}"
        )

    print()

    print(
        "SUCCESS: Python accepted and preserved all "
        f"{len(vectors)} JavaScript "
        "Generic ResourceGraph vectors."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())