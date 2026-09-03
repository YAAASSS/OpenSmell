"""Experimental Resource ID utilities for OpenSmell.

This module explores the Resource ID architecture described by RFC-0006.

Nothing in this module is normative OpenSmell 0.1.
"""

from __future__ import annotations

import json
import re
from typing import TypeAlias
from uuid import UUID, uuid4, uuid5


OPENSMELL_EXPERIMENTAL_NAMESPACE = UUID(
    "7f0f1d72-83c7-4f57-a1f6-4bc43bb26e58"
)


SourceIdentity: TypeAlias = str | dict[str, str]


_COMPOSITE_KEY_PATTERN = re.compile(
    r"^[a-z][a-z0-9_.-]*$"
)


def _validate_unicode_scalar_string(
    value: str,
    *,
    field_name: str,
) -> None:
    """Validate a non-empty string containing only Unicode scalar values."""

    if not isinstance(value, str) or not value:
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )

    for character in value:
        codepoint = ord(character)

        if 0xD800 <= codepoint <= 0xDFFF:
            raise ValueError(
                f"{field_name} must not contain Unicode surrogate code points"
            )


def _validate_source_identity(
    source_identity: SourceIdentity,
) -> None:
    """Validate an experimental atomic or composite source identity."""

    if isinstance(source_identity, str):
        _validate_unicode_scalar_string(
            source_identity,
            field_name="source_identity",
        )
        return

    if not isinstance(source_identity, dict):
        raise ValueError(
            "source_identity must be a non-empty string "
            "or a non-empty dict[str, str]"
        )

    if not source_identity:
        raise ValueError(
            "composite source_identity must not be empty"
        )

    for key, value in source_identity.items():
        if not isinstance(key, str) or not key:
            raise ValueError(
                "composite source_identity keys "
                "must be non-empty strings"
            )

        if not _COMPOSITE_KEY_PATTERN.fullmatch(key):
            raise ValueError(
                "composite source_identity keys must match "
                "^[a-z][a-z0-9_.-]*$"
            )

        _validate_unicode_scalar_string(
            value,
            field_name=(
                f"source_identity[{key!r}]"
            ),
        )


def new_resource_id() -> str:
    """Generate a new opaque experimental Resource ID using UUIDv4."""

    return str(uuid4())


def deterministic_resource_id(
    name: str,
) -> str:
    """Generate an experimental deterministic UUIDv5 from a canonical name."""

    _validate_unicode_scalar_string(
        name,
        field_name="name",
    )

    return str(
        uuid5(
            OPENSMELL_EXPERIMENTAL_NAMESPACE,
            name,
        )
    )


def canonical_generation_name(
    dataset: str,
    resource_type: str,
    source_identity: SourceIdentity,
) -> str:
    """Build deterministic generation material for a source resource."""

    _validate_unicode_scalar_string(
        dataset,
        field_name="dataset",
    )

    _validate_unicode_scalar_string(
        resource_type,
        field_name="resource_type",
    )

    _validate_source_identity(
        source_identity
    )

    payload = {
        "dataset": dataset,
        "resource_type": resource_type,
        "source_identity": source_identity,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def deterministic_resource_id_from_source(
    dataset: str,
    resource_type: str,
    source_identity: SourceIdentity,
) -> str:
    """Generate an experimental UUIDv5 from structured source identity."""

    name = canonical_generation_name(
        dataset=dataset,
        resource_type=resource_type,
        source_identity=source_identity,
    )

    return deterministic_resource_id(name)


def validate_resource_id(
    value: str,
) -> None:
    """Validate canonical lowercase UUID textual syntax.

    This validates canonical UUID syntax only. It intentionally does not
    restrict the UUID version to UUIDv4 or UUIDv5.
    """

    if not isinstance(value, str) or not value:
        raise ValueError(
            "resource ID must be a non-empty string"
        )

    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            "resource ID must be a valid UUID"
        ) from exc

    if str(parsed) != value:
        raise ValueError(
            "resource ID must use canonical lowercase UUID syntax"
        )