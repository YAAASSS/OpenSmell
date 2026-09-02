"""Convenience builders for OpenSmell objects."""

import uuid

from .models import Metadata, Odor, Representation, Scheme
from .schemes import chemical_smiles as smiles_scheme
from .schemes import semantic_descriptors as semantic_scheme


def semantic_descriptors(
    *values: str,
    language: str | None = None,
) -> Representation:
    """Create a semantic descriptor representation."""

    descriptors = []

    for value in values:
        descriptor = {
            "value": value,
        }

        if language is not None:
            descriptor["language"] = language

        descriptors.append(descriptor)

    data = {
        "descriptors": descriptors,
    }

    # The scheme itself owns its validation rules.
    semantic_scheme.validate(data)

    return Representation(
        type="semantic",
        scheme=Scheme(
            id=semantic_scheme.SCHEME_ID,
            version=semantic_scheme.SCHEME_VERSION,
        ),
        data=data,
    )

def chemical_smiles(
    smiles: str,
) -> Representation:
    """Create a chemical SMILES representation."""

    data = {
        "smiles": smiles,
    }

    smiles_scheme.validate(data)

    return Representation(
        type="chemical",
        scheme=Scheme(
            id=smiles_scheme.SCHEME_ID,
            version=smiles_scheme.SCHEME_VERSION,
        ),
        data=data,
    )

def odor(
    representations: list[Representation],
    *,
    labels: dict[str, str] | None = None,
    description: str | None = None,
    odor_id: str | None = None,
) -> Odor:
    """Create an Odor with optional metadata and automatic UUID."""

    if not representations:
        raise ValueError(
            "at least one representation is required"
        )

    if odor_id is None:
        odor_id = uuid.uuid4().urn

    metadata = None

    if labels or description is not None:
        metadata = Metadata(
            labels=dict(labels or {}),
            description=description,
        )

    return Odor(
        id=odor_id,
        representations=list(representations),
        metadata=metadata,
    )