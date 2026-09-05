"""Validate the experimental enriched OdorNet adapter on the real dataset.

This tool reads the locally enriched OdorNet CSV and converts every row into
the experimental OpenSmell GenericResourceGraph representation.

It validates that:

- every source row can be converted;
- every graph contains one Molecule and one Annotation;
- every Annotation references its Molecule;
- every semantic annotation contains all OdorNet labels;
- PubChem InChIKey identifiers are preserved when available;
- Resource IDs remain unique across the imported dataset.

This is an experimental validation tool and does not modify OpenSmell Core.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from opensmell.adapters.odornet import (
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


DEFAULT_CSV = Path(
    "examples/odornet_enriched.csv"
)


def _parse_semantic_value(
    value: str | None,
) -> int | None:
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


def _build_record(
    row: dict[str, str],
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "SMILES": row.get(
            "SMILES",
            "",
        ),
        "PubChem_Status": row.get(
            "PubChem_Status",
            "",
        ),
        "PubChem_Title": row.get(
            "PubChem_Title",
            "",
        ),
        "PubChem_IUPACName": row.get(
            "PubChem_IUPACName",
            "",
        ),
        "PubChem_CanonicalSMILES": row.get(
            "PubChem_CanonicalSMILES",
            "",
        ),
        "PubChem_InChIKey": row.get(
            "PubChem_InChIKey",
            "",
        ),
    }

    for label in ODORNET_LABELS:
        record[label] = (
            _parse_semantic_value(
                row.get(label)
            )
        )

    return record


def main() -> None:
    csv_path = DEFAULT_CSV

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"dataset not found: {csv_path}"
        )

    total_rows = 0
    resolved_pubchem = 0
    inchikey_identifiers = 0
    missing_inchikey = 0

    semantic_states = {
        "present": 0,
        "absent": 0,
        "unknown": 0,
    }

    molecule_ids: set[str] = set()
    annotation_ids: set[str] = set()

    first_molecule: Molecule | None = None
    first_annotation: Annotation | None = None

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
                "dataset has no header"
            )

        required_fields = {
            "SMILES",
            *ODORNET_LABELS,
            "PubChem_Status",
            "PubChem_Title",
            "PubChem_IUPACName",
            "PubChem_CanonicalSMILES",
            "PubChem_InChIKey",
        }

        missing_fields = (
            required_fields
            - set(reader.fieldnames)
        )

        if missing_fields:
            names = ", ".join(
                sorted(missing_fields)
            )

            raise ValueError(
                "dataset is missing required "
                f"column(s): {names}"
            )

        for row_index, row in enumerate(
            reader
        ):
            record = _build_record(
                row
            )

            result = (
                enriched_odornet_record_to_graph(
                    record
                )
            )

            molecule = (
                result.graph.require(
                    result.molecule_id
                )
            )

            annotation = (
                result.graph.require(
                    result.annotation_id
                )
            )

            if not isinstance(
                molecule,
                Molecule,
            ):
                raise TypeError(
                    f"row {row_index}: "
                    "expected Molecule"
                )

            if not isinstance(
                annotation,
                Annotation,
            ):
                raise TypeError(
                    f"row {row_index}: "
                    "expected Annotation"
                )

            if len(
                result.graph.resources
            ) != 2:
                raise ValueError(
                    f"row {row_index}: "
                    "graph must contain exactly "
                    "two resources"
                )

            if (
                annotation.subject.resource_id
                != molecule.id
            ):
                raise ValueError(
                    f"row {row_index}: "
                    "Annotation subject does not "
                    "reference Molecule"
                )

            annotations = (
                annotation.data.get(
                    "annotations"
                )
            )

            if not isinstance(
                annotations,
                list,
            ):
                raise TypeError(
                    f"row {row_index}: "
                    "annotations must be a list"
                )

            if len(
                annotations
            ) != len(
                ODORNET_LABELS
            ):
                raise ValueError(
                    f"row {row_index}: "
                    "unexpected annotation count"
                )

            values = [
                item.get(
                    "value"
                )
                for item in annotations
            ]

            if values != list(
                ODORNET_LABELS
            ):
                raise ValueError(
                    f"row {row_index}: "
                    "OdorNet label order or "
                    "contents changed"
                )

            for item in annotations:
                state = item.get(
                    "state"
                )

                if (
                    state
                    not in semantic_states
                ):
                    raise ValueError(
                        f"row {row_index}: "
                        "invalid semantic state "
                        f"{state!r}"
                    )

                semantic_states[
                    state
                ] += 1

            status = (
                str(
                    record.get(
                        "PubChem_Status",
                        "",
                    )
                )
                .strip()
            )

            inchikey = (
                str(
                    record.get(
                        "PubChem_InChIKey",
                        "",
                    )
                )
                .strip()
            )

            if status == "resolved":
                resolved_pubchem += 1

            matching_identifiers = [
                identifier
                for identifier
                in molecule.identifiers
                if (
                    identifier.scheme
                    == PUBCHEM_INCHIKEY_SCHEME
                )
            ]

            if (
                status == "resolved"
                and inchikey
            ):
                if len(
                    matching_identifiers
                ) != 1:
                    raise ValueError(
                        f"row {row_index}: "
                        "expected one PubChem "
                        "InChIKey identifier"
                    )

                if (
                    matching_identifiers[
                        0
                    ].value
                    != inchikey
                ):
                    raise ValueError(
                        f"row {row_index}: "
                        "PubChem InChIKey mismatch"
                    )

                inchikey_identifiers += 1

            else:
                if matching_identifiers:
                    raise ValueError(
                        f"row {row_index}: "
                        "unexpected PubChem "
                        "InChIKey identifier"
                    )

                missing_inchikey += 1

            if (
                molecule.id
                in molecule_ids
            ):
                raise ValueError(
                    f"row {row_index}: "
                    "duplicate Molecule "
                    f"Resource ID {molecule.id}"
                )

            if (
                annotation.id
                in annotation_ids
            ):
                raise ValueError(
                    f"row {row_index}: "
                    "duplicate Annotation "
                    f"Resource ID {annotation.id}"
                )

            molecule_ids.add(
                molecule.id
            )

            annotation_ids.add(
                annotation.id
            )

            if first_molecule is None:
                first_molecule = (
                    molecule
                )

                first_annotation = (
                    annotation
                )

            total_rows += 1

    print(
        "OpenSmell enriched OdorNet "
        "adapter validation"
    )
    print(
        "=" * 43
    )
    print()

    print(
        f"Dataset: {csv_path}"
    )
    print(
        f"Rows converted: "
        f"{total_rows:,}"
    )
    print(
        f"Molecule IDs: "
        f"{len(molecule_ids):,}"
    )
    print(
        f"Annotation IDs: "
        f"{len(annotation_ids):,}"
    )

    print()

    print(
        "PubChem:"
    )
    print(
        f"  resolved rows: "
        f"{resolved_pubchem:,}"
    )
    print(
        f"  InChIKey identifiers: "
        f"{inchikey_identifiers:,}"
    )
    print(
        f"  rows without usable "
        f"InChIKey: "
        f"{missing_inchikey:,}"
    )

    print()

    print(
        "Semantic states:"
    )

    for (
        state,
        count,
    ) in semantic_states.items():
        print(
            f"  {state:<8}: "
            f"{count:,}"
        )

    print()

    if first_molecule is not None:
        print(
            "First imported Molecule:"
        )
        print(
            f"  ID:     "
            f"{first_molecule.id}"
        )
        print(
            f"  SMILES: "
            f"{first_molecule.smiles}"
        )

        for identifier in (
            first_molecule.identifiers
        ):
            print(
                f"  {identifier.scheme}: "
                f"{identifier.value}"
            )

    if first_annotation is not None:
        print()
        print(
            "First Annotation:"
        )
        print(
            f"  ID:      "
            f"{first_annotation.id}"
        )
        print(
            f"  Subject: "
            f"{first_annotation.subject.resource_id}"
        )
        print(
            f"  Scheme:  "
            f"{first_annotation.scheme.id} "
            f"{first_annotation.scheme.version}"
        )

    print()

    print(
        "Validation completed "
        "successfully."
    )


if __name__ == "__main__":
    main()