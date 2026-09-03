"""Build an experimental OpenSmell resource graph from the UCI gas sensor dataset.

Dataset:
    Gas Sensor Array Drift at Different Concentrations
    UCI Machine Learning Repository
    DOI: 10.24432/C5MK6M

Purpose:
    Stress-test the experimental RFC-0007 resource architecture on
    electronic olfaction.

Source semantics and OpenSmell-generated abstractions are deliberately kept
separate.

Source data provides:
    - analyte class;
    - analyte concentration in ppmv;
    - batch membership;
    - source row ordering;
    - 128 sensor-response features.

This experiment generates:
    - deterministic identities for the six analytes;
    - Stimulus resources for unique analyte/concentration pairs;
    - one ObservationTarget representing the complete 16-sensor array;
    - one Observation per source row;
    - one versioned scheme-defined sensor-array Result per Observation.

The generated sensor-array target is an OpenSmell modeling abstraction. It is
not presented as a source-native UCI identifier.

The analyte identities are deterministic reference targets used by this
experiment. This script does not yet define or materialize a normative
OpenSmell Chemical resource type.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from opensmell.experimental.identifiers import (
    deterministic_resource_id_from_source,
)
from opensmell.experimental.resources import (
    Condition,
    Observation,
    ObservationTarget,
    Reference,
    Result,
    ResultScheme,
    Stimulus,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_ROOT = (
    PROJECT_ROOT
    / "examples"
    / "gas_sensor_drift"
)

DATASET_ID = "uci_gas_sensor_drift"

SENSOR_RESULT_SCHEME_ID = (
    "org.opensmell.experimental.sensor-array.features"
)
SENSOR_RESULT_SCHEME_VERSION = "0.1" 

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


def resource_id(
    resource_type: str,
    source_identity: str | dict[str, str],
) -> str:
    return deterministic_resource_id_from_source(
        dataset=DATASET_ID,
        resource_type=resource_type,
        source_identity=source_identity,
    )


def parse_line(
    line: str,
    *,
    batch: int,
    row: int,
) -> SourceMeasurement:
    tokens = line.strip().split()

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

    analyte_class = int(class_text)

    if analyte_class not in ANALYTES:
        raise ValueError(
            f"Batch {batch}, row {row}: "
            f"unknown analyte class {analyte_class}."
        )

    concentration_ppmv = float(
        concentration_text
    )

    features: list[float] = []

    for expected_number, token in enumerate(
        tokens[1:],
        start=1,
    ):
        if ":" not in token:
            raise ValueError(
                f"Batch {batch}, row {row}: "
                f"invalid feature token {token!r}."
            )

        number_text, value_text = token.split(
            ":",
            maxsplit=1,
        )

        number = int(number_text)

        if number != expected_number:
            raise ValueError(
                f"Batch {batch}, row {row}: "
                f"expected feature {expected_number}, "
                f"found {number}."
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


def load_measurements() -> list[SourceMeasurement]:
    measurements: list[SourceMeasurement] = []

    for batch in range(1, 11):
        path = (
            DATASET_ROOT
            / f"batch{batch}.dat"
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Missing dataset file: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for row, line in enumerate(
                handle,
                start=1,
            ):
                if not line.strip():
                    continue

                measurements.append(
                    parse_line(
                        line,
                        batch=batch,
                        row=row,
                    )
                )

    return measurements


def build_analyte_identities() -> dict[int, str]:
    """Generate reference identities for the six source analytes.

    These UUIDs are OpenSmell-generated identities used by this experiment.

    They are not UCI identifiers and this function does not materialize a
    normative OpenSmell Chemical resource.
    """

    return {
        analyte_class: resource_id(
            "chemical",
            analyte_name,
        )
        for analyte_class, analyte_name in ANALYTES.items()
    }


def concentration_identity(
    concentration: float,
) -> str:
    """Return the concentration identity representation used by this adapter."""

    return str(concentration)


def build_stimuli(
    measurements: list[SourceMeasurement],
    analyte_ids: dict[int, str],
) -> dict[tuple[int, float], Stimulus]:
    stimuli: dict[
        tuple[int, float],
        Stimulus,
    ] = {}

    for measurement in measurements:
        key = (
            measurement.analyte_class,
            measurement.concentration_ppmv,
        )

        if key in stimuli:
            continue

        analyte_name = ANALYTES[
            measurement.analyte_class
        ]

        concentration = concentration_identity(
            measurement.concentration_ppmv
        )

        stimulus_id = resource_id(
            "stimulus",
            {
                "analyte": analyte_name,
                "concentration_ppmv": concentration,
            },
        )

        stimuli[key] = Stimulus(
            id=stimulus_id,
            source=Reference(
                resource_id=analyte_ids[
                    measurement.analyte_class
                ]
            ),
            conditions=[
                Condition(
                    property="concentration",
                    value=measurement.concentration_ppmv,
                    unit="ppmv",
                )
            ],
        )

    return stimuli


def build_sensor_array_target() -> ObservationTarget:
    """Create the generated composite sensor-array target.

    The UCI source describes measurements from a 16-sensor array, but
    "sensor_array_16" is not treated as a source-native external identifier.

    The target identity below is generated solely for this OpenSmell
    experiment.
    """

    return ObservationTarget(
        id=resource_id(
            "target",
            "sensor_array_16",
        ),
        extra={
            "kind": "electronic_sensor_array",
            "sensor_count": SENSOR_COUNT,
        },
    )


def build_sensor_result(
    measurement: SourceMeasurement,
) -> Result:
    sensors: list[
        dict[str, object]
    ] = []

    for sensor_index in range(
        SENSOR_COUNT
    ):
        start = (
            sensor_index
            * len(FEATURES_PER_SENSOR)
        )

        values = measurement.features[
            start:
            start + len(FEATURES_PER_SENSOR)
        ]

        if len(values) != len(
            FEATURES_PER_SENSOR
        ):
            raise AssertionError(
                "Incomplete sensor feature group."
            )

        features = {
            property_name: value
            for property_name, value in zip(
                FEATURES_PER_SENSOR,
                values,
                strict=True,
            )
        }

        sensors.append(
            {
                "sensor": sensor_index + 1,
                "features": features,
            }
        )

    return Result(
        scheme=ResultScheme(
            id=SENSOR_RESULT_SCHEME_ID,
            version=SENSOR_RESULT_SCHEME_VERSION,
        ),
        data={
            "sensors": sensors,
        },
    )


def build_observations(
    measurements: list[SourceMeasurement],
    stimuli: dict[
        tuple[int, float],
        Stimulus,
    ],
    target: ObservationTarget,
) -> list[Observation]:
    observations: list[
        Observation
    ] = []

    for measurement in measurements:
        stimulus = stimuli[
            (
                measurement.analyte_class,
                measurement.concentration_ppmv,
            )
        ]

        observation_id = resource_id(
            "observation",
            {
                "batch": str(
                    measurement.batch
                ),
                "row": str(
                    measurement.row
                ),
            },
        )

        observations.append(
            Observation(
                id=observation_id,
                stimulus=Reference(
                    resource_id=stimulus.id
                ),
                target=Reference(
                    resource_id=target.id
                ),
                results=[
                    build_sensor_result(
                        measurement
                    )
                ],
                context={
                    "batch": measurement.batch,
                    "source_row": measurement.row,
                },
            )
        )

    return observations


def extract_feature_values(
    result: Result,
) -> list[float]:
    if result.scheme.id != SENSOR_RESULT_SCHEME_ID:
        raise AssertionError(
            "Unexpected Result scheme ID: "
            f"{result.scheme.id!r}"
        )

    if result.scheme.version != SENSOR_RESULT_SCHEME_VERSION:
        raise AssertionError(
            "Unexpected Result scheme version: "
            f"{result.scheme.version!r}"
        )

    sensors = result.data.get(
        "sensors"
    )

    if not isinstance(
        sensors,
        list,
    ):
        raise AssertionError(
            "Sensor Result has no sensors list."
        )

    if len(sensors) != SENSOR_COUNT:
        raise AssertionError(
            f"Expected {SENSOR_COUNT} sensor channels, "
            f"found {len(sensors)}."
        )

    values: list[float] = []

    for expected_sensor, sensor in enumerate(
        sensors,
        start=1,
    ):
        if not isinstance(
            sensor,
            dict,
        ):
            raise AssertionError(
                "Sensor entry must be an object."
            )

        if (
            sensor.get("sensor")
            != expected_sensor
        ):
            raise AssertionError(
                "Sensor ordering or identity changed."
            )

        features = sensor.get(
            "features"
        )

        if not isinstance(
            features,
            dict,
        ):
            raise AssertionError(
                "Sensor features must be an object."
            )

        if (
            tuple(features.keys())
            != FEATURES_PER_SENSOR
        ):
            raise AssertionError(
                "Sensor feature ordering or identity changed."
            )

        for property_name in FEATURES_PER_SENSOR:
            value = features[
                property_name
            ]

            if (
                isinstance(value, bool)
                or not isinstance(
                    value,
                    (int, float),
                )
            ):
                raise AssertionError(
                    "Sensor feature is not numeric."
                )

            values.append(
                float(value)
            )

    if len(values) != FEATURE_COUNT:
        raise AssertionError(
            "Feature reconstruction failed."
        )

    return values


def validate_graph(
    *,
    measurements: list[SourceMeasurement],
    analyte_ids: dict[int, str],
    stimuli: dict[
        tuple[int, float],
        Stimulus,
    ],
    target: ObservationTarget,
    observations: list[Observation],
) -> None:
    if len(measurements) != 13_910:
        raise AssertionError(
            "Source measurement count changed."
        )

    if len(analyte_ids) != 6:
        raise AssertionError(
            "Expected six generated analyte identities."
        )

    if len(stimuli) != 233:
        raise AssertionError(
            f"Expected 233 unique analyte/concentration "
            f"Stimuli, found {len(stimuli)}."
        )

    if len(observations) != len(
        measurements
    ):
        raise AssertionError(
            "Observation count changed."
        )

    if target.identifiers:
        raise AssertionError(
            "Generated sensor-array target must not "
            "claim a source-native external identifier."
        )

    all_resource_ids = [
        *analyte_ids.values(),
        *(
            stimulus.id
            for stimulus in stimuli.values()
        ),
        target.id,
        *(
            observation.id
            for observation in observations
        ),
    ]

    duplicate_ids = [
        resource_id_value
        for resource_id_value, count in Counter(
            all_resource_ids
        ).items()
        if count > 1
    ]

    if duplicate_ids:
        raise AssertionError(
            "Resource ID collisions: "
            f"{duplicate_ids[:10]}"
        )

    analyte_id_values = set(
        analyte_ids.values()
    )

    stimulus_ids = {
        stimulus.id
        for stimulus in stimuli.values()
    }

    for stimulus in stimuli.values():
        if stimulus.source is None:
            raise AssertionError(
                "Gas sensor Stimulus has no analyte reference."
            )

        if (
            stimulus.source.resource_id
            not in analyte_id_values
        ):
            raise AssertionError(
                "Stimulus has unresolved generated analyte reference."
            )

        if len(
            stimulus.conditions
        ) != 1:
            raise AssertionError(
                "Expected one concentration Condition per Stimulus."
            )

        condition = stimulus.conditions[
            0
        ]

        if (
            condition.property
            != "concentration"
        ):
            raise AssertionError(
                "Unexpected Stimulus condition property."
            )

        if condition.unit != "ppmv":
            raise AssertionError(
                "Unexpected concentration unit."
            )

    for source, observation in zip(
        measurements,
        observations,
        strict=True,
    ):
        if (
            observation.stimulus.resource_id
            not in stimulus_ids
        ):
            raise AssertionError(
                "Observation has unresolved Stimulus reference."
            )

        if observation.target is None:
            raise AssertionError(
                "Sensor Observation has no target."
            )

        if (
            observation.target.resource_id
            != target.id
        ):
            raise AssertionError(
                "Observation references unexpected target."
            )

        if len(
            observation.results
        ) != 1:
            raise AssertionError(
                "Sensor Observation must contain exactly one Result."
            )

        if (
            observation.context.get(
                "batch"
            )
            != source.batch
        ):
            raise AssertionError(
                "Batch context changed."
            )

        if (
            observation.context.get(
                "source_row"
            )
            != source.row
        ):
            raise AssertionError(
                "Source row context changed."
            )

        reconstructed = extract_feature_values(
            observation.results[
                0
            ]
        )

        if len(
            reconstructed
        ) != len(
            source.features
        ):
            raise AssertionError(
                "Feature vector length changed."
            )

        for original, converted in zip(
            source.features,
            reconstructed,
            strict=True,
        ):
            if original != converted:
                raise AssertionError(
                    "Sensor feature changed during graph conversion."
                )


def print_report(
    *,
    measurements: list[SourceMeasurement],
    analyte_ids: dict[int, str],
    stimuli: dict[
        tuple[int, float],
        Stimulus,
    ],
    target: ObservationTarget,
    observations: list[Observation],
) -> None:
    all_resource_ids = [
        *analyte_ids.values(),
        *(
            stimulus.id
            for stimulus in stimuli.values()
        ),
        target.id,
        *(
            observation.id
            for observation in observations
        ),
    ]

    negative_count = 0
    zero_count = 0
    positive_count = 0

    for measurement in measurements:
        for value in measurement.features:
            if value < 0:
                negative_count += 1
            elif value == 0:
                zero_count += 1
            else:
                positive_count += 1

    total_feature_values = (
        len(measurements)
        * FEATURE_COUNT
    )

    print()
    print(
        "OpenSmell experimental electronic-olfaction resource graph"
    )
    print("=" * 76)

    print()
    print("Source data")
    print("-" * 76)
    print(
        f"Source measurements         : "
        f"{len(measurements):>10,}"
    )
    print(
        f"Source analyte classes      : "
        f"{len(ANALYTES):>10,}"
    )
    print(
        f"Source features/measurement : "
        f"{FEATURE_COUNT:>10,}"
    )

    print()
    print("OpenSmell-generated graph")
    print("-" * 76)
    print(
        f"Generated analyte identities: "
        f"{len(analyte_ids):>9,}"
    )
    print(
        f"Stimulus resources          : "
        f"{len(stimuli):>10,}"
    )
    print(
        f"Observation targets         : "
        f"{1:>10,}"
    )
    print(
        f"Observations                : "
        f"{len(observations):>10,}"
    )
    print(
        f"Result objects              : "
        f"{len(observations):>10,}"
    )

    print()
    print("Generated target")
    print("-" * 76)
    print(
        f"Resource ID                 : {target.id}"
    )
    print(
        "Source-native identifier    : none claimed"
    )
    print(
        f"Target kind                 : "
        f"{target.extra.get('kind')}"
    )
    print(
        f"Sensor count                : "
        f"{target.extra.get('sensor_count')}"
    )

    print()
    print("Sensor Result architecture")
    print("-" * 76)
    print(
        f"Sensors per Result          : "
        f"{SENSOR_COUNT:>10,}"
    )
    print(
        f"Features per sensor         : "
        f"{len(FEATURES_PER_SENSOR):>10,}"
    )
    print(
        f"Features per Result         : "
        f"{FEATURE_COUNT:>10,}"
    )
    print(
        f"Result scheme ID            : "
        f"{SENSOR_RESULT_SCHEME_ID}"
    )
    print(
        f"Result scheme version       : "
        f"{SENSOR_RESULT_SCHEME_VERSION}"
    )

    print()
    print("Feature preservation")
    print("-" * 76)
    print(
        f"Total feature values        : "
        f"{total_feature_values:>10,}"
    )
    print(
        f"Negative values             : "
        f"{negative_count:>10,}"
    )
    print(
        f"Zero values                 : "
        f"{zero_count:>10,}"
    )
    print(
        f"Positive values             : "
        f"{positive_count:>10,}"
    )

    print()
    print("Identity")
    print("-" * 76)
    print(
        f"All generated Resource IDs  : "
        f"{len(all_resource_ids):>10,}"
    )
    print(
        f"Unique Resource IDs         : "
        f"{len(set(all_resource_ids)):>10,}"
    )
    print(
        f"Resource ID collisions      : "
        f"{len(all_resource_ids) - len(set(all_resource_ids)):>10,}"
    )

    first_measurement = measurements[
        0
    ]

    first_observation = observations[
        0
    ]

    first_result = first_observation.results[
        0
    ]

    print()
    print("Observation example")
    print("-" * 76)
    print(
        f"Source batch                : "
        f"{first_measurement.batch}"
    )
    print(
        f"Source row                  : "
        f"{first_measurement.row}"
    )
    print(
        f"Source analyte              : "
        f"{ANALYTES[first_measurement.analyte_class]}"
    )
    print(
        f"Source concentration ppmv   : "
        f"{first_measurement.concentration_ppmv}"
    )
    print(
        f"Observation Resource ID     : "
        f"{first_observation.id}"
    )
    print(
        f"Stimulus reference          : "
        f"{first_observation.stimulus.resource_id}"
    )
    print(
        f"Target reference            : "
        f"{first_observation.target.resource_id if first_observation.target else None}"
    )
    print(
        f"Result scheme ID            : "
        f"{first_result.scheme.id}"
    )
    print(
        f"Result scheme version       : "
        f"{first_result.scheme.version}"
    )

    sensors = first_result.data[
        "sensors"
    ]

    first_sensor = sensors[
        0
    ]

    print(
        f"Result sensor channels      : "
        f"{len(sensors)}"
    )
    print(
        f"First sensor                : "
        f"{first_sensor['sensor']}"
    )

    first_features = first_sensor[
        "features"
    ]

    for property_name in FEATURES_PER_SENSOR:
        print(
            f"  {property_name:<24} "
            f"{first_features[property_name]}"
        )

    print()
    print("Methodological checks")
    print("-" * 76)
    print(
        "UCI source analyte classes  : preserved"
    )
    print(
        "UCI concentrations          : preserved"
    )
    print(
        "UCI source rows             : preserved as observation context"
    )
    print(
        "UCI feature vectors         : preserved exactly"
    )
    print(
        "Generated target ID         : not presented as source-native"
    )
    print(
        "Generated analyte IDs       : not presented as source-native"
    )

    print()
    print("Result")
    print("=" * 76)
    print("SUCCESS")
    print(
        "The RFC-0007 experimental versioned Result architecture represented "
        "all electronic-olfaction observations without changing the "
        "generic Stimulus, ObservationTarget, Observation, or Result models."
    )
    print(
        "Source-native data and OpenSmell-generated identities remained "
        "explicitly distinguishable."
    )


def main() -> None:
    print(
        "Loading UCI gas sensor measurements..."
    )

    measurements = load_measurements()

    print(
        f"Loaded {len(measurements):,} measurements."
    )

    print(
        "Generating analyte reference identities..."
    )

    analyte_ids = build_analyte_identities()

    print(
        "Building Stimulus resources..."
    )

    stimuli = build_stimuli(
        measurements,
        analyte_ids,
    )

    print(
        "Building generated sensor-array ObservationTarget..."
    )

    target = build_sensor_array_target()

    print(
        "Building electronic-olfaction Observations with versioned Results..."
    )

    observations = build_observations(
        measurements,
        stimuli,
        target,
    )

    print(
        "Validating versioned Result graph and all 1,780,480 feature values..."
    )

    validate_graph(
        measurements=measurements,
        analyte_ids=analyte_ids,
        stimuli=stimuli,
        target=target,
        observations=observations,
    )

    print_report(
        measurements=measurements,
        analyte_ids=analyte_ids,
        stimuli=stimuli,
        target=target,
        observations=observations,
    )


if __name__ == "__main__":
    main()