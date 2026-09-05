"""Tests for the experimental OpenSmell device protocol.

These tests validate message construction, strict JSON serialization,
capability exchange, and RenderingPlan transport.

They do not validate a physical odor reproduction mechanism.

This module is experimental and non-normative.
"""

from __future__ import annotations

import math

import pytest

from opensmell.experimental.device_capabilities import (
    DeviceCapabilities,
    DeviceChannelCapability,
)
from opensmell.experimental.device_protocol import (
    PROTOCOL_VERSION,
    DeviceProtocolError,
    capabilities_request,
    capabilities_response,
    dumps_message,
    error_response,
    hello_request,
    hello_response,
    loads_message,
    ok_response,
    parse_capabilities_response,
    parse_hello_response,
    parse_render_request,
    render_request_message,
    require_ok_response,
)
from opensmell.experimental.rendering import (
    DeviceCommand,
    RenderingPlan,
)


def capabilities() -> DeviceCapabilities:
    return DeviceCapabilities(
        device_id="prototype-device-1",
        channels=[
            DeviceChannelCapability(
                channel=0,
                min_intensity=0.0,
                max_intensity=1.0,
            ),
            DeviceChannelCapability(
                channel=1,
                min_intensity=0.1,
                max_intensity=0.8,
            ),
            DeviceChannelCapability(
                channel=3,
                min_intensity=0.0,
                max_intensity=0.5,
            ),
        ],
        min_duration=0.1,
        max_duration=30.0,
    )


def plan() -> RenderingPlan:
    return RenderingPlan(
        commands=[
            DeviceCommand(
                channel=0,
                intensity=0.7,
            ),
            DeviceCommand(
                channel=3,
                intensity=0.35,
            ),
        ],
        duration=4.0,
    )


def test_protocol_version_is_0_1() -> None:
    assert PROTOCOL_VERSION == "0.1"


def test_hello_request() -> None:
    assert hello_request() == {
        "protocol_version": "0.1",
        "type": "hello",
    }


def test_hello_response_roundtrip() -> None:
    message = hello_response(
        "prototype-device-1"
    )

    serialized = dumps_message(
        message
    )

    parsed = loads_message(
        serialized
    )

    assert (
        parse_hello_response(
            parsed
        )
        == "prototype-device-1"
    )


def test_hello_response_rejects_empty_device_id() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="device_id must be non-empty",
    ):
        hello_response(
            ""
        )


def test_parse_hello_response_rejects_wrong_type() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="expected message type",
    ):
        parse_hello_response(
            {
                "protocol_version": "0.1",
                "type": "ok",
                "device_id": "device",
            }
        )


def test_parse_hello_response_rejects_wrong_version() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="unsupported protocol version",
    ):
        parse_hello_response(
            {
                "protocol_version": "9.9",
                "type": "hello_response",
                "device_id": "device",
            }
        )


def test_capabilities_request() -> None:
    assert capabilities_request() == {
        "protocol_version": "0.1",
        "type": "get_capabilities",
    }


def test_capabilities_roundtrip() -> None:
    original = capabilities()

    message = capabilities_response(
        original
    )

    parsed = parse_capabilities_response(
        loads_message(
            dumps_message(
                message
            )
        )
    )

    assert parsed.device_id == original.device_id

    assert parsed.min_duration == original.min_duration
    assert parsed.max_duration == original.max_duration

    assert [
        (
            channel.channel,
            channel.min_intensity,
            channel.max_intensity,
        )
        for channel in parsed.channels
    ] == [
        (
            channel.channel,
            channel.min_intensity,
            channel.max_intensity,
        )
        for channel in original.channels
    ]


def test_capabilities_response_rejects_wrong_object() -> None:
    with pytest.raises(
        TypeError,
        match="DeviceCapabilities",
    ):
        capabilities_response(
            {}
        )


def test_parse_capabilities_requires_channels_array() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="channels must be an array",
    ):
        parse_capabilities_response(
            {
                "protocol_version": "0.1",
                "type": "capabilities",
                "device_id": "device",
                "channels": {},
                "min_duration": 1.0,
                "max_duration": 5.0,
            }
        )


def test_parse_capabilities_rejects_duplicate_channels() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="invalid device capabilities",
    ):
        parse_capabilities_response(
            {
                "protocol_version": "0.1",
                "type": "capabilities",
                "device_id": "device",
                "channels": [
                    {
                        "channel": 1,
                        "min_intensity": 0.0,
                        "max_intensity": 1.0,
                    },
                    {
                        "channel": 1,
                        "min_intensity": 0.0,
                        "max_intensity": 1.0,
                    },
                ],
                "min_duration": 1.0,
                "max_duration": 5.0,
            }
        )


