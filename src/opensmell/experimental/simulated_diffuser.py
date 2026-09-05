"""Experimental simulated diffuser for OpenSmell rendering.

This module provides a deterministic in-memory device adapter used to exercise
the experimental rendering pipeline without physical olfactory hardware.

The simulated diffuser does not sleep for the requested rendering duration and
does not attempt to reproduce an odor. It records immutable snapshots of the
RenderingPlan values it receives.

This module is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .rendering import DeviceCommand, RenderingPlan


@dataclass(frozen=True)
class SimulatedRenderEvent:
    """Immutable snapshot of one simulated rendering operation."""

    commands: tuple[DeviceCommand, ...]
    duration: float
    extra: dict[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.commands, tuple):
            raise TypeError(
                "SimulatedRenderEvent.commands must be a tuple"
            )

        for command in self.commands:
            if not isinstance(command, DeviceCommand):
                raise TypeError(
                    "SimulatedRenderEvent.commands must contain "
                    "DeviceCommand values"
                )

        if isinstance(self.duration, bool) or not isinstance(
            self.duration,
            (int, float),
        ):
            raise TypeError(
                "SimulatedRenderEvent.duration must be a number"
            )

        if not isinstance(self.extra, dict):
            raise TypeError(
                "SimulatedRenderEvent.extra must be a dict"
            )

        object.__setattr__(
            self,
            "duration",
            float(self.duration),
        )
        object.__setattr__(
            self,
            "extra",
            dict(self.extra),
        )


class SimulatedDiffuser:
    """In-memory rendering target for tests and demonstrations.

    ``render`` records a snapshot immediately. It performs no real-time wait,
    hardware I/O, cartridge lookup, odor mapping, or physical diffusion.
    """

    def __init__(self) -> None:
        self._events: list[SimulatedRenderEvent] = []

    @property
    def events(self) -> list[SimulatedRenderEvent]:
        """Return a copy of the recorded event list."""

        return list(self._events)

    @property
    def last_event(self) -> SimulatedRenderEvent | None:
        """Return the most recently recorded event, if any."""

        if not self._events:
            return None

        return self._events[-1]

    def render(
        self,
        plan: RenderingPlan,
    ) -> SimulatedRenderEvent:
        """Record one RenderingPlan and return the recorded event."""

        if not isinstance(plan, RenderingPlan):
            raise TypeError(
                "plan must be a RenderingPlan"
            )

        event = SimulatedRenderEvent(
            commands=tuple(plan.commands),
            duration=plan.duration,
            extra=dict(plan.extra),
        )

        self._events.append(event)

        return event

    def clear(self) -> None:
        """Remove all recorded simulated rendering events."""

        self._events.clear()
