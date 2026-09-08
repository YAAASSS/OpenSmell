"""Serialization of OpenSmell documents."""

import json
from pathlib import Path
from typing import Any

from .models import Document, Metadata, Odor, Representation, Scheme
from .validation import validate_document


def _scheme_to_dict(scheme: Scheme) -> dict[str, Any]:
    """Convert a Scheme model to its JSON-compatible dictionary form."""

    result = dict(scheme.extra)

    result.update(
        {
            "id": scheme.id,
            "version": scheme.version,
        }
    )

    return result


def _representation_to_dict(
    representation: Representation,
) -> dict[str, Any]:
    """Convert a Representation model to its dictionary form."""

    result = dict(representation.extra)

    result.update(
        {
            "type": representation.type,
            "scheme": _scheme_to_dict(representation.scheme),
            "data": representation.data,
        }
    )

    return result


def _metadata_to_dict(metadata: Metadata) -> dict[str, Any]:
    """Convert Metadata to its dictionary form."""

    result = dict(metadata.extra)

    if metadata.labels:
        result["labels"] = metadata.labels

    if metadata.description is not None:
        result["description"] = metadata.description

    return result


def _odor_to_dict(odor: Odor) -> dict[str, Any]:
    """Convert an Odor model to its dictionary form."""

    result = dict(odor.extra)

    result.update(
        {
            "id": odor.id,
            "representations": [
                _representation_to_dict(representation)
                for representation in odor.representations
            ],
        }
    )

    if odor.metadata is not None:
        result["metadata"] = _metadata_to_dict(odor.metadata)

    return result


def _document_to_dict(document: Document) -> dict[str, Any]:
    """Convert a Document model to its dictionary form."""

    result = dict(document.extra)

    result.update(
        {
            "opensmell": document.version,
            "odor": _odor_to_dict(document.odor),
        }
    )

    return result


def _serialize_document(document: Document) -> str:
    """Validate and serialize a Document as strict JSON.

    Serialization is completed in memory before the destination file is
    opened. This prevents a serialization failure from truncating or
    partially overwriting an existing file.
    """

    data = _document_to_dict(document)

    validate_document(data)

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )


def dump(
    value: Odor | Document,
    path: str | Path,
) -> None:
    """Serialize an Odor or Document to an OpenSmell file."""

    if isinstance(value, Document):
        document = value
    elif isinstance(value, Odor):
        document = Document(
            odor=value,
            version="0.1",
        )
    else:
        raise TypeError(
            "dump() expects an Odor or Document instance"
        )

    serialized = _serialize_document(document)

    with open(path, "w", encoding="utf-8", newline="\n") as file:
        file.write(serialized)
        file.write("\n")