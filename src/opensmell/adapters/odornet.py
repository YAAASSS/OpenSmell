"""Adapter for converting OdorNet records to OpenSmell."""

from typing import Any

from .. import builders
from ..models import Odor


ODORNET_LABELS = (
    "animalic&ambery",
    "sweety&gourmand",
    "floral",
    "fruity&vegetable",
    "pungent&disagreetable",
    "green&herbal",
    "nutty",
    "woody&mossy",
    "resinous&balsamic",
    "cooked",
    "odorless",
    "spice",
)


def from_record(
    record: dict[str, Any],
    *,
    odor_id: str | None = None,
) -> Odor:
    """Convert an OdorNet record into an OpenSmell odor."""

    smiles = record.get("SMILES")

    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError(
            "OdorNet record must contain a non-empty SMILES value"
        )

    descriptors = [
        label
        for label in ODORNET_LABELS
        if record.get(label) == 1
    ]

    representations = [
        builders.chemical_smiles(smiles),
    ]

    if descriptors:
        representations.append(
            builders.semantic_descriptors(
                *descriptors,
                language="en",
            )
        )

    # Experimental implementation of RFC 0001.
    #
    # Provenance is stored as an extension field rather than as part
    # of the OpenSmell 0.1 core model. This allows the proposal to be
    # tested without changing the 0.1 specification.
    for representation in representations:
        representation.extra["provenance"] = {
            "source": "OdorNet",
        }

    return builders.odor(
        representations=representations,
        odor_id=odor_id,
    )