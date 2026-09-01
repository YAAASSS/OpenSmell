"""Parser for OpenSmell documents."""

import json
from pathlib import Path
from typing import Any

from .models import Metadata, Odor, Representation, Scheme
from .validation import validate_document


def parse_odor(data: dict[str, Any]) -> Odor:
    """Convert an OpenSmell odor dictionary into an Odor object."""

    metadata_data = data.get("metadata")

    metadata = None

    if metadata_data is not None:
        metadata = Metadata(
            labels=metadata_data.get("labels", {}),
            description=metadata_data.get("description"),
        )

    representations = []

    for representation_data in data["representations"]:
        scheme_data = representation_data["scheme"]

        scheme = Scheme(
            id=scheme_data["id"],
            version=scheme_data["version"],
        )

        representation = Representation(
            type=representation_data["type"],
            scheme=scheme,
            data=representation_data["data"],
        )

        representations.append(representation)

    return Odor(
        id=data["id"],
        metadata=metadata,
        representations=representations,
    )


def load(path: str | Path) -> Odor:
    """Load an OpenSmell document from disk."""

    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        document = json.load(file)

    validate_document(document)

    return parse_odor(document["odor"])