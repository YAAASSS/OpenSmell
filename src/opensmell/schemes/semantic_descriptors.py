"""OpenSmell semantic descriptor scheme."""

from typing import Any


SCHEME_ID = "org.opensmell.semantic.descriptors"
SCHEME_VERSION = "0.1"


def validate(data: dict[str, Any]) -> None:
    """Validate semantic descriptor data."""

    descriptors = data.get("descriptors")

    if not isinstance(descriptors, list) or not descriptors:
        raise ValueError(
            "'descriptors' must be a non-empty list"
        )

    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise ValueError(
                "each descriptor must be an object"
            )

        value = descriptor.get("value")

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "descriptor 'value' must be a non-empty string"
            )

        language = descriptor.get("language")

        if language is not None and not isinstance(language, str):
            raise ValueError(
                "descriptor 'language' must be a string"
            )