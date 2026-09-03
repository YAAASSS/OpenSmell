"""Validate lossless OdorNet semantic annotation round trips."""

import csv
import tempfile
from pathlib import Path
from typing import Any

from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    ODORNET_LABELS,
    from_record_with_annotations,
)
from opensmell.parser import load
from opensmell.serializer import dump


DATASET_PATH = Path("examples/odornet_enriched.csv")

EXPECTED_ODORNET_LABELS = (
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


def normalize_odornet_value(value: Any) -> str:
    """Map an OdorNet CSV value to an RFC-0004 annotation state."""

    if value is None:
        return "unknown"

    normalized = str(value).strip()

    if normalized in {"1", "1.0"}:
        return "present"

    if normalized in {"0", "0.0"}:
        return "absent"

    if normalized == "":
        return "unknown"

    raise ValueError(
        f"Unexpected OdorNet annotation value: {value!r}"
    )


def adapter_value(value: Any) -> int | None:
    """Convert an OdorNet CSV value into an adapter value."""

    state = normalize_odornet_value(value)

    if state == "present":
        return 1

    if state == "absent":
        return 0

    return None


def csv_record_for_adapter(
    record: dict[str, str],
) -> dict[str, Any]:
    """Convert a CSV row into values expected by the OdorNet adapter."""

    converted: dict[str, Any] = dict(record)

    for label in ODORNET_LABELS:
        converted[label] = adapter_value(
            record.get(label)
        )

    return converted


def get_annotations(
    odor: Any,
) -> dict[str, str]:
    """Extract RFC-0004 annotation states from an OpenSmell odor."""

    for representation in odor.representations:
        if (
            representation.scheme.id
            == ANNOTATION_SCHEME_ID
        ):
            annotations = representation.data.get(
                "annotations"
            )

            if not isinstance(annotations, list):
                raise ValueError(
                    "RFC-0004 annotations must be a list"
                )

            result: dict[str, str] = {}

            for annotation in annotations:
                value = annotation.get("value")
                state = annotation.get("state")

                if not isinstance(value, str):
                    raise ValueError(
                        "Annotation value must be a string"
                    )

                if not isinstance(state, str):
                    raise ValueError(
                        "Annotation state must be a string"
                    )

                if value in result:
                    raise ValueError(
                        f"Duplicate annotation: {value!r}"
                    )

                result[value] = state

            return result

    raise ValueError(
        "RFC-0004 semantic annotation representation not found"
    )


def validate_dataset_header(
    fieldnames: list[str] | None,
) -> None:
    """Validate the OdorNet CSV header."""

    if fieldnames is None:
        raise SystemExit(
            "Dataset does not contain a CSV header"
        )

    if "SMILES" not in fieldnames:
        raise SystemExit(
            "Dataset is missing the SMILES column"
        )

    missing_columns = [
        label
        for label in EXPECTED_ODORNET_LABELS
        if label not in fieldnames
    ]

    if missing_columns:
        raise SystemExit(
            "Dataset is missing OdorNet columns: "
            + ", ".join(missing_columns)
        )

    unexpected_adapter_labels = (
        set(ODORNET_LABELS)
        - set(EXPECTED_ODORNET_LABELS)
    )

    missing_adapter_labels = (
        set(EXPECTED_ODORNET_LABELS)
        - set(ODORNET_LABELS)
    )

    if (
        unexpected_adapter_labels
        or missing_adapter_labels
    ):
        raise SystemExit(
            "Adapter ODORNET_LABELS does not match "
            "the real OdorNet dataset.\n"
            f"Unexpected: "
            f"{sorted(unexpected_adapter_labels)}\n"
            f"Missing: "
            f"{sorted(missing_adapter_labels)}"
        )


def main() -> None:
    """Validate every OdorNet annotation through OpenSmell."""

    if not DATASET_PATH.exists():
        raise SystemExit(
            f"Dataset not found: {DATASET_PATH}"
        )

    molecules = 0
    annotations_checked = 0
    mismatches: list[str] = []

    print(
        f"Dataset: {DATASET_PATH}"
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

        with tempfile.TemporaryDirectory() as temp_directory:
            temp_path = Path(
                temp_directory
            )

            output_path = (
                temp_path
                / "roundtrip.osmell"
            )

            for row_number, csv_record in enumerate(
                reader,
                start=2,
            ):
                record = csv_record_for_adapter(
                    csv_record
                )

                odor = from_record_with_annotations(
                    record,
                    odor_id=f"odornet-{row_number - 1}",
                )

                # Serialize through the real OpenSmell serializer.
                dump(
                    odor,
                    output_path,
                )

                # Reload through the real OpenSmell parser.
                reloaded = load(
                    output_path
                )

                annotations = get_annotations(
                    reloaded
                )

                if len(annotations) != len(
                    ODORNET_LABELS
                ):
                    mismatches.append(
                        (
                            f"row={row_number} "
                            "unexpected annotation count "
                            f"{len(annotations)}"
                        )
                    )

                for label in ODORNET_LABELS:
                    expected = normalize_odornet_value(
                        csv_record.get(label)
                    )

                    actual = annotations.get(
                        label
                    )

                    annotations_checked += 1

                    if actual != expected:
                        mismatches.append(
                            (
                                f"row={row_number} "
                                f"label={label!r} "
                                f"expected={expected!r} "
                                f"actual={actual!r}"
                            )
                        )

                molecules += 1

                if molecules % 1000 == 0:
                    print(
                        f"Checked {molecules:,} molecules "
                        f"({annotations_checked:,} annotations)"
                    )

    expected_annotations = (
        molecules
        * len(ODORNET_LABELS)
    )

    print()
    print("ROUND-TRIP VALIDATION")
    print("---------------------")
    print(
        f"Molecules:   {molecules:,}"
    )
    print(
        f"Annotations: {annotations_checked:,}"
    )
    print(
        f"Expected:    {expected_annotations:,}"
    )
    print(
        f"Mismatches:  {len(mismatches):,}"
    )

    if annotations_checked != expected_annotations:
        raise SystemExit(
            "Unexpected annotation count: "
            f"{annotations_checked:,} instead of "
            f"{expected_annotations:,}"
        )

    if mismatches:
        print()
        print("First mismatches:")

        for mismatch in mismatches[:20]:
            print(
                f"  {mismatch}"
            )

        raise SystemExit(1)

    print()
    print(
        "SUCCESS: all semantic annotation states "
        "survived the OpenSmell round trip."
    )


if __name__ == "__main__":
    main()