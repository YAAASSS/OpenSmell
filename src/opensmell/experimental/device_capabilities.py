"""Experimental device capability model for OpenSmell rendering.

This module explores how a rendering target can describe technical constraints
without assigning universal olfactory meaning to device channels.

Device capabilities are deliberately separate from:

- OpenSmell odor representations;
- GenericResourceGraph resources;
- semantic or perceptual mapping policies;
- physical odor reproduction models;
- cartridge chemistry;
- transport protocols and hardware drivers.

A channel number is device-facing and opaque to OpenSmell. A capability only
states what commands a particular rendering target accepts.

This module is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from .rendering import (
    DeviceCommand,
    RenderingPlan,
)


def _require_nonempty_string(
    value: Any,
    name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be a string"
        )

    if not value:
        raise ValueError(
            f"{name} must be non-empty"
        )

    return value


def _require_nonnegative_integer(
    value: Any,
    name: str,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
    ):
        raise TypeError(
            f"{name} must be an integer"
        )

    if value < 0:
        raise ValueError(
            f"{name} must be non-negative"
        )

    return value


def _require_unit_interval(
    value: Any,
    name: str,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise TypeError(
            f"{name} must be a number"
        )

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            f"{name} must be finite"
        )

    if (
        result < 0.0
        or result > 1.0
    ):
        raise ValueError(
            f"{name} must be between 0.0 and 1.0"
        )

    return result


def _require_positive_finite_number(
    value: Any,
    name: str,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise TypeError(
            f"{name} must be a number"
        )

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            f"{name} must be finite"
        )

    if result <= 0.0:
        raise ValueError(
            f"{name} must be greater than zero"
        )

    return result


def _require_dict(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(
        value,
        dict,
    ):
        raise TypeError(
            f"{name} must be a dict"
        )

    return value


@dataclass(frozen=True)
class DeviceChannelCapability:
    """Technical capability of one device-facing output channel.

    ``channel`` is an opaque channel number. OpenSmell assigns no universal
    odor, molecule, cartridge, or perceptual meaning to it.

    ``min_intensity`` and ``max_intensity`` describe the normalized command
    range accepted by this channel.
    """

    channel: int
    min_intensity: float = 0.0
    max_intensity: float = 1.0
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        channel = (
            _require_nonnegative_integer(
                self.channel,
                "DeviceChannelCapability.channel",
            )
        )

        min_intensity = (
            _require_unit_interval(
                self.min_intensity,
                "DeviceChannelCapability.min_intensity",
            )
        )

        max_intensity = (
            _require_unit_interval(
                self.max_intensity,
                "DeviceChannelCapability.max_intensity",
            )
        )

        if (
            min_intensity
            > max_intensity
        ):
            raise ValueError(
                "DeviceChannelCapability.min_intensity "
                "must not exceed max_intensity"
            )

        _require_dict(
            self.extra,
            "DeviceChannelCapability.extra",
        )

        object.__setattr__(
            self,
            "channel",
            channel,
        )

        object.__setattr__(
            self,
            "min_intensity",
            min_intensity,
        )

        object.__setattr__(
            self,
            "max_intensity",
            max_intensity,
        )

        object.__setattr__(
            self,
            "extra",
            dict(self.extra),
        )

    def accepts(
        self,
        command: DeviceCommand,
    ) -> bool:
        """Return whether this channel accepts one DeviceCommand."""

        if not isinstance(
            command,
            DeviceCommand,
        ):
            raise TypeError(
                "command must be a DeviceCommand"
            )

        if (
            command.channel
            != self.channel
        ):
            return False

        return (
            self.min_intensity
            <= command.intensity
            <= self.max_intensity
        )


@dataclass
class DeviceCapabilities:
    """Technical rendering constraints advertised by one device.

    The model intentionally describes only what the rendering target accepts.
    It does not describe what odor a channel represents or how an odor should
    be mapped to channels.

    ``device_id`` identifies the rendering target or capability profile.

    ``channels`` lists the device-facing channels accepted by the target.

    ``min_duration`` and ``max_duration`` describe the accepted rendering
    duration range in seconds.
    """

    device_id: str
    channels: list[DeviceChannelCapability]
    min_duration: float
    max_duration: float
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.device_id,
            "DeviceCapabilities.device_id",
        )

        if not isinstance(
            self.channels,
            list,
        ):
            raise TypeError(
                "DeviceCapabilities.channels must be a list"
            )

        copied_channels: list[
            DeviceChannelCapability
        ] = []

        seen_channels: set[int] = set()

        for capability in self.channels:
            if not isinstance(
                capability,
                DeviceChannelCapability,
            ):
                raise TypeError(
                    "DeviceCapabilities.channels must contain "
                    "DeviceChannelCapability values"
                )

            if (
                capability.channel
                in seen_channels
            ):
                raise ValueError(
                    "duplicate device channel capability: "
                    f"{capability.channel}"
                )

            copied_channels.append(
                capability
            )

            seen_channels.add(
                capability.channel
            )

        min_duration = (
            _require_positive_finite_number(
                self.min_duration,
                "DeviceCapabilities.min_duration",
            )
        )

        max_duration = (
            _require_positive_finite_number(
                self.max_duration,
                "DeviceCapabilities.max_duration",
            )
        )

        if (
            min_duration
            > max_duration
        ):
            raise ValueError(
                "DeviceCapabilities.min_duration "
                "must not exceed max_duration"
            )

        _require_dict(
            self.extra,
            "DeviceCapabilities.extra",
        )

        self.channels = (
            copied_channels
        )

        self.min_duration = (
            min_duration
        )

        self.max_duration = (
            max_duration
        )

        self.extra = dict(
            self.extra
        )

        self._channels_by_id = {
            capability.channel: capability
            for capability
            in copied_channels
        }

    def channel(
        self,
        channel: int,
    ) -> DeviceChannelCapability | None:
        """Return one channel capability, if advertised."""

        channel = (
            _require_nonnegative_integer(
                channel,
                "channel",
            )
        )

        return self._channels_by_id.get(
            channel
        )

    def accepts_duration(
        self,
        duration: float,
    ) -> bool:
        """Return whether a duration is within the advertised range."""

        duration = (
            _require_positive_finite_number(
                duration,
                "duration",
            )
        )

        return (
            self.min_duration
            <= duration
            <= self.max_duration
        )

    def accepts_command(
        self,
        command: DeviceCommand,
    ) -> bool:
        """Return whether one command is supported by the device."""

        if not isinstance(
            command,
            DeviceCommand,
        ):
            raise TypeError(
                "command must be a DeviceCommand"
            )

        capability = (
            self._channels_by_id.get(
                command.channel
            )
        )

        if capability is None:
            return False

        return capability.accepts(
            command
        )

    def accepts_plan(
        self,
        plan: RenderingPlan,
    ) -> bool:
        """Return whether all technical constraints accept a plan."""

        if not isinstance(
            plan,
            RenderingPlan,
        ):
            raise TypeError(
                "plan must be a RenderingPlan"
            )

        if not self.accepts_duration(
            plan.duration
        ):
            return False

        return all(
            self.accepts_command(
                command
            )
            for command
            in plan.commands
        )

    def require_plan(
        self,
        plan: RenderingPlan,
    ) -> None:
        """Raise ValueError when a RenderingPlan is not supported."""

        if not isinstance(
            plan,
            RenderingPlan,
        ):
            raise TypeError(
                "plan must be a RenderingPlan"
            )

        if not self.accepts_duration(
            plan.duration
        ):
            raise ValueError(
                "rendering duration is not supported by "
                f"device {self.device_id}: "
                f"{plan.duration}"
            )

        for command in plan.commands:
            capability = (
                self._channels_by_id.get(
                    command.channel
                )
            )

            if capability is None:
                raise ValueError(
                    "rendering channel is not supported by "
                    f"device {self.device_id}: "
                    f"{command.channel}"
                )

            if not capability.accepts(
                command
            ):
                raise ValueError(
                    "rendering intensity is not supported "
                    f"by device {self.device_id} on channel "
                    f"{command.channel}: "
                    f"{command.intensity}"
                )