"""Parsing OpenSmell documents."""

import json
from pathlib import Path
from typing import Any

from .exceptions import OpenSmellValidationError
from .models import Document, Metadata, Odor, Representation, Scheme
from .validation import validate_document


def _reject_non_standard_json_constant(value: str) -> None:
    """Reject non-standard numeric constants accepted by Python's json module."""

    raise ValueError(
        f"non-standard JSON numeric constant {value!r}"
    )


def _load_json(path: str | Path) -> dict[str, Any]:
    """Load and validate a strict JSON OpenSmell document."""

    try:
        with open(path, "r", encoding="utf-8") as file:
            document = json.load(
                file,
                parse_constant=_reject_non_standard_json_constant,
            )
    except (json.JSONDecodeError, ValueError) as error:
        raise OpenSmellValidationError(
            f"invalid JSON: {error}"
        ) from error

    if not isinstance(document, dict):
        raise OpenSmellValidationError(
            "OpenSmell document root must be a JSON object"
        )

    # In addition to schema validation, this rejects values that Python
    # cannot represent faithfully as strict JSON. For example, the valid
    # JSON number 1e400 is parsed by Python as positive infinity.
    validate_document(document)

    return document


def _parse_scheme(data: dict[str, Any]) -> Scheme:
    """Parse a scheme while preserving unknown extension fields."""

    known_fields = {"id", "version"}

    return Scheme(
        id=data["id"],
        version=data["version"],
        extra={
            key: value
            for key, value in data.items()
            if key not in known_fields
        },
    )


def _parse_representation(data: dict[str, Any]) -> Representation:
    """Parse a representation while preserving unknown extension fields."""

    known_fields = {
        "type",
        "scheme",
        "data",
    }

    return Representation(
        type=data["type"],
        scheme=_parse_scheme(data["scheme"]),
        data=data["data"],
        extra={
            key: value
            for key, value in data.items()
            if key not in known_fields
        },
    )


def _parse_metadata(data: dict[str, Any]) -> Metadata:
    """Parse metadata while preserving unknown extension fields."""

    known_fields = {
        "labels",
        "description",
    }

    return Metadata(
        labels=data.get("labels", {}),
        description=data.get("description"),
        extra={
            key: value
            for key, value in data.items()
            if key not in known_fields
        },
    )


def _parse_odor(data: dict[str, Any]) -> Odor:
    """Parse an odor while preserving unknown extension fields."""

    known_fields = {
        "id",
        "metadata",
        "representations",
    }

    metadata = data.get("metadata")

    return Odor(
        id=data["id"],
        representations=[
            _parse_representation(representation)
            for representation in data["representations"]
        ],
        metadata=(
            _parse_metadata(metadata)
            if metadata is not None
            else None
        ),
        extra={
            key: value
            for key, value in data.items()
            if key not in known_fields
        },
    )


def _parse_document(data: dict[str, Any]) -> Document:
    """Parse a complete OpenSmell document."""

    known_fields = {
        "opensmell",
        "odor",
    }

    return Document(
        odor=_parse_odor(data["odor"]),
        version=data["opensmell"],
        extra={
            key: value
            for key, value in data.items()
            if key not in known_fields
        },
    )


def load_document(path: str | Path) -> Document:
    """Load and validate a complete OpenSmell document."""

    data = _load_json(path)
    return _parse_document(data)


def load(path: str | Path) -> Odor:
    """Load an OpenSmell document and return its Odor.

    This preserves the historical public API. Use ``load_document()``
    when the complete document, including document-level extensions,
    must be preserved.
    """

    return load_document(path).odor