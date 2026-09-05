"""Tests for the experimental serial DeviceTransport.

A fake serial connection is used so these tests require no physical serial
port or microcontroller.

The tests validate line framing, UTF-8 handling, timeout behavior, connection
closing, and compatibility with the DeviceTransport contract.

This module is experimental and non-normative.
"""

from __future__ import annotations

from typing import Any

import pytest

from opensmell.experimental.device_transport import (
    DeviceTransport,
    require_device_transport,
)
from opensmell.experimental.serial_device_transport import (
    DEFAULT_BAUDRATE,
    DEFAULT_TIMEOUT,
    SerialDeviceTransport,
)


class FakeSerial:
    """Minimal deterministic serial object for transport tests."""

    def __init__(
        self,
        responses: list[bytes],
    ) -> None:
        self.responses = list(
            responses
        )
        self.writes: list[bytes] = []
        self.flush_count = 0
        self.closed = False

    def write(
        self,
        payload: bytes,
    ) -> int:
        self.writes.append(
            payload
        )

        return len(
            payload
        )

    def flush(self) -> None:
        self.flush_count += 1

    def readline(self) -> bytes:
        if not self.responses:
            return b""

        return self.responses.pop(
            0
        )

    def close(self) -> None:
        self.closed = True


def transport(
    responses: list[bytes] | None = None,
) -> tuple[
    SerialDeviceTransport,
    FakeSerial,
]:
    fake = FakeSerial(
        responses=(
            responses
            if responses is not None
            else [b"OK\n"]
        )
    )

    target = SerialDeviceTransport(
        "COM_TEST",
        serial_instance=fake,
    )

    return target, fake


def test_default_serial_settings() -> None:
    target, _ = transport()

    assert target.port == "COM_TEST"
    assert target.baudrate == DEFAULT_BAUDRATE
    assert target.baudrate == 115200
    assert target.timeout == DEFAULT_TIMEOUT
    assert target.timeout == 2.0


def test_custom_serial_settings() -> None:
    fake = FakeSerial(
        responses=[
            b"OK\n",
        ]
    )

    target = SerialDeviceTransport(
        "COM9",
        baudrate=9600,
        timeout=5.0,
        serial_instance=fake,
    )

    assert target.port == "COM9"
    assert target.baudrate == 9600
    assert target.timeout == 5.0
    assert target.serial_instance is fake


def test_serial_transport_satisfies_device_transport() -> None:
    target, _ = transport()

    assert isinstance(
        target,
        DeviceTransport,
    )

    assert (
        require_device_transport(
            target
        )
        is target
    )


def test_exchange_writes_one_newline_terminated_message() -> None:
    target, fake = transport(
        responses=[
            b'{"type":"ok"}\n',
        ]
    )

    response = target.exchange(
        '{"type":"hello"}'
    )

    assert fake.writes == [
        b'{"type":"hello"}\n'
    ]

    assert fake.flush_count == 1

    assert response == '{"type":"ok"}'


def test_exchange_supports_utf8() -> None:
    target, fake = transport(
        responses=[
            '{"message":"réponse"}\n'.encode(
                "utf-8"
            ),
        ]
    )

    response = target.exchange(
        '{"message":"café"}'
    )

    assert fake.writes == [
        '{"message":"café"}\n'.encode(
            "utf-8"
        )
    ]

    assert response == '{"message":"réponse"}'


@pytest.mark.parametrize(
    "response",
    [
        b"OK\n",
        b"OK\r\n",
        b"OK",
    ],
)
def test_exchange_accepts_common_response_line_endings(
    response: bytes,
) -> None:
    target, _ = transport(
        responses=[
            response,
        ]
    )

    assert target.exchange(
        "HELLO"
    ) == "OK"


def test_exchange_times_out_on_empty_read() -> None:
    target, fake = transport(
        responses=[]
    )

    with pytest.raises(
        TimeoutError,
        match="did not return a response",
    ):
        target.exchange(
            "HELLO"
        )

    assert fake.writes == [
        b"HELLO\n"
    ]


@pytest.mark.parametrize(
    "response",
    [
        b"\n",
        b"\r\n",
    ],
)
def test_exchange_rejects_empty_response_line(
    response: bytes,
) -> None:
    target, _ = transport(
        responses=[
            response,
        ]
    )

    with pytest.raises(
        RuntimeError,
        match="empty response",
    ):
        target.exchange(
            "HELLO"
        )


