"""Experimental device protocol messages for OpenSmell.

This module defines a small JSON message protocol between an OpenSmell device
adapter and a rendering device.

The protocol is transport-independent. A message may later be carried over a
serial connection, USB bridge, network connection, or an in-memory transport.

The protocol currently supports:

- hello requests and responses,
- capability requests and responses,
- rendering requests,
- generic success responses,
- generic error responses.

The protocol does not define:

- physical odor reproduction,
- cartridge or chemical semantics,
- universal channel meanings,
- connection lifecycle,
- hardware discovery,
- scheduling,
- transport framing beyond one serialized message.

This module is experimental and non-normative.
"""

from __future__ import annotations

import json
import math
from typing import Any

from .device_capabilities import (
    DeviceCapabilities,
    DeviceChannelCapability,
)
from .rendering import (
    DeviceCommand,
    RenderingPlan,
)


PROTOCOL_VERSION = "0.1"


class DeviceProtocolError(ValueError):
    """Raised when a device protocol message is invalid."""


def _require_dict(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DeviceProtocolError(
            f"{name} must be an object"
        )

    return value


def _require_nonempty_string(
    value: Any,
    name: str,
) -> str:
    if not isinstance(value, str):
        raise DeviceProtocolError(
            f"{name} must be a string"
        )

    if not value:
        raise DeviceProtocolError(
            f"{name} must be non-empty"
        )

    return value


def _require_number(
    value: Any,
    name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(
        value,
        (int, float),
    ):
        raise DeviceProtocolError(
            f"{name} must be a number"
        )

    result = float(value)

    if not math.isfinite(result):
        raise DeviceProtocolError(
            f"{name} must be finite"
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
        raise DeviceProtocolError(
            f"{name} must be an integer"
        )

    if value < 0:
        raise DeviceProtocolError(
            f"{name} must be non-negative"
        )

    return value


def _require_protocol_version(
    message: dict[str, Any],
) -> None:
    version = _require_nonempty_string(
        message.get("protocol_version"),
        "protocol_version",
    )

    if version != PROTOCOL_VERSION:
        raise DeviceProtocolError(
            f"unsupported protocol version: {version}"
        )


def _require_message_type(
    message: dict[str, Any],
    expected: str,
) -> None:
    message_type = _require_nonempty_string(
        message.get("type"),
        "type",
    )

    if message_type != expected:
        raise DeviceProtocolError(
            f"expected message type {expected!r}, "
            f"got {message_type!r}"
        )


def dumps_message(
    message: dict[str, Any],
) -> str:
    """Serialize a protocol message using strict compact JSON."""

    _require_dict(
        message,
        "message",
    )

    try:
        return json.dumps(
            message,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise DeviceProtocolError(
            "message is not valid strict JSON"
        ) from exc


def loads_message(
    text: str,
) -> dict[str, Any]:
    """Parse one strict JSON protocol message."""

    if not isinstance(text, str):
        raise TypeError(
            "text must be a string"
        )

    if not text:
        raise DeviceProtocolError(
            "message text must be non-empty"
        )

    def reject_constant(
        value: str,
    ) -> None:
        raise DeviceProtocolError(
            f"invalid JSON numeric constant: {value}"
        )

    try:
        value = json.loads(
            text,
            parse_constant=reject_constant,
        )
    except DeviceProtocolError:
        raise
    except json.JSONDecodeError as exc:
        raise DeviceProtocolError(
            "invalid JSON message"
        ) from exc

    return _require_dict(
        value,
        "message",
    )


def hello_request() -> dict[str, Any]:
    """Build a hello request."""

    return {
        "protocol_version": PROTOCOL_VERSION,
        "type": "hello",
    }


def hello_response(
    device_id: str,
) -> dict[str, Any]:
    """Build a hello response."""

    device_id = _require_nonempty_string(
        device_id,
        "device_id",
    )

    return {
        "protocol_version": PROTOCOL_VERSION,
        "type": "hello_response",
        "device_id": device_id,
    }


def parse_hello_response(
    message: dict[str, Any],
) -> str:
    """Validate a hello response and return its device ID."""

    message = _require_dict(
        message,
        "message",
    )

    _require_protocol_version(
        message
    )

    _require_message_type(
        message,
        "hello_response",
    )

    return _require_nonempty_string(
        message.get("device_id"),
        "device_id",
    )


def capabilities_request() -> dict[str, Any]:
    """Build a device capabilities request."""

    return {
        "protocol_version": PROTOCOL_VERSION,
        "type": "get_capabilities",
    }


def capabilities_response(
    capabilities: DeviceCapabilities,
) -> dict[str, Any]:
    """Build a capability response from DeviceCapabilities."""

    if not isinstance(
        capabilities,
        DeviceCapabilities,
    ):
        raise TypeError(
            "capabilities must be a DeviceCapabilities"
        )

    return {
        "protocol_version": PROTOCOL_VERSION,
        "type": "capabilities",
        "device_id": capabilities.device_id,
        "channels": [
            {
                "channel": channel.channel,
                "min_intensity": channel.min_intensity,
                "max_intensity": channel.max_intensity,
            }
            for channel in capabilities.channels
        ],
        "min_duration": capabilities.min_duration,
        "max_duration": capabilities.max_duration,
    }


def parse_capabilities_response(
    message: dict[str, Any],
) -> DeviceCapabilities:
    """Parse a capability response into DeviceCapabilities."""

    message = _require_dict(
        message,
        "message",
    )

    _require_protocol_version(
        message
    )

    _require_message_type(
        message,
        "capabilities",
    )

    device_id = _require_nonempty_string(
        message.get("device_id"),
        "device_id",
    )

    raw_channels = message.get(
        "channels"
    )

    if not isinstance(
        raw_channels,
        list,
    ):
        raise DeviceProtocolError(
            "channels must be an array"
        )

    channels: list[DeviceChannelCapability] = []

    for index, raw_channel in enumerate(
        raw_channels
    ):
        raw_channel = _require_dict(
            raw_channel,
            f"channels[{index}]",
        )

        channel = _require_nonnegative_integer(
            raw_channel.get("channel"),
            f"channels[{index}].channel",
        )

        min_intensity = _require_number(
            raw_channel.get("min_intensity"),
            f"channels[{index}].min_intensity",
        )

        max_intensity = _require_number(
            raw_channel.get("max_intensity"),
            f"channels[{index}].max_intensity",
        )

        try:
            capability = DeviceChannelCapability(
                channel=channel,
                min_intensity=min_intensity,
                max_intensity=max_intensity,
            )
        except (TypeError, ValueError) as exc:
            raise DeviceProtocolError(
                f"invalid capability for channel {channel}"
            ) from exc

        channels.append(
            capability
        )

    min_duration = _require_number(
        message.get("min_duration"),
        "min_duration",
    )

    max_duration = _require_number(
        message.get("max_duration"),
        "max_duration",
    )

    try:
        return DeviceCapabilities(
            device_id=device_id,
            channels=channels,
            min_duration=min_duration,
            max_duration=max_duration,
        )
    except (TypeError, ValueError) as exc:
        raise DeviceProtocolError(
            "invalid device capabilities"
        ) from exc


def render_request_message(
    plan: RenderingPlan,
) -> dict[str, Any]:
    """Build a rendering request from a RenderingPlan."""

    if not isinstance(
        plan,
        RenderingPlan,
    ):
        raise TypeError(
            "plan must be a RenderingPlan"
        )

    return {
        "protocol_version": PROTOCOL_VERSION,
        "type": "render",
        "duration": plan.duration,
        "commands": [
            {
                "channel": command.channel,
                "intensity": command.intensity,
            }
            for command in plan.commands
        ],
    }


def parse_render_request(
    message: dict[str, Any],
) -> RenderingPlan:
    """Parse a rendering request into a RenderingPlan."""

    message = _require_dict(
        message,
        "message",
    )

    _require_protocol_version(
        message
    )

    _require_message_type(
        message,
        "render",
    )

    duration = _require_number(
        message.get("duration"),
        "duration",
    )

    raw_commands = message.get(
        "commands"
    )

    if not isinstance(
        raw_commands,
        list,
    ):
        raise DeviceProtocolError(
            "commands must be an array"
        )

    commands: list[DeviceCommand] = []

    for index, raw_command in enumerate(
        raw_commands
    ):
        raw_command = _require_dict(
            raw_command,
            f"commands[{index}]",
        )

        channel = _require_nonnegative_integer(
            raw_command.get("channel"),
            f"commands[{index}].channel",
        )

        intensity = _require_number(
            raw_command.get("intensity"),
            f"commands[{index}].intensity",
        )

        try:
            command = DeviceCommand(
                channel=channel,
                intensity=intensity,
            )
        except (TypeError, ValueError) as exc:
            raise DeviceProtocolError(
                f"invalid rendering command at index {index}"
            ) from exc

        commands.append(
            command
        )

    try:
        return RenderingPlan(
            commands=commands,
            duration=duration,
        )
    except (TypeError, ValueError) as exc:
        raise DeviceProtocolError(
            "invalid rendering plan"
        ) from exc


def ok_response() -> dict[str, Any]:
    """Build a generic successful response."""

    return {
        "protocol_version": PROTOCOL_VERSION,
        "type": "ok",
    }


def error_response(
    code: str,
    message: str,
) -> dict[str, Any]:
    """Build a generic device error response."""

    code = _require_nonempty_string(
        code,
        "code",
    )

    message = _require_nonempty_string(
        message,
        "message",
    )

    return {
        "protocol_version": PROTOCOL_VERSION,
        "type": "error",
        "code": code,
        "message": message,
    }


def require_ok_response(
    message: dict[str, Any],
) -> None:
    """Require a successful device response.

    Device error responses are converted into DeviceProtocolError.
    """

    message = _require_dict(
        message,
        "message",
    )

    _require_protocol_version(
        message
    )

    message_type = _require_nonempty_string(
        message.get("type"),
        "type",
    )

    if message_type == "ok":
        return

    if message_type == "error":
        code = _require_nonempty_string(
            message.get("code"),
            "code",
        )

        detail = _require_nonempty_string(
            message.get("message"),
            "message",
        )

        raise DeviceProtocolError(
            f"device error {code}: {detail}"
        )

    raise DeviceProtocolError(
        f"expected 'ok' response, got {message_type!r}"
    )