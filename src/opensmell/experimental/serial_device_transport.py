"""Experimental serial DeviceTransport for OpenSmell.

SerialDeviceTransport carries one textual OpenSmell device-protocol message
per serial line.

Each exchange:

1. encodes one message as UTF-8,
2. appends a newline delimiter,
3. writes and flushes the serial connection,
4. reads one response line,
5. removes the line terminator,
6. decodes the response as strict UTF-8.

Some serial devices reset when the host opens the serial port. The transport
therefore supports optional startup settling and initial input-buffer
discarding. These behaviors are transport-level concerns and do not interpret
the OpenSmell device protocol.

The transport does not interpret the OpenSmell device protocol itself.
Protocol parsing remains the responsibility of ProtocolDeviceAdapter and
device_protocol.

This implementation deliberately keeps serial behavior minimal. It does not
define:

- hardware discovery,
- automatic reconnection,
- connection lifecycle commands,
- retries,
- asynchronous communication,
- unsolicited device events,
- physical odor reproduction.

This module is experimental and non-normative.
"""

from __future__ import annotations

import time
from typing import Any

try:
    import serial
except ImportError:  # pragma: no cover
    serial = None


DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 2.0
DEFAULT_STARTUP_DELAY = 0.0
DEFAULT_DISCARD_INITIAL_INPUT = False


class SerialDeviceTransport:
    """Line-oriented DeviceTransport backed by a serial connection."""

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = DEFAULT_TIMEOUT,
        startup_delay: float = DEFAULT_STARTUP_DELAY,
        discard_initial_input: bool = DEFAULT_DISCARD_INITIAL_INPUT,
        serial_instance: Any | None = None,
    ) -> None:
        if not isinstance(port, str):
            raise TypeError(
                "port must be a string"
            )

        if not port:
            raise ValueError(
                "port must be non-empty"
            )

        if isinstance(baudrate, bool) or not isinstance(
            baudrate,
            int,
        ):
            raise TypeError(
                "baudrate must be an integer"
            )

        if baudrate <= 0:
            raise ValueError(
                "baudrate must be positive"
            )

        if isinstance(timeout, bool) or not isinstance(
            timeout,
            (int, float),
        ):
            raise TypeError(
                "timeout must be a number"
            )

        timeout = float(timeout)

        if timeout <= 0:
            raise ValueError(
                "timeout must be positive"
            )

        if isinstance(startup_delay, bool) or not isinstance(
            startup_delay,
            (int, float),
        ):
            raise TypeError(
                "startup_delay must be a number"
            )

        startup_delay = float(startup_delay)

        if startup_delay < 0:
            raise ValueError(
                "startup_delay must be non-negative"
            )

        if not isinstance(
            discard_initial_input,
            bool,
        ):
            raise TypeError(
                "discard_initial_input must be a boolean"
            )

        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._startup_delay = startup_delay
        self._discard_initial_input = discard_initial_input

        if serial_instance is None:
            if serial is None:
                raise RuntimeError(
                    "PySerial is required for SerialDeviceTransport; "
                    "install OpenSmell with the 'serial' extra"
                )

            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=timeout,
                write_timeout=timeout,
            )
        else:
            self._serial = serial_instance

        self._prepare_connection()

    @property
    def port(self) -> str:
        """Return the configured serial port."""

        return self._port

    @property
    def baudrate(self) -> int:
        """Return the configured baud rate."""

        return self._baudrate

    @property
    def timeout(self) -> float:
        """Return the configured response timeout."""

        return self._timeout

    @property
    def startup_delay(self) -> float:
        """Return the configured startup settling delay."""

        return self._startup_delay

    @property
    def discard_initial_input(self) -> bool:
        """Return whether startup input is discarded."""

        return self._discard_initial_input

    @property
    def serial_instance(self) -> Any:
        """Return the underlying serial connection."""

        return self._serial

    def _prepare_connection(self) -> None:
        """Apply optional serial startup preparation."""

        if self._startup_delay > 0:
            time.sleep(
                self._startup_delay
            )

        if self._discard_initial_input:
            reset_input_buffer = getattr(
                self._serial,
                "reset_input_buffer",
                None,
            )

            if not callable(
                reset_input_buffer
            ):
                raise RuntimeError(
                    "serial connection does not support "
                    "reset_input_buffer"
                )

            reset_input_buffer()

    def exchange(
        self,
        message: str,
    ) -> str:
        """Send one UTF-8 line and return one UTF-8 response line."""

        if not isinstance(message, str):
            raise TypeError(
                "message must be a string"
            )

        if not message:
            raise ValueError(
                "message must be non-empty"
            )

        if "\n" in message or "\r" in message:
            raise ValueError(
                "message must not contain line terminators"
            )

        payload = (
            message.encode("utf-8")
            + b"\n"
        )

        self._serial.write(
            payload
        )

        self._serial.flush()

        response = self._serial.readline()

        if not isinstance(
            response,
            bytes,
        ):
            raise RuntimeError(
                "serial readline must return bytes"
            )

        if not response:
            raise TimeoutError(
                "serial device did not return a response"
            )

        response = response.rstrip(
            b"\r\n"
        )

        if not response:
            raise RuntimeError(
                "serial device returned an empty response"
            )

        try:
            return response.decode(
                "utf-8"
            )
        except UnicodeDecodeError as exc:
            raise RuntimeError(
                "serial device returned invalid UTF-8"
            ) from exc

    def close(self) -> None:
        """Close the underlying serial connection."""

        self._serial.close()

    def __enter__(
        self,
    ) -> SerialDeviceTransport:
        """Return this transport as a context manager."""

        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        """Close the serial connection when leaving the context."""

        self.close()