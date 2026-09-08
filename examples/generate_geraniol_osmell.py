"""Generate a Core OpenSmell .osmell document from real enriched OdorNet data.

This example selects the Geraniol record from:

    examples/odornet_enriched.csv

and converts it using the existing Core OdorNet adapter.

The enriched OdorNet + PubChem dataset is an external, locally prepared
development input. It is intentionally not tracked in the OpenSmell
repository.

The generated .osmell document intentionally contains only information that
belongs in, or is already experimentally supported by, the Core OpenSmell
document model:

- a Core OpenSmell odor identifier;
- the original OdorNet SMILES representation;
- the complete twelve-state OdorNet semantic annotation representation;
- experimental OdorNet provenance already implemented by the adapter;
- a human-readable Geraniol label.

PubChem enrichment is deliberately NOT copied into the Core .osmell document.

PubChem title, IUPAC name, canonical SMILES and InChIKey belong to the
experimental Molecule / ResourceGraph layer, where OpenSmell already has a
dedicated enriched OdorNet adapter.

The script writes the file and then reloads it to verify the Core round trip.

The committed Geraniol fixture uses a stable OpenSmell odor identifier so
regenerating the fixture from the same source record does not create a new
identity on every run.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import opensmell

from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    ODORNET_LABELS,
    from_record_with_annotations,
)


CSV_PATH = Path(
    "examples/odornet_enriched.csv"
)

OUTPUT_PATH = Path(
    "examples/geraniol.osmell"
)

GERANIOL_ROW = 2106

GERANIOL_ODOR_ID = (
    "urn:uuid:89e67268-14dc-4b5b-9743-447c24deec41"
)

EXPECTED_TITLE = "Geraniol"

EXPECTED_INCHIKEY = (
    "GLZPCOQZEFWAFX-JXMROGBWSA-N"
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
    """Return one required non-empty CSV field."""

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
) -> tuple[
    dict[str, Any],
    dict[str, str],
]:
    """Load one zero-based data row from enriched OdorNet."""

    if not csv_path.is_file():
        raise FileNotFoundError(
            "Enriched OdorNet dataset not found: "
            f"{csv_path}\n"
            "\n"
            "This generator depends on the locally prepared "
            "OdorNet + PubChem enrichment dataset. The dataset is "
            "external to OpenSmell and is intentionally not tracked "
            "in the repository.\n"
            "\n"
            "Expected local path:\n"
            f"  {csv_path}\n"
            "\n"
            "The committed examples/geraniol.osmell fixture is "
            "already available without this external dataset. "
            "This dataset is required only when regenerating the "
            "fixture from the enriched OdorNet source."
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
            "PubChem_Title",
            "PubChem_InChIKey",
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

    smiles = require_text(
        selected_row,
        "SMILES",
    )

    record: dict[str, Any] = {
        "SMILES": smiles,
    }

    for label in ODORNET_LABELS:
        record[label] = (
            parse_odornet_value(
                selected_row.get(
                    label
                )
            )
        )

    return (
        record,
        selected_row,
    )


def semantic_states(
    odor: opensmell.Odor,
) -> dict[str, str]:
    """Return semantic annotation states from an Odor."""

    for representation in odor.representations:
        if (
            representation.scheme.id
            == ANNOTATION_SCHEME_ID
        ):
            annotations = (
                representation.data[
                    "annotations"
                ]
            )

            return {
                item["value"]: item["state"]
                for item in annotations
            }

    raise RuntimeError(
        "semantic annotation representation "
        "not found"
    )


def find_smiles(
    odor: opensmell.Odor,
) -> str:
    """Return the chemical SMILES from an Odor."""

    for representation in odor.representations:
        if (
            representation.scheme.id
            == "org.opensmell.chemical.smiles"
        ):
            smiles = (
                representation.data.get(
                    "smiles"
                )
            )

            if not isinstance(
                smiles,
                str,
            ):
                raise RuntimeError(
                    "chemical SMILES is invalid"
                )

            return smiles

    raise RuntimeError(
        "chemical SMILES representation "
        "not found"
    )


def verify_odornet_provenance(
    odor: opensmell.Odor,
) -> None:
    """Verify provenance already added by the OdorNet adapter."""

    for representation in odor.representations:
        provenance = (
            representation.extra.get(
                "provenance"
            )
        )

        if provenance != {
            "source": "OdorNet",
        }:
            raise RuntimeError(
                "OdorNet provenance missing "
                "from representation "
                f"{representation.scheme.id}"
            )


def main() -> None:
    print(
        "OpenSmell - Geraniol Core generator"
    )
    print(
        "=" * 44
    )
    print()

    record, enriched_row = (
        load_enriched_row(
            CSV_PATH,
            GERANIOL_ROW,
        )
    )

    title = require_text(
        enriched_row,
        "PubChem_Title",
    )

    inchikey = require_text(
        enriched_row,
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

    print(
        "Source record:"
    )
    print(
        "  dataset       : OdorNet enriched"
    )
    print(
        f"  row           : {GERANIOL_ROW}"
    )
    print(
        f"  PubChem title : {title}"
    )
    print(
        f"  InChIKey      : {inchikey}"
    )
    print(
        f"  OdorNet SMILES: {record['SMILES']}"
    )
    print()

    odor = (
        from_record_with_annotations(
            record,
            odor_id=GERANIOL_ODOR_ID,
        )
    )

    if odor.metadata is None:
        odor.metadata = (
            opensmell.Metadata(
                labels={
                    "en": title,
                },
                description=(
                    "Geraniol record converted "
                    "from the enriched OdorNet "
                    "dataset."
                ),
            )
        )
    else:
        odor.metadata.labels[
            "en"
        ] = title

    print(
        "Generated Core identity:"
    )
    print(
        f"  {odor.id}"
    )
    print()

    states = semantic_states(
        odor
    )

    print(
        "OdorNet semantic states:"
    )

    for label in ODORNET_LABELS:
        print(
            f"  {label:<24} "
            f"{states[label]}"
        )

    print()

    verify_odornet_provenance(
        odor
    )

    opensmell.dump(
        odor,
        OUTPUT_PATH,
    )

    print(
        f"Written: {OUTPUT_PATH}"
    )
    print()

    print(
        "Reloading generated .osmell..."
    )

    reloaded = opensmell.load(
        OUTPUT_PATH
    )

    if reloaded.id != odor.id:
        raise RuntimeError(
            "odor ID changed during round trip"
        )

    if reloaded.id != GERANIOL_ODOR_ID:
        raise RuntimeError(
            "Geraniol fixture ID changed during generation"
        )

    if (
        find_smiles(
            reloaded
        )
        != record["SMILES"]
    ):
        raise RuntimeError(
            "SMILES changed during round trip"
        )

    reloaded_states = (
        semantic_states(
            reloaded
        )
    )

    if reloaded_states != states:
        raise RuntimeError(
            "semantic annotations changed "
            "during round trip"
        )

    verify_odornet_provenance(
        reloaded
    )

    if reloaded.metadata is None:
        raise RuntimeError(
            "metadata disappeared "
            "during round trip"
        )

    if (
        reloaded.metadata.labels.get(
            "en"
        )
        != title
    ):
        raise RuntimeError(
            "Geraniol label changed "
            "during round trip"
        )

    if (
        reloaded_states.get(
            "floral"
        )
        != "present"
    ):
        raise RuntimeError(
            "Geraniol floral annotation "
            "is not present"
        )

    print(
        "Round trip: OK"
    )
    print()

    print(
        "Verified OpenSmell document:"
    )
    print(
        f"  ID       : {reloaded.id}"
    )
    print(
        f"  Name     : {title}"
    )
    print(
        f"  SMILES   : {find_smiles(reloaded)}"
    )
    print(
        "  floral   : "
        f"{reloaded_states['floral']}"
    )
    print(
        "  states   : "
        f"{len(reloaded_states)}"
    )
    print()

    print(
        "PubChem enrichment was used only "
        "to verify the selected source row."
    )
    print(
        "It was intentionally not embedded "
        "into the Core .osmell document."
    )
    print()

    print(
        "SUCCESS: OdorNet -> Core OpenSmell "
        "-> .osmell -> Core OpenSmell."
    )


if __name__ == "__main__":
    main()