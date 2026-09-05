"""Tests for the experimental OpenSmell simulated diffuser.

The simulated diffuser is a deterministic in-memory device adapter. It records
RenderingPlan snapshots without sleeping, performing hardware I/O, mapping odor
information, or attempting physical odor reproduction.

A diffuser may optionally expose DeviceCapabilities. When capabilities are
configured, incompatible RenderingPlans must be rejected before any event is
recorded.
"""

from __future__ import annotations

from typing import Any

import pytest

from opensmell.experimental.device_capabilities import (
    DeviceCapabilities,
    DeviceChannelCapability,
)
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


def make_capabilities() -> DeviceCapabilities:
    return DeviceCapabilities(
        device_id="simulated-diffuser",
        channels=[
            DeviceChannelCapability(
                channel=2,
                min_intensity=0.1,
                max_intensity=0.8,
            ),
            DeviceChannelCapability(
                channel=5,
                min_intensity=0.0,
                max_intensity=0.5,
            ),
            DeviceChannelCapability(
                channel=7,
                min_intensity=0.1,
                max_intensity=0.4,
            ),
        ],
        min_duration=1.0,
        max_duration=10.0,
        extra={
            "adapter": "simulation",
        },
    )


def test_simulated_diffuser_starts_empty() -> None:
    diffuser = SimulatedDiffuser()

    assert diffuser.events == []
    assert diffuser.last_event is None


def test_simulated_diffuser_defaults_to_no_capabilities() -> None:
    diffuser = SimulatedDiffuser()

    assert diffuser.capabilities is None


def test_simulated_diffuser_exposes_capabilities() -> None:
    capabilities = make_capabilities()

    diffuser = SimulatedDiffuser(
        capabilities=capabilities,
    )

    assert diffuser.capabilities is capabilities


@pytest.mark.parametrize(
    "value",
    [
        "capabilities",
        1,
        False,
        [],
        {},
        object(),
    ],
)
def test_simulated_diffuser_rejects_invalid_capabilities(
    value: Any,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "capabilities must be a "
            "DeviceCapabilities or None"
        ),
    ):
        SimulatedDiffuser(
            capabilities=value,
        )


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

    with pytest.raises(
        TypeError,
        match="plan must be a RenderingPlan",
    ):
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
    def fail_if_called(
        *args: Any,
        **kwargs: Any,
    ) -> None:
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


def test_capability_aware_diffuser_accepts_supported_plan() -> None:
    diffuser = SimulatedDiffuser(
        capabilities=make_capabilities(),
    )

    plan = make_plan()

    event = diffuser.render(
        plan
    )

    assert event.commands == tuple(
        plan.commands
    )
    assert event.duration == 3.0
    assert diffuser.events == [event]
    assert diffuser.last_event is event


def test_capability_aware_diffuser_accepts_empty_supported_plan() -> None:
    diffuser = SimulatedDiffuser(
        capabilities=make_capabilities(),
    )

    event = diffuser.render(
        RenderingPlan(
            commands=[],
            duration=3.0,
        )
    )

    assert event.commands == ()
    assert event.duration == 3.0
    assert diffuser.events == [event]


def test_capability_aware_diffuser_rejects_unknown_channel() -> None:
    diffuser = SimulatedDiffuser(
        capabilities=make_capabilities(),
    )

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=99,
                intensity=0.5,
            ),
        ],
        duration=3.0,
    )

    with pytest.raises(
        ValueError,
        match="rendering channel is not supported",
    ):
        diffuser.render(
            plan
        )

    assert diffuser.events == []
    assert diffuser.last_event is None


def test_capability_aware_diffuser_rejects_unsupported_intensity() -> None:
    diffuser = SimulatedDiffuser(
        capabilities=make_capabilities(),
    )

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=2,
                intensity=0.95,
            ),
        ],
        duration=3.0,
    )

    with pytest.raises(
        ValueError,
        match="rendering intensity is not supported",
    ):
        diffuser.render(
            plan
        )

    assert diffuser.events == []
    assert diffuser.last_event is None


def test_capability_aware_diffuser_rejects_short_duration() -> None:
    diffuser = SimulatedDiffuser(
        capabilities=make_capabilities(),
    )

    plan = RenderingPlan(
        commands=[],
        duration=0.5,
    )

    with pytest.raises(
        ValueError,
        match="rendering duration is not supported",
    ):
        diffuser.render(
            plan
        )

    assert diffuser.events == []
    assert diffuser.last_event is None


def test_capability_aware_diffuser_rejects_long_duration() -> None:
    diffuser = SimulatedDiffuser(
        capabilities=make_capabilities(),
    )

    plan = RenderingPlan(
        commands=[],
        duration=11.0,
    )

    with pytest.raises(
        ValueError,
        match="rendering duration is not supported",
    ):
        diffuser.render(
            plan
        )

    assert diffuser.events == []
    assert diffuser.last_event is None


def test_rejected_plan_does_not_modify_existing_event_history() -> None:
    diffuser = SimulatedDiffuser(
        capabilities=make_capabilities(),
    )

    accepted_event = diffuser.render(
        make_plan()
    )

    invalid_plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=99,
                intensity=0.5,
            ),
        ],
        duration=3.0,
    )

    with pytest.raises(
        ValueError,
        match="rendering channel is not supported",
    ):
        diffuser.render(
            invalid_plan
        )

    assert diffuser.events == [
        accepted_event,
    ]
    assert diffuser.last_event is accepted_event


def test_unconstrained_diffuser_preserves_legacy_behavior() -> None:
    diffuser = SimulatedDiffuser()

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=999,
                intensity=1.0,
            ),
        ],
        duration=10000.0,
    )

    event = diffuser.render(
        plan
    )

    assert event.commands == (
        DeviceCommand(
            channel=999,
            intensity=1.0,
        ),
    )
    assert event.duration == 10000.0