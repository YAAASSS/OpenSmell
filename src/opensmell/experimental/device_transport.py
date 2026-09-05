"""Experimental device transport boundary for OpenSmell.

A DeviceTransport represents a low-level request/response communication
channel between a device adapter and an external rendering device.

The transport is intentionally unaware of OpenSmell ResourceGraph,
RenderRequest, RenderingPlan, semantic annotations, mapping policy, and
physical odor reproduction.

Its responsibility is limited to transporting textual device-protocol
messages.

Concrete implementations may later use serial ports, USB bridges, network
connections, or other mechanisms.

This module does not define the device protocol itself.

This module is experimental and non-normative.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DeviceTransport(Protocol):
    """Minimal structural contract for request/response device transport."""

    def exchange(
        self,
        message: str,
    ) -> str:
        """Send one message and return the device response."""

        ...


def require_device_transport(
    transport: object,
) -> DeviceTransport:
    """Validate and return a runtime-usable DeviceTransport."""

    if not isinstance(
        transport,
        DeviceTransport,
    ):
        raise TypeError(
            "transport must satisfy the DeviceTransport protocol"
        )

    exchange = transport.exchange

    if not callable(
        exchange
    ):
        raise TypeError(
            "transport.exchange must be callable"
        )

    return transport


class MemoryDeviceTransport:
    """Deterministic in-memory transport for experiments and tests.

    Responses are configured in advance. Every call to ``exchange`` records
    the outgoing message and consumes the next configured response.

    This class performs no hardware or network I/O.
    """

    def __init__(
        self,
        responses: list[str],
    ) -> None:
        if not isinstance(
            responses,
            list,
        ):
            raise TypeError(
                "responses must be a list"
            )

        validated: list[str] = []

        for response in responses:
            if not isinstance(
                response,
                str,
            ):
                raise TypeError(
                    "responses must contain strings"
                )

            validated.append(
                response
            )

        self._responses = list(
            validated
        )
        self._messages: list[str] = []

    @property
    def messages(
        self,
    ) -> list[str]:
        """Return a copy of messages sent through this transport."""

        return list(
            self._messages
        )

    @property
    def remaining_responses(
        self,
    ) -> list[str]:
        """Return a copy of responses that have not yet been consumed."""

        return list(
            self._responses
        )

    def exchange(
        self,
        message: str,
    ) -> str:
        """Record a message and return the next configured response."""

        if not isinstance(
            message,
            str,
        ):
            raise TypeError(
                "message must be a string"
            )

        if not message:
            raise ValueError(
                "message must be non-empty"
            )

        if not self._responses:
            raise RuntimeError(
                "memory device transport has no configured response"
            )

        self._messages.append(
            message
        )

        return self._responses.pop(
            0
        )