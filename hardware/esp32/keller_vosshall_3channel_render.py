"""Physical three-channel rendering experiment from Keller/Vosshall data.

This experiment demonstrates:

    Keller/Vosshall source observation
        -> OpenSmell experimental ResourceGraph
        -> Observation
        -> perceptual Result
        -> quantitative measurement mapping
        -> RenderingPlan
        -> Device Protocol 0.1
        -> physical ESP32 outputs

The physical channel bindings are experimental device/application policy.

The source perceptual measurements are normalized from their explicitly
declared source scale to the DeviceCommand intensity range 0..1.

This experiment does not claim to reproduce the odor represented by the
source observation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

from tools.analyze_keller_vosshall_resource_graph import (  # noqa: E402
    build_resource_graph,
    clean_source_value,
    get_perceptual_measurements,
    load_dataset,
    require_column,
)

from opensmell.experimental.protocol_device_adapter import (  # noqa: E402
    ProtocolDeviceAdapter,
)
from opensmell.experimental.rendering import (  # noqa: E402
    DeviceCommand,
    RenderingPlan,
)
from opensmell.experimental.resources import (  # noqa: E402
    Observation,
)
from opensmell.experimental.serial_device_transport import (  # noqa: E402
    SerialDeviceTransport,
)


TARGET_SOURCE_ROW = 2500

EXPECTED_CID = "61918"
EXPECTED_ODOR = "2-Acetyl-3-ethylpyrazine"
EXPECTED_DILUTION = "1/1,000"
EXPECTED_SUBJECT = "3"

EXPECTED_DEVICE_ID = (
    "opensmell-esp32-led-3ch-001"
)

RENDER_DURATION_SECONDS = 5.0


CHANNEL_BINDINGS = {
    "FLOWER": 0,
    "GRASS": 1,
    "WOOD": 2,
}


def normalize_measurement(
    measurement: dict,
) -> float:
    """Normalize a scheme-defined quantitative measurement to 0..1."""

    value = measurement.get(
        "value"
    )

    scale = measurement.get(
        "scale"
    )

    if not isinstance(
        value,
        (int, float),
    ):
        raise ValueError(
            "measurement value must be numeric"
        )

    if not isinstance(
        scale,
        dict,
    ):
        raise ValueError(
            "measurement scale must be a dict"
        )

    minimum = scale.get(
        "min"
    )

    maximum = scale.get(
        "max"
    )

    if not isinstance(
        minimum,
        (int, float),
    ):
        raise ValueError(
            "measurement scale min must be numeric"
        )

    if not isinstance(
        maximum,
        (int, float),
    ):
        raise ValueError(
            "measurement scale max must be numeric"
        )

    if maximum <= minimum:
        raise ValueError(
            "measurement scale max must be greater than min"
        )

    if not minimum <= value <= maximum:
        raise ValueError(
            "measurement value is outside its declared scale"
        )

    normalized = (
        (float(value) - float(minimum))
        / (float(maximum) - float(minimum))
    )

    return normalized


def find_target_observation(
    graph,
    dataframe,
) -> Observation:
    """Resolve source row 2500 to its OpenSmell Observation."""

    if TARGET_SOURCE_ROW not in dataframe.index:
        raise RuntimeError(
            f"Source row {TARGET_SOURCE_ROW} does not exist"
        )

    row = dataframe.loc[
        TARGET_SOURCE_ROW
    ]

    cid_column = require_column(
        dataframe,
        ("CID",),
        dataset_name="Keller/Vosshall",
    )

    odor_column = require_column(
        dataframe,
        ("Odor",),
        dataset_name="Keller/Vosshall",
    )

    dilution_column = require_column(
        dataframe,
        ("Odor dilution",),
        dataset_name="Keller/Vosshall",
    )

    subject_column = require_column(
        dataframe,
        ("Subject # (this study)",),
        dataset_name="Keller/Vosshall",
    )

    cid = clean_source_value(
        row[cid_column]
    )

    odor = clean_source_value(
        row[odor_column]
    )

    dilution = clean_source_value(
        row[dilution_column]
    )

    subject = clean_source_value(
        row[subject_column]
    )

    print()
    print("=== Keller/Vosshall source observation ===")
    print()

    print(
        "Source row:",
        TARGET_SOURCE_ROW,
    )
    print(
        "CID:",
        cid,
    )
    print(
        "Odor:",
        odor,
    )
    print(
        "Dilution:",
        dilution,
    )
    print(
        "Subject:",
        subject,
    )

    if cid != EXPECTED_CID:
        raise RuntimeError(
            f"Unexpected CID: {cid!r}"
        )

    if odor != EXPECTED_ODOR:
        raise RuntimeError(
            f"Unexpected odor: {odor!r}"
        )

    if dilution != EXPECTED_DILUTION:
        raise RuntimeError(
            f"Unexpected dilution: {dilution!r}"
        )

    if subject != EXPECTED_SUBJECT:
        raise RuntimeError(
            f"Unexpected subject: {subject!r}"
        )

    matches: list[Observation] = []

    for resource in graph.resources:
        if not isinstance(
            resource,
            Observation,
        ):
            continue

        target = graph.resolve(
            resource.target
        )

        stimulus = graph.resolve(
            resource.stimulus
        )

        if target is None or stimulus is None:
            continue

        target_subject = None

        for identifier in target.identifiers:
            if (
                identifier.scheme
                == "keller_vosshall.subject"
            ):
                target_subject = (
                    identifier.value
                )
                break

        if target_subject != subject:
            continue

        stimulus_dilution = None

        for condition in stimulus.conditions:
            if (
                condition.property
                == "dilution"
            ):
                stimulus_dilution = (
                    str(condition.value)
                )
                break

        if stimulus_dilution != dilution:
            continue

        # Stimulus.source points to the deterministic molecule ID.
        # The molecule itself is intentionally unresolved in this graph.
        #
        # Several observations can therefore share subject and dilution.
        # Verify the exact source observation by checking its quantitative
        # measurements below.

        measurements = (
            get_perceptual_measurements(
                resource
            )
        )

        measurement_map = {
            str(measurement.get("property")):
                measurement
            for measurement in measurements
        }

        expected_values = {
            "FLOWER": row[
                require_column(
                    dataframe,
                    ("FLOWER",),
                    dataset_name="Keller/Vosshall",
                )
            ],
            "GRASS": row[
                require_column(
                    dataframe,
                    ("GRASS",),
                    dataset_name="Keller/Vosshall",
                )
            ],
            "WOOD": row[
                require_column(
                    dataframe,
                    ("WOOD",),
                    dataset_name="Keller/Vosshall",
                )
            ],
        }

        descriptor_match = True

        for descriptor, expected in (
            expected_values.items()
        ):
            measurement = (
                measurement_map.get(
                    descriptor
                )
            )

            if measurement is None:
                descriptor_match = False
                break

            if float(
                measurement["value"]
            ) != float(expected):
                descriptor_match = False
                break

        if descriptor_match:
            matches.append(
                resource
            )

    if len(matches) != 1:
        raise RuntimeError(
            "Could not uniquely resolve source row "
            f"{TARGET_SOURCE_ROW} to one Observation; "
            f"matches={len(matches)}"
        )

    return matches[0]


def build_plan(
    observation: Observation,
) -> RenderingPlan:
    """Build a three-channel plan from perceptual measurements."""

    measurements = (
        get_perceptual_measurements(
            observation
        )
    )

    measurement_map = {
        str(measurement.get("property")):
            measurement
        for measurement in measurements
    }

    commands: list[
        DeviceCommand
    ] = []

    print()
    print("=== Perceptual Result ===")
    print()

    for (
        descriptor,
        channel,
    ) in CHANNEL_BINDINGS.items():

        measurement = (
            measurement_map.get(
                descriptor
            )
        )

        if measurement is None:
            raise RuntimeError(
                f"Missing required measurement: {descriptor}"
            )

        normalized = (
            normalize_measurement(
                measurement
            )
        )

        scale = measurement[
            "scale"
        ]

        print(
            f"{descriptor}: "
            f"{measurement['value']} "
            f"[{scale['min']}..{scale['max']}] "
            f"-> {normalized:.2f} "
            f"-> channel {channel}"
        )

        commands.append(
            DeviceCommand(
                channel=channel,
                intensity=normalized,
            )
        )

    return RenderingPlan(
        commands=commands,
        duration=RENDER_DURATION_SECONDS,
        extra={
            "experiment": (
                "keller_vosshall_quantitative_3channel"
            ),
            "source_observation_id": (
                observation.id
            ),
        },
    )


def print_plan(
    plan: RenderingPlan,
) -> None:
    print()
    print("=== OpenSmell RenderingPlan ===")
    print()

    print(
        "Duration:",
        plan.duration,
        "seconds",
    )

    for command in plan.commands:
        print(
            f"  channel {command.channel}"
            f" -> {command.intensity:.2f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Render one Keller/Vosshall psychophysical "
            "observation through the experimental "
            "OpenSmell ESP32 pipeline."
        )
    )

    parser.add_argument(
        "--port",
        required=True,
        help="ESP32 serial port.",
    )

    args = parser.parse_args()

    print(
        "Loading Keller/Vosshall dataset..."
    )

    dataframe = load_dataset()

    print(
        f"Loaded {len(dataframe):,} observations."
    )

    print(
        "Building OpenSmell ResourceGraph..."
    )

    graph = build_resource_graph()

    print(
        f"Graph resources: {len(graph):,}"
    )

    observation = (
        find_target_observation(
            graph,
            dataframe,
        )
    )

    print()
    print("=== OpenSmell Observation ===")
    print()

    print(
        "Observation ID:",
        observation.id,
    )

    print(
        "Stimulus ID:",
        observation.stimulus.resource_id,
    )

    if observation.target is not None:
        print(
            "Target ID:",
            observation.target.resource_id,
        )

    plan = build_plan(
        observation
    )

    print_plan(
        plan
    )

    print()
    print(
        f"Opening serial device on {args.port}..."
    )

    with SerialDeviceTransport(
        port=args.port,
        baudrate=115200,
        timeout=2.0,
        startup_delay=2.0,
        discard_initial_input=True,
    ) as transport:

        adapter = ProtocolDeviceAdapter(
            transport
        )

        print()
        print("=== Physical device ===")
        print()

        print(
            "Device ID:",
            adapter.device_id,
        )

        if (
            adapter.device_id
            != EXPECTED_DEVICE_ID
        ):
            raise RuntimeError(
                "Unexpected physical device: "
                f"{adapter.device_id!r}"
            )

        # Validate the exact generated plan against the capabilities
        # advertised by the physical device before execution.
        adapter.capabilities.require_plan(
            plan
        )

        print()
        print(
            "Rendering quantitative observation..."
        )

        response = adapter.render(
            plan
        )

        print(
            "Device response:",
            response,
        )

    print()
    print("SUCCESS")
    print(
        "Keller/Vosshall -> OpenSmell Observation -> "
        "perceptual Result -> normalized RenderingPlan -> "
        "Device Protocol -> ESP32 completed."
    )


if __name__ == "__main__":
    main()