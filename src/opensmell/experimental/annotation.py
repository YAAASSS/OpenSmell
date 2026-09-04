"""Experimental OpenSmell annotation resource.

This module explores a generic resource for attaching scheme-defined
annotation data to another OpenSmell resource.

The resource is intentionally generic. It does not define semantic odor
categories itself. Instead, the meaning of ``data`` is determined by the
versioned experimental Scheme.

Resource contract:

    type: org.opensmell.annotation
    type_version: 0.1

An Annotation references another resource through ``subject`` and carries
scheme-defined data describing an assertion, classification, label set, or
other annotation associated with that resource.

This model is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .generic_graph import ResourceTypeRegistry
from .graph_serialization import (
    reference_from_dict,
    reference_to_dict,
)
from .resources import Reference
from .scheme import (
    Scheme,
    scheme_from_dict,
    scheme_to_dict,
)


ANNOTATION_RESOURCE_TYPE = "org.opensmell.annotation"
ANNOTATION_RESOURCE_TYPE_VERSION = "0.1"


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
    """Recursively copy JSON-compatible annotation data."""

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
                    "annotation data object keys "
                    "must be strings"
                )

            result[key] = _copy_json_value(
                item
            )

        return result

    raise TypeError(
        "annotation data must contain only "
        "JSON-compatible values"
    )


@dataclass
class Annotation:
    """Experimental scheme-defined annotation resource.

    ``id`` is the OpenSmell Resource ID.

    ``subject`` identifies the resource being annotated.

    ``scheme`` identifies the versioned rules required to interpret
    ``data``.

    ``data`` is intentionally opaque to the generic Annotation resource.
    Scheme-specific validation belongs outside this resource model.

    ``extra`` preserves unknown extension fields associated with the
    Annotation resource.
    """

    id: str
    subject: Reference
    scheme: Scheme
    data: dict[str, Any] = field(
        default_factory=dict
    )
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.id,
            "Annotation.id",
        )

        if not isinstance(
            self.subject,
            Reference,
        ):
            raise TypeError(
                "Annotation.subject must be a Reference"
            )

        if not isinstance(
            self.scheme,
            Scheme,
        ):
            raise TypeError(
                "Annotation.scheme must be a Scheme"
            )

        _require_dict(
            self.data,
            "Annotation.data",
        )

        _require_dict(
            self.extra,
            "Annotation.extra",
        )

        self.data = _copy_json_value(
            self.data
        )

        self.extra = _copy_json_value(
            self.extra
        )

        reserved_extra_fields = {
            "type",
            "type_version",
            "id",
            "subject",
            "scheme",
            "data",
        }

        conflicting_fields = (
            reserved_extra_fields
            & self.extra.keys()
        )

        if conflicting_fields:
            names = ", ".join(
                sorted(conflicting_fields)
            )

            raise ValueError(
                "Annotation.extra contains reserved "
                f"field(s): {names}"
            )


def annotation_to_dict(
    annotation: Annotation,
) -> dict[str, Any]:
    """Serialize an Annotation using the RFC-0008 resource contract."""

    if not isinstance(
        annotation,
        Annotation,
    ):
        raise TypeError(
            "annotation must be an Annotation"
        )

    document = _copy_json_value(
        annotation.extra
    )

    document.update(
        {
            "type": ANNOTATION_RESOURCE_TYPE,
            "type_version": (
                ANNOTATION_RESOURCE_TYPE_VERSION
            ),
            "id": annotation.id,
            "subject": reference_to_dict(
                annotation.subject
            ),
            "scheme": scheme_to_dict(
                annotation.scheme
            ),
            "data": _copy_json_value(
                annotation.data
            ),
        }
    )

    return document


def annotation_from_dict(
    value: Any,
) -> Annotation:
    """Parse a serialized Annotation resource."""

    obj = _require_dict(
        value,
        "annotation",
    )

    resource_type = _require_nonempty_string(
        obj.get("type"),
        "annotation.type",
    )

    if resource_type != ANNOTATION_RESOURCE_TYPE:
        raise ValueError(
            "unexpected annotation resource type"
        )

    resource_type_version = (
        _require_nonempty_string(
            obj.get("type_version"),
            "annotation.type_version",
        )
    )

    if (
        resource_type_version
        != ANNOTATION_RESOURCE_TYPE_VERSION
    ):
        raise ValueError(
            "unsupported annotation resource type_version"
        )

    resource_id = _require_nonempty_string(
        obj.get("id"),
        "annotation.id",
    )

    if "subject" not in obj:
        raise ValueError(
            "annotation.subject is required"
        )

    subject = reference_from_dict(
        obj["subject"]
    )

    if "scheme" not in obj:
        raise ValueError(
            "annotation.scheme is required"
        )

    scheme = scheme_from_dict(
        obj["scheme"]
    )

    if "data" not in obj:
        raise ValueError(
            "annotation.data is required"
        )

    data = _require_dict(
        obj["data"],
        "annotation.data",
    )

    known_fields = {
        "type",
        "type_version",
        "id",
        "subject",
        "scheme",
        "data",
    }

    extra = {
        key: _copy_json_value(item)
        for key, item in obj.items()
        if key not in known_fields
    }

    return Annotation(
        id=resource_id,
        subject=subject,
        scheme=scheme,
        data=_copy_json_value(data),
        extra=extra,
    )


def register_annotation_resource_type(
    registry: ResourceTypeRegistry,
) -> None:
    """Register Annotation 0.1 in an RFC-0008 resource registry."""

    if not isinstance(
        registry,
        ResourceTypeRegistry,
    ):
        raise TypeError(
            "registry must be a ResourceTypeRegistry"
        )

    registry.register(
        ANNOTATION_RESOURCE_TYPE,
        Annotation,
        annotation_from_dict,
        annotation_to_dict,
        resource_type_version=(
            ANNOTATION_RESOURCE_TYPE_VERSION
        ),
    )