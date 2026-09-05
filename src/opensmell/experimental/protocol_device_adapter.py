"""Experimental protocol-backed DeviceAdapter for OpenSmell.

ProtocolDeviceAdapter connects the experimental DeviceAdapter contract to the
experimental JSON device protocol through a DeviceTransport.

Initialization performs two protocol exchanges:

1. HELLO, to identify the remote device,
2. GET_CAPABILITIES, to obtain its technical rendering constraints.

Rendering validates the RenderingPlan locally, serializes it as a protocol
render request, sends it through the transport, and requires a successful
device response.

The adapter is transport-independent. The same adapter may therefore be used
with an in-memory transport during tests and, later, with serial, USB, network,
or other transport implementations.

This module does not define:

- physical odor reproduction,
- cartridge or chemical semantics,
- universal channel meanings,
- hardware discovery,
- connection lifecycle,
- scheduling.

This module is experimental and non-normative.
"""

from __future__ import annotations

from .device_capabilities import DeviceCapabilities
from .device_protocol import (
    capabilities_request,
    dumps_message,
    hello_request,
    loads_message,
    parse_capabilities_response,
    parse_hello_response,
    render_request_message,
    require_ok_response,
)
from .device_transport import (
    DeviceTransport,
    require_device_transport,
)
from .rendering import RenderingPlan


class ProtocolDeviceAdapter:
    """DeviceAdapter backed by the experimental device protocol."""

    def __init__(
        self,
        transport: DeviceTransport,
    ) -> None:
        self._transport = require_device_transport(
            transport
        )

        hello_reply = self._exchange(
            hello_request()
        )

        self._device_id = parse_hello_response(
            hello_reply
        )

        capabilities_reply = self._exchange(
            capabilities_request()
        )

        capabilities = parse_capabilities_response(
            capabilities_reply
        )

        if capabilities.device_id != self._device_id:
            raise ValueError(
                "device identity mismatch between hello "
                "and capabilities responses"
            )

        self._capabilities = capabilities

    @property
    def device_id(self) -> str:
        """Return the remote device identifier."""

        return self._device_id

    @property
    def capabilities(self) -> DeviceCapabilities:
        """Return capabilities reported by the remote device."""

        return self._capabilities

    @property
    def transport(self) -> DeviceTransport:
        """Return the transport used by this adapter."""

        return self._transport

    def _exchange(
        self,
        message: dict[str, object],
    ) -> dict[str, object]:
        serialized = dumps_message(
            message
        )

        response = self._transport.exchange(
            serialized
        )

        return loads_message(
            response
        )

    def render(
        self,
        plan: RenderingPlan,
    ) -> object:
        """Validate and render a plan through the remote device."""

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

        response = self._exchange(
            render_request_message(
                plan
            )
        )

        require_ok_response(
            response
        )

        return response