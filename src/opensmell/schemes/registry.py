"""Registry for OpenSmell representation schemes."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


SchemeValidator = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class SchemeDefinition:
    """Definition of a registered OpenSmell scheme."""

    representation_type: str
    validator: SchemeValidator


_registry: dict[
    tuple[str, str],
    SchemeDefinition,
] = {}


def register(
    scheme_id: str,
    version: str,
    representation_type: str,
    validator: SchemeValidator,
) -> None:
    """Register a scheme definition."""

    key = (scheme_id, version)

    if key in _registry:
        raise ValueError(
            f"Scheme {scheme_id!r} version "
            f"{version!r} is already registered"
        )

    _registry[key] = SchemeDefinition(
        representation_type=representation_type,
        validator=validator,
    )


def get_definition(
    scheme_id: str,
    version: str,
) -> SchemeDefinition | None:
    """Return a registered scheme definition."""

    return _registry.get(
        (scheme_id, version)
    )


def get_validator(
    scheme_id: str,
    version: str,
) -> SchemeValidator | None:
    """Return the validator registered for a scheme."""

    definition = get_definition(
        scheme_id,
        version,
    )

    if definition is None:
        return None

    return definition.validator