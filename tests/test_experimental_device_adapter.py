"""Tests for the experimental DeviceAdapter contract.

The DeviceAdapter protocol defines the minimal structural boundary between
OpenSmell RenderingPlan objects and rendering targets.

These tests distinguish structural Protocol compatibility from semantic
runtime adapter validation.

They do not define physical odor reproduction, transport protocols, hardware
lifecycle, or universal channel semantics.

This module is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from opensmell.experimental.device_adapter import (
    DeviceAdapter,
    require_device_adapter,
)
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
)


def capabilities() -> DeviceCapabilities:
    return DeviceCapabilities(
        device_id="adapter-test-device",
        channels=[
            DeviceChannelCapability(
                channel=1,
                min_intensity=0.0,
                max_intensity=0.8,
            ),
            DeviceChannelCapability(
                channel=2,
                min_intensity=0.0,
                max_intensity=0.6,
            ),
        ],
        min_duration=1.0,
        max_duration=5.0,
    )


@dataclass(frozen=True)
class RenderReceipt:
    command_count: int
    duration: float


class ExampleDeviceAdapter:
    """Independent implementation that does not inherit DeviceAdapter."""

    def __init__(
        self,
        device_capabilities: DeviceCapabilities,
    ) -> None:
        self._capabilities = device_capabilities
        self._plans: list[RenderingPlan] = []

    @property
    def capabilities(self) -> DeviceCapabilities:
        return self._capabilities

    @property
    def plans(self) -> list[RenderingPlan]:
        return list(self._plans)

    def render(
        self,
        plan: RenderingPlan,
    ) -> RenderReceipt:
        if not isinstance(
            plan,
            RenderingPlan,
        ):
            raise TypeError(
                "plan must be a RenderingPlan"
            )

        self._capabilities.require_plan(
            plan
        )

        self._plans.append(
            plan
        )

        return RenderReceipt(
            command_count=len(
                plan.commands
            ),
            duration=plan.duration,
        )


class MissingCapabilities:
    def render(
        self,
        plan: RenderingPlan,
    ) -> None:
        return None


class MissingRender:
    @property
    def capabilities(self) -> DeviceCapabilities:
        return capabilities()


class NoneCapabilities:
    @property
    def capabilities(self) -> None:
        return None

    def render(
        self,
        plan: RenderingPlan,
    ) -> None:
        return None


class WrongCapabilities:
    @property
    def capabilities(self) -> str:
        return "not-capabilities"

    def render(
        self,
        plan: RenderingPlan,
    ) -> None:
        return None


class NonCallableRender:
    def __init__(self) -> None:
        self.capabilities = capabilities()
        self.render = "not-callable"


def compatible_plan() -> RenderingPlan:
    return RenderingPlan(
        commands=[
            DeviceCommand(
                channel=1,
                intensity=0.7,
            ),
            DeviceCommand(
                channel=2,
                intensity=0.5,
            ),
        ],
        duration=3.0,
    )


def test_independent_implementation_satisfies_device_adapter() -> None:
    adapter = ExampleDeviceAdapter(
        capabilities()
    )

    assert isinstance(
        adapter,
        DeviceAdapter,
    )


def test_protocol_does_not_require_explicit_inheritance() -> None:
    assert DeviceAdapter not in (
        ExampleDeviceAdapter.__bases__
    )

    adapter = ExampleDeviceAdapter(
        capabilities()
    )

    assert isinstance(
        adapter,
        DeviceAdapter,
    )


def test_adapter_exposes_device_capabilities() -> None:
    target_capabilities = capabilities()

    adapter = ExampleDeviceAdapter(
        target_capabilities
    )

    assert (
        adapter.capabilities
        is target_capabilities
    )


def test_adapter_accepts_compatible_rendering_plan() -> None:
    adapter = ExampleDeviceAdapter(
        capabilities()
    )

    plan = compatible_plan()

    receipt = adapter.render(
        plan
    )

    assert receipt == RenderReceipt(
        command_count=2,
        duration=3.0,
    )

    assert adapter.plans == [
        plan
    ]


def test_adapter_rejects_unsupported_channel() -> None:
    adapter = ExampleDeviceAdapter(
        capabilities()
    )

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=9,
                intensity=0.5,
            ),
        ],
        duration=3.0,
    )

    with pytest.raises(
        ValueError,
    ):
        adapter.render(
            plan
        )

    assert adapter.plans == []


def test_adapter_rejects_unsupported_intensity() -> None:
    adapter = ExampleDeviceAdapter(
        capabilities()
    )

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=1,
                intensity=0.9,
            ),
        ],
        duration=3.0,
    )

    with pytest.raises(
        ValueError,
    ):
        adapter.render(
            plan
        )

    assert adapter.plans == []


def test_adapter_rejects_unsupported_duration() -> None:
    adapter = ExampleDeviceAdapter(
        capabilities()
    )

    plan = RenderingPlan(
        commands=[
            DeviceCommand(
                channel=1,
                intensity=0.5,
            ),
        ],
        duration=10.0,
    )

    with pytest.raises(
        ValueError,
    ):
        adapter.render(
            plan
        )

    assert adapter.plans == []


def test_missing_capabilities_does_not_satisfy_protocol() -> None:
    adapter = MissingCapabilities()

    assert not isinstance(
        adapter,
        DeviceAdapter,
    )


def test_missing_render_does_not_satisfy_protocol() -> None:
    adapter = MissingRender()

    assert not isinstance(
        adapter,
        DeviceAdapter,
    )


def test_empty_plan_can_be_rendered_when_duration_is_supported() -> None:
    adapter = ExampleDeviceAdapter(
        capabilities()
    )

    plan = RenderingPlan(
        commands=[],
        duration=2.0,
    )

    receipt = adapter.render(
        plan
    )

    assert receipt == RenderReceipt(
        command_count=0,
        duration=2.0,
    )


def test_protocol_does_not_constrain_render_return_type() -> None:
    adapter: DeviceAdapter = ExampleDeviceAdapter(
        capabilities()
    )

    result = adapter.render(
        compatible_plan()
    )

    assert isinstance(
        result,
        RenderReceipt,
    )


def test_require_device_adapter_accepts_valid_adapter() -> None:
    adapter = ExampleDeviceAdapter(
        capabilities()
    )

    result = require_device_adapter(
        adapter
    )

    assert result is adapter


def test_require_device_adapter_rejects_missing_capabilities() -> None:
    with pytest.raises(
        TypeError,
        match="DeviceAdapter protocol",
    ):
        require_device_adapter(
            MissingCapabilities()
        )


def test_require_device_adapter_rejects_missing_render() -> None:
    with pytest.raises(
        TypeError,
        match="DeviceAdapter protocol",
    ):
        require_device_adapter(
            MissingRender()
        )


def test_protocol_check_does_not_validate_capabilities_value() -> None:
    adapter = NoneCapabilities()

    assert isinstance(
        adapter,
        DeviceAdapter,
    )

    with pytest.raises(
        TypeError,
        match=(
            "adapter.capabilities must be "
            "a DeviceCapabilities"
        ),
    ):
        require_device_adapter(
            adapter
        )


def test_require_device_adapter_rejects_wrong_capabilities_type() -> None:
    adapter = WrongCapabilities()

    assert isinstance(
        adapter,
        DeviceAdapter,
    )

    with pytest.raises(
        TypeError,
        match=(
            "adapter.capabilities must be "
            "a DeviceCapabilities"
        ),
    ):
        require_device_adapter(
            adapter
        )


def test_require_device_adapter_rejects_non_callable_render() -> None:
    adapter = NonCallableRender()

    with pytest.raises(
        TypeError,
    ):
        require_device_adapter(
            adapter
        )


def test_capability_aware_simulated_diffuser_is_valid_adapter() -> None:
    target_capabilities = capabilities()

    diffuser = SimulatedDiffuser(
        capabilities=target_capabilities,
    )

    assert isinstance(
        diffuser,
        DeviceAdapter,
    )

    assert (
        require_device_adapter(
            diffuser
        )
        is diffuser
    )


def test_capability_aware_simulated_diffuser_renders_through_adapter_contract() -> None:
    diffuser = SimulatedDiffuser(
        capabilities=capabilities(),
    )

    adapter = require_device_adapter(
        diffuser
    )

    event = adapter.render(
        compatible_plan()
    )

    assert event.duration == 3.0

    assert [
        (
            command.channel,
            command.intensity,
        )
        for command in event.commands
    ] == [
        (1, 0.7),
        (2, 0.5),
    ]


def test_legacy_unconstrained_simulated_diffuser_is_only_structurally_compatible() -> None:
    diffuser = SimulatedDiffuser()

    assert isinstance(
        diffuser,
        DeviceAdapter,
    )

    assert diffuser.capabilities is None

    with pytest.raises(
        TypeError,
        match=(
            "adapter.capabilities must be "
            "a DeviceCapabilities"
        ),
    ):
        require_device_adapter(
            diffuser
        )