def test_exchange_rejects_non_bytes_response() -> None:
    class InvalidSerial(FakeSerial):
        def readline(self) -> bytes:
            return "OK"  # type: ignore[return-value]

    fake = InvalidSerial(
        responses=[]
    )

    target = SerialDeviceTransport(
        "COM_TEST",
        serial_instance=fake,
    )

    with pytest.raises(
        RuntimeError,
        match="readline must return bytes",
    ):
        target.exchange(
            "HELLO"
        )


def test_exchange_rejects_invalid_utf8() -> None:
    target, _ = transport(
        responses=[
            b"\xff\xfe\n",
        ]
    )

    with pytest.raises(
        RuntimeError,
        match="invalid UTF-8",
    ):
        target.exchange(
            "HELLO"
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
def test_exchange_rejects_non_string_message(
    message: Any,
) -> None:
    target, fake = transport()

    with pytest.raises(
        TypeError,
        match="message must be a string",
    ):
        target.exchange(
            message
        )

    assert fake.writes == []


def test_exchange_rejects_empty_message() -> None:
    target, fake = transport()

    with pytest.raises(
        ValueError,
        match="message must be non-empty",
    ):
        target.exchange(
            ""
        )

    assert fake.writes == []


@pytest.mark.parametrize(
    "message",
    [
        "HELLO\nSECOND",
        "HELLO\rSECOND",
        "HELLO\r\nSECOND",
    ],
)
def test_exchange_rejects_embedded_line_terminator(
    message: str,
) -> None:
    target, fake = transport()

    with pytest.raises(
        ValueError,
        match="line terminators",
    ):
        target.exchange(
            message
        )

    assert fake.writes == []


@pytest.mark.parametrize(
    "port",
    [
        None,
        1,
        False,
        [],
        {},
    ],
)
def test_constructor_rejects_non_string_port(
    port: Any,
) -> None:
    with pytest.raises(
        TypeError,
        match="port must be a string",
    ):
        SerialDeviceTransport(
            port,
            serial_instance=FakeSerial(
                responses=[]
            ),
        )


def test_constructor_rejects_empty_port() -> None:
    with pytest.raises(
        ValueError,
        match="port must be non-empty",
    ):
        SerialDeviceTransport(
            "",
            serial_instance=FakeSerial(
                responses=[]
            ),
        )


@pytest.mark.parametrize(
    "baudrate",
    [
        None,
        1.5,
        "115200",
        False,
    ],
)
def test_constructor_rejects_invalid_baudrate_type(
    baudrate: Any,
) -> None:
    with pytest.raises(
        TypeError,
        match="baudrate must be an integer",
    ):
        SerialDeviceTransport(
            "COM_TEST",
            baudrate=baudrate,
            serial_instance=FakeSerial(
                responses=[]
            ),
        )


@pytest.mark.parametrize(
    "baudrate",
    [
        0,
        -1,
        -115200,
    ],
)
def test_constructor_rejects_nonpositive_baudrate(
    baudrate: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="baudrate must be positive",
    ):
        SerialDeviceTransport(
            "COM_TEST",
            baudrate=baudrate,
            serial_instance=FakeSerial(
                responses=[]
            ),
        )


@pytest.mark.parametrize(
    "timeout",
    [
        None,
        "2",
        False,
    ],
)
def test_constructor_rejects_invalid_timeout_type(
    timeout: Any,
) -> None:
    with pytest.raises(
        TypeError,
        match="timeout must be a number",
    ):
        SerialDeviceTransport(
            "COM_TEST",
            timeout=timeout,
            serial_instance=FakeSerial(
                responses=[]
            ),
        )


@pytest.mark.parametrize(
    "timeout",
    [
        0,
        0.0,
        -1,
        -0.1,
    ],
)
def test_constructor_rejects_nonpositive_timeout(
    timeout: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="timeout must be positive",
    ):
        SerialDeviceTransport(
            "COM_TEST",
            timeout=timeout,
            serial_instance=FakeSerial(
                responses=[]
            ),
        )


def test_close_closes_serial_connection() -> None:
    target, fake = transport()

    assert fake.closed is False

    target.close()

    assert fake.closed is True


def test_context_manager_returns_transport() -> None:
    target, fake = transport()

    with target as entered:
        assert entered is target
        assert fake.closed is False

    assert fake.closed is True


def test_serial_instance_is_exposed() -> None:
    target, fake = transport()

    assert target.serial_instance is fake