def test_parse_capabilities_rejects_invalid_intensity_range() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="invalid capability",
    ):
        parse_capabilities_response(
            {
                "protocol_version": "0.1",
                "type": "capabilities",
                "device_id": "device",
                "channels": [
                    {
                        "channel": 1,
                        "min_intensity": 0.8,
                        "max_intensity": 0.2,
                    }
                ],
                "min_duration": 1.0,
                "max_duration": 5.0,
            }
        )


def test_render_request_roundtrip() -> None:
    original = plan()

    message = render_request_message(
        original
    )

    parsed = parse_render_request(
        loads_message(
            dumps_message(
                message
            )
        )
    )

    assert parsed.duration == original.duration

    assert [
        (
            command.channel,
            command.intensity,
        )
        for command in parsed.commands
    ] == [
        (
            command.channel,
            command.intensity,
        )
        for command in original.commands
    ]


def test_render_request_has_expected_wire_shape() -> None:
    message = render_request_message(
        plan()
    )

    assert message == {
        "protocol_version": "0.1",
        "type": "render",
        "duration": 4.0,
        "commands": [
            {
                "channel": 0,
                "intensity": 0.7,
            },
            {
                "channel": 3,
                "intensity": 0.35,
            },
        ],
    }


def test_render_request_supports_empty_plan() -> None:
    original = RenderingPlan(
        commands=[],
        duration=2.0,
    )

    parsed = parse_render_request(
        render_request_message(
            original
        )
    )

    assert parsed.commands == []
    assert parsed.duration == 2.0


def test_render_request_rejects_wrong_object() -> None:
    with pytest.raises(
        TypeError,
        match="RenderingPlan",
    ):
        render_request_message(
            {}
        )


def test_parse_render_request_requires_commands_array() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="commands must be an array",
    ):
        parse_render_request(
            {
                "protocol_version": "0.1",
                "type": "render",
                "duration": 1.0,
                "commands": {},
            }
        )


def test_parse_render_request_rejects_negative_channel() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="must be non-negative",
    ):
        parse_render_request(
            {
                "protocol_version": "0.1",
                "type": "render",
                "duration": 1.0,
                "commands": [
                    {
                        "channel": -1,
                        "intensity": 0.5,
                    }
                ],
            }
        )


def test_parse_render_request_rejects_invalid_intensity() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="invalid rendering command",
    ):
        parse_render_request(
            {
                "protocol_version": "0.1",
                "type": "render",
                "duration": 1.0,
                "commands": [
                    {
                        "channel": 0,
                        "intensity": 2.0,
                    }
                ],
            }
        )


def test_parse_render_request_rejects_nonpositive_duration() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="invalid rendering plan",
    ):
        parse_render_request(
            {
                "protocol_version": "0.1",
                "type": "render",
                "duration": 0.0,
                "commands": [],
            }
        )


def test_ok_response() -> None:
    message = ok_response()

    require_ok_response(
        message
    )


def test_error_response_becomes_protocol_error() -> None:
    message = error_response(
        "unsupported_channel",
        "channel 9 is not available",
    )

    with pytest.raises(
        DeviceProtocolError,
        match="unsupported_channel",
    ):
        require_ok_response(
            message
        )


def test_require_ok_response_rejects_unexpected_type() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="expected 'ok' response",
    ):
        require_ok_response(
            {
                "protocol_version": "0.1",
                "type": "hello_response",
                "device_id": "device",
            }
        )


def test_dumps_message_uses_compact_json() -> None:
    serialized = dumps_message(
        hello_request()
    )

    assert serialized == (
        '{"protocol_version":"0.1","type":"hello"}'
    )


@pytest.mark.parametrize(
    "value",
    [
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_dumps_message_rejects_nonfinite_numbers(
    value: float,
) -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="strict JSON",
    ):
        dumps_message(
            {
                "value": value,
            }
        )


@pytest.mark.parametrize(
    "text",
    [
        '{"value":NaN}',
        '{"value":Infinity}',
        '{"value":-Infinity}',
    ],
)
def test_loads_message_rejects_nonfinite_numbers(
    text: str,
) -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="invalid JSON numeric constant",
    ):
        loads_message(
            text
        )


def test_loads_message_rejects_invalid_json() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="invalid JSON message",
    ):
        loads_message(
            "{not-json}"
        )


def test_loads_message_requires_json_object() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="message must be an object",
    ):
        loads_message(
            '["hello"]'
        )


def test_loads_message_rejects_empty_text() -> None:
    with pytest.raises(
        DeviceProtocolError,
        match="non-empty",
    ):
        loads_message(
            ""
        )


def test_protocol_messages_survive_json_roundtrip() -> None:
    messages = [
        hello_request(),
        hello_response(
            "prototype-device-1"
        ),
        capabilities_request(),
        capabilities_response(
            capabilities()
        ),
        render_request_message(
            plan()
        ),
        ok_response(),
        error_response(
            "example",
            "example error",
        ),
    ]

    for message in messages:
        assert loads_message(
            dumps_message(
                message
            )
        ) == message