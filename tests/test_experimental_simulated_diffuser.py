"""Tests for the experimental OpenSmell simulated diffuser.

The simulated diffuser is a deterministic in-memory device adapter. It records
RenderingPlan snapshots without sleeping, performing hardware I/O, mapping odor
information, or attempting physical odor reproduction.
"""

from __future__ import annotations

from typing import Any

import pytest

from opensmell.experimental.rendering import (
    DeviceCommand,
    RenderingPlan,
)
from opensmell.experimental.simulated_diffuser import (
    SimulatedDiffuser,
    SimulatedRenderEvent,
)


def make_plan() -> RenderingPlan:
    return RenderingPlan(
        commands=[
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
        ],
        duration=3.0,
        extra={
            "mapper": "example",
        },
    )


def test_simulated_diffuser_starts_empty() -> None:
    diffuser = SimulatedDiffuser()

    assert diffuser.events == []
    assert diffuser.last_event is None


def test_render_records_event() -> None:
    diffuser = SimulatedDiffuser()
    plan = make_plan()

    event = diffuser.render(plan)

    assert isinstance(
        event,
        SimulatedRenderEvent,
    )
    assert diffuser.events == [event]
    assert diffuser.last_event is event


def test_render_event_contains_plan_values() -> None:
    diffuser = SimulatedDiffuser()

    event = diffuser.render(
        make_plan()
    )

    assert event.commands == (
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
    )
    assert event.duration == 3.0
    assert event.extra == {
        "mapper": "example",
    }


def test_render_records_multiple_events_in_order() -> None:
    diffuser = SimulatedDiffuser()

    first = diffuser.render(
        RenderingPlan(
            commands=[
                DeviceCommand(
                    channel=1,
                    intensity=0.25,
                ),
            ],
            duration=1.0,
        )
    )

    second = diffuser.render(
        RenderingPlan(
            commands=[
                DeviceCommand(
                    channel=3,
                    intensity=0.75,
                ),
            ],
            duration=2.0,
        )
    )

    assert diffuser.events == [
        first,
        second,
    ]
    assert diffuser.last_event is second


@pytest.mark.parametrize(
    "value",
    [
        None,
        "plan",
        1,
        False,
        [],
        {},
    ],
)
def test_render_rejects_non_rendering_plan(
    value: Any,
) -> None:
    diffuser = SimulatedDiffuser()

    with pytest.raises(TypeError):
        diffuser.render(value)


def test_render_does_not_modify_plan() -> None:
    diffuser = SimulatedDiffuser()
    plan = make_plan()

    original_commands = list(
        plan.commands
    )
    original_extra = dict(
        plan.extra
    )

    diffuser.render(plan)

    assert plan.commands == original_commands
    assert plan.extra == original_extra
    assert plan.duration == 3.0


def test_render_event_is_snapshot_of_command_list() -> None:
    diffuser = SimulatedDiffuser()
    plan = make_plan()

    event = diffuser.render(plan)

    plan.commands.append(
        DeviceCommand(
            channel=9,
            intensity=1.0,
        )
    )

    assert len(event.commands) == 3
    assert all(
        command.channel != 9
        for command in event.commands
    )


def test_render_event_is_snapshot_of_extra_dict() -> None:
    diffuser = SimulatedDiffuser()
    plan = make_plan()

    event = diffuser.render(plan)

    plan.extra["mapper"] = "changed"
    plan.extra["new"] = True

    assert event.extra == {
        "mapper": "example",
    }


def test_events_property_returns_list_copy() -> None:
    diffuser = SimulatedDiffuser()
    event = diffuser.render(
        make_plan()
    )

    events = diffuser.events
    events.clear()

    assert diffuser.events == [event]
    assert diffuser.last_event is event


def test_clear_removes_all_events() -> None:
    diffuser = SimulatedDiffuser()

    diffuser.render(
        make_plan()
    )
    diffuser.render(
        RenderingPlan(
            commands=[],
            duration=1.0,
        )
    )

    diffuser.clear()

    assert diffuser.events == []
    assert diffuser.last_event is None


def test_empty_rendering_plan_can_be_recorded() -> None:
    diffuser = SimulatedDiffuser()

    event = diffuser.render(
        RenderingPlan(
            commands=[],
            duration=1.0,
        )
    )

    assert event.commands == ()
    assert event.duration == 1.0


def test_rendering_is_immediate_and_does_not_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(
            "simulated diffuser must not sleep"
        )

    monkeypatch.setattr(
        "time.sleep",
        fail_if_called,
    )

    diffuser = SimulatedDiffuser()

    event = diffuser.render(
        RenderingPlan(
            commands=[
                DeviceCommand(
                    channel=1,
                    intensity=1.0,
                ),
            ],
            duration=3600.0,
        )
    )

    assert event.duration == 3600.0


def test_simulated_event_is_not_graph_resource() -> None:
    event = SimulatedDiffuser().render(
        make_plan()
    )

    assert not hasattr(
        event,
        "id",
    )
    assert not hasattr(
        event,
        "type",
    )
    assert not hasattr(
        event,
        "type_version",
    )
