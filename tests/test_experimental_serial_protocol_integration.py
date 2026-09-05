"""Integration tests for the experimental serial protocol stack.

These tests exercise the software path:

ProtocolDeviceAdapter
    -> OpenSmell JSON device protocol
    -> SerialDeviceTransport
    -> fake serial connection

The fake serial connection behaves like a small line-oriented device. It
examines requests and produces protocol responses dynamically rather than
returning a preconfigured response sequence.

No physical serial port, microcontroller, or odor reproduction is involved.

This module is experimental and non-normative.
"""

from __future__ import annotations

import json

import pytest

from opensmell.experimental.device_adapter import (
    DeviceAdapter,
    require_device_adapter,
)
from opensmell.experimental.device_protocol import (
    PROTOCOL_VERSION,
)
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


DEVICE_ID = "serial-prototype-device"


class FakeProtocolSerial:
    """Small simulated serial device speaking protocol 0.1."""

    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.flush_count = 0
        self.closed = False
        self._pending_response: bytes | None = None

    def write(
        self,
        payload: bytes,
    ) -> int:
        self.writes.append(
            payload
        )

        if not payload.endswith(
            b"\n"
        ):
            self._pending_response = self._encode(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "type": "error",
                    "code": "invalid_framing",
                    "message": "request must end with newline",
                }
            )

            return len(payload)

        try:
            message = json.loads(
                payload[:-1].decode(
                    "utf-8"
                )
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            self._pending_response = self._encode(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "type": "error",
                    "code": "invalid_json",
                    "message": "request is not valid JSON",
                }
            )

            return len(payload)

        self._pending_response = self._handle(
            message
        )

        return len(payload)

    def flush(self) -> None:
        self.flush_count += 1

    def readline(self) -> bytes:
        if self._pending_response is None:
            return b""

        response = self._pending_response
        self._pending_response = None

        return response

    def close(self) -> None:
        self.closed = True

    @staticmethod
    def _encode(
        message: dict[str, object],
    ) -> bytes:
        return (
            json.dumps(
                message,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode(
                "utf-8"
            )
            + b"\n"
        )

    def _handle(
        self,
        message: object,
    ) -> bytes:
        if not isinstance(
            message,
            dict,
        ):
            return self._error(
                "invalid_message",
                "message must be an object",
            )

        if (
            message.get("protocol_version")
            != PROTOCOL_VERSION
        ):
            return self._error(
                "unsupported_protocol",
                "unsupported protocol version",
            )

        message_type = message.get(
            "type"
        )

        if message_type == "hello":
            return self._encode(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "type": "hello_response",
                    "device_id": DEVICE_ID,
                }
            )

        if message_type == "get_capabilities":
            return self._encode(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "type": "capabilities",
                    "device_id": DEVICE_ID,
                    "channels": [
                        {
                            "channel": 0,
                            "min_intensity": 0.0,
                            "max_intensity": 1.0,
                        },
                        {
                            "channel": 1,
                            "min_intensity": 0.0,
                            "max_intensity": 0.8,
                        },
                        {
                            "channel": 2,
                            "min_intensity": 0.1,
                            "max_intensity": 0.6,
                        },
                    ],
                    "min_duration": 0.1,
                    "max_duration": 30.0,
                }
            )

        if message_type == "render":
            return self._handle_render(
                message
            )

        return self._error(
            "unsupported_message",
            "unsupported message type",
        )

    def _handle_render(
        self,
        message: dict[str, object],
    ) -> bytes:
        duration = message.get(
            "duration"
        )

        commands = message.get(
            "commands"
        )

        if not isinstance(
            duration,
            (int, float),
        ) or isinstance(
            duration,
            bool,
        ):
            return self._error(
                "invalid_duration",
                "duration must be a number",
            )

        if (
            duration < 0.1
            or duration > 30.0
        ):
            return self._error(
                "unsupported_duration",
                "duration is outside device capabilities",
            )

        if not isinstance(
            commands,
            list,
        ):
            return self._error(
                "invalid_commands",
                "commands must be an array",
            )

        limits = {
            0: (0.0, 1.0),
            1: (0.0, 0.8),
            2: (0.1, 0.6),
        }

        for command in commands:
            if not isinstance(
                command,
                dict,
            ):
                return self._error(
                    "invalid_command",
                    "command must be an object",
                )

            channel = command.get(
                "channel"
            )

            intensity = command.get(
                "intensity"
            )

            if channel not in limits:
                return self._error(
                    "unsupported_channel",
                    "channel is not available",
                )

            if not isinstance(
                intensity,
                (int, float),
            ) or isinstance(
                intensity,
                bool,
            ):
                return self._error(
                    "invalid_intensity",
                    "intensity must be a number",
                )

            minimum, maximum = limits[
                channel
            ]

            if (
                intensity < minimum
                or intensity > maximum
            ):
                return self._error(
                    "unsupported_intensity",
                    "intensity is outside channel capabilities",
                )

        return self._encode(
            {
                "protocol_version": PROTOCOL_VERSION,
                "type": "ok",
            }
        )

    def _error(
        self,
        code: str,
        message: str,
    ) -> bytes:
        return self._encode(
            {
                "protocol_version": PROTOCOL_VERSION,
                "type": "error",
                "code": code,
                "message": message,
            }
        )


