"""Explicit hardware actions, isolated from graph loading and preview mapping."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
import importlib.util
import threading
import time

EXPECTED_DEVICE_ID = "opensmell-esp32-led-3ch-001"
INSTALL_HELP = 'PySerial is not installed. From the repository root, run: python -m pip install -e ".[serial]". Preview remains available.'


class HardwareError(ValueError):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status


def serial_available():
    return importlib.util.find_spec("serial") is not None


def list_ports():
    # Enumeration only: never open ports to identify devices.
    from serial.tools import list_ports as ports
    return [{"port": item.device, "description": item.description} for item in ports.comports()]


def open_transport(port):
    import serial
    from opensmell.experimental.serial_device_transport import SerialDeviceTransport

    # Own the serial handle before SDK startup/reset preparation, so even a
    # preparation failure closes it. Same settings as the physical CLI demo.
    connection = serial.Serial(port=port, baudrate=115200, timeout=2.0, write_timeout=2.0)
    try:
        return SerialDeviceTransport(
            port=port, baudrate=115200, timeout=2.0, startup_delay=2.0,
            discard_initial_input=True, serial_instance=connection,
        )
    except BaseException:
        connection.close()
        raise


class RecordedTransport:
    """Keep the last reply for a faithful error diagnostic, without retrying."""
    def __init__(self, transport):
        self.transport = transport
        self.reply = None

    def exchange(self, message):
        self.reply = None
        self.reply = self.transport.exchange(message)
        return self.reply


def device_error_reply(reply):
    # Reuse SDK parsing and error construction to distinguish a valid device
    # rejection from malformed/absent replies. The adapter still interprets OK.
    from opensmell.experimental.device_protocol import error_response, loads_message
    try:
        parsed = loads_message(reply)
        expected = error_response(parsed.get("code"), parsed.get("message"))
        if all(parsed.get(key) == value for key, value in expected.items()):
            return parsed
    except (TypeError, ValueError):
        pass
    return None


class HardwareService:
    def __init__(self, *, factory=open_transport, available=serial_available,
                 ports=list_ports, clock=time.monotonic, simulated=False):
        self._factory, self._available, self._ports = factory, available, ports
        self._clock = clock
        self._simulated = simulated
        self._operation = threading.Lock()
        self._state_lock = threading.RLock()
        self._state = "disconnected"
        self._port = None
        self._adapter = self._transport = self._recorded = None
        self._message = "Select a port and click Connect."
        self._execution = None
        self._busy_until = 0.0
        self._closed = False

    @contextmanager
    def operation(self):
        if not self._operation.acquire(blocking=False):
            raise HardwareError("A hardware operation is already in progress. No second command was sent.")
        try:
            if self._closed:
                raise HardwareError("The server is shutting down.")
            yield
        finally:
            self._operation.release()

    def status(self):
        with self._state_lock:
            available = self._available()
            return {
                "available": available, "simulated": self._simulated,
                "connection": self._state, "port": self._port,
                "device_id": self._adapter.device_id if self._adapter else None,
                "capabilities": asdict(self._adapter.capabilities) if self._adapter else None,
                "message": self._message if available else INSTALL_HELP,
                "execution": deepcopy(self._execution),
                "remaining_seconds": max(0.0, self._busy_until - self._clock()),
                "operation_pending": self._operation.locked(),
            }

    def ports(self):
        if not self._available():
            return {"available": False, "ports": [], "message": INSTALL_HELP}
        try:
            return {"available": True, "ports": self._ports(), "message": "Choose a listed port or enter its name."}
        except Exception as exc:
            raise HardwareError(f"Cannot list serial ports. You can enter a port manually. Details: {exc}", 503) from exc

    def _require_idle_execution(self):
        remaining = self._busy_until - self._clock()
        if remaining > 0:
            raise HardwareError(
                f"Wait for the expected execution window ({remaining:.1f} s remaining). "
                "This is a local estimate, not a device completion signal."
            )

    def _close_transport(self):
        transport = self._transport
        self._adapter = self._recorded = self._transport = None
        self._state = "disconnected"
        if transport:
            try:
                transport.close()
            except Exception as exc:
                return f" Serial close failed: {exc}. Check the USB connection."
        return ""

    def connect(self, port):
        if not isinstance(port, str) or not port.strip() or len(port) > 256 or any(c in port for c in "\r\n\0"):
            raise HardwareError("Enter a valid serial port name, such as COM3.", 400)
        with self.operation():
            with self._state_lock:
                if not self._available():
                    raise HardwareError(INSTALL_HELP, 503)
                if self._adapter:
                    raise HardwareError("Already connected. Disconnect before choosing another port.")
                self._require_idle_execution()
                self._port = port.strip()
                self._state = "connecting"
                self._message = "Connecting; waiting for device startup, identity and capabilities…"
            try:
                from opensmell.experimental.protocol_device_adapter import ProtocolDeviceAdapter
                transport = self._factory(self._port)
                with self._state_lock:
                    self._transport = transport
                recorded = RecordedTransport(transport)
                adapter = ProtocolDeviceAdapter(recorded)
                if adapter.device_id != EXPECTED_DEVICE_ID:
                    raise HardwareError(f"Unexpected device: {adapter.device_id!r}. Expected {EXPECTED_DEVICE_ID}.")
                with self._state_lock:
                    self._adapter, self._recorded = adapter, recorded
                    self._state = "connected"
                    self._message = "Connected. Identity and capabilities received from the device."
            except Exception as exc:
                with self._state_lock:
                    cleanup = self._close_transport()
                    self._message = (f"Connection failed: {exc}. Check the selected port, USB cable and firmware; "
                                     "close any serial monitor. No render command was sent." + cleanup)
                raise HardwareError(self._message, 503) from exc
        return self.status()

    def _require_plan(self, plan):
        if not self._adapter:
            raise HardwareError("Connect the device before sending.")
        self._require_idle_execution()
        if not plan.commands:
            raise HardwareError("An empty plan can be previewed but cannot be sent to hardware.")
        try:
            self._adapter.capabilities.require_plan(plan)
        except ValueError as exc:
            raise HardwareError(f"Plan incompatible with the device: {exc}. Nothing was sent.") from exc

    def check(self, previews, ticket):
        # Lock order matches send: preview state then hardware state. No I/O.
        with previews.current(ticket) as entry, self._state_lock:
            if self._operation.locked():
                raise HardwareError("A hardware operation is in progress.")
            self._require_plan(entry["plan"])
        return {"ready": True, "message": "Ready to send"}

    def send(self, previews, ticket):
        with self.operation():
            with previews.current(ticket) as entry, self._state_lock:
                self._require_plan(entry["plan"])
                plan = deepcopy(entry["plan"])
                # Atomic freshness check/consumption. Even a failed exchange
                # cannot reuse this ticket and duplicate a possible command.
                entry["used"] = True
                self._execution = {"state": "sending", "duration": plan.duration,
                                   "preview_id": ticket["preview_id"], "response": None}
                self._message = "Sending the previewed plan…"
            try:
                response = self._adapter.render(plan)
            except Exception as exc:
                rejection = device_error_reply(self._recorded.reply)
                with self._state_lock:
                    if rejection:
                        self._execution.update(state="rejected", response=rejection)
                        self._message = f"Device rejected the command: {rejection['code']}: {rejection['message']}. No automatic retry."
                    else:
                        self._execution.update(state="uncertain", detail=str(exc))
                        self._busy_until = self._clock() + plan.duration
                        cleanup = self._close_transport()
                        self._message = (f"Execution uncertain: the command may have reached the device. {exc}. "
                                         "The connection was closed. Check the LEDs before reconnecting; no automatic retry." + cleanup)
                raise HardwareError(self._message, 502) from exc
            with self._state_lock:
                self._execution.update(state="accepted", response=response)
                self._busy_until = self._clock() + plan.duration
                self._message = "Command accepted. The device does not report completion or LED state."
        return self.status()

    def disconnect(self):
        with self.operation(), self._state_lock:
            cleanup = self._close_transport()
            self._message = "Disconnected. Closing the link does not stop an accepted command." + cleanup
        return self.status()

    def close(self):
        # Server shutdown waits for any bounded serial exchange before closing.
        with self._operation, self._state_lock:
            self._closed = True
            self._close_transport()
