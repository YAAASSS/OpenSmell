"""Parity tests between the experimental ResourceGraph JSON Schema and parser.

These tests verify that the machine-readable JSON Schema and the Python
ResourceGraph parser make the same accept/reject decisions for structural
exchange-format constraints.

Graph-semantic constraints that cannot be expressed directly by the current
JSON Schema, such as uniqueness of Resource IDs across the graph, are outside
the scope of this parity suite.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from opensmell.experimental.graph_serialization import graph_from_dict


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = (
    ROOT
    / "schema"
    / "experimental-resource-graph-0.1.schema.json"
)

VECTORS_PATH = (
    ROOT
    / "examples"
    / "resource_graph_interop_vectors.json"
)


def _load_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


SCHEMA = _load_json(SCHEMA_PATH)
VECTOR_DOCUMENT = _load_json(VECTORS_PATH)

VALIDATOR = Draft202012Validator(SCHEMA)

VECTORS = VECTOR_DOCUMENT["vectors"]


def _graph(name: str) -> dict[str, Any]:
    for vector in VECTORS:
        if vector["name"] == name:
            return copy.deepcopy(vector["graph"])

    raise AssertionError(
        f"unknown interoperability vector: {name}"
    )


def _base_graph(
    resource: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resources = []

    if resource is not None:
        resources.append(resource)

    return {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": resources,
    }


def _stimulus(
    **fields: Any,
) -> dict[str, Any]:
    resource: dict[str, Any] = {
        "type": "stimulus",
        "id": "stimulus-1",
    }

    resource.update(fields)

    return resource


def _observation(
    **fields: Any,
) -> dict[str, Any]:
    resource: dict[str, Any] = {
        "type": "observation",
        "id": "observation-1",
        "stimulus": {
            "resource_id": "stimulus-1",
        },
    }

    resource.update(fields)

    return resource


def _result(
    **fields: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "scheme": {
            "id": "example.scheme",
            "version": "0.1",
        },
        "data": {},
    }

    result.update(fields)

    return result


def _schema_accepts(document: Any) -> bool:
    try:
        VALIDATOR.validate(document)
    except ValidationError:
        return False

    return True


def _parser_accepts(document: Any) -> bool:
    try:
        graph_from_dict(copy.deepcopy(document))
    except (TypeError, ValueError):
        return False

    return True


def _remove_format(
    document: dict[str, Any],
) -> None:
    del document["format"]


def _wrong_format(
    document: dict[str, Any],
) -> None:
    document["format"] = "example.invalid"


def _remove_version(
    document: dict[str, Any],
) -> None:
    del document["version"]


def _wrong_version(
    document: dict[str, Any],
) -> None:
    document["version"] = "999"


def _remove_resources(
    document: dict[str, Any],
) -> None:
    del document["resources"]


def _resources_object(
    document: dict[str, Any],
) -> None:
    document["resources"] = {}


def _mutated_basic_graph(
    mutation: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    document = _graph("basic_graph")
    mutation(document)
    return document


VALID_CASES: list[
    tuple[str, dict[str, Any]]
] = [
    (
        "empty_graph",
        _base_graph(),
    ),
    (
        "unresolved_reference",
        _base_graph(
            _stimulus(
                source={
                    "resource_id": "missing-resource",
                },
            )
        ),
    ),
    (
        "unknown_result_scheme",
        _base_graph(
            _observation(
                results=[
                    {
                        "scheme": {
                            "id": "example.unknown.scheme",
                            "version": "99",
                        },
                        "data": {
                            "anything": True,
                        },
                    },
                ],
            )
        ),
    ),
    (
        "document_extension",
        {
            **_base_graph(),
            "example_extension": {
                "future": True,
            },
        },
    ),
    (
        "stimulus_extension",
        _base_graph(
            _stimulus(
                example_extension={
                    "future": True,
                },
            )
        ),
    ),
    (
        "condition_null_value",
        _base_graph(
            _stimulus(
                conditions=[
                    {
                        "property": "example.condition",
                        "value": None,
                    },
                ],
            )
        ),
    ),
    (
        "optional_source_null",
        _base_graph(
            _stimulus(
                source=None,
            )
        ),
    ),
    (
        "optional_target_null",
        _base_graph(
            _observation(
                target=None,
            )
        ),
    ),
    (
        "empty_result_data",
        _base_graph(
            _observation(
                results=[
                    _result(),
                ],
            )
        ),
    ),
    (
        "empty_context",
        _base_graph(
            _observation(
                context={},
            )
        ),
    ),
]


INVALID_CASES: list[
    tuple[str, Any]
] = [
    (
        "document_not_object",
        [],
    ),
    (
        "missing_format",
        _mutated_basic_graph(
            _remove_format
        ),
    ),
    (
        "wrong_format",
        _mutated_basic_graph(
            _wrong_format
        ),
    ),
    (
        "missing_version",
        _mutated_basic_graph(
            _remove_version
        ),
    ),
    (
        "wrong_version",
        _mutated_basic_graph(
            _wrong_version
        ),
    ),
    (
        "missing_resources",
        _mutated_basic_graph(
            _remove_resources
        ),
    ),
    (
        "resources_not_array",
        _mutated_basic_graph(
            _resources_object
        ),
    ),
    (
        "resource_not_object",
        _base_graph(
            "not-a-resource"  # type: ignore[arg-type]
        ),
    ),
    (
        "resource_missing_type",
        _base_graph(
            {
                "id": "resource-1",
            }
        ),
    ),
    (
        "unknown_resource_type",
        _base_graph(
            {
                "type": "future_resource",
                "id": "resource-1",
            }
        ),
    ),
    (
        "resource_missing_id",
        _base_graph(
            {
                "type": "stimulus",
            }
        ),
    ),
    (
        "resource_empty_id",
        _base_graph(
            {
                "type": "stimulus",
                "id": "",
            }
        ),
    ),
    (
        "resource_non_string_id",
        _base_graph(
            {
                "type": "stimulus",
                "id": 123,
            }
        ),
    ),
    (
        "reference_missing_resource_id",
        _base_graph(
            _stimulus(
                source={},
            )
        ),
    ),
    (
        "reference_empty_resource_id",
        _base_graph(
            _stimulus(
                source={
                    "resource_id": "",
                },
            )
        ),
    ),
    (
        "reference_non_string_resource_id",
        _base_graph(
            _stimulus(
                source={
                    "resource_id": 123,
                },
            )
        ),
    ),
    (
        "source_not_reference",
        _base_graph(
            _stimulus(
                source="molecule-1",
            )
        ),
    ),
    (
        "identifiers_not_array",
        _base_graph(
            _stimulus(
                identifiers={},
            )
        ),
    ),
    (
        "identifier_not_object",
        _base_graph(
            _stimulus(
                identifiers=[
                    "identifier",
                ],
            )
        ),
    ),
    (
        "identifier_missing_scheme",
        _base_graph(
            _stimulus(
                identifiers=[
                    {
                        "value": "123",
                    },
                ],
            )
        ),
    ),
    (
        "identifier_missing_value",
        _base_graph(
            _stimulus(
                identifiers=[
                    {
                        "scheme": "example.id",
                    },
                ],
            )
        ),
    ),
    (
        "identifier_empty_scheme",
        _base_graph(
            _stimulus(
                identifiers=[
                    {
                        "scheme": "",
                        "value": "123",
                    },
                ],
            )
        ),
    ),
    (
        "identifier_empty_value",
        _base_graph(
            _stimulus(
                identifiers=[
                    {
                        "scheme": "example.id",
                        "value": "",
                    },
                ],
            )
        ),
    ),
    (
        "conditions_not_array",
        _base_graph(
            _stimulus(
                conditions={},
            )
        ),
    ),
    (
        "condition_not_object",
        _base_graph(
            _stimulus(
                conditions=[
                    "condition",
                ],
            )
        ),
    ),
    (
        "condition_missing_property",
        _base_graph(
            _stimulus(
                conditions=[
                    {
                        "value": 1.0,
                    },
                ],
            )
        ),
    ),
    (
        "condition_missing_value",
        _base_graph(
            _stimulus(
                conditions=[
                    {
                        "property": "concentration",
                    },
                ],
            )
        ),
    ),
    (
        "condition_empty_property",
        _base_graph(
            _stimulus(
                conditions=[
                    {
                        "property": "",
                        "value": 1.0,
                    },
                ],
            )
        ),
    ),
    (
        "condition_empty_unit",
        _base_graph(
            _stimulus(
                conditions=[
                    {
                        "property": "concentration",
                        "value": 1.0,
                        "unit": "",
                    },
                ],
            )
        ),
    ),
    (
        "condition_non_string_unit",
        _base_graph(
            _stimulus(
                conditions=[
                    {
                        "property": "concentration",
                        "value": 1.0,
                        "unit": 123,
                    },
                ],
            )
        ),
    ),
    (
        "observation_missing_stimulus",
        _base_graph(
            {
                "type": "observation",
                "id": "observation-1",
            }
        ),
    ),
    (
        "observation_stimulus_not_reference",
        _base_graph(
            _observation(
                stimulus="stimulus-1",
            )
        ),
    ),
    (
        "observation_target_not_reference_or_null",
        _base_graph(
            _observation(
                target="target-1",
            )
        ),
    ),
    (
        "observation_results_not_array",
        _base_graph(
            _observation(
                results={},
            )
        ),
    ),
    (
        "observation_context_not_object",
        _base_graph(
            _observation(
                context=[],
            )
        ),
    ),
    (
        "observation_identifiers_not_array",
        _base_graph(
            _observation(
                identifiers={},
            )
        ),
    ),
    (
        "result_not_object",
        _base_graph(
            _observation(
                results=[
                    "result",
                ],
            )
        ),
    ),
    (
        "result_missing_scheme",
        _base_graph(
            _observation(
                results=[
                    {
                        "data": {},
                    },
                ],
            )
        ),
    ),
    (
        "result_missing_data",
        _base_graph(
            _observation(
                results=[
                    {
                        "scheme": {
                            "id": "example.scheme",
                            "version": "0.1",
                        },
                    },
                ],
            )
        ),
    ),
    (
        "result_data_not_object",
        _base_graph(
            _observation(
                results=[
                    _result(
                        data=[],
                    ),
                ],
            )
        ),
    ),
    (
        "result_scheme_not_object",
        _base_graph(
            _observation(
                results=[
                    {
                        "scheme": "example.scheme",
                        "data": {},
                    },
                ],
            )
        ),
    ),
    (
        "result_scheme_missing_id",
        _base_graph(
            _observation(
                results=[
                    {
                        "scheme": {
                            "version": "0.1",
                        },
                        "data": {},
                    },
                ],
            )
        ),
    ),
    (
        "result_scheme_missing_version",
        _base_graph(
            _observation(
                results=[
                    {
                        "scheme": {
                            "id": "example.scheme",
                        },
                        "data": {},
                    },
                ],
            )
        ),
    ),
    (
        "result_scheme_empty_id",
        _base_graph(
            _observation(
                results=[
                    {
                        "scheme": {
                            "id": "",
                            "version": "0.1",
                        },
                        "data": {},
                    },
                ],
            )
        ),
    ),
    (
        "result_scheme_empty_version",
        _base_graph(
            _observation(
                results=[
                    {
                        "scheme": {
                            "id": "example.scheme",
                            "version": "",
                        },
                        "data": {},
                    },
                ],
            )
        ),
    ),
]


@pytest.mark.parametrize(
    ("vector_name", "document"),
    [
        (
            vector["name"],
            vector["graph"],
        )
        for vector in VECTORS
    ],
)
def test_golden_vectors_have_schema_parser_parity(
    vector_name: str,
    document: dict[str, Any],
) -> None:
    schema_accepts = _schema_accepts(document)
    parser_accepts = _parser_accepts(document)

    assert schema_accepts, (
        f"JSON Schema unexpectedly rejected "
        f"golden vector {vector_name!r}"
    )

    assert parser_accepts, (
        f"Python parser unexpectedly rejected "
        f"golden vector {vector_name!r}"
    )

    assert schema_accepts == parser_accepts


@pytest.mark.parametrize(
    ("case_name", "document"),
    VALID_CASES,
)
def test_valid_documents_have_schema_parser_parity(
    case_name: str,
    document: dict[str, Any],
) -> None:
    schema_accepts = _schema_accepts(document)
    parser_accepts = _parser_accepts(document)

    assert schema_accepts, (
        f"JSON Schema unexpectedly rejected "
        f"valid case {case_name!r}"
    )

    assert parser_accepts, (
        f"Python parser unexpectedly rejected "
        f"valid case {case_name!r}"
    )

    assert schema_accepts == parser_accepts


@pytest.mark.parametrize(
    ("case_name", "document"),
    INVALID_CASES,
)
def test_invalid_documents_have_schema_parser_parity(
    case_name: str,
    document: Any,
) -> None:
    schema_accepts = _schema_accepts(document)
    parser_accepts = _parser_accepts(document)

    assert not schema_accepts, (
        f"JSON Schema unexpectedly accepted "
        f"invalid case {case_name!r}"
    )

    assert not parser_accepts, (
        f"Python parser unexpectedly accepted "
        f"invalid case {case_name!r}"
    )

    assert schema_accepts == parser_accepts