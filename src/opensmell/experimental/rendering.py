"""Experimental device-independent rendering primitives for OpenSmell.

This module explores the boundary between an application request to render an
OpenSmell resource and device-specific commands produced by a mapper.

It deliberately does not define:

- how an odor is physically reproduced;
- how OpenSmell representations are mapped to device channels;
- diffuser capabilities or cartridge semantics;
- transport protocols or hardware drivers;
- a serialized OpenSmell wire format for rendering.

The model is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any


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


def _require_positive_finite_number(
    value: Any,
    name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
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


def _require_unit_interval(
    value: Any,
    name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise TypeError(
            f"{name} must be a number"
        )

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            f"{name} must be finite"
        )

    if result < 0.0 or result > 1.0:
        raise ValueError(
            f"{name} must be between 0.0 and 1.0"
        )

    return result


def _require_nonnegative_integer(
    value: Any,
    name: str,
) -> int:
    if isinstance(value, bool) or not isinstance(
        value,
        int,
    ):
        raise TypeError(
            f"{name} must be an integer"
        )

    if value < 0:
        raise ValueError(
            f"{name} must be non-negative"
        )

    return value


def _require_dict(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(
            f"{name} must be a dict"
        )

    return value


@dataclass(frozen=True)
class RenderRequest:
    """Application-level request to render one OpenSmell resource.

    ``resource_id`` identifies the graph resource the application wants to
    render.

    ``duration`` is the requested duration in seconds. It expresses application
    intent only. A mapper or device may later reject unsupported durations.
    """

    resource_id: str
    duration: float

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.resource_id,
            "RenderRequest.resource_id",
        )

        object.__setattr__(
            self,
            "duration",
            _require_positive_finite_number(
                self.duration,
                "RenderRequest.duration",
            ),
        )


@dataclass(frozen=True)
class DeviceCommand:
    """One abstract output-channel command.

    ``channel`` is a device-facing channel number. OpenSmell assigns no
    universal olfactory meaning to that number.

    ``intensity`` is normalized to the closed interval 0.0 through 1.0. The
    physical interpretation of intensity belongs to the device adapter.
    """

    channel: int
    intensity: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "channel",
            _require_nonnegative_integer(
                self.channel,
                "DeviceCommand.channel",
            ),
        )

        object.__setattr__(
            self,
            "intensity",
            _require_unit_interval(
                self.intensity,
                "DeviceCommand.intensity",
            ),
        )


@dataclass
class RenderingPlan:
    """Device-facing plan produced by a mapper.

    A RenderingPlan is not an odor representation and is not part of the
    GenericResourceGraph. It is transient output produced for a particular
    rendering path.

    ``commands`` are intentionally generic channel/intensity pairs.

    ``duration`` is expressed in seconds.

    ``extra`` is available for experimental mapper/device metadata. This module
    does not interpret its contents.
    """

    commands: list[DeviceCommand]
    duration: float
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.commands,
            list,
        ):
            raise TypeError(
                "RenderingPlan.commands must be a list"
            )

        for command in self.commands:
            if not isinstance(
                command,
                DeviceCommand,
            ):
                raise TypeError(
                    "RenderingPlan.commands must contain "
                    "DeviceCommand values"
                )

        self.commands = list(
            self.commands
        )

        self.duration = (
            _require_positive_finite_number(
                self.duration,
                "RenderingPlan.duration",
            )
        )

        _require_dict(
            self.extra,
            "RenderingPlan.extra",
        )

        self.extra = dict(
            self.extra
        )
