"""Physical OpenSmell rendering example using an ESP32.

This script requires:

- an ESP32 connected through USB serial,
- OpenSmell device-protocol firmware running on the ESP32,
- one output actuator mapped to device channel 0.

For the current prototype, the actuator is an LED connected to GPIO23.

This script requires physical hardware and is not intended to be collected
as a normal automated pytest test.
"""

from __future__ import annotations

import argparse

from opensmell.experimental.protocol_device_adapter import (
    ProtocolDeviceAdapter,
)
from opensmell.experimental.rendering import (
    DeviceCommand,
    RenderingPlan,
)
from opensmell.experimental.serial_device_transport import (
    SerialDeviceTransport,
)


DEFAULT_PORT = "COM8"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the physical OpenSmell ESP32 rendering tests."
        )
    )

    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        help=(
            "Serial port connected to the ESP32 "
            f"(default: {DEFAULT_PORT})."
        ),
    )

    return parser.parse_args()


def print_capabilities(
    device: ProtocolDeviceAdapter,
) -> None:
    print(
        "Device découvert :",
        device.device_id,
    )

    print("Capabilities :")
    print(
        "  min duration :",
        device.capabilities.min_duration,
    )
    print(
        "  max duration :",
        device.capabilities.max_duration,
    )

    for channel in device.capabilities.channels:
        print(
            "  channel",
            channel.channel,
            "intensity",
            channel.min_intensity,
            "->",
            channel.max_intensity,
        )


def run_valid_render(
    device: ProtocolDeviceAdapter,
) -> None:
    print()
    print("=== TEST 1 : rendu valide ===")

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=0,
                intensity=0.7,
            )
        ],
        duration=4.0,
    )

    response = device.render(
        plan
    )

    print("Résultat : ACCEPTÉ")
    print(
        "Réponse :",
        response,
    )


def run_invalid_channel_test(
    device: ProtocolDeviceAdapter,
) -> None:
    print()
    print(
        "=== TEST 2 : canal non supporté ==="
    )

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=5,
                intensity=0.7,
            )
        ],
        duration=1.0,
    )

    try:
        device.render(
            plan
        )

    except Exception as exc:
        print(
            "Résultat : REFUSÉ PAR OPENSMELL"
        )
        print(
            "Exception :",
            type(exc).__name__,
        )
        print(
            "Message   :",
            exc,
        )

    else:
        print(
            "ERREUR : le plan a été accepté."
        )


def run_invalid_duration_test(
    device: ProtocolDeviceAdapter,
) -> None:
    print()
    print(
        "=== TEST 3 : durée hors capacités ==="
    )

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=0,
                intensity=0.5,
            )
        ],
        duration=60.0,
    )

    try:
        device.render(
            plan
        )

    except Exception as exc:
        print(
            "Résultat : REFUSÉ PAR OPENSMELL"
        )
        print(
            "Exception :",
            type(exc).__name__,
        )
        print(
            "Message   :",
            exc,
        )

    else:
        print(
            "ERREUR : le plan a été accepté."
        )


def main() -> None:
    args = parse_args()

    with SerialDeviceTransport(
        args.port,
        startup_delay=2.0,
        discard_initial_input=True,
    ) as transport:
        print(
            "Connexion série ouverte et synchronisée."
        )

        device = ProtocolDeviceAdapter(
            transport
        )

        print_capabilities(
            device
        )

        run_valid_render(
            device
        )

        run_invalid_channel_test(
            device
        )

        run_invalid_duration_test(
            device
        )

        print()
        print(
            "Tests physiques terminés."
        )


if __name__ == "__main__":
    main()