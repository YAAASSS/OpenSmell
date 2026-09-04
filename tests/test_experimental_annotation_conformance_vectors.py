"""Portable Annotation resource conformance vector tests.

These tests consume the language-independent conformance vectors stored in:

    examples/annotation_conformance_vectors.json

Each vector declares whether an Annotation resource is structurally valid.

The same resource is checked against:

1. the experimental Annotation JSON Schema;
2. the experimental Python Annotation parser.

Both implementations must agree with the expected validity declared by the
vector.

Vectors marked ``preserve: true`` must additionally survive an exact
parse/serialize round trip.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from opensmell.experimental.annotation import (
    annotation_from_dict,
    annotation_to_dict,
)


ROOT = Path(__file__).resolve().parents[1]

VECTOR_PATH = (
    ROOT
    / "examples"
    / "annotation_conformance_vectors.json"
)

SCHEMA_PATH = (
    ROOT
    / "schema"
    / "experimental-annotation-0.1.schema.json"
)

EXPECTED_FORMAT = (
    "org.opensmell.experimental.annotation-conformance"
)
EXPECTED_VERSION = "0.1"

EXPECTED_VECTOR_COUNT = 44
EXPECTED_VALID_VECTOR_COUNT = 12
EXPECTED_INVALID_VECTOR_COUNT = 32
EXPECTED_PRESERVATION_VECTOR_COUNT = 12


def _load_json(
    path: Path,
) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


VECTOR_DOCUMENT = _load_json(
    VECTOR_PATH
)

SCHEMA_DOCUMENT = _load_json(
    SCHEMA_PATH
)

SCHEMA_VALIDATOR = Draft202012Validator(
    SCHEMA_DOCUMENT
)


def _vectors() -> list[dict[str, Any]]:
    assert isinstance(
        VECTOR_DOCUMENT,
        dict,
    )

    assert (
        VECTOR_DOCUMENT.get("format")
        == EXPECTED_FORMAT
    )

    assert (
        VECTOR_DOCUMENT.get("version")
        == EXPECTED_VERSION
    )

    vectors = VECTOR_DOCUMENT.get(
        "vectors"
    )

    assert isinstance(
        vectors,
        list,
    )

    return vectors


VECTORS = _vectors()


def _vector_name(
    vector: dict[str, Any],
) -> str:
    name = vector.get(
        "name"
    )

    assert isinstance(
        name,
        str,
    )
    assert name

    return name


def _schema_accepts(
    resource: Any,
) -> bool:
    return not any(
        SCHEMA_VALIDATOR.iter_errors(
            resource
        )
    )


def _python_accepts(
    resource: Any,
) -> bool:
    try:
        annotation_from_dict(
            resource
        )
    except (
        TypeError,
        ValueError,
    ):
        return False

    return True


def test_vector_document_metadata() -> None:
    assert (
        VECTOR_DOCUMENT["format"]
        == EXPECTED_FORMAT
    )
    assert (
        VECTOR_DOCUMENT["version"]
        == EXPECTED_VERSION
    )


def test_vector_count() -> None:
    assert (
        len(VECTORS)
        == EXPECTED_VECTOR_COUNT
    )


def test_vector_names_are_unique() -> None:
    names = [
        _vector_name(vector)
        for vector in VECTORS
    ]

    assert len(names) == len(
        set(names)
    )


def test_vector_structure() -> None:
    for vector in VECTORS:
        assert isinstance(
            vector,
            dict,
        )

        assert isinstance(
            vector.get("name"),
            str,
        )

        assert vector["name"]

        assert isinstance(
            vector.get("valid"),
            bool,
        )

        assert "resource" in vector

        if "preserve" in vector:
            assert isinstance(
                vector["preserve"],
                bool,
            )

            assert vector["valid"] is True


def test_expected_valid_vector_count() -> None:
    valid_vectors = [
        vector
        for vector in VECTORS
        if vector["valid"]
    ]

    assert (
        len(valid_vectors)
        == EXPECTED_VALID_VECTOR_COUNT
    )


def test_expected_invalid_vector_count() -> None:
    invalid_vectors = [
        vector
        for vector in VECTORS
        if not vector["valid"]
    ]

    assert (
        len(invalid_vectors)
        == EXPECTED_INVALID_VECTOR_COUNT
    )


def test_expected_preservation_vector_count() -> None:
    preservation_vectors = [
        vector
        for vector in VECTORS
        if vector.get(
            "preserve",
            False,
        )
    ]

    assert (
        len(preservation_vectors)
        == EXPECTED_PRESERVATION_VECTOR_COUNT
    )


@pytest.mark.parametrize(
    "vector",
    VECTORS,
    ids=_vector_name,
)
def test_schema_matches_expected_validity(
    vector: dict[str, Any],
) -> None:
    expected = vector[
        "valid"
    ]

    actual = _schema_accepts(
        vector["resource"]
    )

    assert actual is expected


@pytest.mark.parametrize(
    "vector",
    VECTORS,
    ids=_vector_name,
)
def test_python_parser_matches_expected_validity(
    vector: dict[str, Any],
) -> None:
    expected = vector[
        "valid"
    ]

    actual = _python_accepts(
        vector["resource"]
    )

    assert actual is expected


@pytest.mark.parametrize(
    "vector",
    VECTORS,
    ids=_vector_name,
)
def test_schema_and_python_parser_agree(
    vector: dict[str, Any],
) -> None:
    schema_result = _schema_accepts(
        vector["resource"]
    )

    python_result = _python_accepts(
        vector["resource"]
    )

    assert (
        schema_result
        is python_result
    )


PRESERVATION_VECTORS = [
    vector
    for vector in VECTORS
    if vector.get(
        "preserve",
        False,
    )
]


@pytest.mark.parametrize(
    "vector",
    PRESERVATION_VECTORS,
    ids=_vector_name,
)
def test_preservation_round_trip(
    vector: dict[str, Any],
) -> None:
    resource = vector[
        "resource"
    ]

    parsed = annotation_from_dict(
        resource
    )

    recovered = annotation_to_dict(
        parsed
    )

    assert recovered == resource