"""Adapter for converting OdorNet records to OpenSmell."""

from typing import Any

from .. import builders
from ..models import (
    Odor,
    Representation,
    Scheme,
)


ODORNET_LABELS = (
    "animalic&ambery",
    "sweety&gourmand",
    "floral",
    "fruity&vegetable",
    "pungent&disagreeable",
    "green&herbal",
    "nutty",
    "woody&mossy",
    "resinous&balsamic",
    "cooked",
    "odorless",
    "spice",
)


ANNOTATION_SCHEME_ID = (
    "org.opensmell.semantic.annotations"
)

ANNOTATION_SCHEME_VERSION = "0.1"


def _get_smiles(
    record: dict[str, Any],
) -> str:
    """Return and validate the SMILES value from an OdorNet record."""

    smiles = record.get("SMILES")

    if (
        not isinstance(smiles, str)
        or not smiles.strip()
    ):
        raise ValueError(
            "OdorNet record must contain "
            "a non-empty SMILES value"
        )

    return smiles.strip()


def _add_odornet_provenance(
    representation: Representation,
) -> None:
    """Attach experimental RFC-0003 provenance."""

    representation.extra["provenance"] = {
        "source": "OdorNet",
    }


def _positive_descriptors(
    record: dict[str, Any],
) -> list[str]:
    """Return positive OdorNet descriptors."""

    return [
        label
        for label in ODORNET_LABELS
        if record.get(label) == 1
    ]


def _annotation_state(
    value: Any,
) -> str:
    """Map an OdorNet category value to an RFC-0004 state."""

    if value == 1:
        return "present"

    if value == 0:
        return "absent"

    return "unknown"


def semantic_annotations(
    record: dict[str, Any],
) -> Representation:
    """Create an experimental RFC-0004 representation.

    This representation is intentionally not registered as a built-in
    OpenSmell 0.1 scheme. It is used to evaluate the semantic annotation
    model proposed by RFC-0004 against real OdorNet records.
    """

    annotations = [
        {
            "value": label,
            "language": "en",
            "state": _annotation_state(
                record.get(label)
            ),
        }
        for label in ODORNET_LABELS
    ]

    representation = Representation(
        type="semantic",
        scheme=Scheme(
            id=ANNOTATION_SCHEME_ID,
            version=ANNOTATION_SCHEME_VERSION,
        ),
        data={
            "annotations": annotations,
        },
    )

    _add_odornet_provenance(
        representation
    )

    return representation


def from_record(
    record: dict[str, Any],
    *,
    odor_id: str | None = None,
) -> Odor:
    """Convert an OdorNet record into an OpenSmell odor.

    This function preserves the existing OpenSmell 0.1 adapter
    behavior and exports positive OdorNet labels using the
    semantic descriptor scheme.
    """

    smiles = _get_smiles(
        record
    )

    descriptors = _positive_descriptors(
        record
    )

    representations = [
        builders.chemical_smiles(
            smiles
        ),
    ]

    if descriptors:
        representations.append(
            builders.semantic_descriptors(
                *descriptors,
                language="en",
            )
        )

    # Experimental implementation of RFC-0003 provenance.
    #
    # Provenance is stored as an extension field rather than as part
    # of the OpenSmell 0.1 core model. This allows the proposal to be
    # tested without changing the 0.1 specification.
    for representation in representations:
        _add_odornet_provenance(
            representation
        )

    return builders.odor(
        representations=representations,
        odor_id=odor_id,
    )


def from_record_with_annotations(
    record: dict[str, Any],
    *,
    odor_id: str | None = None,
) -> Odor:
    """Convert an OdorNet record using experimental RFC-0004 annotations.

    The returned odor contains:

    - the normal chemical SMILES representation;
    - a semantic annotation representation preserving all twelve
      OdorNet category states.

    The experimental annotation scheme is not registered as a built-in
    OpenSmell 0.1 scheme.
    """

    smiles = _get_smiles(
        record
    )

    chemical = builders.chemical_smiles(
        smiles
    )

    _add_odornet_provenance(
        chemical
    )

    annotations = semantic_annotations(
        record
    )

    return builders.odor(
        representations=[
            chemical,
            annotations,
        ],
        odor_id=odor_id,
    )