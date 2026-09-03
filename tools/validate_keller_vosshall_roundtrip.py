"""Validate Keller/Vosshall perceptual measurement round trips."""

from pathlib import Path
import tempfile
from typing import Any

import pandas as pd

from opensmell.adapters.keller_vosshall import (
    DESCRIPTOR_COLUMNS,
    GLOBAL_RATINGS,
    SCHEME_ID,
    measurements_from_record,
    representation_from_record,
)
from opensmell.builders import odor
from opensmell.parser import load
from opensmell.serializer import dump


DATASET_PATH = Path("examples/keller_vosshall.xlsx")


def is_missing(value: Any) -> bool:
    """Return True when a source value is missing."""

    return bool(pd.isna(value))


def normalize_numeric(value: Any) -> int | float:
    """Normalize a source numeric value for comparison."""

    numeric = float(value)

    if numeric.is_integer():
        return int(numeric)

    return numeric


def expected_measurements(
    record: dict[str, Any],
) -> dict[str, int | float]:
    """Extract explicitly stored measurements from the source row."""

    expected: dict[str, int | float] = {}

    for source_field, property_name in GLOBAL_RATINGS.items():
        value = record.get(source_field)

        if not is_missing(value):
            expected[property_name] = normalize_numeric(value)

    for source_field in DESCRIPTOR_COLUMNS:
        value = record.get(source_field)

        if not is_missing(value):
            expected[source_field.lower()] = normalize_numeric(value)

    return expected


def recovered_measurements(
    loaded_odor: Any,
) -> dict[str, dict[str, Any]]:
    """Extract perceptual measurements from a parsed OpenSmell odor."""

    for representation in loaded_odor.representations:
        if representation.scheme.id != SCHEME_ID:
            continue

        measurements = representation.data.get("measurements")

        if not isinstance(measurements, list):
            raise ValueError("measurements must be a list")

        result: dict[str, dict[str, Any]] = {}

        for measurement in measurements:
            property_name = measurement.get("property")

            if not isinstance(property_name, str):
                raise ValueError(
                    "measurement property must be a string"
                )

            if property_name in result:
                raise ValueError(
                    f"duplicate measurement property: {property_name!r}"
                )

            result[property_name] = measurement

        return result

    raise ValueError(
        "perceptual measurement representation not found"
    )


def validate_source_against_adapter(
    record: dict[str, Any],
) -> None:
    """Ensure adapter extraction already matches explicit source values."""

    expected = expected_measurements(record)

    extracted = {
        measurement["property"]: measurement["value"]
        for measurement in measurements_from_record(record)
    }

    if extracted != expected:
        raise ValueError(
            "adapter extraction differs from source values"
        )


def main() -> None:
    if not DATASET_PATH.exists():
        raise SystemExit(f"Dataset not found: {DATASET_PATH}")

    dataframe = pd.read_excel(
        DATASET_PATH,
        sheet_name="data",
        header=2,
    )

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    observations = 0
    observations_with_measurements = 0
    observations_without_measurements = 0
    measurements_checked = 0
    mismatches: list[str] = []

    print(f"Dataset: {DATASET_PATH}")
    print(f"Observations: {len(dataframe):,}")
    print()

    with tempfile.TemporaryDirectory() as temporary_directory:
        output_path = (
            Path(temporary_directory) / "roundtrip.osmell"
        )

        for dataframe_index, row in dataframe.iterrows():
            row_number = dataframe_index + 4
            record = row.to_dict()

            observations += 1

            try:
                validate_source_against_adapter(record)

                expected = expected_measurements(record)

                representation = representation_from_record(record)

                if not expected:
                    observations_without_measurements += 1

                    if representation is not None:
                        mismatches.append(
                            f"row={row_number} expected no representation"
                        )

                    continue

                observations_with_measurements += 1

                if representation is None:
                    mismatches.append(
                        f"row={row_number} representation missing"
                    )
                    continue

                source_odor = odor(
                    representations=[representation],
                    odor_id=f"keller-vosshall-{observations}",
                )

                dump(source_odor, output_path)

                loaded_odor = load(output_path)

                recovered = recovered_measurements(loaded_odor)

                if set(recovered) != set(expected):
                    missing = sorted(
                        set(expected) - set(recovered)
                    )
                    unexpected = sorted(
                        set(recovered) - set(expected)
                    )

                    mismatches.append(
                        f"row={row_number} "
                        f"property mismatch "
                        f"missing={missing} "
                        f"unexpected={unexpected}"
                    )

                for property_name, expected_value in expected.items():
                    measurement = recovered.get(property_name)

                    measurements_checked += 1

                    if measurement is None:
                        continue

                    actual_value = measurement.get("value")

                    if actual_value != expected_value:
                        mismatches.append(
                            f"row={row_number} "
                            f"property={property_name!r} "
                            f"expected={expected_value!r} "
                            f"actual={actual_value!r}"
                        )

                    scale = measurement.get("scale")

                    if scale != {"min": 0, "max": 100}:
                        mismatches.append(
                            f"row={row_number} "
                            f"property={property_name!r} "
                            f"unexpected scale={scale!r}"
                        )

            except Exception as error:
                mismatches.append(
                    f"row={row_number} error={error}"
                )

            if observations % 5000 == 0:
                print(
                    f"Checked {observations:,} observations "
                    f"({measurements_checked:,} measurements)"
                )

    expected_measurements_total = 0

    for _, row in dataframe.iterrows():
        expected_measurements_total += len(
            expected_measurements(row.to_dict())
        )

    print()
    print("ROUND-TRIP VALIDATION")
    print("---------------------")
    print(f"Observations:              {observations:,}")
    print(
        "With measurements:         "
        f"{observations_with_measurements:,}"
    )
    print(
        "Without measurements:      "
        f"{observations_without_measurements:,}"
    )
    print(
        "Measurements checked:       "
        f"{measurements_checked:,}"
    )
    print(
        "Expected measurements:      "
        f"{expected_measurements_total:,}"
    )
    print(f"Mismatches:                {len(mismatches):,}")

    if measurements_checked != expected_measurements_total:
        raise SystemExit(
            "Unexpected measurement count: "
            f"{measurements_checked:,} instead of "
            f"{expected_measurements_total:,}"
        )

    if mismatches:
        print()
        print("First mismatches:")

        for mismatch in mismatches[:20]:
            print(f"  {mismatch}")

        raise SystemExit(1)

    print()
    print(
        "SUCCESS: all explicit Keller/Vosshall perceptual "
        "measurements survived the OpenSmell round trip."
    )


if __name__ == "__main__":
    main()