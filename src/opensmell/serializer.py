"""Serialization of OpenSmell objects."""

import json
from pathlib import Path
from typing import Any

from .models import Document, Odor
from .validation import validate_document


def odor_to_data(
    odor: Odor,
) -> dict[str, Any]:
    """Convert an Odor object into its JSON-compatible dictionary."""

    representations = []

    for representation in odor.representations:
        scheme_data = dict(
            representation.scheme.extra
        )

        scheme_data.update(
            {
                "id": representation.scheme.id,
                "version": representation.scheme.version,
            }
        )

        representation_data = dict(
            representation.extra
        )

        representation_data.update(
            {
                "type": representation.type,
                "scheme": scheme_data,
                "data": representation.data,
            }
        )

        representations.append(
            representation_data
        )

    odor_data: dict[str, Any] = dict(
        odor.extra
    )

    odor_data.update(
        {
            "id": odor.id,
            "representations": representations,
        }
    )

    if odor.metadata is not None:
        metadata = dict(
            odor.metadata.extra
        )

        if odor.metadata.labels:
            metadata["labels"] = odor.metadata.labels

        if odor.metadata.description is not None:
            metadata["description"] = odor.metadata.description

        odor_data["metadata"] = metadata

    return odor_data


def document_to_dict(
    document: Document,
) -> dict[str, Any]:
    """Convert a Document into a JSON-compatible dictionary."""

    data = dict(
        document.extra
    )

    data.update(
        {
            "opensmell": document.version,
            "odor": odor_to_data(document.odor),
        }
    )

    return data


def odor_to_dict(
    odor: Odor,
) -> dict[str, Any]:
    """Convert an Odor into a complete OpenSmell document.

    This function is retained for compatibility with the
    OpenSmell 0.1 API.
    """

    return document_to_dict(
        Document(
            odor=odor,
            version="0.1",
        )
    )


def dump(
    value: Odor | Document,
    path: str | Path,
) -> None:
    """Write an Odor or Document to an OpenSmell file."""

    if isinstance(value, Document):
        document = document_to_dict(value)

    elif isinstance(value, Odor):
        document = odor_to_dict(value)

    else:
        raise TypeError(
            "dump() expects an Odor or Document"
        )

    validate_document(document)

    path = Path(path)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            document,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")