def stack() -> tuple[
    ProtocolDeviceAdapter,
    SerialDeviceTransport,
    FakeProtocolSerial,
]:
    fake = FakeProtocolSerial()

    transport = SerialDeviceTransport(
        "COM_TEST",
        serial_instance=fake,
    )

    adapter = ProtocolDeviceAdapter(
        transport
    )

    return (
        adapter,
        transport,
        fake,
    )


def decode_write(
    payload: bytes,
) -> dict[str, object]:
    assert payload.endswith(
        b"\n"
    )

    value = json.loads(
        payload[:-1].decode(
            "utf-8"
        )
    )

    assert isinstance(
        value,
        dict,
    )

    return value


def test_serial_protocol_stack_discovers_device() -> None:
    adapter, _, fake = stack()

    assert adapter.device_id == DEVICE_ID

    assert len(
        fake.writes
    ) == 2

    assert decode_write(
        fake.writes[0]
    ) == {
        "protocol_version": "0.1",
        "type": "hello",
    }

    assert decode_write(
        fake.writes[1]
    ) == {
        "protocol_version": "0.1",
        "type": "get_capabilities",
    }


def test_serial_protocol_stack_discovers_capabilities() -> None:
    adapter, _, _ = stack()

    assert (
        adapter.capabilities.device_id
        == DEVICE_ID
    )

    assert [
        (
            channel.channel,
            channel.min_intensity,
            channel.max_intensity,
        )
        for channel in adapter.capabilities.channels
    ] == [
        (0, 0.0, 1.0),
        (1, 0.0, 0.8),
        (2, 0.1, 0.6),
    ]

    assert adapter.capabilities.min_duration == 0.1
    assert adapter.capabilities.max_duration == 30.0


def test_serial_protocol_adapter_satisfies_device_contract() -> None:
    adapter, _, _ = stack()

    assert isinstance(
        adapter,
        DeviceAdapter,
    )

    assert (
        require_device_adapter(
            adapter
        )
        is adapter
    )


def test_serial_protocol_stack_renders_plan() -> None:
    adapter, _, fake = stack()

    result = adapter.render(
        RenderingPlan(
            commands=[
                DeviceCommand(
                    channel=0,
                    intensity=0.7,
                ),
                DeviceCommand(
                    channel=2,
                    intensity=0.4,
                ),
            ],
            duration=4.0,
        )
    )

    assert result == {
        "protocol_version": "0.1",
        "type": "ok",
    }

    assert len(
        fake.writes
    ) == 3

    assert decode_write(
        fake.writes[2]
    ) == {
        "protocol_version": "0.1",
        "type": "render",
        "duration": 4.0,
        "commands": [
            {
                "channel": 0,
                "intensity": 0.7,
            },
            {
                "channel": 2,
                "intensity": 0.4,
            },
        ],
    }


def test_serial_protocol_stack_supports_multiple_renders() -> None:
    adapter, _, fake = stack()

    adapter.render(
        RenderingPlan(
            commands=[
                DeviceCommand(
                    channel=0,
                    intensity=0.2,
                )
            ],
            duration=1.0,
        )
    )

    adapter.render(
        RenderingPlan(
            commands=[
                DeviceCommand(
                    channel=1,
                    intensity=0.5,
                )
            ],
            duration=2.0,
        )
    )

    assert len(
        fake.writes
    ) == 4

    assert decode_write(
        fake.writes[2]
    )["type"] == "render"

    assert decode_write(
        fake.writes[3]
    )["type"] == "render"


def test_local_capabilities_reject_bad_channel_before_serial_write() -> None:
    adapter, _, fake = stack()

    invalid_plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=9,
                intensity=0.5,
            )
        ],
        duration=4.0,
    )

    with pytest.raises(
        ValueError,
    ):
        adapter.render(
            invalid_plan
        )

    assert len(
        fake.writes
    ) == 2


def test_local_capabilities_reject_bad_intensity_before_serial_write() -> None:
    adapter, _, fake = stack()

    invalid_plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=2,
                intensity=0.9,
            )
        ],
        duration=4.0,
    )

    with pytest.raises(
        ValueError,
    ):
        adapter.render(
            invalid_plan
        )

    assert len(
        fake.writes
    ) == 2


def test_local_capabilities_reject_bad_duration_before_serial_write() -> None:
    adapter, _, fake = stack()

    invalid_plan = RenderingPlan(
        commands=[],
        duration=40.0,
    )

    with pytest.raises(
        ValueError,
    ):
        adapter.render(
            invalid_plan
        )

    assert len(
        fake.writes
    ) == 2


def test_serial_transport_flushes_every_protocol_message() -> None:
    adapter, _, fake = stack()

    assert fake.flush_count == 2

    adapter.render(
        RenderingPlan(
            commands=[],
            duration=1.0,
        )
    )

    assert fake.flush_count == 3


def test_serial_transport_can_be_closed_after_protocol_use() -> None:
    _, transport, fake = stack()

    assert fake.closed is False

    transport.close()

    assert fake.closed is True