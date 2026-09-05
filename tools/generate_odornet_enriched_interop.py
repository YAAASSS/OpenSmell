"""Generate a real enriched OdorNet interoperability document.

This tool creates an experimental OpenSmell GenericResourceGraph from one
real row of the enriched OdorNet CSV dataset.

The resulting JSON document is intended to be consumed by an independent
JavaScript implementation. It demonstrates interoperability across:

    OdorNet CSV
        -> OpenSmell Python adapter
        -> GenericResourceGraph
        -> JSON
        -> independent JavaScript consumer

This is an experimental interoperability validation tool. It does not modify
the OpenSmell 0.1 Core specification.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from opensmell.adapters.odornet import ODORNET_LABELS
from opensmell.experimental.annotation import (
    register_annotation_resource_type,
)
from opensmell.experimental.generic_graph import (
    ResourceTypeRegistry,
    create_default_resource_type_registry,
    generic_graph_dumps,
)
from opensmell.experimental.molecule import (
    register_molecule_resource_type,
)
from opensmell.experimental.odornet_enriched_adapter import (
    enriched_odornet_record_to_graph,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CSV = (
    PROJECT_ROOT
    / "examples"
    / "odornet_enriched.csv"
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "examples"
    / "odornet_enriched_interop.json"
)

DEFAULT_ROW = 0

PUBCHEM_FIELDS = (
    "PubChem_Status",
    "PubChem_Title",
    "PubChem_IUPACName",
    "PubChem_CanonicalSMILES",
    "PubChem_InChIKey",
)


def parse_odornet_value(
    raw: str | None,
) -> int | None:
    """Parse one OdorNet label value."""

    if raw is None:
        return None

    value = raw.strip()

    if not value:
        return None

    if value in {"1", "1.0"}:
        return 1

    if value in {"0", "0.0"}:
        return 0

    raise ValueError(
        "unexpected OdorNet label value: "
        f"{raw!r}"
    )


def create_registry() -> ResourceTypeRegistry:
    """Create the registry required for Molecule and Annotation."""

    registry = (
        create_default_resource_type_registry()
    )

    register_molecule_resource_type(
        registry
    )

    register_annotation_resource_type(
        registry
    )

    return registry


def load_row(
    csv_path: Path,
    row_index: int,
) -> dict[str, Any]:
    """Load one zero-based data row from enriched OdorNet."""

    if row_index < 0:
        raise ValueError(
            "--row must be zero or greater"
        )

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"OdorNet CSV not found: {csv_path}"
        )

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        fieldnames = reader.fieldnames

        if fieldnames is None:
            raise ValueError(
                "OdorNet CSV has no header"
            )

        required = {
            "SMILES",
            *ODORNET_LABELS,
        }

        missing = sorted(
            required.difference(
                fieldnames
            )
        )

        if missing:
            raise ValueError(
                "OdorNet CSV is missing required "
                "column(s): "
                + ", ".join(missing)
            )

        selected: dict[str, str | None] | None = None

        for index, row in enumerate(
            reader
        ):
            if index == row_index:
                selected = row
                break

    if selected is None:
        raise IndexError(
            f"OdorNet data row {row_index} does not exist"
        )

    raw_smiles = selected.get(
        "SMILES"
    )

    if raw_smiles is None:
        raise ValueError(
            "selected row has no SMILES value"
        )

    smiles = raw_smiles.strip()

    if not smiles:
        raise ValueError(
            "selected row has an empty SMILES"
        )

    record: dict[str, Any] = {
        "SMILES": smiles,
    }

    for label in ODORNET_LABELS:
        record[label] = (
            parse_odornet_value(
                selected.get(label)
            )
        )

    for field in PUBCHEM_FIELDS:
        record[field] = selected.get(
            field,
            "",
        )

    return record


def build_document(
    csv_path: Path,
    row_index: int,
) -> dict[str, Any]:
    """Build the cross-language interoperability document."""

    record = load_row(
        csv_path,
        row_index,
    )

    result = (
        enriched_odornet_record_to_graph(
            record
        )
    )

    registry = create_registry()

    graph_json = generic_graph_dumps(
        result.graph,
        registry=registry,
        indent=2,
    )

    graph_document = json.loads(
        graph_json
    )

    return {
        "interop_test": (
            "org.opensmell.experimental."
            "odornet-enriched.interop"
        ),
        "version": "0.1",
        "source": {
            "dataset": "OdorNet",
            "row": row_index,
        },
        "expected": {
            "molecule_id": (
                result.molecule_id
            ),
            "annotation_id": (
                result.annotation_id
            ),
            "smiles": record["SMILES"],
            "pubchem_inchikey": (
                record.get(
                    "PubChem_InChIKey"
                )
                or None
            ),
            "semantic_states": {
                label: (
                    "present"
                    if record[label] == 1
                    else (
                        "absent"
                        if record[label] == 0
                        else "unknown"
                    )
                )
                for label in ODORNET_LABELS
            },
        },
        "graph": graph_document,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a real enriched OdorNet "
            "OpenSmell interoperability document."
        )
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=(
            "Path to enriched OdorNet CSV "
            f"(default: {DEFAULT_CSV})"
        ),
    )

    parser.add_argument(
        "--row",
        type=int,
        default=DEFAULT_ROW,
        help=(
            "Zero-based OdorNet data row "
            f"(default: {DEFAULT_ROW})"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(
            "Output interoperability JSON "
            f"(default: {DEFAULT_OUTPUT})"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    document = build_document(
        args.csv,
        args.row,
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    graph = document["graph"]
    expected = document["expected"]

    print(
        "OpenSmell enriched OdorNet "
        "interop generator"
    )
    print(
        "=================================="
    )
    print()
    print(
        f"CSV: {args.csv}"
    )
    print(
        f"Data row: {args.row}"
    )
    print(
        f"Resources: {len(graph['resources'])}"
    )
    print(
        "Molecule ID: "
        f"{expected['molecule_id']}"
    )
    print(
        "Annotation ID: "
        f"{expected['annotation_id']}"
    )
    print(
        f"SMILES: {expected['smiles']}"
    )
    print(
        "PubChem InChIKey: "
        f"{expected['pubchem_inchikey']}"
    )
    print()
    print(
        "Wrote "
        f"{args.output}"
    )


if __name__ == "__main__":
    main()