"""Validation of OpenSmell documents."""

import json
import math
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator

from .exceptions import OpenSmellValidationError, SchemeValidationError
from .schemes import get_definition


def _load_schema() -> dict[str, Any]:
    """Load the OpenSmell 0.1 JSON Schema from package resources."""

    schema_resource = (
        files("opensmell")
        .joinpath("schemas")
        .joinpath("opensmell-0.1.schema.json")
    )

    with schema_resource.open("r", encoding="utf-8") as file:
        return json.load(file)


def _json_location(path: tuple[str | int, ...]) -> str:
    """Return a readable location for a value in a JSON document."""

    if not path:
        return "$"

    location = "$"

    for part in path:
        if isinstance(part, int):
            location += f"[{part}]"
        else:
            location += f".{part}"

    return location


def _validate_json_value(
    value: Any,
    path: tuple[str | int, ...] = (),
) -> None:
    """Reject values that cannot be represented faithfully as strict JSON."""

    if value is None or isinstance(value, (str, bool)):
        return

    if isinstance(value, int):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise OpenSmellValidationError(
                f"{_json_location(path)}: non-finite numbers are not valid JSON"
            )
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, path + (index,))
        return

    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise OpenSmellValidationError(
                    f"{_json_location(path)}: JSON object keys must be strings"
                )

            _validate_json_value(item, path + (key,))
        return

    raise OpenSmellValidationError(
        f"{_json_location(path)}: value of type "
        f"{type(value).__name__!r} is not a valid JSON value"
    )


def _validate_representation_schemes(
    document: dict[str, Any],
) -> None:
    """Validate representations using registered scheme definitions."""

    representations = document["odor"]["representations"]

    for index, representation in enumerate(representations):
        scheme = representation["scheme"]

        definition = get_definition(
            scheme["id"],
            scheme["version"],
        )

        if definition is None:
            continue

        if representation["type"] != definition.representation_type:
            raise SchemeValidationError(
                f"odor.representations[{index}]: "
                f"{scheme['id']} {scheme['version']} "
                f"requires representation type "
                f"{definition.representation_type!r}, "
                f"got {representation['type']!r}"
            )

        try:
            definition.validator(
                representation["data"]
            )
        except ValueError as error:
            raise SchemeValidationError(
                f"odor.representations[{index}]: "
                f"{scheme['id']} {scheme['version']}: {error}"
            ) from error


def validate_document(document: dict[str, Any]) -> None:
    """Validate an OpenSmell document."""

    _validate_json_value(document)

    schema = _load_schema()
    validator = Draft202012Validator(schema)

    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )

    if errors:
        error = errors[0]

        location = ".".join(
            str(part) for part in error.absolute_path
        )

        if location:
            message = f"{location}: {error.message}"
        else:
            message = error.message

        raise OpenSmellValidationError(message)

    _validate_representation_schemes(document)