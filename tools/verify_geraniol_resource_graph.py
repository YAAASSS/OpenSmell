"""Verify the enriched OdorNet ResourceGraph representation of Geraniol.

This example loads the same real Geraniol record used to generate:

    examples/geraniol.osmell

but sends it through the experimental enriched OdorNet ResourceGraph adapter.

The purpose is to verify that the two OpenSmell representations remain
consistent while keeping their architectural responsibilities separate:

Core .osmell:
    Odor
    - original OdorNet SMILES
    - complete semantic annotation state

Experimental ResourceGraph:
    Molecule
    - original OdorNet SMILES
    - PubChem ExternalIdentifier
    - PubChem enrichment

    Annotation
    - subject -> Molecule
    - complete semantic annotation state

This script does not modify geraniol.osmell.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import opensmell

from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    ODORNET_LABELS,
)
from opensmell.experimental.annotation import (
    Annotation,
)
from opensmell.experimental.molecule import (
    Molecule,
)
from opensmell.experimental.odornet_enriched_adapter import (
    PUBCHEM_INCHIKEY_SCHEME,
    enriched_odornet_record_to_graph,
)


CSV_PATH = Path(
    "examples/odornet_enriched.csv"
)

OSMELL_PATH = Path(
    "examples/geraniol.osmell"
)

GERANIOL_ROW = 2106

EXPECTED_TITLE = "Geraniol"

EXPECTED_INCHIKEY = (
    "GLZPCOQZEFWAFX-JXMROGBWSA-N"
)


PUBCHEM_FIELDS = (
    "PubChem_Status",
    "PubChem_Title",
    "PubChem_IUPACName",
    "PubChem_CanonicalSMILES",
    "PubChem_InChIKey",
)


def parse_odornet_value(
    value: str | None,
) -> int | None:
    """Convert one OdorNet CSV semantic value."""

    if value is None:
        return None

    normalized = value.strip()

    if normalized in {
        "1",
        "1.0",
    }:
        return 1

    if normalized in {
        "0",
        "0.0",
    }:
        return 0

    if normalized == "":
        return None

    raise ValueError(
        "unexpected OdorNet semantic value: "
        f"{value!r}"
    )


def require_text(
    row: dict[str, str],
    field: str,
) -> str:
    """Return one required non-empty CSV value."""

    value = row.get(
        field,
        "",
    )

    if value is None:
        value = ""

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field} is empty"
        )

    return normalized


def load_enriched_row(
    csv_path: Path,
    row_index: int,
) -> dict[str, Any]:
    """Load one real enriched OdorNet row."""

    if not csv_path.is_file():
        raise FileNotFoundError(
            "Enriched OdorNet dataset not found: "
            f"{csv_path}\n"
            "\n"
            "This verification tool depends on the locally prepared "
            "OdorNet + PubChem enrichment dataset. The dataset is "
            "external to OpenSmell and is intentionally not tracked "
            "in the repository.\n"
            "\n"
            "Expected local path:\n"
            f"  {csv_path}\n"
            "\n"
            "The committed examples/geraniol.osmell fixture and the "
            "Core OpenSmell tests do not require this external dataset."
        )

    if row_index < 0:
        raise ValueError(
            "row_index must be zero or greater"
        )

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        if reader.fieldnames is None:
            raise ValueError(
                "OdorNet CSV has no header"
            )

        required_fields = {
            "SMILES",
            *ODORNET_LABELS,
            *PUBCHEM_FIELDS,
        }

        missing_fields = (
            required_fields
            - set(reader.fieldnames)
        )

        if missing_fields:
            raise ValueError(
                "CSV is missing required fields: "
                + ", ".join(
                    sorted(
                        missing_fields
                    )
                )
            )

        selected_row: (
            dict[str, str]
            | None
        ) = None

        for (
            current_index,
            row,
        ) in enumerate(reader):
            if current_index == row_index:
                selected_row = row
                break

    if selected_row is None:
        raise IndexError(
            f"OdorNet row {row_index} does not exist"
        )

    record: dict[str, Any] = {
        "SMILES": require_text(
            selected_row,
            "SMILES",
        )
    }

    for label in ODORNET_LABELS:
        record[label] = (
            parse_odornet_value(
                selected_row.get(
                    label
                )
            )
        )

    for field in PUBCHEM_FIELDS:
        record[field] = (
            selected_row.get(
                field,
                ""
            )
        )

    return record


def core_smiles(
    odor: opensmell.Odor,
) -> str:
    """Return the SMILES stored in the Core Odor."""

    for representation in odor.representations:
        if (
            representation.scheme.id
            == "org.opensmell.chemical.smiles"
        ):
            value = (
                representation.data.get(
                    "smiles"
                )
            )

            if not isinstance(
                value,
                str,
            ):
                raise RuntimeError(
                    "Core SMILES is invalid"
                )

            return value

    raise RuntimeError(
        "Core chemical SMILES representation "
        "not found"
    )


def core_semantic_states(
    odor: opensmell.Odor,
) -> dict[str, str]:
    """Return semantic states stored in the Core Odor."""

    for representation in odor.representations:
        if (
            representation.scheme.id
            == ANNOTATION_SCHEME_ID
        ):
            annotations = (
                representation.data.get(
                    "annotations"
                )
            )

            if not isinstance(
                annotations,
                list,
            ):
                raise RuntimeError(
                    "Core semantic annotations "
                    "are invalid"
                )

            return {
                item["value"]: item["state"]
                for item in annotations
            }

    raise RuntimeError(
        "Core semantic annotation "
        "representation not found"
    )


def graph_semantic_states(
    annotation: Annotation,
) -> dict[str, str]:
    """Return semantic states stored in the graph Annotation."""

    annotations = (
        annotation.data.get(
            "annotations"
        )
    )

    if not isinstance(
        annotations,
        list,
    ):
        raise RuntimeError(
            "Graph semantic annotations "
            "are invalid"
        )

    return {
        item["value"]: item["state"]
        for item in annotations
    }


def find_pubchem_inchikey(
    molecule: Molecule,
) -> str:
    """Return the PubChem InChIKey ExternalIdentifier."""

    for identifier in molecule.identifiers:
        if (
            identifier.scheme
            == PUBCHEM_INCHIKEY_SCHEME
        ):
            return identifier.value

    raise RuntimeError(
        "PubChem InChIKey ExternalIdentifier "
        "not found"
    )


def main() -> None:
    print(
        "OpenSmell - Geraniol ResourceGraph verification"
    )
    print(
        "=" * 50
    )
    print()

    record = load_enriched_row(
        CSV_PATH,
        GERANIOL_ROW,
    )

    title = require_text(
        record,
        "PubChem_Title",
    )

    inchikey = require_text(
        record,
        "PubChem_InChIKey",
    )

    if title != EXPECTED_TITLE:
        raise RuntimeError(
            "selected row no longer identifies "
            f"Geraniol: {title!r}"
        )

    if inchikey != EXPECTED_INCHIKEY:
        raise RuntimeError(
            "unexpected Geraniol InChIKey: "
            f"{inchikey}"
        )

    if not OSMELL_PATH.is_file():
        raise FileNotFoundError(
            "Core Geraniol document not found: "
            f"{OSMELL_PATH}"
        )

    core_odor = opensmell.load(
        OSMELL_PATH
    )

    result = (
        enriched_odornet_record_to_graph(
            record
        )
    )

    molecule = result.graph.require(
        result.molecule_id
    )

    annotation = result.graph.require(
        result.annotation_id
    )

    if not isinstance(
        molecule,
        Molecule,
    ):
        raise RuntimeError(
            "expected Molecule resource"
        )

    if not isinstance(
        annotation,
        Annotation,
    ):
        raise RuntimeError(
            "expected Annotation resource"
        )

    print(
        "Core OpenSmell:"
    )
    print(
        f"  Odor ID       : {core_odor.id}"
    )
    print(
        f"  SMILES        : {core_smiles(core_odor)}"
    )
    print()

    print(
        "Experimental ResourceGraph:"
    )
    print(
        f"  Molecule ID   : {molecule.id}"
    )
    print(
        f"  Annotation ID : {annotation.id}"
    )
    print(
        "  Subject       : "
        f"{annotation.subject.resource_id}"
    )
    print(
        f"  SMILES        : {molecule.smiles}"
    )
    print()

    if (
        annotation.subject.resource_id
        != molecule.id
    ):
        raise RuntimeError(
            "Annotation subject does not "
            "reference the Molecule"
        )

    print(
        "Reference:"
    )
    print(
        "  Annotation -> Molecule : OK"
    )
    print()

    graph_inchikey = (
        find_pubchem_inchikey(
            molecule
        )
    )

    if graph_inchikey != inchikey:
        raise RuntimeError(
            "PubChem InChIKey changed "
            "during graph conversion"
        )

    print(
        "External chemical identity:"
    )
    print(
        "  Scheme        : "
        f"{PUBCHEM_INCHIKEY_SCHEME}"
    )
    print(
        f"  InChIKey      : {graph_inchikey}"
    )
    print()

    pubchem = (
        molecule.extra.get(
            "pubchem"
        )
    )

    if not isinstance(
        pubchem,
        dict,
    ):
        raise RuntimeError(
            "PubChem enrichment missing "
            "from Molecule.extra"
        )

    print(
        "PubChem enrichment:"
    )
    print(
        "  status        : "
        f"{pubchem.get('status')}"
    )
    print(
        "  title         : "
        f"{pubchem.get('title')}"
    )
    print(
        "  IUPAC name    : "
        f"{pubchem.get('iupac_name')}"
    )
    print(
        "  canonical     : "
        f"{pubchem.get('canonical_smiles')}"
    )
    print()

    if (
        pubchem.get(
            "title"
        )
        != EXPECTED_TITLE
    ):
        raise RuntimeError(
            "PubChem title was not preserved"
        )

    if (
        core_smiles(
            core_odor
        )
        != molecule.smiles
    ):
        raise RuntimeError(
            "Core and ResourceGraph SMILES differ"
        )

    print(
        "Core / ResourceGraph chemical consistency:"
    )
    print(
        "  SMILES        : OK"
    )
    print()

    core_states = (
        core_semantic_states(
            core_odor
        )
    )

    graph_states = (
        graph_semantic_states(
            annotation
        )
    )

    if core_states != graph_states:
        raise RuntimeError(
            "Core and ResourceGraph semantic "
            "states differ"
        )

    print(
        "Core / ResourceGraph semantic consistency:"
    )
    print(
        f"  states        : {len(graph_states)}"
    )
    print(
        "  floral        : "
        f"{graph_states['floral']}"
    )
    print(
        "  comparison    : OK"
    )
    print()

    molecule_provenance = (
        molecule.extra.get(
            "provenance"
        )
    )

    annotation_provenance = (
        annotation.extra.get(
            "provenance"
        )
    )

    if molecule_provenance != {
        "source": "OdorNet",
    }:
        raise RuntimeError(
            "Molecule OdorNet provenance missing"
        )

    if annotation_provenance != {
        "source": "OdorNet",
    }:
        raise RuntimeError(
            "Annotation OdorNet provenance missing"
        )

    print(
        "Provenance:"
    )
    print(
        "  Molecule      : OdorNet"
    )
    print(
        "  Annotation    : OdorNet"
    )
    print()

    second_result = (
        enriched_odornet_record_to_graph(
            record
        )
    )

    if (
        second_result.molecule_id
        != result.molecule_id
    ):
        raise RuntimeError(
            "Molecule Resource ID "
            "is not deterministic"
        )

    if (
        second_result.annotation_id
        != result.annotation_id
    ):
        raise RuntimeError(
            "Annotation Resource ID "
            "is not deterministic"
        )

    print(
        "Resource identity:"
    )
    print(
        "  Molecule ID deterministic   : OK"
    )
    print(
        "  Annotation ID deterministic : OK"
    )
    print()

    print(
        "SUCCESS"
    )
    print(
        "The same real OdorNet Geraniol record "
        "is consistent across:"
    )
    print(
        "  1. Core .osmell"
    )
    print(
        "  2. experimental Molecule"
    )
    print(
        "  3. experimental Annotation"
    )
    print(
        "  4. PubChem ExternalIdentifier"
    )


if __name__ == "__main__":
    main()