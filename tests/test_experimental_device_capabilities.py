"""Tests for experimental OpenSmell device capabilities."""

from __future__ import annotations

import math

import pytest

from opensmell.experimental.device_capabilities import (
    DeviceCapabilities,
    DeviceChannelCapability,
)
from opensmell.experimental.rendering import (
    DeviceCommand,
    RenderingPlan,
)


def _capabilities() -> DeviceCapabilities:
    return DeviceCapabilities(
        device_id="example-device",
        channels=[
            DeviceChannelCapability(
                channel=0,
            ),
            DeviceChannelCapability(
                channel=1,
                min_intensity=0.2,
                max_intensity=0.8,
            ),
            DeviceChannelCapability(
                channel=4,
                min_intensity=0.4,
                max_intensity=0.9,
            ),
        ],
        min_duration=1.0,
        max_duration=30.0,
        extra={
            "manufacturer": "Example",
        },
    )


def test_channel_capability_defaults() -> None:
    capability = DeviceChannelCapability(
        channel=3,
    )

    assert capability.channel == 3
    assert capability.min_intensity == 0.0
    assert capability.max_intensity == 1.0
    assert capability.extra == {}


@pytest.mark.parametrize(
    "channel",
    [
        -1,
        -100,
    ],
)
def test_channel_capability_rejects_negative_channel(
    channel: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be non-negative",
    ):
        DeviceChannelCapability(
            channel=channel,
        )


@pytest.mark.parametrize(
    "channel",
    [
        True,
        False,
        1.5,
        "1",
        None,
    ],
)
def test_channel_capability_rejects_non_integer_channel(
    channel: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="must be an integer",
    ):
        DeviceChannelCapability(
            channel=channel,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [
        (-0.1, 1.0),
        (0.0, 1.1),
        (-1.0, 2.0),
    ],
)
def test_channel_capability_rejects_intensity_outside_unit_interval(
    minimum: float,
    maximum: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be between 0.0 and 1.0",
    ):
        DeviceChannelCapability(
            channel=1,
            min_intensity=minimum,
            max_intensity=maximum,
        )


