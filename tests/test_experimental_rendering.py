"""Tests for experimental OpenSmell rendering primitives.

These tests exercise the first device-independent boundary between an
application render request and device-facing commands.

The rendering primitives do not define odor reproduction, semantic mapping,
diffuser cartridge meaning, hardware transport, or a serialized OpenSmell
rendering format.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from opensmell.experimental.rendering import (
    DeviceCommand,
    RenderingPlan,
    RenderRequest,
)


def test_render_request() -> None:
    request = RenderRequest(
        resource_id="molecule-1",
        duration=3.0,
    )

    assert request.resource_id == "molecule-1"
    assert request.duration == 3.0


@pytest.mark.parametrize(
    "resource_id",
    [
        "",
        None,
        1,
        False,
        [],
        {},
    ],
)
def test_render_request_rejects_invalid_resource_id(
    resource_id: Any,
) -> None:
    with pytest.raises(
        (TypeError, ValueError)
    ):
        RenderRequest(
            resource_id=resource_id,
            duration=3.0,
        )


@pytest.mark.parametrize(
    "duration",
    [
        0,
        0.0,
        -1,
        -0.1,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_render_request_rejects_invalid_duration_value(
    duration: float,
) -> None:
    with pytest.raises(ValueError):
        RenderRequest(
            resource_id="molecule-1",
            duration=duration,
        )


@pytest.mark.parametrize(
    "duration",
    [
        None,
        "3",
        False,
        [],
        {},
    ],
)
def test_render_request_rejects_invalid_duration_type(
    duration: Any,
) -> None:
    with pytest.raises(TypeError):
        RenderRequest(
            resource_id="molecule-1",
            duration=duration,
        )


def test_render_request_normalizes_integer_duration() -> None:
    request = RenderRequest(
        resource_id="molecule-1",
        duration=3,
    )

    assert request.duration == 3.0
    assert isinstance(
        request.duration,
        float,
    )


def test_device_command() -> None:
    command = DeviceCommand(
        channel=2,
        intensity=0.65,
    )

    assert command.channel == 2
    assert command.intensity == 0.65


@pytest.mark.parametrize(
    "channel",
    [
        -1,
        -10,
    ],
)
def test_device_command_rejects_negative_channel(
    channel: int,
) -> None:
    with pytest.raises(ValueError):
        DeviceCommand(
            channel=channel,
            intensity=0.5,
        )


@pytest.mark.parametrize(
    "channel",
    [
        None,
        1.5,
        "1",
        False,
        [],
        {},
    ],
)
def test_device_command_rejects_invalid_channel_type(
    channel: Any,
) -> None:
    with pytest.raises(TypeError):
        DeviceCommand(
            channel=channel,
            intensity=0.5,
        )


@pytest.mark.parametrize(
    "intensity",
    [
        -0.1,
        1.1,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_device_command_rejects_invalid_intensity_value(
    intensity: float,
) -> None:
    with pytest.raises(ValueError):
        DeviceCommand(
            channel=1,
            intensity=intensity,
        )


@pytest.mark.parametrize(
    "intensity",
    [
        None,
        "0.5",
        False,
        [],
        {},
    ],
)
def test_device_command_rejects_invalid_intensity_type(
    intensity: Any,
) -> None:
    with pytest.raises(TypeError):
        DeviceCommand(
            channel=1,
            intensity=intensity,
        )


@pytest.mark.parametrize(
    "intensity",
    [
        0.0,
        1.0,
    ],
)
def test_device_command_accepts_intensity_boundaries(
    intensity: float,
) -> None:
    command = DeviceCommand(
        channel=1,
        intensity=intensity,
    )

    assert command.intensity == intensity


def test_device_command_normalizes_integer_intensity() -> None:
    command = DeviceCommand(
        channel=1,
        intensity=1,
    )

    assert command.intensity == 1.0
    assert isinstance(
        command.intensity,
        float,
    )


def test_rendering_plan() -> None:
    commands = [
        DeviceCommand(
            channel=2,
            intensity=0.65,
        ),
        DeviceCommand(
            channel=5,
            intensity=0.20,
        ),
        DeviceCommand(
            channel=7,
            intensity=0.15,
        ),
    ]

    plan = RenderingPlan(
        commands=commands,
        duration=3.0,
    )

    assert plan.commands == commands
    assert plan.duration == 3.0
    assert plan.extra == {}


def test_rendering_plan_accepts_empty_commands() -> None:
    plan = RenderingPlan(
        commands=[],
        duration=1.0,
    )

    assert plan.commands == []


def test_rendering_plan_rejects_non_list_commands() -> None:
    with pytest.raises(TypeError):
        RenderingPlan(
            commands=(
                DeviceCommand(
                    channel=1,
                    intensity=0.5,
                ),
            ),
            duration=1.0,
        )


def test_rendering_plan_rejects_invalid_command_item() -> None:
    with pytest.raises(TypeError):
        RenderingPlan(
            commands=[
                {
                    "channel": 1,
                    "intensity": 0.5,
                },
            ],
            duration=1.0,
        )


@pytest.mark.parametrize(
    "duration",
    [
        0,
        -1,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_rendering_plan_rejects_invalid_duration_value(
    duration: float,
) -> None:
    with pytest.raises(ValueError):
        RenderingPlan(
            commands=[],
            duration=duration,
        )


@pytest.mark.parametrize(
    "duration",
    [
        None,
        "1",
        False,
        [],
        {},
    ],
)
def test_rendering_plan_rejects_invalid_duration_type(
    duration: Any,
) -> None:
    with pytest.raises(TypeError):
        RenderingPlan(
            commands=[],
            duration=duration,
        )


def test_rendering_plan_rejects_non_dict_extra() -> None:
    with pytest.raises(TypeError):
        RenderingPlan(
            commands=[],
            duration=1.0,
            extra=[],
        )


def test_rendering_plan_copies_commands_list() -> None:
    commands = [
        DeviceCommand(
            channel=1,
            intensity=0.5,
        ),
    ]

    plan = RenderingPlan(
        commands=commands,
        duration=1.0,
    )

    commands.append(
        DeviceCommand(
            channel=2,
            intensity=0.25,
        )
    )

    assert plan.commands == [
        DeviceCommand(
            channel=1,
            intensity=0.5,
        ),
    ]


def test_rendering_plan_copies_extra_dict() -> None:
    extra = {
        "mapper": "example",
    }

    plan = RenderingPlan(
        commands=[],
        duration=1.0,
        extra=extra,
    )

    extra["mapper"] = "changed"

    assert plan.extra == {
        "mapper": "example",
    }


def test_rendering_primitives_are_not_graph_resources() -> None:
    request = RenderRequest(
        resource_id="molecule-1",
        duration=1.0,
    )
    command = DeviceCommand(
        channel=1,
        intensity=0.5,
    )
    plan = RenderingPlan(
        commands=[command],
        duration=1.0,
    )

    for value in (
        request,
        command,
        plan,
    ):
        assert not hasattr(
            value,
            "id",
        )
        assert not hasattr(
            value,
            "type",
        )
        assert not hasattr(
            value,
            "type_version",
        )
