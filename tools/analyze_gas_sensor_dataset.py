"""Analyze the UCI Gas Sensor Array Drift at Different Concentrations dataset.

This script intentionally analyzes the source dataset before mapping it to
experimental OpenSmell resources.

Dataset:
    Gas Sensor Array Drift at Different Concentrations
    UCI Machine Learning Repository
    DOI: 10.24432/C5MK6M

The source dataset contains:

- 10 batches;
- 13,910 measurements;
- 6 analytes;
- concentration in ppmv;
- 16 chemical sensors;
- 8 extracted features per sensor;
- 128 feature values per measurement.

No OpenSmell resource-model decisions are made by this script.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_ROOT = (
    PROJECT_ROOT
    / "examples"
    / "gas_sensor_drift"
)


ANALYTES = {
    1: "ethanol",
    2: "ethylene",
    3: "ammonia",
    4: "acetaldehyde",
    5: "acetone",
    6: "toluene",
}


FEATURES_PER_SENSOR = (
    "delta_r",
    "normalized_delta_r",
    "ema_rise_0.001",
    "ema_rise_0.01",
    "ema_rise_0.1",
    "ema_decay_0.001",
    "ema_decay_0.01",
    "ema_decay_0.1",
)


SENSOR_COUNT = 16
FEATURE_COUNT = 128


@dataclass(frozen=True)
class SourceMeasurement:
    batch: int
    row: int
    analyte_class: int
    concentration_ppmv: float
    features: tuple[float, ...]


def feature_identity(
    feature_number: int,
) -> tuple[int, str]:
    """Map source feature number 1..128 to sensor and feature identity."""

    if not 1 <= feature_number <= FEATURE_COUNT:
        raise ValueError(
            f"Invalid feature number: {feature_number}"
        )

    zero_based = feature_number - 1

    sensor_number = (
        zero_based
        // len(FEATURES_PER_SENSOR)
        + 1
    )

    feature_name = FEATURES_PER_SENSOR[
        zero_based
        % len(FEATURES_PER_SENSOR)
    ]

    return (
        sensor_number,
        feature_name,
    )


def parse_line(
    line: str,
    *,
    batch: int,
    row: int,
) -> SourceMeasurement:
    line = line.strip()

    if not line:
        raise ValueError(
            f"Empty line in batch {batch}, row {row}."
        )

    tokens = line.split()

    if len(tokens) != FEATURE_COUNT + 1:
        raise ValueError(
            f"Batch {batch}, row {row}: "
            f"expected {FEATURE_COUNT + 1} tokens, "
            f"found {len(tokens)}."
        )

    header = tokens[0]

    if ";" not in header:
        raise ValueError(
            f"Batch {batch}, row {row}: "
            f"invalid class/concentration token {header!r}."
        )

    class_text, concentration_text = header.split(
        ";",
        maxsplit=1,
    )

    analyte_class = int(
        class_text
    )

    if analyte_class not in ANALYTES:
        raise ValueError(
            f"Batch {batch}, row {row}: "
            f"unknown analyte class {analyte_class}."
        )

    concentration_ppmv = float(
        concentration_text
    )

    features: list[float] = []

    for expected_feature_number, token in enumerate(
        tokens[1:],
        start=1,
    ):
        if ":" not in token:
            raise ValueError(
                f"Batch {batch}, row {row}: "
                f"invalid feature token {token!r}."
            )

        feature_number_text, value_text = token.split(
            ":",
            maxsplit=1,
        )

        feature_number = int(
            feature_number_text
        )

        if (
            feature_number
            != expected_feature_number
        ):
            raise ValueError(
                f"Batch {batch}, row {row}: "
                f"expected feature {expected_feature_number}, "
                f"found {feature_number}."
            )

        features.append(
            float(value_text)
        )

    return SourceMeasurement(
        batch=batch,
        row=row,
        analyte_class=analyte_class,
        concentration_ppmv=concentration_ppmv,
        features=tuple(features),
    )


def load_batch(
    batch_number: int,
) -> list[SourceMeasurement]:
    path = (
        DATASET_ROOT
        / f"batch{batch_number}.dat"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Missing dataset file: {path}"
        )

    measurements: list[
        SourceMeasurement
    ] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for row_number, line in enumerate(
            handle,
            start=1,
        ):
            if not line.strip():
                continue

            measurements.append(
                parse_line(
                    line,
                    batch=batch_number,
                    row=row_number,
                )
            )

    return measurements


def main() -> None:
    print(
        "OpenSmell source analysis"
    )
    print(
        "UCI Gas Sensor Array Drift at Different Concentrations"
    )
    print("=" * 76)

    all_measurements: list[
        SourceMeasurement
    ] = []

    batch_counts: dict[
        int,
        int,
    ] = {}

    for batch_number in range(
        1,
        11,
    ):
        measurements = load_batch(
            batch_number
        )

        batch_counts[
            batch_number
        ] = len(
            measurements
        )

        all_measurements.extend(
            measurements
        )

    print()
    print("Batch counts")
    print("-" * 76)

    for batch_number in range(
        1,
        11,
    ):
        print(
            f"Batch {batch_number:>2}: "
            f"{batch_counts[batch_number]:>6,}"
        )

    total = len(
        all_measurements
    )

    print("-" * 76)
    print(
        f"Total   : {total:>6,}"
    )

    if total != 13_910:
        raise AssertionError(
            f"Expected 13,910 measurements, found {total:,}."
        )

    analyte_counts = Counter(
        measurement.analyte_class
        for measurement in all_measurements
    )

    print()
    print("Analytes")
    print("-" * 76)

    for analyte_class in sorted(
        ANALYTES
    ):
        print(
            f"{analyte_class}: "
            f"{ANALYTES[analyte_class]:<16} "
            f"{analyte_counts[analyte_class]:>6,}"
        )

    concentration_values = [
        measurement.concentration_ppmv
        for measurement in all_measurements
    ]

    unique_concentrations = sorted(
        set(
            concentration_values
        )
    )

    print()
    print("Concentration")
    print("-" * 76)
    print(
        f"Minimum ppmv               : "
        f"{min(concentration_values)}"
    )
    print(
        f"Maximum ppmv               : "
        f"{max(concentration_values)}"
    )
    print(
        f"Unique concentration values: "
        f"{len(unique_concentrations):,}"
    )

    analyte_concentrations: dict[
        int,
        set[float],
    ] = {
        analyte_class: set()
        for analyte_class in ANALYTES
    }

    for measurement in all_measurements:
        analyte_concentrations[
            measurement.analyte_class
        ].add(
            measurement.concentration_ppmv
        )

    print()
    print("Concentrations by analyte")
    print("-" * 76)

    for analyte_class in sorted(
        ANALYTES
    ):
        values = sorted(
            analyte_concentrations[
                analyte_class
            ]
        )

        print(
            f"{ANALYTES[analyte_class]:<16}: "
            f"{len(values):>4} unique, "
            f"min={min(values)}, "
            f"max={max(values)}"
        )

    print()
    print("Feature structure")
    print("-" * 76)
    print(
        f"Sensors                     : {SENSOR_COUNT}"
    )
    print(
        f"Features per sensor         : {len(FEATURES_PER_SENSOR)}"
    )
    print(
        f"Features per measurement    : {FEATURE_COUNT}"
    )

    print()
    print("Feature mapping")
    print("-" * 76)

    for sensor_number in range(
        1,
        SENSOR_COUNT + 1,
    ):
        first_feature = (
            (sensor_number - 1)
            * len(FEATURES_PER_SENSOR)
            + 1
        )

        last_feature = (
            first_feature
            + len(FEATURES_PER_SENSOR)
            - 1
        )

        print(
            f"Sensor {sensor_number:>2}: "
            f"features {first_feature:>3}-{last_feature:>3}"
        )

    feature_min = [
        float("inf")
        for _ in range(
            FEATURE_COUNT
        )
    ]

    feature_max = [
        float("-inf")
        for _ in range(
            FEATURE_COUNT
        )
    ]

    zero_values = 0
    negative_values = 0
    positive_values = 0

    for measurement in all_measurements:
        if (
            len(measurement.features)
            != FEATURE_COUNT
        ):
            raise AssertionError(
                "Unexpected feature vector length."
            )

        for index, value in enumerate(
            measurement.features
        ):
            if value < feature_min[
                index
            ]:
                feature_min[
                    index
                ] = value

            if value > feature_max[
                index
            ]:
                feature_max[
                    index
                ] = value

            if value == 0:
                zero_values += 1
            elif value < 0:
                negative_values += 1
            else:
                positive_values += 1

    total_feature_values = (
        total
        * FEATURE_COUNT
    )

    print()
    print("Feature values")
    print("-" * 76)
    print(
        f"Total feature values        : "
        f"{total_feature_values:,}"
    )
    print(
        f"Negative values             : "
        f"{negative_values:,}"
    )
    print(
        f"Zero values                 : "
        f"{zero_values:,}"
    )
    print(
        f"Positive values             : "
        f"{positive_values:,}"
    )

    if (
        negative_values
        + zero_values
        + positive_values
        != total_feature_values
    ):
        raise AssertionError(
            "Feature value accounting mismatch."
        )

    print()
    print("Example feature identities")
    print("-" * 76)

    for feature_number in (
        1,
        2,
        8,
        9,
        16,
        121,
        128,
    ):
        sensor_number, feature_name = (
            feature_identity(
                feature_number
            )
        )

        print(
            f"Feature {feature_number:>3}: "
            f"sensor={sensor_number:>2}, "
            f"property={feature_name}"
        )

    example = all_measurements[
        0
    ]

    print()
    print("First source measurement")
    print("-" * 76)
    print(
        f"Batch                       : {example.batch}"
    )
    print(
        f"Source row                  : {example.row}"
    )
    print(
        f"Analyte class               : {example.analyte_class}"
    )
    print(
        f"Analyte                     : "
        f"{ANALYTES[example.analyte_class]}"
    )
    print(
        f"Concentration ppmv          : "
        f"{example.concentration_ppmv}"
    )
    print(
        f"Feature values              : "
        f"{len(example.features)}"
    )

    print()
    print("First 8 features")
    print("-" * 76)

    for feature_number in range(
        1,
        9,
    ):
        sensor_number, feature_name = (
            feature_identity(
                feature_number
            )
        )

        value = example.features[
            feature_number - 1
        ]

        print(
            f"{feature_number:>3}: "
            f"sensor={sensor_number:>2} "
            f"{feature_name:<24} "
            f"{value}"
        )

    print()
    print("Result")
    print("=" * 76)
    print("SUCCESS")
    print(
        "All 13,910 source measurements were parsed with "
        "128 ordered sensor features each."
    )
    print(
        "No OpenSmell resource-model assumptions were required."
    )


if __name__ == "__main__":
    main()