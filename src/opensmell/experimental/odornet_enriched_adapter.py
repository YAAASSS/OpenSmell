"""Experimental enriched OdorNet ResourceGraph adapter.

This module converts one enriched OdorNet record into experimental OpenSmell
resources.

The adapter creates:

- one Molecule resource representing the chemical source;
- one Annotation resource containing the complete OdorNet semantic state;
- one GenericResourceGraph containing both resources.

The original OdorNet SMILES value is the source identity used for
deterministic OpenSmell Resource ID generation.

PubChem enrichment is supplementary. A resolved PubChem InChIKey is preserved
as an ExternalIdentifier when available, but PubChem enrichment is not
required for successful conversion.

OdorNet semantic values are interpreted as:

    1 / 1.0   -> present
    0 / 0.0   -> absent
    missing   -> unknown

This adapter is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    ANNOTATION_SCHEME_VERSION,
    ODORNET_LABELS,
)

from .annotation import Annotation
from .generic_graph import GenericResourceGraph
from .molecule import Molecule
from .identifiers import (
    deterministic_resource_id_from_source,
)
from .resources import (
    ExternalIdentifier,
    Reference,
)
from .scheme import Scheme


ODORNET_DATASET_ID = "odornet"

PUBCHEM_INCHIKEY_SCHEME = (
    "pubchem.inchikey"
)


def _require_record(
    record: Any,
) -> dict[str, Any]:
    if not isinstance(
        record,
        dict,
    ):
        raise TypeError(
            "record must be a dict"
        )

    return record


def _require_smiles(
    record: dict[str, Any],
) -> str:
    value = record.get(
        "SMILES"
    )

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "record SMILES must be a string"
        )

    smiles = value.strip()

    if not smiles:
        raise ValueError(
            "record SMILES must be non-empty"
        )

    return smiles


def _normalized_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "enrichment values must be strings or None"
        )

    normalized = value.strip()

    if not normalized:
        return None

    return normalized


def _annotation_state(
    value: Any,
) -> str:
    if value in {
        1,
        1.0,
        "1",
        "1.0",
    }:
        return "present"

    if value in {
        0,
        0.0,
        "0",
        "0.0",
    }:
        return "absent"

    if value is None:
        return "unknown"

    if (
        isinstance(value, str)
        and not value.strip()
    ):
        return "unknown"

    raise ValueError(
        "unexpected OdorNet semantic value: "
        f"{value!r}"
    )


def _pubchem_identifiers(
    record: dict[str, Any],
) -> list[ExternalIdentifier]:
    status = _normalized_text(
        record.get(
            "PubChem_Status"
        )
    )

    inchikey = _normalized_text(
        record.get(
            "PubChem_InChIKey"
        )
    )

    if (
        status != "resolved"
        or inchikey is None
    ):
        return []

    return [
        ExternalIdentifier(
            scheme=(
                PUBCHEM_INCHIKEY_SCHEME
            ),
            value=inchikey,
        )
    ]


def _molecule_extra(
    record: dict[str, Any],
) -> dict[str, Any]:
    extra: dict[str, Any] = {
        "provenance": {
            "source": "OdorNet",
        }
    }

    pubchem_status = _normalized_text(
        record.get(
            "PubChem_Status"
        )
    )

    pubchem_title = _normalized_text(
        record.get(
            "PubChem_Title"
        )
    )

    pubchem_iupac_name = (
        _normalized_text(
            record.get(
                "PubChem_IUPACName"
            )
        )
    )

    pubchem_canonical_smiles = (
        _normalized_text(
            record.get(
                "PubChem_CanonicalSMILES"
            )
        )
    )

    pubchem: dict[str, Any] = {}

    if pubchem_status is not None:
        pubchem["status"] = (
            pubchem_status
        )

    if pubchem_title is not None:
        pubchem["title"] = (
            pubchem_title
        )

    if pubchem_iupac_name is not None:
        pubchem["iupac_name"] = (
            pubchem_iupac_name
        )

    if (
        pubchem_canonical_smiles
        is not None
    ):
        pubchem["canonical_smiles"] = (
            pubchem_canonical_smiles
        )

    if pubchem:
        extra["pubchem"] = pubchem

    return extra


def _annotation_data(
    record: dict[str, Any],
) -> dict[str, Any]:
    annotations = []

    for label in ODORNET_LABELS:
        annotations.append(
            {
                "value": label,
                "language": "en",
                "state": (
                    _annotation_state(
                        record.get(
                            label
                        )
                    )
                ),
            }
        )

    return {
        "annotations": annotations,
    }


@dataclass(frozen=True)
class EnrichedOdorNetGraphResult:
    """Result of converting one enriched OdorNet record."""

    graph: GenericResourceGraph
    molecule_id: str
    annotation_id: str


def enriched_odornet_record_to_graph(
    record: dict[str, Any],
) -> EnrichedOdorNetGraphResult:
    """Convert one enriched OdorNet record into a GenericResourceGraph."""

    record = _require_record(
        record
    )

    smiles = _require_smiles(
        record
    )

    molecule_id = (
        deterministic_resource_id_from_source(
            dataset=ODORNET_DATASET_ID,
            resource_type="molecule",
            source_identity={
                "smiles": smiles,
            },
        )
    )

    annotation_id = (
        deterministic_resource_id_from_source(
            dataset=ODORNET_DATASET_ID,
            resource_type="annotation",
            source_identity={
                "scheme": (
                    ANNOTATION_SCHEME_ID
                ),
                "smiles": smiles,
            },
        )
    )

    molecule = Molecule(
        id=molecule_id,
        smiles=smiles,
        identifiers=(
            _pubchem_identifiers(
                record
            )
        ),
        extra=_molecule_extra(
            record
        ),
    )

    annotation = Annotation(
        id=annotation_id,
        subject=Reference(
            resource_id=molecule_id
        ),
        scheme=Scheme(
            id=ANNOTATION_SCHEME_ID,
            version=(
                ANNOTATION_SCHEME_VERSION
            ),
        ),
        data=_annotation_data(
            record
        ),
        extra={
            "provenance": {
                "source": "OdorNet",
            }
        },
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )

    return EnrichedOdorNetGraphResult(
        graph=graph,
        molecule_id=molecule_id,
        annotation_id=annotation_id,
    )