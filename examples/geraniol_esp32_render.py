"""Render a real Geraniol .osmell document on the ESP32 LED prototype.

Pipeline:

    geraniol.osmell
        ->
    Core OpenSmell Odor
        ->
    GenericResourceGraph
        ->
    SemanticChannelMapper
        ->
    RenderingPlan
        ->
    ProtocolDeviceAdapter
        ->
    SerialDeviceTransport
        ->
    ESP32
        ->
    LED

The LED is only a stand-in actuator.

The mapping:

    floral -> channel 0

is device/application policy. It is deliberately NOT stored in the .osmell
document and does not claim that channel 0 physically reproduces a floral odor.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import opensmell

from opensmell.experimental.odor_graph_bridge import (
    bridge_odor_to_resource_graph,
)
from opensmell.experimental.protocol_device_adapter import (
    ProtocolDeviceAdapter,
)
from opensmell.experimental.rendering import (
    RenderRequest,
)
from opensmell.experimental.semantic_channel_mapper import (
    SemanticChannelBinding,
    SemanticChannelMapper,
)
from opensmell.experimental.serial_device_transport import (
    SerialDeviceTransport,
)


OSMELL_PATH = Path(
    "examples/geraniol.osmell"
)

DURATION_SECONDS = 4.0

FLORAL_INTENSITY = 0.7


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render the Geraniol OpenSmell example "
            "on the ESP32 LED prototype."
        )
    )

    parser.add_argument(
        "--port",
        required=True,
        help="Serial port connected to the ESP32.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(
        "OpenSmell - Geraniol physical rendering"
    )
    print(
        "=" * 44
    )
    print()

    if not OSMELL_PATH.is_file():
        raise FileNotFoundError(
            f"OpenSmell document not found: {OSMELL_PATH}"
        )

    print(
        "1. Loading Core .osmell..."
    )

    odor = opensmell.load(
        OSMELL_PATH
    )

    print(
        f"   Odor ID : {odor.id}"
    )

    if odor.metadata is not None:
        name = odor.metadata.labels.get(
            "en"
        )

        if name:
            print(
                f"   Name    : {name}"
            )

    print()

    print(
        "2. Bridging Core Odor to ResourceGraph..."
    )

    bridge = bridge_odor_to_resource_graph(
        odor
    )

    print(
        "   Primary resource : "
        f"{bridge.primary_resource_id}"
    )

    print(
        "   Annotations      : "
        f"{len(bridge.annotation_ids)}"
    )

    print()

    print(
        "3. Configuring semantic mapper..."
    )

    mapper = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=0,
                intensity=FLORAL_INTENSITY,
            ),
        ]
    )

    print(
        "   floral -> channel 0 "
        f"@ {FLORAL_INTENSITY}"
    )

    print()

    print(
        "4. Creating rendering request..."
    )

    request = RenderRequest(
        resource_id=bridge.primary_resource_id,
        duration=DURATION_SECONDS,
    )

    plan = mapper.map(
        bridge.graph,
        request,
    )

    print(
        f"   Duration : {plan.duration} s"
    )

    print(
        f"   Commands : {len(plan.commands)}"
    )

    for command in plan.commands:
        print(
            "   - channel "
            f"{command.channel} "
            f"@ {command.intensity}"
        )

    if not plan.commands:
        raise RuntimeError(
            "No rendering command was produced. "
            "Geraniol should contain a present "
            "'floral' annotation."
        )

    print()

    print(
        "5. Opening ESP32 serial connection..."
    )

    with SerialDeviceTransport(
        args.port,
        startup_delay=2.0,
        discard_initial_input=True,
    ) as transport:
        print(
            "   Serial connection synchronized."
        )
        print()

        print(
            "6. Discovering OpenSmell device..."
        )

        device = ProtocolDeviceAdapter(
            transport
        )

        print(
            f"   Device ID : {device.device_id}"
        )

        print()

        print(
            "7. Checking mapper/device compatibility..."
        )

        mapper.require_support(
            device.capabilities
        )

        print(
            "   Mapper bindings accepted."
        )

        print()

        print(
            "8. Rendering Geraniol plan..."
        )

        response = device.render(
            plan
        )

        print(
            "   Render accepted."
        )
        print(
            f"   Response : {response}"
        )

    print()
    print(
        "SUCCESS"
    )
    print()
    print(
        "Real pipeline completed:"
    )
    print(
        "  geraniol.osmell"
    )
    print(
        "      -> ResourceGraph"
    )
    print(
        "      -> semantic mapping"
    )
    print(
        "      -> RenderingPlan"
    )
    print(
        "      -> OpenSmell device protocol"
    )
    print(
        "      -> ESP32"
    )
    print(
        "      -> LED"
    )
    print()
    print(
        "The LED represents a controllable actuator only."
    )
    print(
        "No claim is made that this hardware reproduces "
        "the physical smell of Geraniol."
    )


if __name__ == "__main__":
    main()