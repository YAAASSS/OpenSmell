"""Validate OdorNet using Molecule and Annotation resources.

This experiment tests whether the RFC-0004 semantic annotation model can be
attached cleanly to RFC-0009 Molecule resources through a generic Annotation
resource transported by the RFC-0008 Generic ResourceGraph.

Each OdorNet row becomes:

- one Molecule resource containing chemical identity; and
- one Annotation resource referencing that Molecule.

Each Annotation carries all twelve OdorNet semantic category states using the
RFC-0004 semantic annotation scheme:

    org.opensmell.semantic.annotations
    version 0.1

The validation checks that:

- all 8,892 OdorNet rows become Molecule resources;
- all 8,892 rows become Annotation resources;
- every Annotation references the corresponding Molecule;
- all 106,704 semantic annotation states are represented;
- present, absent, and unknown states survive exactly;
- original SMILES values survive exactly;
- available PubChem InChIKey identifiers survive exactly;
- OdorNet provenance survives exactly;
- typed Molecule and Annotation resources survive parsing;
- the complete Generic ResourceGraph survives strict JSON and
  parse/serialize round trips unchanged.

This is an experimental validation tool. It does not define RFC-0010 and does
not make the Annotation resource normative.
"""

from __future__ import annotations

import csv
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from opensmell.experimental.annotation import (
    Annotation,
    register_annotation_resource_type,
)
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
    Reference,
)
from opensmell.experimental.scheme import (
    Scheme,
)


DATASET_PATH = Path(
    "examples/odornet_enriched.csv"
)

EXPECTED_ROW_COUNT = 8892

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

EXPECTED_ANNOTATIONS_PER_ROW = len(
    ODORNET_LABELS
)

EXPECTED_ANNOTATION_COUNT = (
    EXPECTED_ROW_COUNT
    * EXPECTED_ANNOTATIONS_PER_ROW
)

PUBCHEM_STATUS_COLUMN = "PubChem_Status"
PUBCHEM_INCHIKEY_COLUMN = "PubChem_InChIKey"
PUBCHEM_INCHIKEY_SCHEME = "pubchem.inchikey"

SEMANTIC_ANNOTATION_SCHEME_ID = (
    "org.opensmell.semantic.annotations"
)
SEMANTIC_ANNOTATION_SCHEME_VERSION = "0.1"

ODORNET_PROVENANCE = {
    "source": "OdorNet",
}


def require_nonempty_smiles(
    record: dict[str, str],
    *,
    row_number: int,
) -> str:
    """Return the original non-empty OdorNet SMILES value."""

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


def annotation_state(
    value: str | None,
    *,
    row_number: int,
    label: str,
) -> str:
    """Map one OdorNet CSV value to an RFC-0004 annotation state."""

    if value is None:
        return "unknown"

    normalized = value.strip()

    if normalized == "":
        return "unknown"

    if normalized in {
        "1",
        "1.0",
    }:
        return "present"

    if normalized in {
        "0",
        "0.0",
    }:
        return "absent"

    raise ValueError(
        f"row {row_number}: unexpected value "
        f"{value!r} for OdorNet label {label!r}"
    )


