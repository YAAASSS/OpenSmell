"""Portable ResourceGraph conformance vector tests.

These tests consume the language-independent conformance vectors stored in:

    examples/resource_graph_conformance_vectors.json

Each vector declares whether a ResourceGraph document is structurally valid.

The same document is checked against:

1. the experimental ResourceGraph JSON Schema;
2. the experimental Python ResourceGraph parser.

Both implementations must agree with the expected validity declared by the
vector.

Graph-semantic constraints that are intentionally outside the JSON Schema,
such as uniqueness of Resource IDs, do not belong in this vector set.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from opensmell.experimental.graph_serialization import graph_from_dict


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = ROOT / "schema" / "experimental-resource-graph-0.1.schema.json"

VECTORS_PATH = ROOT / "examples" / "resource_graph_conformance_vectors.json"

EXPECTED_VECTOR_FORMAT = (
    "org.opensmell.experimental.resource-graph-conformance"
)
EXPECTED_VECTOR_VERSION = "0.1"


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
        graph_from_dict(document)
    except (TypeError, ValueError):
        return False

    return True


def test_conformance_vector_file_contains_unique_names() -> None:
    names = [vector["name"] for vector in VECTORS]

    assert len(names) == len(set(names))


def test_conformance_vector_file_contains_expected_number_of_vectors() -> None:
    assert len(VECTORS) == 55


def test_conformance_vector_file_contains_valid_and_invalid_cases() -> None:
    expected_values = {vector["valid"] for vector in VECTORS}

    assert expected_values == {True, False}


@pytest.mark.parametrize("vector", VECTORS, ids=_vector_id)
def test_resource_graph_conformance_vector(
    vector: dict[str, Any],
) -> None:
    assert isinstance(vector, dict)

    assert set(vector) == {
        "name",
        "valid",
        "document",
    }

    name = vector["name"]
    expected = vector["valid"]
    document = vector["document"]

    assert isinstance(name, str)
    assert name
    assert isinstance(expected, bool)

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