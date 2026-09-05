"""Tests for the experimental protocol-backed DeviceAdapter.

These tests exercise the complete in-memory boundary:

DeviceAdapter
    -> JSON device protocol
    -> DeviceTransport
    -> simulated protocol responses

No physical odor reproduction or hardware I/O is involved.

This module is experimental and non-normative.
"""

from __future__ import annotations

from typing import Any

import pytest

from opensmell.experimental.device_adapter import (
    DeviceAdapter,
    require_device_adapter,
)
from opensmell.experimental.device_capabilities import (
    DeviceCapabilities,
    DeviceChannelCapability,
)
from opensmell.experimental.device_protocol import (
    capabilities_response,
    dumps_message,
    error_response,
    hello_response,
    loads_message,
    ok_response,
)
from opensmell.experimental.device_transport import (
    MemoryDeviceTransport,
)
from opensmell.experimental.protocol_device_adapter import (
    ProtocolDeviceAdapter,
)
from opensmell.experimental.rendering import (
    DeviceCommand,
    RenderingPlan,
)


DEVICE_ID = "protocol-test-device"


def capabilities() -> DeviceCapabilities:
    return DeviceCapabilities(
        device_id=DEVICE_ID,
        channels=[
            DeviceChannelCapability(
                channel=0,
                min_intensity=0.0,
                max_intensity=1.0,
            ),
            DeviceChannelCapability(
                channel=2,
                min_intensity=0.1,
                max_intensity=0.8,
            ),
        ],
        min_duration=1.0,
        max_duration=10.0,
    )


def transport(
    render_response: dict[str, Any] | None = None,
) -> MemoryDeviceTransport:
    responses = [
        dumps_message(
            hello_response(
                DEVICE_ID
            )
        ),
        dumps_message(
            capabilities_response(
                capabilities()
            )
        ),
    ]

    if render_response is not None:
        responses.append(
            dumps_message(
                render_response
            )
        )

    return MemoryDeviceTransport(
        responses=responses
    )


def adapter(
    render_response: dict[str, Any] | None = None,
) -> ProtocolDeviceAdapter:
    return ProtocolDeviceAdapter(
        transport(
            render_response=render_response
        )
    )


