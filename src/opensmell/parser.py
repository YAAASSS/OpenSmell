"""Parser for OpenSmell documents."""

import json
from pathlib import Path
from typing import Any

from .models import (
    Document,
    Metadata,
    Odor,
    Representation,
    Scheme,
)
from .validation import validate_document


_DOCUMENT_FIELDS = {
    "opensmell",
    "odor",
}

_ODOR_FIELDS = {
    "id",
    "metadata",
    "representations",
}

_METADATA_FIELDS = {
    "labels",
    "description",
}

_REPRESENTATION_FIELDS = {
    "type",
    "scheme",
    "data",
}

_SCHEME_FIELDS = {
    "id",
    "version",
}


def _extra_fields(
    data: dict[str, Any],
    known_fields: set[str],
) -> dict[str, Any]:
    """Return fields not defined by the OpenSmell core model."""

    return {
        key: value
        for key, value in data.items()
        if key not in known_fields
    }


def parse_odor(data: dict[str, Any]) -> Odor:
    """Convert an OpenSmell odor dictionary into an Odor object."""

    metadata_data = data.get("metadata")

    metadata = None

    if metadata_data is not None:
        metadata = Metadata(
            labels=metadata_data.get("labels", {}),
            description=metadata_data.get("description"),
            extra=_extra_fields(
                metadata_data,
                _METADATA_FIELDS,
            ),
        )

    representations = []

    for representation_data in data["representations"]:
        scheme_data = representation_data["scheme"]

        scheme = Scheme(
            id=scheme_data["id"],
            version=scheme_data["version"],
            extra=_extra_fields(
                scheme_data,
                _SCHEME_FIELDS,
            ),
        )

        representation = Representation(
            type=representation_data["type"],
            scheme=scheme,
            data=representation_data["data"],
            extra=_extra_fields(
                representation_data,
                _REPRESENTATION_FIELDS,
            ),
        )

        representations.append(representation)

    return Odor(
        id=data["id"],
        metadata=metadata,
        representations=representations,
        extra=_extra_fields(
            data,
            _ODOR_FIELDS,
        ),
    )


def parse_document(
    data: dict[str, Any],
) -> Document:
    """Convert an OpenSmell document dictionary into a Document."""

    validate_document(data)

    return Document(
        version=data["opensmell"],
        odor=parse_odor(data["odor"]),
        extra=_extra_fields(
            data,
            _DOCUMENT_FIELDS,
        ),
    )


def load_document(
    path: str | Path,
) -> Document:
    """Load a complete OpenSmell document from disk."""

    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return parse_document(data)


def load(path: str | Path) -> Odor:
    """Load an OpenSmell odor from disk.

    This function preserves the OpenSmell 0.1 API and returns
    the odor contained in the document.

    Use load_document() when document-level extension fields
    must also be preserved.
    """

    return load_document(path).odor