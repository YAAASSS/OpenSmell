from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from opensmell.experimental.graph import ResourceGraph
from opensmell.experimental.graph_serialization import (
    graph_from_dict,
    graph_to_dict,
)


ROOT = Path(__file__).resolve().parents[1]

VECTORS_PATH = (
    ROOT
    / "examples"
    / "resource_graph_interop_vectors.json"
)

EXPECTED_VECTOR_SET = (
    "org.opensmell.experimental.resource-graph.interop-vectors"
)

EXPECTED_VECTOR_VERSION = "0.1"

EXPECTED_GRAPH_FORMAT = (
    "org.opensmell.experimental.resource-graph"
)

EXPECTED_GRAPH_VERSION = "0.1"

EXPECTED_VECTOR_NAMES = (
    "basic_graph",
    "unicode",
    "negative_zero",
    "unresolved_references",
    "extensions_and_unknown_scheme",
    "multiple_results",
)


def load_vector_document() -> dict[str, Any]:
    with VECTORS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
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
    vectors = vectors_by_name()

    vector = vectors[name]
    graph = vector["graph"]

    assert isinstance(graph, dict)

    return graph


def observation_from_graph_dict(
    graph: dict[str, Any],
) -> dict[str, Any]:
    resources = graph["resources"]

    assert isinstance(resources, list)

    for resource in resources:
        if (
            isinstance(resource, dict)
            and resource.get("type") == "observation"
        ):
            return resource

    raise AssertionError(
        "graph does not contain an observation"
    )


def stimulus_from_graph_dict(
    graph: dict[str, Any],
) -> dict[str, Any]:
    resources = graph["resources"]

    assert isinstance(resources, list)

    for resource in resources:
        if (
            isinstance(resource, dict)
            and resource.get("type") == "stimulus"
        ):
            return resource

    raise AssertionError(
        "graph does not contain a stimulus"
    )


def target_from_graph_dict(
    graph: dict[str, Any],
) -> dict[str, Any]:
    resources = graph["resources"]

    assert isinstance(resources, list)

    for resource in resources:
        if (
            isinstance(resource, dict)
            and resource.get("type")
            == "observation_target"
        ):
            return resource

    raise AssertionError(
        "graph does not contain an observation target"
    )


def is_negative_zero(value: Any) -> bool:
    return (
        isinstance(value, float)
        and value == 0.0
        and math.copysign(1.0, value) < 0.0
    )


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
    vectors = vectors_by_name()

    assert tuple(vectors) == EXPECTED_VECTOR_NAMES


@pytest.mark.parametrize(
    "name",
    EXPECTED_VECTOR_NAMES,
)
def test_interop_vectors_parse_with_real_resource_graph_model(
    name: str,
) -> None:
    graph_data = vector_graph(name)

    graph = graph_from_dict(graph_data)

    assert isinstance(graph, ResourceGraph)


@pytest.mark.parametrize(
    "name",
    EXPECTED_VECTOR_NAMES,
)
def test_interop_vectors_are_stable_after_python_roundtrip(
    name: str,
) -> None:
    graph_data = vector_graph(name)

    graph = graph_from_dict(graph_data)

    serialized = graph_to_dict(graph)

    assert serialized == graph_data


def test_basic_graph_preserves_structural_references() -> None:
    graph_data = vector_graph("basic_graph")

    graph = graph_from_dict(graph_data)
    serialized = graph_to_dict(graph)

    stimulus = stimulus_from_graph_dict(serialized)
    target = target_from_graph_dict(serialized)
    observation = observation_from_graph_dict(serialized)

    assert (
        observation["stimulus"]["resource_id"]
        == stimulus["id"]
    )

    assert (
        observation["target"]["resource_id"]
        == target["id"]
    )

    assert observation["results"][0]["data"]["value"] == 42.5


def test_unicode_vector_preserves_unicode_values() -> None:
    graph_data = vector_graph("unicode")

    graph = graph_from_dict(graph_data)
    serialized = graph_to_dict(graph)

    stimulus = stimulus_from_graph_dict(serialized)
    observation = observation_from_graph_dict(serialized)

    assert (
        stimulus["identifiers"][0]["value"]
        == "café-香り-🌹"
    )

    assert (
        stimulus["conditions"][0]["value"]
        == "Crème brûlée — ваниль — 香り 🌹"
    )

    assert (
        stimulus["unicode_extension"]
        == "éèê-日本語-🚀"
    )

    result_data = observation["results"][0]["data"]

    assert result_data["label"] == "café"
    assert result_data["japanese"] == "香り"
    assert result_data["russian"] == "запах"
    assert result_data["emoji"] == "🌹"


def test_negative_zero_vector_preserves_sign_in_python() -> None:
    graph_data = vector_graph("negative_zero")

    graph = graph_from_dict(graph_data)
    serialized = graph_to_dict(graph)

    observation = observation_from_graph_dict(serialized)

    value = observation["results"][0]["data"]["value"]

    assert is_negative_zero(value)


def test_unresolved_references_remain_unresolved() -> None:
    graph_data = vector_graph(
        "unresolved_references"
    )

    graph = graph_from_dict(graph_data)

    unresolved = set(
        graph.unresolved_reference_ids()
    )

    assert unresolved == {
        "88888888-8888-4888-8888-888888888888",
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    }


def test_extensions_and_unknown_result_scheme_survive() -> None:
    graph_data = vector_graph(
        "extensions_and_unknown_scheme"
    )

    graph = graph_from_dict(graph_data)
    serialized = graph_to_dict(graph)

    assert (
        serialized["graph_extension"]["producer"]
        == "OpenSmell interoperability test"
    )

    stimulus = stimulus_from_graph_dict(serialized)
    target = target_from_graph_dict(serialized)
    observation = observation_from_graph_dict(serialized)

    assert (
        stimulus["future_stimulus_field"]["enabled"]
        is True
    )

    assert (
        stimulus["future_stimulus_field"]
        ["nested"]["value"]
        == 123
    )

    assert (
        stimulus["conditions"][0]
        ["condition_extension"]["origin"]
        == "interop-test"
    )

    assert target["future_target_field"] == [
        "a",
        "b",
        "c",
    ]

    result = observation["results"][0]

    assert (
        result["scheme"]["id"]
        == "org.example.future.result-scheme"
    )

    assert result["scheme"]["version"] == "9.7"

    assert (
        result["scheme"]["scheme_extension"]
        == "preserve-me"
    )

    assert result["result_extension"] is True

    assert (
        result["data"]["arbitrary"]["nested"]
        == [1, 2, 3]
    )

    assert (
        observation["context"]["protocol"]
        == "future-protocol"
    )

    assert (
        observation["future_observation_field"]["answer"]
        == 42
    )


def test_multiple_results_preserve_order_and_schemes() -> None:
    graph_data = vector_graph(
        "multiple_results"
    )

    graph = graph_from_dict(graph_data)
    serialized = graph_to_dict(graph)

    observation = observation_from_graph_dict(serialized)

    results = observation["results"]

    assert len(results) == 3

    assert [
        result["scheme"]["id"]
        for result in results
    ] == [
        "org.opensmell.experimental.observation.categories",
        "org.opensmell.perceptual.measurements",
        "org.example.unknown",
    ]

    assert results[0]["data"]["state"] == "present"

    assert (
        results[1]["data"]["measurements"][0]["value"]
        == 75.0
    )

    assert (
        results[2]["data"]["opaque"]
        == "preserve this"
    )