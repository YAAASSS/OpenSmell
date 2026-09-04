"""Portable Generic ResourceGraph conformance vector tests.

These tests consume the language-independent conformance vectors stored in:

    examples/generic_resource_graph_conformance_vectors.json

Each vector declares whether a Generic ResourceGraph document is structurally
valid.

The same document is checked against:

1. the experimental Generic ResourceGraph JSON Schema;
2. the experimental Python Generic ResourceGraph parser.

Both implementations must agree with the expected validity declared by the
vector.

Valid vectors may additionally declare ``preserve: true``. For those vectors,
the Python parser/serializer must preserve the complete document through a
dict -> GenericResourceGraph -> dict round-trip.

Preservation conformance is deliberately separate from structural validity.
The JSON Schema determines whether a document is structurally valid; it does
not define parser/serializer preservation behavior.

Registry-specific dispatch and graph-semantic constraints that are
intentionally outside the transport JSON Schema do not belong in this vector
set.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from opensmell.experimental.generic_graph import (
    generic_graph_from_dict,
    generic_graph_to_dict,
)


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = (
    ROOT
    / "schema"
    / "experimental-generic-resource-graph-0.1.schema.json"
)

VECTORS_PATH = (
    ROOT
    / "examples"
    / "generic_resource_graph_conformance_vectors.json"
)

EXPECTED_VECTOR_FORMAT = (
    "org.opensmell.experimental.generic-resource-graph-conformance"
)
EXPECTED_VECTOR_VERSION = "0.1"
EXPECTED_VECTOR_COUNT = 42
EXPECTED_VALID_VECTOR_COUNT = 12
EXPECTED_INVALID_VECTOR_COUNT = 30
EXPECTED_PRESERVATION_VECTOR_COUNT = 11


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


SCHEMA = _load_json(SCHEMA_PATH)
VECTOR_DOCUMENT = _load_json(VECTORS_PATH)


def _load_vectors() -> list[dict[str, Any]]:
    assert isinstance(VECTOR_DOCUMENT, dict)

    assert VECTOR_DOCUMENT.get("format") == EXPECTED_VECTOR_FORMAT
    assert VECTOR_DOCUMENT.get("version") == EXPECTED_VECTOR_VERSION

    vectors = VECTOR_DOCUMENT.get("vectors")
    assert isinstance(vectors, list)

    return vectors


VECTORS = _load_vectors()


def _vector_id(vector: dict[str, Any]) -> str:
    name = vector.get("name")
    if isinstance(name, str):
        return name
    return "<invalid-vector-name>"


def _schema_accepts(document: Any) -> bool:
    validator = Draft202012Validator(SCHEMA)
    return not any(validator.iter_errors(document))


def _parser_accepts(document: Any) -> bool:
    try:
        generic_graph_from_dict(document)
    except (TypeError, ValueError):
        return False

    return True


def _preservation_vectors() -> list[dict[str, Any]]:
    return [
        vector
        for vector in VECTORS
        if vector.get("preserve") is True
    ]


PRESERVATION_VECTORS = _preservation_vectors()


def test_conformance_vector_file_contains_unique_names() -> None:
    names = [vector["name"] for vector in VECTORS]

    assert len(names) == len(set(names))


def test_conformance_vector_file_contains_expected_number_of_vectors() -> None:
    assert len(VECTORS) == EXPECTED_VECTOR_COUNT


def test_conformance_vector_file_contains_expected_validity_counts() -> None:
    valid_count = sum(
        vector["valid"] is True
        for vector in VECTORS
    )
    invalid_count = sum(
        vector["valid"] is False
        for vector in VECTORS
    )

    assert valid_count == EXPECTED_VALID_VECTOR_COUNT
    assert invalid_count == EXPECTED_INVALID_VECTOR_COUNT


def test_conformance_vector_file_contains_valid_and_invalid_cases() -> None:
    expected_values = {vector["valid"] for vector in VECTORS}

    assert expected_values == {True, False}


def test_conformance_vector_file_contains_expected_preservation_cases() -> None:
    assert (
        len(PRESERVATION_VECTORS)
        == EXPECTED_PRESERVATION_VECTOR_COUNT
    )


def test_preservation_vectors_are_valid() -> None:
    for vector in PRESERVATION_VECTORS:
        assert vector["valid"] is True, (
            f"{vector['name']}: preservation vectors must be valid"
        )


@pytest.mark.parametrize("vector", VECTORS, ids=_vector_id)
def test_generic_resource_graph_conformance_vector(
    vector: dict[str, Any],
) -> None:
    assert isinstance(vector, dict)

    allowed_fields = {
        "name",
        "valid",
        "document",
        "preserve",
    }

    assert set(vector).issubset(allowed_fields)

    required_fields = {
        "name",
        "valid",
        "document",
    }

    assert required_fields.issubset(vector)

    name = vector["name"]
    expected = vector["valid"]
    document = vector["document"]
    preserve = vector.get("preserve", False)

    assert isinstance(name, str)
    assert name
    assert isinstance(expected, bool)
    assert isinstance(preserve, bool)

    if preserve:
        assert expected is True, (
            f"{name}: preserve=true requires valid=true"
        )

    schema_accepts = _schema_accepts(document)
    parser_accepts = _parser_accepts(document)

    assert schema_accepts == expected, (
        f"{name}: JSON Schema validity was {schema_accepts}, "
        f"expected {expected}"
    )

    assert parser_accepts == expected, (
        f"{name}: Python parser validity was {parser_accepts}, "
        f"expected {expected}"
    )

    assert schema_accepts == parser_accepts, (
        f"{name}: JSON Schema and Python parser disagree"
    )


@pytest.mark.parametrize(
    "vector",
    PRESERVATION_VECTORS,
    ids=_vector_id,
)
def test_generic_resource_graph_preservation_vector(
    vector: dict[str, Any],
) -> None:
    name = vector["name"]
    document = vector["document"]

    graph = generic_graph_from_dict(document)
    round_tripped = generic_graph_to_dict(graph)

    assert round_tripped == document, (
        f"{name}: Python parser/serializer did not preserve "
        "the complete document"
    )