@pytest.mark.parametrize(
    "value",
    [
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_channel_capability_rejects_non_finite_intensity(
    value: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be finite",
    ):
        DeviceChannelCapability(
            channel=1,
            min_intensity=value,
        )


def test_channel_capability_rejects_reversed_intensity_range() -> None:
    with pytest.raises(
        ValueError,
        match="must not exceed",
    ):
        DeviceChannelCapability(
            channel=1,
            min_intensity=0.8,
            max_intensity=0.2,
        )


def test_channel_capability_accepts_matching_command() -> None:
    capability = DeviceChannelCapability(
        channel=2,
        min_intensity=0.2,
        max_intensity=0.8,
    )

    assert capability.accepts(
        DeviceCommand(
            channel=2,
            intensity=0.5,
        )
    )


@pytest.mark.parametrize(
    "intensity",
    [
        0.2,
        0.8,
    ],
)
def test_channel_capability_accepts_intensity_boundaries(
    intensity: float,
) -> None:
    capability = DeviceChannelCapability(
        channel=2,
        min_intensity=0.2,
        max_intensity=0.8,
    )

    assert capability.accepts(
        DeviceCommand(
            channel=2,
            intensity=intensity,
        )
    )


def test_channel_capability_rejects_other_channel() -> None:
    capability = DeviceChannelCapability(
        channel=2,
    )

    assert not capability.accepts(
        DeviceCommand(
            channel=3,
            intensity=0.5,
        )
    )


def test_channel_capability_rejects_intensity_outside_range() -> None:
    capability = DeviceChannelCapability(
        channel=2,
        min_intensity=0.2,
        max_intensity=0.8,
    )

    assert not capability.accepts(
        DeviceCommand(
            channel=2,
            intensity=0.9,
        )
    )


def test_channel_capability_accepts_requires_device_command() -> None:
    capability = DeviceChannelCapability(
        channel=2,
    )

    with pytest.raises(
        TypeError,
        match="command must be a DeviceCommand",
    ):
        capability.accepts(
            object()  # type: ignore[arg-type]
        )


def test_device_capabilities_preserves_configuration() -> None:
    capabilities = _capabilities()

    assert capabilities.device_id == "example-device"

    assert [
        capability.channel
        for capability in capabilities.channels
    ] == [
        0,
        1,
        4,
    ]

    assert capabilities.min_duration == 1.0
    assert capabilities.max_duration == 30.0

    assert capabilities.extra == {
        "manufacturer": "Example",
    }


def test_device_capabilities_copies_input_lists_and_extra() -> None:
    channels = [
        DeviceChannelCapability(
            channel=1,
        )
    ]

    extra = {
        "profile": "test",
    }

    capabilities = DeviceCapabilities(
        device_id="example-device",
        channels=channels,
        min_duration=1.0,
        max_duration=10.0,
        extra=extra,
    )

    channels.append(
        DeviceChannelCapability(
            channel=2,
        )
    )

    extra["changed"] = True

    assert [
        capability.channel
        for capability in capabilities.channels
    ] == [
        1,
    ]

    assert capabilities.extra == {
        "profile": "test",
    }


@pytest.mark.parametrize(
    "device_id",
    [
        "",
    ],
)
def test_device_capabilities_rejects_empty_device_id(
    device_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be non-empty",
    ):
        DeviceCapabilities(
            device_id=device_id,
            channels=[],
            min_duration=1.0,
            max_duration=10.0,
        )


@pytest.mark.parametrize(
    "device_id",
    [
        None,
        123,
        True,
    ],
)
def test_device_capabilities_rejects_non_string_device_id(
    device_id: object,
) -> None:
    with pytest.raises(
        TypeError,
        match="must be a string",
    ):
        DeviceCapabilities(
            device_id=device_id,  # type: ignore[arg-type]
            channels=[],
            min_duration=1.0,
            max_duration=10.0,
        )


def test_device_capabilities_rejects_non_list_channels() -> None:
    with pytest.raises(
        TypeError,
        match="channels must be a list",
    ):
        DeviceCapabilities(
            device_id="example-device",
            channels=(),  # type: ignore[arg-type]
            min_duration=1.0,
            max_duration=10.0,
        )


def test_device_capabilities_rejects_invalid_channel_entry() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "channels must contain "
            "DeviceChannelCapability values"
        ),
    ):
        DeviceCapabilities(
            device_id="example-device",
            channels=[
                object(),  # type: ignore[list-item]
            ],
            min_duration=1.0,
            max_duration=10.0,
        )


def test_device_capabilities_rejects_duplicate_channels() -> None:
    with pytest.raises(
        ValueError,
        match="duplicate device channel capability",
    ):
        DeviceCapabilities(
            device_id="example-device",
            channels=[
                DeviceChannelCapability(
                    channel=1,
                ),
                DeviceChannelCapability(
                    channel=1,
                ),
            ],
            min_duration=1.0,
            max_duration=10.0,
        )


@pytest.mark.parametrize(
    "duration",
    [
        0.0,
        -1.0,
    ],
)
def test_device_capabilities_rejects_non_positive_duration(
    duration: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be greater than zero",
    ):
        DeviceCapabilities(
            device_id="example-device",
            channels=[],
            min_duration=duration,
            max_duration=10.0,
        )


