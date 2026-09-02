"""Serialization of OpenSmell objects."""

import json
from pathlib import Path
from typing import Any

from .models import Odor
from .validation import validate_document


def odor_to_dict(odor: Odor) -> dict[str, Any]:
    """Convert an Odor object into an OpenSmell document dictionary."""

    representations = []

    for representation in odor.representations:
        representations.append(
            {
                "type": representation.type,
                "scheme": {
                    "id": representation.scheme.id,
                    "version": representation.scheme.version,
                },
                "data": representation.data,
            }
        )

    odor_data: dict[str, Any] = {
        "id": odor.id,
        "representations": representations,
    }

    if odor.metadata is not None:
        metadata: dict[str, Any] = {}

        if odor.metadata.labels:
            metadata["labels"] = odor.metadata.labels

        if odor.metadata.description is not None:
            metadata["description"] = odor.metadata.description

        odor_data["metadata"] = metadata

    return {
        "opensmell": "0.1",
        "odor": odor_data,
    }


def dump(
    odor: Odor,
    path: str | Path,
) -> None:
    """Write an Odor object to an OpenSmell document."""

    document = odor_to_dict(odor)

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