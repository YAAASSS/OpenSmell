"""Validate OdorNet using the experimental OpenSmell Molecule resource.

This validation imports the enriched OdorNet dataset into the first
namespaced and versioned RFC-0008 OpenSmell resource type:

    org.opensmell.molecule
    type_version 0.1

Each OdorNet row becomes one Molecule resource.

The original OdorNet SMILES value is preserved as the Molecule.smiles value.

When PubChem enrichment provides an InChIKey, it is represented as an
ExternalIdentifier. No PubChem CID is invented because the current enrichment
dataset does not contain PubChem CID values.

The validation checks:

- every dataset row can become a Molecule;
- all Molecule resources can coexist in one GenericResourceGraph;
- resource IDs are unique;
- SMILES values survive an exact JSON round trip;
- PubChem InChIKey identifiers survive an exact JSON round trip;
- unresolved PubChem entries remain representable using their original SMILES;
- the serialized Generic ResourceGraph survives parse/serialize unchanged.

This is an experimental validation tool. It does not perform chemical
canonicalization or chemical-equivalence checking.
"""

from __future__ import annotations

import csv
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from opensmell.experimental.generic_graph import (
    GenericResourceGraph,
    create_default_resource_type_registry,
    generic_graph_from_dict,
    generic_graph_to_dict,
)
from opensmell.experimental.molecule import (
    Molecule,
    register_molecule_resource_type,
)
from opensmell.experimental.resources import (
    ExternalIdentifier,
)


DATASET_PATH = Path(
    "examples/odornet_enriched.csv"
)

EXPECTED_ROW_COUNT = 8892

PUBCHEM_STATUS_COLUMN = "PubChem_Status"
PUBCHEM_INCHIKEY_COLUMN = "PubChem_InChIKey"

PUBCHEM_INCHIKEY_SCHEME = "pubchem.inchikey"


def require_nonempty_smiles(
    record: dict[str, str],
    *,
    row_number: int,
) -> str:
    """Return the original OdorNet SMILES value."""

    value = record.get(
        "SMILES",
        "",
    )

    smiles = value.strip()

    if not smiles:
        raise ValueError(
            f"row {row_number}: missing SMILES"
        )

    return smiles


def optional_text(
    record: dict[str, str],
    field: str,
) -> str | None:
    """Return a stripped optional CSV value."""

    value = record.get(
        field,
        "",
    ).strip()

    if not value:
        return None

    return value


def validate_dataset_header(
    fieldnames: list[str] | None,
) -> None:
    """Validate columns required by this experiment."""

    if fieldnames is None:
        raise SystemExit(
            "Dataset does not contain a CSV header"
        )

    required_fields = {
        "SMILES",
        PUBCHEM_STATUS_COLUMN,
        PUBCHEM_INCHIKEY_COLUMN,
    }

    missing = sorted(
        required_fields
        - set(fieldnames)
    )

    if missing:
        raise SystemExit(
            "Dataset is missing required columns: "
            + ", ".join(missing)
        )


def create_registry():
    """Create an RFC-0008 registry containing Molecule 0.1."""

    registry = (
        create_default_resource_type_registry()
    )

    register_molecule_resource_type(
        registry
    )

    return registry


def molecule_from_odornet_record(
    record: dict[str, str],
    *,
    resource_id: str,
    row_number: int,
) -> Molecule:
    """Convert one enriched OdorNet row into a Molecule."""

    smiles = require_nonempty_smiles(
        record,
        row_number=row_number,
    )

    identifiers: list[
        ExternalIdentifier
    ] = []

    inchikey = optional_text(
        record,
        PUBCHEM_INCHIKEY_COLUMN,
    )

    if inchikey is not None:
        identifiers.append(
            ExternalIdentifier(
                scheme=PUBCHEM_INCHIKEY_SCHEME,
                value=inchikey,
            )
        )

    return Molecule(
        id=resource_id,
        smiles=smiles,
        identifiers=identifiers,
    )


