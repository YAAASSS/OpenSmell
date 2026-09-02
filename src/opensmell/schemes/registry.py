"""Registry for OpenSmell representation schemes."""

from collections.abc import Callable
from typing import Any


SchemeValidator = Callable[[dict[str, Any]], None]


_registry: dict[tuple[str, str], SchemeValidator] = {}


def register(
    scheme_id: str,
    version: str,
    validator: SchemeValidator,
) -> None:
    """Register a validator for a scheme and version."""

    key = (scheme_id, version)

    if key in _registry:
        raise ValueError(
            f"Scheme {scheme_id!r} version {version!r} is already registered"
        )

    _registry[key] = validator


def get_validator(
    scheme_id: str,
    version: str,
) -> SchemeValidator | None:
    """Return the validator registered for a scheme and version."""

    return _registry.get((scheme_id, version))