@pytest.mark.parametrize(
    "duration",
    [
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_device_capabilities_rejects_non_finite_duration(
    duration: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be finite",
    ):
        DeviceCapabilities(
            device_id="example-device",
            channels=[],
            min_duration=duration,
            max_duration=10.0,
        )


def test_device_capabilities_rejects_reversed_duration_range() -> None:
    with pytest.raises(
        ValueError,
        match="must not exceed",
    ):
        DeviceCapabilities(
            device_id="example-device",
            channels=[],
            min_duration=10.0,
            max_duration=1.0,
        )


def test_device_capabilities_returns_channel() -> None:
    capabilities = _capabilities()

    capability = capabilities.channel(
        1
    )

    assert capability is not None
    assert capability.channel == 1
    assert capability.min_intensity == 0.2
    assert capability.max_intensity == 0.8


def test_device_capabilities_returns_none_for_unknown_channel() -> None:
    capabilities = _capabilities()

    assert (
        capabilities.channel(
            99
        )
        is None
    )


@pytest.mark.parametrize(
    "duration",
    [
        1.0,
        4.0,
        30.0,
    ],
)
def test_device_capabilities_accepts_supported_duration(
    duration: float,
) -> None:
    capabilities = _capabilities()

    assert capabilities.accepts_duration(
        duration
    )


@pytest.mark.parametrize(
    "duration",
    [
        0.5,
        31.0,
    ],
)
def test_device_capabilities_rejects_unsupported_duration(
    duration: float,
) -> None:
    capabilities = _capabilities()

    assert not capabilities.accepts_duration(
        duration
    )


def test_device_capabilities_accepts_supported_command() -> None:
    capabilities = _capabilities()

    assert capabilities.accepts_command(
        DeviceCommand(
            channel=1,
            intensity=0.5,
        )
    )


def test_device_capabilities_rejects_unknown_channel_command() -> None:
    capabilities = _capabilities()

    assert not capabilities.accepts_command(
        DeviceCommand(
            channel=99,
            intensity=0.5,
        )
    )


def test_device_capabilities_rejects_unsupported_intensity_command() -> None:
    capabilities = _capabilities()

    assert not capabilities.accepts_command(
        DeviceCommand(
            channel=1,
            intensity=0.9,
        )
    )


def test_device_capabilities_accepts_supported_plan() -> None:
    capabilities = _capabilities()

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=1,
                intensity=0.5,
            ),
            DeviceCommand(
                channel=4,
                intensity=0.8,
            ),
        ],
        duration=4.0,
    )

    assert capabilities.accepts_plan(
        plan
    )


def test_device_capabilities_accepts_empty_plan_when_duration_supported() -> None:
    capabilities = _capabilities()

    plan = RenderingPlan(
        commands=[],
        duration=4.0,
    )

    assert capabilities.accepts_plan(
        plan
    )


def test_device_capabilities_rejects_plan_with_unknown_channel() -> None:
    capabilities = _capabilities()

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=7,
                intensity=0.5,
            )
        ],
        duration=4.0,
    )

    assert not capabilities.accepts_plan(
        plan
    )


def test_device_capabilities_rejects_plan_with_unsupported_intensity() -> None:
    capabilities = _capabilities()

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=1,
                intensity=0.9,
            )
        ],
        duration=4.0,
    )

    assert not capabilities.accepts_plan(
        plan
    )


def test_device_capabilities_rejects_plan_with_unsupported_duration() -> None:
    capabilities = _capabilities()

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=1,
                intensity=0.5,
            )
        ],
        duration=60.0,
    )

    assert not capabilities.accepts_plan(
        plan
    )


def test_require_plan_accepts_supported_plan() -> None:
    capabilities = _capabilities()

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=1,
                intensity=0.5,
            )
        ],
        duration=4.0,
    )

    assert (
        capabilities.require_plan(
            plan
        )
        is None
    )


def test_require_plan_reports_unsupported_duration() -> None:
    capabilities = _capabilities()

    plan = RenderingPlan(
        commands=[],
        duration=60.0,
    )

    with pytest.raises(
        ValueError,
        match="rendering duration is not supported",
    ):
        capabilities.require_plan(
            plan
        )


def test_require_plan_reports_unknown_channel() -> None:
    capabilities = _capabilities()

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=99,
                intensity=0.5,
            )
        ],
        duration=4.0,
    )

    with pytest.raises(
        ValueError,
        match="rendering channel is not supported",
    ):
        capabilities.require_plan(
            plan
        )


def test_require_plan_reports_unsupported_intensity() -> None:
    capabilities = _capabilities()

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=1,
                intensity=0.95,
            )
        ],
        duration=4.0,
    )

    with pytest.raises(
        ValueError,
        match="rendering intensity is not supported",
    ):
        capabilities.require_plan(
            plan
        )


@pytest.mark.parametrize(
    "method_name",
    [
        "accepts_plan",
        "require_plan",
    ],
)
def test_plan_methods_require_rendering_plan(
    method_name: str,
) -> None:
    capabilities = _capabilities()

    method = getattr(
        capabilities,
        method_name,
    )

    with pytest.raises(
        TypeError,
        match="plan must be a RenderingPlan",
    ):
        method(
            object()
        )