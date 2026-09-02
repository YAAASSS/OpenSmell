"""Validation of OpenSmell documents."""

import json
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