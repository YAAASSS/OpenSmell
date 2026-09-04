"""Experimental generic scheme model.

This module defines a small generic structure for identifying the versioned
rules used to interpret scheme-defined data.

A Scheme does not interpret or validate the data itself. It only identifies
the family and version of the interpretation rules.

The model is intentionally independent from any particular container such as
Representation, Result, or Annotation.

This experimental Scheme is deliberately separate from the OpenSmell 0.1 Core
Scheme model. A future specification may decide whether the Core and
experimental scheme concepts should converge.

This model is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _require_nonempty_string(
    value: Any,
    name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be a string"
        )

    if not value:
        raise ValueError(
            f"{name} must be non-empty"
        )

    return value


def _require_dict(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(
            f"{name} must be a dict"
        )

    return value


def _copy_json_value(
    value: Any,
) -> Any:
    """Recursively copy a JSON-compatible value."""

    if value is None:
        return None

    if isinstance(
        value,
        (bool, str, int, float),
    ):
        return value

    if isinstance(value, list):
        return [
            _copy_json_value(item)
            for item in value
        ]

    if isinstance(value, dict):
        result: dict[str, Any] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "scheme extension object keys "
                    "must be strings"
                )

            result[key] = _copy_json_value(
                item
            )

        return result

    raise TypeError(
        "scheme extensions must contain only "
        "JSON-compatible values"
    )


@dataclass(frozen=True)
class Scheme:
    """Versioned identifier for rules that interpret scheme-defined data.

    ``id`` identifies the family of interpretation rules.

    ``version`` identifies the specific version of those rules.

    ``extra`` preserves additional scheme metadata without requiring the
    generic Scheme model to understand it.

    Scheme-specific data validation belongs outside this model.
    """

    id: str
    version: str
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.id,
            "Scheme.id",
        )

        _require_nonempty_string(
            self.version,
            "Scheme.version",
        )

        _require_dict(
            self.extra,
            "Scheme.extra",
        )

        object.__setattr__(
            self,
            "extra",
            _copy_json_value(
                self.extra
            ),
        )


def scheme_to_dict(
    scheme: Scheme,
) -> dict[str, Any]:
    """Serialize an experimental Scheme."""

    if not isinstance(
        scheme,
        Scheme,
    ):
        raise TypeError(
            "scheme must be a Scheme"
        )

    document = _copy_json_value(
        scheme.extra
    )

    document.update(
        {
            "id": scheme.id,
            "version": scheme.version,
        }
    )

    return document


def scheme_from_dict(
    value: Any,
) -> Scheme:
    """Parse an experimental Scheme."""

    obj = _require_dict(
        value,
        "scheme",
    )

    scheme_id = _require_nonempty_string(
        obj.get("id"),
        "scheme.id",
    )

    scheme_version = _require_nonempty_string(
        obj.get("version"),
        "scheme.version",
    )

    extra = {
        key: _copy_json_value(item)
        for key, item in obj.items()
        if key not in {
            "id",
            "version",
        }
    }

    return Scheme(
        id=scheme_id,
        version=scheme_version,
        extra=extra,
    )