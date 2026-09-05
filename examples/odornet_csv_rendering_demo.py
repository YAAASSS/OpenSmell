"""Render one real row from the enriched OdorNet CSV through OpenSmell.

This example reads ``examples/odornet_enriched.csv`` by default, selects one
real dataset row, shows both the original OdorNet semantic labels and the
available PubChem enrichment metadata, converts the row with the existing
OpenSmell OdorNet adapter, bridges the Core Odor into the experimental
ResourceGraph, maps positive semantic annotations through an illustrative
device policy, and records the resulting RenderingPlan with a
SimulatedDiffuser.

The PubChem enrichment metadata is displayed for context only. The OpenSmell
semantic annotation states still come from the original OdorNet label columns.

The mapping from semantic descriptors to virtual device channels is a demo
policy only. It is not a scientific claim about physical odor reproduction.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    ODORNET_LABELS,
    from_record_with_annotations,
)
from opensmell.experimental.annotation import Annotation
from opensmell.experimental.odor_graph_bridge import (
    bridge_odor_to_resource_graph,
)
from opensmell.experimental.rendering import RenderRequest
from opensmell.experimental.semantic_channel_mapper import (
    SemanticChannelBinding,
    SemanticChannelMapper,
)
from opensmell.experimental.simulated_diffuser import (
    SimulatedDiffuser,
)


DEFAULT_CSV = Path(
    "examples/odornet_enriched.csv"
)

PUBCHEM_FIELDS = (
    ("Status", "PubChem_Status"),
    ("Title", "PubChem_Title"),
    ("IUPACName", "PubChem_IUPACName"),
    (
        "CanonicalSMILES",
        "PubChem_CanonicalSMILES",
    ),
    ("InChIKey", "PubChem_InChIKey"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render one real enriched OdorNet CSV row "
            "through the experimental OpenSmell "
            "rendering pipeline."
        )
    )

    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=DEFAULT_CSV,
        help=(
            "Path to the enriched OdorNet CSV "
            "(default: "
            "examples/odornet_enriched.csv)"
        ),
    )

    parser.add_argument(
        "--row",
        type=int,
        default=0,
        help=(
            "Zero-based data-row index "
            "(default: 0)."
        ),
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=4.0,
        help=(
            "Requested render duration in seconds "
            "(default: 4.0)."
        ),
    )

    return parser.parse_args()


def parse_odornet_value(
    value: str | None,
) -> int | None:
    """Convert an OdorNet CSV value to 1, 0, or unknown."""

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
        "unexpected OdorNet label value: "
        f"{value!r}"
    )


def load_row(
    csv_path: Path,
    row_index: int,
) -> tuple[
    dict[str, Any],
    dict[str, str],
]:
    """Load one real row from an enriched OdorNet CSV."""

    if row_index < 0:
        raise ValueError(
            "--row must be zero or greater"
        )

    if not csv_path.is_file():
        raise FileNotFoundError(
            "OdorNet CSV not found: "
            f"{csv_path}"
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

        required = {
            "SMILES",
            *ODORNET_LABELS,
        }

        missing = (
            required
            - set(reader.fieldnames)
        )

        if missing:
            names = ", ".join(
                sorted(missing)
            )

            raise ValueError(
                "OdorNet CSV is missing "
                "required column(s): "
                f"{names}"
            )

        raw_row: dict[str, str] | None = None

        for (
            current_index,
            candidate,
        ) in enumerate(reader):
            if current_index == row_index:
                raw_row = candidate
                break

    if raw_row is None:
        raise IndexError(
            "OdorNet row "
            f"{row_index} does not exist"
        )

    smiles_value = raw_row.get(
        "SMILES",
        "",
    )

    if smiles_value is None:
        smiles = ""
    else:
        smiles = smiles_value.strip()

    if not smiles:
        raise ValueError(
            "OdorNet row "
            f"{row_index} has an empty "
            "SMILES value"
        )

    record: dict[str, Any] = {
        "SMILES": smiles,
    }

    for label in ODORNET_LABELS:
        record[label] = (
            parse_odornet_value(
                raw_row.get(label)
            )
        )

    return (
        record,
        raw_row,
    )


def display_value(
    row: dict[str, str],
    field: str,
) -> str:
    """Return a readable value for a CSV field."""

    value = row.get(
        field,
        "",
    )

    if value is None:
        return "<missing>"

    value = value.strip()

    if not value:
        return "<blank>"

    return value


def main() -> None:
    args = parse_args()

    record, raw_row = load_row(
        args.csv_path,
        args.row,
    )

    odor = (
        from_record_with_annotations(
            record,
            odor_id=(
                "odornet-enriched-row-"
                f"{args.row}"
            ),
        )
    )

    semantic = next(
        representation
        for representation
        in odor.representations
        if representation.scheme.id
        == ANNOTATION_SCHEME_ID
    )

    result = (
        bridge_odor_to_resource_graph(
            odor
        )
    )

    annotation = (
        result.graph.require(
            result.annotation_ids[0]
        )
    )

    if not isinstance(
        annotation,
        Annotation,
    ):
        raise RuntimeError(
            "expected bridged "
            "Annotation resource"
        )

    bindings = [
        SemanticChannelBinding(
            descriptor="floral",
            channel=1,
            intensity=0.70,
        ),
        SemanticChannelBinding(
            descriptor=(
                "sweety&gourmand"
            ),
            channel=2,
            intensity=0.55,
        ),
        SemanticChannelBinding(
            descriptor="spice",
            channel=3,
            intensity=0.35,
        ),
        SemanticChannelBinding(
            descriptor="nutty",
            channel=4,
            intensity=0.80,
        ),
    ]

    mapper = (
        SemanticChannelMapper(
            bindings=bindings
        )
    )

    request = RenderRequest(
        resource_id=(
            result.primary_resource_id
        ),
        duration=args.duration,
    )

    plan = mapper.map(
        result.graph,
        request,
    )

    diffuser = (
        SimulatedDiffuser()
    )

    event = diffuser.render(
        plan
    )

    print(
        "OpenSmell enriched "
        "OdorNet rendering demo"
    )
    print(
        "=" * 42
    )
    print()

    print(
        f"CSV: {args.csv_path}"
    )

    print(
        "Data row: "
        f"{args.row} "
        "(zero-based, header excluded)"
    )

    print()

    print(
        "Chemical source data:"
    )

    print(
        f"  {'SMILES':<18} : "
        f"{record['SMILES']}"
    )

    for (
        display_name,
        csv_field,
    ) in PUBCHEM_FIELDS:
        print(
            f"  {display_name:<18} : "
            f"{display_value(raw_row, csv_field)}"
        )

    print()

    print(
        "Raw OdorNet semantic values:"
    )

    for label in ODORNET_LABELS:
        print(
            f"  {label:<24} : "
            f"{display_value(raw_row, label)}"
        )

    print()

    print(
        "OpenSmell semantic states:"
    )

    for item in (
        semantic.data["annotations"]
    ):
        print(
            f"  {item['value']:<24} : "
            f"{item['state']}"
        )

    print()

    print(
        "OpenSmell ResourceGraph:"
    )

    print(
        "  Molecule:   "
        f"{result.primary_resource_id}"
    )

    print(
        "  Annotation: "
        f"{annotation.id}"
    )

    print(
        "  Subject:    "
        f"{annotation.subject.resource_id}"
    )

    print()

    print(
        "Device-specific demo policy:"
    )

    for binding in bindings:
        print(
            f"  {binding.descriptor:<24} "
            f"-> channel "
            f"{binding.channel} "
            f"@ {binding.intensity:.2f}"
        )

    print()

    print(
        "RenderingPlan:"
    )

    if plan.commands:
        for command in plan.commands:
            print(
                f"  Channel "
                f"{command.channel}: "
                f"{command.intensity:.2f}"
            )
    else:
        print(
            "  No present descriptor "
            "is mapped by this demo "
            "device policy."
        )

    print(
        f"  Duration: "
        f"{plan.duration:.1f} s"
    )

    print()

    print(
        "SimulatedDiffuser:"
    )

    if event.commands:
        for command in event.commands:
            print(
                "  Recorded channel "
                f"{command.channel} @ "
                f"{command.intensity:.2f}"
            )
    else:
        print(
            "  No channel commands "
            "recorded"
        )

    print(
        "  Recorded duration: "
        f"{event.duration:.1f} s"
    )

    print()

    print(
        "Rendering completed "
        "successfully "
        "(simulation only)."
    )


if __name__ == "__main__":
    main()