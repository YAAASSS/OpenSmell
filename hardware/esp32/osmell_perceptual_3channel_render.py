"""Render quantitative perceptual measurements from an .osmell file.

Pipeline:

    .osmell
        -> GenericResourceGraph parser
        -> Observation
        -> PerceptualChannelMapper
        -> RenderingPlan
        -> Device Protocol 0.1
        -> ESP32

This renderer has no dependency on the original Keller/Vosshall dataset.

Channel bindings are experimental device/application policy.

The mapping between perceptual properties and physical channels is not part
of the OpenSmell representation itself.

This experiment validates interoperability and physical device control.
It does not claim physical odor reproduction.
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


from opensmell.experimental.annotation import (  # noqa: E402
    register_annotation_resource_type,
)
from opensmell.experimental.generic_graph import (  # noqa: E402
    create_default_resource_type_registry,
    generic_graph_loads,
)
from opensmell.experimental.molecule import (  # noqa: E402
    register_molecule_resource_type,
)
from opensmell.experimental.perceptual_channel_mapper import (  # noqa: E402
    PerceptualChannelBinding,
    PerceptualChannelMapper,
)
from opensmell.experimental.protocol_device_adapter import (  # noqa: E402
    ProtocolDeviceAdapter,
)
from opensmell.experimental.rendering import (  # noqa: E402
    RenderRequest,
)
from opensmell.experimental.resources import (  # noqa: E402
    Observation,
)
from opensmell.experimental.serial_device_transport import (  # noqa: E402
    SerialDeviceTransport,
)


EXPECTED_DEVICE_ID = (
    "opensmell-esp32-led-3ch-001"
)

DEFAULT_DURATION = 5.0

CHANNEL_BINDINGS = [
    PerceptualChannelBinding(
        property="flower",
        channel=0,
    ),
    PerceptualChannelBinding(
        property="grass",
        channel=1,
    ),
    PerceptualChannelBinding(
        property="wood",
        channel=2,
    ),
]


def create_registry():
    """Create the registry required by the multi-source graph."""

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Render quantitative perceptual "
            "measurements directly from an "
            "experimental OpenSmell .osmell "
            "GenericResourceGraph."
        )
    )

    parser.add_argument(
        "path",
        type=Path,
        help="Path to the .osmell file",
    )

    parser.add_argument(
        "--observation",
        default=None,
        help=(
            "Observation resource ID. "
            "When omitted, the graph must contain "
            "exactly one Observation."
        ),
    )

    parser.add_argument(
        "--port",
        default="COM8",
        help=(
            "ESP32 serial port "
            "(default: COM8)"
        ),
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION,
        help=(
            "Render duration in seconds "
            f"(default: {DEFAULT_DURATION})"
        ),
    )

    args = parser.parse_args()

    print(
        "Loading .osmell:",
        args.path,
    )

    text = args.path.read_text(
        encoding="utf-8"
    )

    registry = create_registry()

    graph = generic_graph_loads(
        text,
        registry=registry,
    )

    print(
        "GenericResourceGraph resources:",
        len(graph),
    )

    observations = [
        resource
        for resource in graph.resources
        if isinstance(
            resource,
            Observation,
        )
    ]

    if args.observation is None:
        if len(observations) != 1:
            raise RuntimeError(
                "No --observation was supplied and "
                "the graph does not contain exactly "
                "one Observation; "
                f"found {len(observations)}"
            )

        observation = observations[0]

    else:
        resource = graph.get(
            args.observation
        )

        if resource is None:
            raise RuntimeError(
                "Requested Observation does not exist: "
                f"{args.observation}"
            )

        if not isinstance(
            resource,
            Observation,
        ):
            raise RuntimeError(
                "Requested resource is not "
                "an Observation: "
                f"{args.observation}"
            )

        observation = resource

    print()
    print("Observation")
    print("-" * 72)

    print(
        "ID:",
        observation.id,
    )

    print(
        "Stimulus:",
        observation.stimulus.resource_id,
    )

    if observation.target is not None:
        print(
            "Target:",
            observation.target.resource_id,
        )

    mapper = PerceptualChannelMapper(
        bindings=CHANNEL_BINDINGS
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=observation.id,
            duration=args.duration,
        ),
    )

    if not plan.commands:
        raise RuntimeError(
            "The selected Observation produced "
            "no device commands"
        )

    print()
    print("RenderingPlan")
    print("-" * 72)

    print(
        "Mapper:",
        plan.extra.get(
            "mapper"
        ),
    )

    print(
        "Source:",
        plan.extra.get(
            "source_resource_id"
        ),
    )

    print(
        "Duration:",
        plan.duration,
    )

    for command in sorted(
        plan.commands,
        key=lambda item: item.channel,
    ):
        print(
            f"channel {command.channel}"
            f" -> {command.intensity:.2f}"
        )

    print()
    print(
        "Opening physical device:",
        args.port,
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

        adapter.capabilities.require_plan(
            plan
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
        ".osmell -> GenericResourceGraph -> "
        "Observation -> PerceptualChannelMapper -> "
        "RenderingPlan -> Device Protocol -> "
        "ESP32 completed."
    )


if __name__ == "__main__":
    main()