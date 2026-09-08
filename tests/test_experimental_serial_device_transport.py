"""Tests for the experimental serial DeviceTransport.

A fake serial connection is used so these tests require no physical serial
port or microcontroller.

The tests validate line framing, UTF-8 handling, timeout behavior, startup
preparation, connection closing, and compatibility with the DeviceTransport
contract.

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
    DEFAULT_DISCARD_INITIAL_INPUT,
    DEFAULT_STARTUP_DELAY,
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
        self.reset_input_buffer_count = 0

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

    def reset_input_buffer(self) -> None:
        self.reset_input_buffer_count += 1
        self.responses.clear()

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
    assert target.startup_delay == DEFAULT_STARTUP_DELAY
    assert target.startup_delay == 0.0
    assert (
        target.discard_initial_input
        == DEFAULT_DISCARD_INITIAL_INPUT
    )
    assert target.discard_initial_input is False


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
        startup_delay=0.0,
        discard_initial_input=False,
        serial_instance=fake,
    )

    assert target.port == "COM9"
    assert target.baudrate == 9600
    assert target.timeout == 5.0
    assert target.startup_delay == 0.0
    assert target.discard_initial_input is False
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


@pytest.mark.parametrize(
    "startup_delay",
    [
        None,
        "2",
        False,
    ],
)
def test_constructor_rejects_invalid_startup_delay_type(
    startup_delay: Any,
) -> None:
    with pytest.raises(
        TypeError,
        match="startup_delay must be a number",
    ):
        SerialDeviceTransport(
            "COM_TEST",
            startup_delay=startup_delay,
            serial_instance=FakeSerial(
                responses=[]
            ),
        )


@pytest.mark.parametrize(
    "startup_delay",
    [
        -1,
        -0.1,
    ],
)
def test_constructor_rejects_negative_startup_delay(
    startup_delay: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="startup_delay must be non-negative",
    ):
        SerialDeviceTransport(
            "COM_TEST",
            startup_delay=startup_delay,
            serial_instance=FakeSerial(
                responses=[]
            ),
        )


@pytest.mark.parametrize(
    "discard_initial_input",
    [
        None,
        0,
        1,
        "true",
        [],
        {},
    ],
)
def test_constructor_rejects_invalid_discard_initial_input_type(
    discard_initial_input: Any,
) -> None:
    with pytest.raises(
        TypeError,
        match="discard_initial_input must be a boolean",
    ):
        SerialDeviceTransport(
            "COM_TEST",
            discard_initial_input=discard_initial_input,
            serial_instance=FakeSerial(
                responses=[]
            ),
        )


def test_startup_delay_uses_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []

    def fake_sleep(
        seconds: float,
    ) -> None:
        sleeps.append(
            seconds
        )

    monkeypatch.setattr(
        "opensmell.experimental.serial_device_transport.time.sleep",
        fake_sleep,
    )

    fake = FakeSerial(
        responses=[]
    )

    target = SerialDeviceTransport(
        "COM_TEST",
        startup_delay=1.5,
        serial_instance=fake,
    )

    assert target.startup_delay == 1.5
    assert sleeps == [
        1.5,
    ]


def test_zero_startup_delay_does_not_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []

    def fake_sleep(
        seconds: float,
    ) -> None:
        sleeps.append(
            seconds
        )

    monkeypatch.setattr(
        "opensmell.experimental.serial_device_transport.time.sleep",
        fake_sleep,
    )

    SerialDeviceTransport(
        "COM_TEST",
        startup_delay=0.0,
        serial_instance=FakeSerial(
            responses=[]
        ),
    )

    assert sleeps == []


def test_discard_initial_input_resets_serial_buffer() -> None:
    fake = FakeSerial(
        responses=[
            b"BOOT MESSAGE\n",
        ]
    )

    target = SerialDeviceTransport(
        "COM_TEST",
        discard_initial_input=True,
        serial_instance=fake,
    )

    assert target.discard_initial_input is True
    assert fake.reset_input_buffer_count == 1
    assert fake.responses == []


def test_default_does_not_reset_serial_buffer() -> None:
    fake = FakeSerial(
        responses=[
            b"BOOT MESSAGE\n",
        ]
    )

    target = SerialDeviceTransport(
        "COM_TEST",
        serial_instance=fake,
    )

    assert target.discard_initial_input is False
    assert fake.reset_input_buffer_count == 0
    assert fake.responses == [
        b"BOOT MESSAGE\n",
    ]


def test_discard_initial_input_requires_supported_serial_object() -> None:
    class SerialWithoutReset:
        def close(self) -> None:
            pass

    with pytest.raises(
        RuntimeError,
        match="does not support reset_input_buffer",
    ):
        SerialDeviceTransport(
            "COM_TEST",
            discard_initial_input=True,
            serial_instance=SerialWithoutReset(),
        )


def test_startup_delay_happens_before_input_discard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    def fake_sleep(
        seconds: float,
    ) -> None:
        events.append(
            f"sleep:{seconds}"
        )

    class OrderedFakeSerial(FakeSerial):
        def reset_input_buffer(self) -> None:
            events.append(
                "reset_input_buffer"
            )
            super().reset_input_buffer()

    monkeypatch.setattr(
        "opensmell.experimental.serial_device_transport.time.sleep",
        fake_sleep,
    )

    fake = OrderedFakeSerial(
        responses=[
            b"BOOT MESSAGE\n",
        ]
    )

    SerialDeviceTransport(
        "COM_TEST",
        startup_delay=2.0,
        discard_initial_input=True,
        serial_instance=fake,
    )

    assert events == [
        "sleep:2.0",
        "reset_input_buffer",
    ]


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