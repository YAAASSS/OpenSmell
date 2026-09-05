"""Experimental simulated diffuser for OpenSmell rendering.

This module provides a deterministic in-memory device adapter used to exercise
the experimental rendering pipeline without physical olfactory hardware.

The simulated diffuser does not sleep for the requested rendering duration and
does not attempt to reproduce an odor. It records immutable snapshots of the
RenderingPlan values it receives.

A simulated diffuser may optionally expose DeviceCapabilities. When
capabilities are configured, every RenderingPlan is validated against those
capabilities before it is recorded.

This module is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .device_capabilities import (
    DeviceCapabilities,
)
from .rendering import (
    DeviceCommand,
    RenderingPlan,
)


@dataclass(frozen=True)
class SimulatedRenderEvent:
    """Immutable snapshot of one simulated rendering operation."""

    commands: tuple[DeviceCommand, ...]
    duration: float
    extra: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(
            self.commands,
            tuple,
        ):
            raise TypeError(
                "SimulatedRenderEvent.commands must be a tuple"
            )

        for command in self.commands:
            if not isinstance(
                command,
                DeviceCommand,
            ):
                raise TypeError(
                    "SimulatedRenderEvent.commands must contain "
                    "DeviceCommand values"
                )

        if (
            isinstance(
                self.duration,
                bool,
            )
            or not isinstance(
                self.duration,
                (int, float),
            )
        ):
            raise TypeError(
                "SimulatedRenderEvent.duration must be a number"
            )

        if not isinstance(
            self.extra,
            dict,
        ):
            raise TypeError(
                "SimulatedRenderEvent.extra must be a dict"
            )

        object.__setattr__(
            self,
            "duration",
            float(
                self.duration
            ),
        )

        object.__setattr__(
            self,
            "extra",
            dict(
                self.extra
            ),
        )


class SimulatedDiffuser:
    """In-memory rendering target for tests and demonstrations.

    ``render`` records a snapshot immediately. It performs no real-time wait,
    hardware I/O, cartridge lookup, odor mapping, or physical diffusion.

    ``capabilities`` optionally describes the technical constraints accepted
    by this simulated target. When omitted, the diffuser preserves the original
    unconstrained experimental behavior.
    """

    def __init__(
        self,
        capabilities: DeviceCapabilities | None = None,
    ) -> None:
        if (
            capabilities is not None
            and not isinstance(
                capabilities,
                DeviceCapabilities,
            )
        ):
            raise TypeError(
                "capabilities must be a DeviceCapabilities "
                "or None"
            )

        self._capabilities = capabilities
        self._events: list[
            SimulatedRenderEvent
        ] = []

    @property
    def capabilities(
        self,
    ) -> DeviceCapabilities | None:
        """Return the configured device capabilities, if any."""

        return self._capabilities

    @property
    def events(
        self,
    ) -> list[SimulatedRenderEvent]:
        """Return a copy of the recorded event list."""

        return list(
            self._events
        )

    @property
    def last_event(
        self,
    ) -> SimulatedRenderEvent | None:
        """Return the most recently recorded event, if any."""

        if not self._events:
            return None

        return self._events[-1]

    def render(
        self,
        plan: RenderingPlan,
    ) -> SimulatedRenderEvent:
        """Validate and record one RenderingPlan.

        When capabilities are configured, validation happens before any event
        is recorded. An incompatible plan therefore leaves the simulated
        device state unchanged.
        """

        if not isinstance(
            plan,
            RenderingPlan,
        ):
            raise TypeError(
                "plan must be a RenderingPlan"
            )

        if (
            self._capabilities
            is not None
        ):
            self._capabilities.require_plan(
                plan
            )

        event = SimulatedRenderEvent(
            commands=tuple(
                plan.commands
            ),
            duration=plan.duration,
            extra=dict(
                plan.extra
            ),
        )

        self._events.append(
            event
        )

        return event

    def clear(
        self,
    ) -> None:
        """Remove all recorded simulated rendering events."""

        self._events.clear()