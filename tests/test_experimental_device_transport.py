"""Tests for the experimental device transport boundary.

The transport layer is deliberately independent from OpenSmell rendering
semantics and from any concrete serial, USB, or network implementation.

This module is experimental and non-normative.
"""

from __future__ import annotations

from typing import Any

import pytest

from opensmell.experimental.device_transport import (
    DeviceTransport,
    MemoryDeviceTransport,
    require_device_transport,
)


class IndependentTransport:
    """Structural implementation without explicit inheritance."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def exchange(
        self,
        message: str,
    ) -> str:
        self.messages.append(
            message
        )

        return "OK"


class MissingExchange:
    pass


class NonCallableExchange:
    def __init__(self) -> None:
        self.exchange = "not-callable"


def test_independent_transport_satisfies_protocol() -> None:
    transport = IndependentTransport()

    assert isinstance(
        transport,
        DeviceTransport,
    )


def test_protocol_does_not_require_explicit_inheritance() -> None:
    assert DeviceTransport not in (
        IndependentTransport.__bases__
    )

    transport = IndependentTransport()

    assert isinstance(
        transport,
        DeviceTransport,
    )


def test_require_device_transport_returns_same_transport() -> None:
    transport = IndependentTransport()

    result = require_device_transport(
        transport
    )

    assert result is transport


def test_require_device_transport_rejects_missing_exchange() -> None:
    with pytest.raises(
        TypeError,
        match="DeviceTransport protocol",
    ):
        require_device_transport(
            MissingExchange()
        )


def test_require_device_transport_rejects_non_callable_exchange() -> None:
    with pytest.raises(
        TypeError,
    ):
        require_device_transport(
            NonCallableExchange()
        )


def test_memory_transport_satisfies_protocol() -> None:
    transport = MemoryDeviceTransport(
        responses=[
            "OK",
        ]
    )

    assert isinstance(
        transport,
        DeviceTransport,
    )

    assert (
        require_device_transport(
            transport
        )
        is transport
    )


def test_memory_transport_exchanges_message() -> None:
    transport = MemoryDeviceTransport(
        responses=[
            "DEVICE prototype-1",
        ]
    )

    response = transport.exchange(
        "HELLO"
    )

    assert response == "DEVICE prototype-1"

    assert transport.messages == [
        "HELLO"
    ]

    assert transport.remaining_responses == []


def test_memory_transport_consumes_responses_in_order() -> None:
    transport = MemoryDeviceTransport(
        responses=[
            "FIRST",
            "SECOND",
            "THIRD",
        ]
    )

    assert transport.exchange(
        "message-1"
    ) == "FIRST"

    assert transport.exchange(
        "message-2"
    ) == "SECOND"

    assert transport.exchange(
        "message-3"
    ) == "THIRD"

    assert transport.messages == [
        "message-1",
        "message-2",
        "message-3",
    ]


def test_memory_transport_returns_copies_of_internal_lists() -> None:
    transport = MemoryDeviceTransport(
        responses=[
            "OK",
            "NEXT",
        ]
    )

    messages = transport.messages
    responses = transport.remaining_responses

    messages.append(
        "external-message"
    )

    responses.clear()

    assert transport.messages == []

    assert transport.remaining_responses == [
        "OK",
        "NEXT",
    ]


def test_memory_transport_copies_constructor_responses() -> None:
    responses = [
        "OK",
    ]

    transport = MemoryDeviceTransport(
        responses=responses
    )

    responses.append(
        "EXTERNAL"
    )

    assert transport.remaining_responses == [
        "OK",
    ]


def test_memory_transport_rejects_non_list_responses() -> None:
    with pytest.raises(
        TypeError,
        match="responses must be a list",
    ):
        MemoryDeviceTransport(
            responses=(),
        )


@pytest.mark.parametrize(
    "response",
    [
        None,
        1,
        False,
        [],
        {},
    ],
)
def test_memory_transport_rejects_non_string_response(
    response: Any,
) -> None:
    with pytest.raises(
        TypeError,
        match="responses must contain strings",
    ):
        MemoryDeviceTransport(
            responses=[
                response,
            ]
        )


@pytest.mark.parametrize(
    "message",
    [
        None,
        1,
        False,
        [],
        {},
    ],
)
def test_memory_transport_rejects_non_string_message(
    message: Any,
) -> None:
    transport = MemoryDeviceTransport(
        responses=[
            "OK",
        ]
    )

    with pytest.raises(
        TypeError,
        match="message must be a string",
    ):
        transport.exchange(
            message
        )

    assert transport.messages == []

    assert transport.remaining_responses == [
        "OK",
    ]


def test_memory_transport_rejects_empty_message() -> None:
    transport = MemoryDeviceTransport(
        responses=[
            "OK",
        ]
    )

    with pytest.raises(
        ValueError,
        match="message must be non-empty",
    ):
        transport.exchange(
            ""
        )

    assert transport.messages == []

    assert transport.remaining_responses == [
        "OK",
    ]


def test_memory_transport_rejects_exchange_without_response() -> None:
    transport = MemoryDeviceTransport(
        responses=[]
    )

    with pytest.raises(
        RuntimeError,
        match="no configured response",
    ):
        transport.exchange(
            "HELLO"
        )

    assert transport.messages == []


def test_failed_exchange_does_not_modify_transport_state() -> None:
    transport = MemoryDeviceTransport(
        responses=[
            "OK",
        ]
    )

    with pytest.raises(
        ValueError,
    ):
        transport.exchange(
            ""
        )

    assert transport.messages == []

    assert transport.remaining_responses == [
        "OK",
    ]