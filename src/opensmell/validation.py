"""Validation of OpenSmell documents."""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .exceptions import OpenSmellValidationError


def _schema_path() -> Path:
    """Return the path to the OpenSmell 0.1 JSON Schema."""

    return Path(__file__).parents[2] / "schema" / "opensmell-0.1.schema.json"


def _load_schema() -> dict[str, Any]:
    """Load the OpenSmell 0.1 JSON Schema."""

    with _schema_path().open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_document(document: dict[str, Any]) -> None:
    """Validate an OpenSmell document against the 0.1 schema."""

    schema = _load_schema()
    validator = Draft202012Validator(schema)

    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )

    if errors:
        error = errors[0]

        location = ".".join(str(part) for part in error.absolute_path)

        if location:
            message = f"{location}: {error.message}"
        else:
            message = error.message

        raise OpenSmellValidationError(message)