def plan() -> RenderingPlan:
    return RenderingPlan(
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


def test_protocol_adapter_satisfies_device_adapter() -> None:
    target = adapter()

    assert isinstance(
        target,
        DeviceAdapter,
    )

    assert (
        require_device_adapter(
            target
        )
        is target
    )


def test_protocol_adapter_does_not_require_explicit_inheritance() -> None:
    assert DeviceAdapter not in (
        ProtocolDeviceAdapter.__bases__
    )


def test_initialization_performs_hello_and_capabilities_exchange() -> None:
    memory = transport()

    target = ProtocolDeviceAdapter(
        memory
    )

    assert target.device_id == DEVICE_ID

    assert len(
        memory.messages
    ) == 2

    hello = loads_message(
        memory.messages[0]
    )

    capabilities_request = loads_message(
        memory.messages[1]
    )

    assert hello == {
        "protocol_version": "0.1",
        "type": "hello",
    }

    assert capabilities_request == {
        "protocol_version": "0.1",
        "type": "get_capabilities",
    }


def test_adapter_exposes_remote_capabilities() -> None:
    target = adapter()

    assert target.capabilities.device_id == DEVICE_ID
    assert target.capabilities.min_duration == 1.0
    assert target.capabilities.max_duration == 10.0

    assert [
        (
            channel.channel,
            channel.min_intensity,
            channel.max_intensity,
        )
        for channel in target.capabilities.channels
    ] == [
        (0, 0.0, 1.0),
        (2, 0.1, 0.8),
    ]


def test_adapter_exposes_transport() -> None:
    memory = transport()

    target = ProtocolDeviceAdapter(
        memory
    )

    assert target.transport is memory


def test_adapter_render_sends_protocol_message() -> None:
    memory = transport(
        render_response=ok_response()
    )

    target = ProtocolDeviceAdapter(
        memory
    )

    response = target.render(
        plan()
    )

    assert response == {
        "protocol_version": "0.1",
        "type": "ok",
    }

    assert len(
        memory.messages
    ) == 3

    render_message = loads_message(
        memory.messages[2]
    )

    assert render_message == {
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


def test_adapter_accepts_empty_supported_plan() -> None:
    memory = transport(
        render_response=ok_response()
    )

    target = ProtocolDeviceAdapter(
        memory
    )

    response = target.render(
        RenderingPlan(
            commands=[],
            duration=2.0,
        )
    )

    assert response["type"] == "ok"

    message = loads_message(
        memory.messages[2]
    )

    assert message["commands"] == []


def test_adapter_rejects_unsupported_channel_before_transport() -> None:
    memory = transport(
        render_response=ok_response()
    )

    target = ProtocolDeviceAdapter(
        memory
    )

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
        target.render(
            invalid_plan
        )

    assert len(
        memory.messages
    ) == 2

    assert memory.remaining_responses == [
        dumps_message(
            ok_response()
        )
    ]


def test_adapter_rejects_unsupported_intensity_before_transport() -> None:
    memory = transport(
        render_response=ok_response()
    )

    target = ProtocolDeviceAdapter(
        memory
    )

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
        target.render(
            invalid_plan
        )

    assert len(
        memory.messages
    ) == 2


def test_adapter_rejects_unsupported_duration_before_transport() -> None:
    memory = transport(
        render_response=ok_response()
    )

    target = ProtocolDeviceAdapter(
        memory
    )

    invalid_plan = RenderingPlan(
        commands=[],
        duration=20.0,
    )

    with pytest.raises(
        ValueError,
    ):
        target.render(
            invalid_plan
        )

    assert len(
        memory.messages
    ) == 2


def test_adapter_rejects_non_rendering_plan() -> None:
    target = adapter()

    with pytest.raises(
        TypeError,
        match="plan must be a RenderingPlan",
    ):
        target.render(
            {}
        )


def test_adapter_propagates_device_error() -> None:
    memory = transport(
        render_response=error_response(
            "render_failed",
            "device rejected rendering request",
        )
    )

    target = ProtocolDeviceAdapter(
        memory
    )

    with pytest.raises(
        ValueError,
        match="render_failed",
    ):
        target.render(
            plan()
        )

    assert len(
        memory.messages
    ) == 3


def test_adapter_rejects_hello_capability_identity_mismatch() -> None:
    mismatched_capabilities = DeviceCapabilities(
        device_id="different-device",
        channels=[
            DeviceChannelCapability(
                channel=0,
            )
        ],
        min_duration=1.0,
        max_duration=10.0,
    )

    memory = MemoryDeviceTransport(
        responses=[
            dumps_message(
                hello_response(
                    DEVICE_ID
                )
            ),
            dumps_message(
                capabilities_response(
                    mismatched_capabilities
                )
            ),
        ]
    )

    with pytest.raises(
        ValueError,
        match="device identity mismatch",
    ):
        ProtocolDeviceAdapter(
            memory
        )


def test_adapter_rejects_invalid_hello_response() -> None:
    memory = MemoryDeviceTransport(
        responses=[
            dumps_message(
                ok_response()
            ),
            dumps_message(
                capabilities_response(
                    capabilities()
                )
            ),
        ]
    )

    with pytest.raises(
        ValueError,
    ):
        ProtocolDeviceAdapter(
            memory
        )


def test_adapter_rejects_invalid_capabilities_response() -> None:
    memory = MemoryDeviceTransport(
        responses=[
            dumps_message(
                hello_response(
                    DEVICE_ID
                )
            ),
            dumps_message(
                ok_response()
            ),
        ]
    )

    with pytest.raises(
        ValueError,
    ):
        ProtocolDeviceAdapter(
            memory
        )


def test_adapter_rejects_invalid_json_response() -> None:
    memory = MemoryDeviceTransport(
        responses=[
            "{not-json}",
        ]
    )

    with pytest.raises(
        ValueError,
    ):
        ProtocolDeviceAdapter(
            memory
        )


def test_adapter_rejects_transport_without_enough_responses() -> None:
    memory = MemoryDeviceTransport(
        responses=[
            dumps_message(
                hello_response(
                    DEVICE_ID
                )
            ),
        ]
    )

    with pytest.raises(
        RuntimeError,
        match="no configured response",
    ):
        ProtocolDeviceAdapter(
            memory
        )


def test_adapter_rejects_invalid_transport() -> None:
    with pytest.raises(
        TypeError,
        match="DeviceTransport protocol",
    ):
        ProtocolDeviceAdapter(
            object()
        )


def test_multiple_render_requests_use_same_discovered_capabilities() -> None:
    memory = MemoryDeviceTransport(
        responses=[
            dumps_message(
                hello_response(
                    DEVICE_ID
                )
            ),
            dumps_message(
                capabilities_response(
                    capabilities()
                )
            ),
            dumps_message(
                ok_response()
            ),
            dumps_message(
                ok_response()
            ),
        ]
    )

    target = ProtocolDeviceAdapter(
        memory
    )

    first = target.render(
        RenderingPlan(
            commands=[
                DeviceCommand(
                    channel=0,
                    intensity=0.2,
                )
            ],
            duration=2.0,
        )
    )

    second = target.render(
        RenderingPlan(
            commands=[
                DeviceCommand(
                    channel=2,
                    intensity=0.5,
                )
            ],
            duration=3.0,
        )
    )

    assert first["type"] == "ok"
    assert second["type"] == "ok"

    assert len(
        memory.messages
    ) == 4

    assert target.capabilities.device_id == DEVICE_ID


def test_protocol_adapter_can_be_used_through_device_adapter_contract() -> None:
    target = adapter(
        render_response=ok_response()
    )

    device: DeviceAdapter = require_device_adapter(
        target
    )

    result = device.render(
        plan()
    )

    assert result == {
        "protocol_version": "0.1",
        "type": "ok",
    }