def validate_dataset_header(
    fieldnames: list[str] | None,
) -> None:
    """Validate all columns required by this experiment."""

    if fieldnames is None:
        raise SystemExit(
            "Dataset does not contain a CSV header"
        )

    required_fields = {
        "SMILES",
        PUBCHEM_STATUS_COLUMN,
        PUBCHEM_INCHIKEY_COLUMN,
        *ODORNET_LABELS,
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
    """Create the RFC-0008 registry used by this experiment."""

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


def semantic_annotation_data(
    record: dict[str, str],
    *,
    row_number: int,
) -> dict[str, Any]:
    """Build the RFC-0004 semantic annotation payload for one row."""

    annotations: list[
        dict[str, str]
    ] = []

    for label in ODORNET_LABELS:
        state = annotation_state(
            record.get(label),
            row_number=row_number,
            label=label,
        )

        annotations.append(
            {
                "value": label,
                "language": "en",
                "state": state,
            }
        )

    return {
        "annotations": annotations,
    }


def annotation_from_odornet_record(
    record: dict[str, str],
    *,
    resource_id: str,
    molecule_resource_id: str,
    row_number: int,
) -> Annotation:
    """Convert one OdorNet row into a semantic Annotation."""

    return Annotation(
        id=resource_id,
        subject=Reference(
            resource_id=molecule_resource_id,
        ),
        scheme=Scheme(
            id=SEMANTIC_ANNOTATION_SCHEME_ID,
            version=(
                SEMANTIC_ANNOTATION_SCHEME_VERSION
            ),
        ),
        data=semantic_annotation_data(
            record,
            row_number=row_number,
        ),
        extra={
            "provenance": dict(
                ODORNET_PROVENANCE
            ),
        },
    )


def get_inchikey(
    molecule: Molecule,
) -> str | None:
    """Extract the PubChem InChIKey from a Molecule."""

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


def annotation_states(
    annotation: Annotation,
) -> dict[str, str]:
    """Extract label-to-state values from one semantic Annotation."""

    if (
        annotation.scheme.id
        != SEMANTIC_ANNOTATION_SCHEME_ID
    ):
        raise ValueError(
            f"{annotation.id}: unexpected "
            "annotation scheme id"
        )

    if (
        annotation.scheme.version
        != SEMANTIC_ANNOTATION_SCHEME_VERSION
    ):
        raise ValueError(
            f"{annotation.id}: unexpected "
            "annotation scheme version"
        )

    raw_annotations = annotation.data.get(
        "annotations"
    )

    if not isinstance(
        raw_annotations,
        list,
    ):
        raise TypeError(
            f"{annotation.id}: annotations "
            "must be a list"
        )

    states: dict[str, str] = {}

    for item in raw_annotations:
        if not isinstance(
            item,
            dict,
        ):
            raise TypeError(
                f"{annotation.id}: annotation "
                "entry must be an object"
            )

        value = item.get(
            "value"
        )
        language = item.get(
            "language"
        )
        state = item.get(
            "state"
        )

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{annotation.id}: annotation "
                "value must be a string"
            )

        if language != "en":
            raise ValueError(
                f"{annotation.id}: unexpected "
                f"language for {value!r}"
            )

        if state not in {
            "present",
            "absent",
            "unknown",
        }:
            raise ValueError(
                f"{annotation.id}: unexpected "
                f"state for {value!r}: {state!r}"
            )

        if value in states:
            raise ValueError(
                f"{annotation.id}: duplicate "
                f"annotation value {value!r}"
            )

        states[value] = state

    return states