def get_inchikey(
    molecule: Molecule,
) -> str | None:
    """Extract the PubChem InChIKey identifier from a Molecule."""

    matches = [
        identifier.value
        for identifier in molecule.identifiers
        if (
            identifier.scheme
            == PUBCHEM_INCHIKEY_SCHEME
        )
    ]

    if len(matches) > 1:
        raise ValueError(
            f"{molecule.id}: duplicate "
            "PubChem InChIKey identifiers"
        )

    if not matches:
        return None

    return matches[0]


def json_round_trip(
    document: dict[str, Any],
) -> dict[str, Any]:
    """Round-trip a graph document through strict standard JSON."""

    with tempfile.TemporaryDirectory() as directory:
        path = (
            Path(directory)
            / "odornet_molecules.json"
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                document,
                file,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            loaded = json.load(
                file
            )

    if not isinstance(
        loaded,
        dict,
    ):
        raise TypeError(
            "JSON round trip did not produce an object"
        )

    return loaded


def main() -> None:
    """Validate the complete enriched OdorNet dataset."""

    if not DATASET_PATH.exists():
        raise SystemExit(
            f"Dataset not found: {DATASET_PATH}"
        )

    print(
        f"Dataset: {DATASET_PATH}"
    )

    molecules: list[Molecule] = []

    expected_smiles: dict[
        str,
        str,
    ] = {}

    expected_inchikeys: dict[
        str,
        str | None,
    ] = {}

    pubchem_statuses: Counter[str] = (
        Counter()
    )

    smiles_counts: Counter[str] = (
        Counter()
    )

    with DATASET_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(
            csv_file
        )

        validate_dataset_header(
            reader.fieldnames
        )

        print(
            "Dataset header validated."
        )

        for dataset_index, record in enumerate(
            reader,
            start=1,
        ):
            row_number = (
                dataset_index + 1
            )

            resource_id = (
                f"odornet-molecule-"
                f"{dataset_index}"
            )

            molecule = (
                molecule_from_odornet_record(
                    record,
                    resource_id=resource_id,
                    row_number=row_number,
                )
            )

            if resource_id in expected_smiles:
                raise AssertionError(
                    "Duplicate generated Resource ID: "
                    f"{resource_id}"
                )

            molecules.append(
                molecule
            )

            expected_smiles[
                resource_id
            ] = molecule.smiles or ""

            expected_inchikeys[
                resource_id
            ] = get_inchikey(
                molecule
            )

            smiles_counts[
                molecule.smiles or ""
            ] += 1

            status = optional_text(
                record,
                PUBCHEM_STATUS_COLUMN,
            )

            if status is None:
                status = "missing"

            pubchem_statuses[
                status
            ] += 1

            if (
                dataset_index % 1000
                == 0
            ):
                print(
                    "Created "
                    f"{dataset_index:,} "
                    "Molecule resources"
                )

    print()

    if len(molecules) != EXPECTED_ROW_COUNT:
        raise SystemExit(
            "Unexpected OdorNet row count: "
            f"{len(molecules):,}; "
            f"expected {EXPECTED_ROW_COUNT:,}"
        )

    unique_resource_ids = {
        molecule.id
        for molecule in molecules
    }

    if (
        len(unique_resource_ids)
        != len(molecules)
    ):
        raise SystemExit(
            "Generated Molecule Resource IDs "
            "are not unique"
        )

    unique_smiles = len(
        smiles_counts
    )

    duplicate_smiles_rows = sum(
        count - 1
        for count in smiles_counts.values()
        if count > 1
    )

    molecules_with_inchikey = sum(
        1
        for value in expected_inchikeys.values()
        if value is not None
    )

    molecules_without_inchikey = (
        len(molecules)
        - molecules_with_inchikey
    )

    print(
        "Building GenericResourceGraph..."
    )

    graph = GenericResourceGraph(
        resources=molecules
    )

    registry = create_registry()

    print(
        "Serializing GenericResourceGraph..."
    )

    serialized = generic_graph_to_dict(
        graph,
        registry=registry,
    )

    print(
        "Performing strict JSON round trip..."
    )

    json_reloaded = json_round_trip(
        serialized
    )

    if json_reloaded != serialized:
        raise SystemExit(
            "Strict JSON round trip changed "
            "the Generic ResourceGraph document"
        )

    print(
        "Parsing GenericResourceGraph..."
    )

    reloaded_graph = (
        generic_graph_from_dict(
            json_reloaded,
            registry=registry,
        )
    )

    print(
        "Re-serializing GenericResourceGraph..."
    )

    reserialized = (
        generic_graph_to_dict(
            reloaded_graph,
            registry=registry,
        )
    )

    if reserialized != serialized:
        raise SystemExit(
            "Generic ResourceGraph "
            "parse/serialize round trip changed "
            "the document"
        )

    if (
        len(reloaded_graph.resources)
        != len(molecules)
    ):
        raise SystemExit(
            "Resource count changed during "
            "round trip"
        )

    smiles_mismatches: list[str] = []
    inchikey_mismatches: list[str] = []
    unexpected_types: list[str] = []

    for resource in (
        reloaded_graph.resources
    ):
        if not isinstance(
            resource,
            Molecule,
        ):
            unexpected_types.append(
                (
                    f"{resource.id}: "
                    f"{type(resource).__name__}"
                )
            )
            continue

        expected_smiles_value = (
            expected_smiles[
                resource.id
            ]
        )

        if (
            resource.smiles
            != expected_smiles_value
        ):
            smiles_mismatches.append(
                (
                    f"{resource.id}: "
                    f"expected "
                    f"{expected_smiles_value!r}, "
                    f"actual "
                    f"{resource.smiles!r}"
                )
            )

        expected_inchikey = (
            expected_inchikeys[
                resource.id
            ]
        )

        actual_inchikey = get_inchikey(
            resource
        )

        if (
            actual_inchikey
            != expected_inchikey
        ):
            inchikey_mismatches.append(
                (
                    f"{resource.id}: "
                    f"expected "
                    f"{expected_inchikey!r}, "
                    f"actual "
                    f"{actual_inchikey!r}"
                )
            )

    print()
    print(
        "MOLECULE RESOURCE VALIDATION"
    )
    print(
        "----------------------------"
    )

    print(
        f"Dataset rows:             "
        f"{len(molecules):,}"
    )

    print(
        f"Molecule resources:       "
        f"{len(molecules):,}"
    )

    print(
        f"Unique Resource IDs:      "
        f"{len(unique_resource_ids):,}"
    )

    print(
        f"Unique SMILES:            "
        f"{unique_smiles:,}"
    )

    print(
        f"Duplicate SMILES rows:    "
        f"{duplicate_smiles_rows:,}"
    )

    print(
        f"With PubChem InChIKey:    "
        f"{molecules_with_inchikey:,}"
    )

    print(
        f"Without PubChem InChIKey: "
        f"{molecules_without_inchikey:,}"
    )

    print(
        f"SMILES mismatches:        "
        f"{len(smiles_mismatches):,}"
    )

    print(
        f"InChIKey mismatches:      "
        f"{len(inchikey_mismatches):,}"
    )

    print(
        f"Unexpected resource type: "
        f"{len(unexpected_types):,}"
    )

    print()
    print(
        "PubChem statuses:"
    )

    for status, count in sorted(
        pubchem_statuses.items()
    ):
        print(
            f"  {status}: {count:,}"
        )

    if unexpected_types:
        print()
        print(
            "First unexpected resource types:"
        )

        for mismatch in unexpected_types[
            :20
        ]:
            print(
                f"  {mismatch}"
            )

        raise SystemExit(1)

    if smiles_mismatches:
        print()
        print(
            "First SMILES mismatches:"
        )

        for mismatch in smiles_mismatches[
            :20
        ]:
            print(
                f"  {mismatch}"
            )

        raise SystemExit(1)

    if inchikey_mismatches:
        print()
        print(
            "First InChIKey mismatches:"
        )

        for mismatch in inchikey_mismatches[
            :20
        ]:
            print(
                f"  {mismatch}"
            )

        raise SystemExit(1)

    print()
    print(
        "SUCCESS: all OdorNet Molecule resources "
        "survived the RFC-0008 Generic "
        "ResourceGraph round trip."
    )


if __name__ == "__main__":
    main()