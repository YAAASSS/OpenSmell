from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from opensmell.experimental.graph_serialization import (
    graph_from_dict,
    graph_to_dict,
)


SOURCE_PATH = Path("examples/resource_graph_interop_vectors.json")
JAVASCRIPT_PATH = Path("examples/resource_graph_interop_vectors_js.json")

EXPECTED_VECTOR_SET = (
    "org.opensmell.experimental.resource-graph.interop-vectors"
)
EXPECTED_VERSION = "0.1"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)

    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")

    return value


def vectors_by_name(
    document: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    vectors = document.get("vectors")

    if not isinstance(vectors, list):
        raise ValueError("vectors must be a JSON array")

    result: dict[str, dict[str, Any]] = {}

    for vector in vectors:
        if not isinstance(vector, dict):
            raise ValueError("each vector must be a JSON object")

        name = vector.get("name")

        if not isinstance(name, str) or not name:
            raise ValueError("each vector must have a non-empty name")

        if name in result:
            raise ValueError(f"duplicate vector name: {name}")

        result[name] = vector

    return result


def is_negative_zero(value: Any) -> bool:
    return (
        isinstance(value, float)
        and value == 0.0
        and math.copysign(1.0, value) < 0.0
    )


def normalize_known_json_runtime_difference(
    vector_name: str,
    graph: dict[str, Any],
) -> dict[str, Any]:
    """
    Normalize only explicitly documented cross-runtime JSON behavior.

    JavaScript JSON.stringify() serializes -0 as 0. This function does
    not perform general numeric normalization. It handles only the
    dedicated interoperability vector that intentionally exercises
    negative zero.
    """

    if vector_name != "negative_zero":
        return graph

    normalized = json.loads(
        json.dumps(
            graph,
            ensure_ascii=False,
            allow_nan=False,
        )
    )

    resources = normalized.get("resources")

    if not isinstance(resources, list):
        raise ValueError("negative_zero graph has no resources array")

    for resource in resources:
        if (
            isinstance(resource, dict)
            and resource.get("type") == "observation"
        ):
            results = resource.get("results")

            if (
                isinstance(results, list)
                and results
                and isinstance(results[0], dict)
            ):
                data = results[0].get("data")

                if isinstance(data, dict):
                    value = data.get("value")

                    if value == 0:
                        data["value"] = 0.0

    return normalized


def verify_metadata(
    source: dict[str, Any],
    javascript: dict[str, Any],
) -> None:
    if source.get("vector_set") != EXPECTED_VECTOR_SET:
        raise ValueError("unexpected source vector_set")

    if javascript.get("vector_set") != EXPECTED_VECTOR_SET:
        raise ValueError("unexpected JavaScript vector_set")

    if source.get("version") != EXPECTED_VERSION:
        raise ValueError("unexpected source vector version")

    if javascript.get("version") != EXPECTED_VERSION:
        raise ValueError("unexpected JavaScript vector version")

    for key in (
        "resource_graph_format",
        "resource_graph_version",
    ):
        if source.get(key) != javascript.get(key):
            raise ValueError(f"document metadata mismatch: {key}")


def verify_negative_zero_behavior(
    source_vectors: dict[str, dict[str, Any]],
    javascript_vectors: dict[str, dict[str, Any]],
) -> None:
    source_graph = graph_from_dict(
        source_vectors["negative_zero"]["graph"]
    )

    javascript_graph = graph_from_dict(
        javascript_vectors["negative_zero"]["graph"]
    )

    source_dict = graph_to_dict(source_graph)
    javascript_dict = graph_to_dict(javascript_graph)

    source_value: Any = None
    javascript_value: Any = None

    for resource in source_dict["resources"]:
        if resource["type"] == "observation":
            source_value = resource["results"][0]["data"]["value"]

    for resource in javascript_dict["resources"]:
        if resource["type"] == "observation":
            javascript_value = resource["results"][0]["data"]["value"]

    if not is_negative_zero(source_value):
        raise AssertionError(
            "Python source vector did not preserve -0.0"
        )

    if javascript_value != 0:
        raise AssertionError(
            "JavaScript round-trip value is not numeric zero"
        )

    if is_negative_zero(javascript_value):
        raise AssertionError(
            "JavaScript JSON unexpectedly preserved negative-zero sign"
        )


def verify_vector(
    name: str,
    source_vector: dict[str, Any],
    javascript_vector: dict[str, Any],
) -> None:
    source_graph_data = source_vector.get("graph")
    javascript_graph_data = javascript_vector.get("graph")

    if not isinstance(source_graph_data, dict):
        raise ValueError(f"{name}: source graph must be an object")

    if not isinstance(javascript_graph_data, dict):
        raise ValueError(
            f"{name}: JavaScript graph must be an object"
        )

    # This comparison intentionally occurs after both documents have been
    # parsed into the real Python ResourceGraph model and serialized again.

    source_graph = graph_from_dict(source_graph_data)
    javascript_graph = graph_from_dict(javascript_graph_data)

    source_canonical = graph_to_dict(source_graph)
    javascript_canonical = graph_to_dict(javascript_graph)

    if name == "negative_zero":
        source_canonical = normalize_known_json_runtime_difference(
            name,
            source_canonical,
        )

        javascript_canonical = normalize_known_json_runtime_difference(
            name,
            javascript_canonical,
        )

    if source_canonical != javascript_canonical:
        raise AssertionError(
            f"{name}: ResourceGraph semantic mismatch"
        )


def main() -> None:
    source = load_json(SOURCE_PATH)
    javascript = load_json(JAVASCRIPT_PATH)

    verify_metadata(source, javascript)

    source_vectors = vectors_by_name(source)
    javascript_vectors = vectors_by_name(javascript)

    if source_vectors.keys() != javascript_vectors.keys():
        raise AssertionError(
            "vector sets differ between Python and JavaScript"
        )

    print(
        "OpenSmell ResourceGraph Python/JavaScript round-trip verification"
    )
    print("=" * 72)
    print(f"Source : {SOURCE_PATH}")
    print(f"JS     : {JAVASCRIPT_PATH}")
    print(f"Vectors: {len(source_vectors)}")
    print()

    for name, source_vector in source_vectors.items():
        verify_vector(
            name,
            source_vector,
            javascript_vectors[name],
        )

        print(f"  PASS  {name}")

    verify_negative_zero_behavior(
        source_vectors,
        javascript_vectors,
    )

    print()
    print(
        "  INFO  -0.0 -> JavaScript JSON -> 0 is explicitly recognized"
    )
    print()
    print("SUCCESS")
    print(
        "All ResourceGraph vectors survived "
        "Python -> JSON -> JavaScript -> JSON -> Python "
        "with semantic equivalence."
    )


if __name__ == "__main__":
    main()