def json_round_trip(
    document: dict[str, Any],
) -> dict[str, Any]:
    """Round-trip a graph document through strict standard JSON."""

    with tempfile.TemporaryDirectory() as directory:
        path = (
            Path(directory)
            / "odornet_annotations.json"
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
    """Validate Molecule-to-Annotation mapping for complete OdorNet."""

    if not DATASET_PATH.exists():
        raise SystemExit(
            f"Dataset not found: {DATASET_PATH}"
        )

    print(
        f"Dataset: {DATASET_PATH}"
    )

    molecules: list[Molecule] = []
    annotations: list[Annotation] = []

    expected_smiles: dict[
        str,
        str,
    ] = {}

    expected_inchikeys: dict[
        str,
        str | None,
    ] = {}

    expected_states: dict[
        str,
        dict[str, str],
    ] = {}

    expected_subjects: dict[
        str,
        str,
    ] = {}

    source_state_counts: Counter[str] = (
        Counter()
    )

    pubchem_statuses: Counter[str] = (
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

            molecule_id = (
                f"odornet-molecule-"
                f"{dataset_index}"
            )

            annotation_id = (
                f"odornet-annotation-"
                f"{dataset_index}"
            )

            molecule = (
                molecule_from_odornet_record(
                    record,
                    resource_id=molecule_id,
                    row_number=row_number,
                )
            )

            annotation = (
                annotation_from_odornet_record(
                    record,
                    resource_id=annotation_id,
                    molecule_resource_id=(
                        molecule_id
                    ),
                    row_number=row_number,
                )
            )

            molecules.append(
                molecule
            )

            annotations.append(
                annotation
            )

            expected_smiles[
                molecule_id
            ] = molecule.smiles or ""

            expected_inchikeys[
                molecule_id
            ] = get_inchikey(
                molecule
            )

            states = annotation_states(
                annotation
            )

            if (
                set(states)
                != set(ODORNET_LABELS)
            ):
                raise AssertionError(
                    f"{annotation_id}: annotation "
                    "labels do not match OdorNet labels"
                )

            expected_states[
                annotation_id
            ] = states

            expected_subjects[
                annotation_id
            ] = molecule_id

            source_state_counts.update(
                states.values()
            )

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
                    "Molecule + Annotation pairs"
                )

    print()

    if len(molecules) != EXPECTED_ROW_COUNT:
        raise SystemExit(
            "Unexpected OdorNet row count: "
            f"{len(molecules):,}; "
            f"expected {EXPECTED_ROW_COUNT:,}"
        )

    if len(annotations) != EXPECTED_ROW_COUNT:
        raise SystemExit(
            "Unexpected Annotation count: "
            f"{len(annotations):,}; "
            f"expected {EXPECTED_ROW_COUNT:,}"
        )

    source_annotation_count = sum(
        source_state_counts.values()
    )

    if (
        source_annotation_count
        != EXPECTED_ANNOTATION_COUNT
    ):
        raise SystemExit(
            "Unexpected semantic annotation count: "
            f"{source_annotation_count:,}; "
            f"expected "
            f"{EXPECTED_ANNOTATION_COUNT:,}"
        )

    all_resources = [
        *molecules,
        *annotations,
    ]

    unique_resource_ids = {
        resource.id
        for resource in all_resources
    }

    if (
        len(unique_resource_ids)
        != len(all_resources)
    ):
        raise SystemExit(
            "Generated Resource IDs are not unique"
        )

    print(
        "Building GenericResourceGraph..."
    )

    graph = GenericResourceGraph(
        resources=all_resources
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
        != len(all_resources)
    ):
        raise SystemExit(
            "Resource count changed during "
            "round trip"
        )

    smiles_mismatches: list[str] = []
    inchikey_mismatches: list[str] = []
    subject_mismatches: list[str] = []
    state_mismatches: list[str] = []
    provenance_mismatches: list[str] = []
    unexpected_types: list[str] = []

    recovered_state_counts: Counter[str] = (
        Counter()
    )

    recovered_molecule_count = 0
    recovered_annotation_count = 0
    resolved_subject_count = 0

    for resource in reloaded_graph.resources:
        if isinstance(
            resource,
            Molecule,
        ):
            recovered_molecule_count += 1

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

            continue

        if isinstance(
            resource,
            Annotation,
        ):
            recovered_annotation_count += 1

            if not isinstance(
                resource.scheme,
                Scheme,
            ):
                unexpected_types.append(
                    (
                        f"{resource.id}: scheme is "
                        f"{type(resource.scheme).__name__}"
                    )
                )
                continue

            expected_subject = (
                expected_subjects[
                    resource.id
                ]
            )

            actual_subject = (
                resource.subject.resource_id
            )

            if (
                actual_subject
                != expected_subject
            ):
                subject_mismatches.append(
                    (
                        f"{resource.id}: "
                        f"expected subject "
                        f"{expected_subject!r}, "
                        f"actual "
                        f"{actual_subject!r}"
                    )
                )
            else:
                resolved = (
                    reloaded_graph.resolve(
                        resource.subject
                    )
                )

                if not isinstance(
                    resolved,
                    Molecule,
                ):
                    subject_mismatches.append(
                        (
                            f"{resource.id}: "
                            "subject did not resolve "
                            "to a Molecule"
                        )
                    )
                elif (
                    resolved.id
                    != expected_subject
                ):
                    subject_mismatches.append(
                        (
                            f"{resource.id}: "
                            "subject resolved to "
                            f"{resolved.id!r}; "
                            f"expected "
                            f"{expected_subject!r}"
                        )
                    )
                else:
                    resolved_subject_count += 1

            actual_states = annotation_states(
                resource
            )

            recovered_state_counts.update(
                actual_states.values()
            )

            expected_annotation_states = (
                expected_states[
                    resource.id
                ]
            )

            if (
                actual_states
                != expected_annotation_states
            ):
                state_mismatches.append(
                    (
                        f"{resource.id}: "
                        "semantic annotation states "
                        "changed"
                    )
                )

            provenance = resource.extra.get(
                "provenance"
            )

            if (
                provenance
                != ODORNET_PROVENANCE
            ):
                provenance_mismatches.append(
                    (
                        f"{resource.id}: "
                        f"expected provenance "
                        f"{ODORNET_PROVENANCE!r}, "
                        f"actual "
                        f"{provenance!r}"
                    )
                )

            continue

        unexpected_types.append(
            (
                f"{resource.id}: "
                f"{type(resource).__name__}"
            )
        )

    recovered_annotation_state_count = sum(
        recovered_state_counts.values()
    )

    print()
    print(
        "ODORNET ANNOTATION RESOURCE VALIDATION"
    )
    print(
        "--------------------------------------"
    )

    print(
        f"Dataset rows:               "
        f"{len(molecules):,}"
    )
    print(
        f"Molecule resources:         "
        f"{len(molecules):,}"
    )
    print(
        f"Annotation resources:       "
        f"{len(annotations):,}"
    )
    print(
        f"Total graph resources:      "
        f"{len(all_resources):,}"
    )
    print(
        f"Unique Resource IDs:        "
        f"{len(unique_resource_ids):,}"
    )
    print(
        f"Semantic annotation states: "
        f"{source_annotation_count:,}"
    )
    print(
        f"Recovered states:           "
        f"{recovered_annotation_state_count:,}"
    )
    print(
        f"Resolved subjects:          "
        f"{resolved_subject_count:,}"
    )
    print(
        f"Recovered Molecules:        "
        f"{recovered_molecule_count:,}"
    )
    print(
        f"Recovered Annotations:      "
        f"{recovered_annotation_count:,}"
    )
    print(
        f"SMILES mismatches:          "
        f"{len(smiles_mismatches):,}"
    )
    print(
        f"InChIKey mismatches:        "
        f"{len(inchikey_mismatches):,}"
    )
    print(
        f"Subject mismatches:         "
        f"{len(subject_mismatches):,}"
    )
    print(
        f"State mismatches:           "
        f"{len(state_mismatches):,}"
    )
    print(
        f"Provenance mismatches:      "
        f"{len(provenance_mismatches):,}"
    )
    print(
        f"Unexpected resource types:  "
        f"{len(unexpected_types):,}"
    )

    print()
    print(
        "Source semantic states:"
    )

    for state in (
        "present",
        "absent",
        "unknown",
    ):
        print(
            f"  {state}: "
            f"{source_state_counts[state]:,}"
        )

    print()
    print(
        "Recovered semantic states:"
    )

    for state in (
        "present",
        "absent",
        "unknown",
    ):
        print(
            f"  {state}: "
            f"{recovered_state_counts[state]:,}"
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

    failures = (
        smiles_mismatches
        or inchikey_mismatches
        or subject_mismatches
        or state_mismatches
        or provenance_mismatches
        or unexpected_types
        or (
            recovered_molecule_count
            != EXPECTED_ROW_COUNT
        )
        or (
            recovered_annotation_count
            != EXPECTED_ROW_COUNT
        )
        or (
            resolved_subject_count
            != EXPECTED_ROW_COUNT
        )
        or (
            recovered_annotation_state_count
            != EXPECTED_ANNOTATION_COUNT
        )
        or (
            recovered_state_counts
            != source_state_counts
        )
    )

    if failures:
        print()

        categories = [
            (
                "SMILES mismatches",
                smiles_mismatches,
            ),
            (
                "InChIKey mismatches",
                inchikey_mismatches,
            ),
            (
                "Subject mismatches",
                subject_mismatches,
            ),
            (
                "State mismatches",
                state_mismatches,
            ),
            (
                "Provenance mismatches",
                provenance_mismatches,
            ),
            (
                "Unexpected resource types",
                unexpected_types,
            ),
        ]

        for title, mismatches in categories:
            if not mismatches:
                continue

            print(
                f"First {title.lower()}:"
            )

            for mismatch in mismatches[:20]:
                print(
                    f"  {mismatch}"
                )

            print()

        raise SystemExit(1)

    print()
    print(
        "SUCCESS: all OdorNet Molecule and "
        "Annotation resources survived the "
        "RFC-0008 Generic ResourceGraph round trip "
        "with exact semantic states and subject "
        "relationships preserved."
    )


if __name__ == "__main__":
    main()