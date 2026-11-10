"""Explicit hardware actions, isolated from graph loading and preview mapping."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
import importlib.util
import json

from .evidence import ExecutionEvidence
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
    def __init__(self, transport, evidence=None):
        self.transport = transport
        self.evidence = evidence
        self.reply = None

    def exchange(self, message):
        self.reply = None
        try:
            self.reply = self.transport.exchange(message)
        except Exception as exc:
            if self.evidence:
                self.evidence.record(message, error=type(exc).__name__ + ": " + str(exc))
            raise
        if self.evidence:
            self.evidence.record(message, response=self.reply)
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
    unconfirmed_send_state = "uncertain"

    def __init__(self, *, factory=open_transport, available=serial_available,
                 ports=list_ports, clock=time.monotonic, simulated=False, expected_device_id=EXPECTED_DEVICE_ID):
        self._factory, self._available, self._ports = factory, available, ports
        self._clock = clock
        self._simulated = simulated
        self._expected_device_id = expected_device_id
        self._operation = threading.Lock()
        self._state_lock = threading.RLock()
        self._state = "disconnected"
        self._port = None
        self._adapter = self._transport = self._recorded = None
        self._message = "Select a port and click Connect."
        self._execution = None
        self._evidence = ExecutionEvidence()
        self._evidence_history = []
        self._history_bytes = 0
        self._evicted_reports = 0
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
                "evidence_id": self._execution.get("report_id") if self._execution else None,
                "remaining_seconds": max(0.0, self._busy_until - self._clock()),
                "operation_pending": self._operation.locked(),
                "evidence_history": self._history_summary(),
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
                if adapter.device_id != self._expected_device_id:
                    raise HardwareError(f"Unexpected device: {adapter.device_id!r}. Expected {self._expected_device_id}.")
                with self._state_lock:
                    self._adapter, self._recorded = adapter, recorded
                    self._state = "connected"
                    self._message = "Connected. Identity and capabilities received from the device."
            except Exception as exc:
                with self._state_lock:
                    cleanup = self._close_transport()
                    guidance = ("Check the software command, identity and capability replies. " if self._simulated
                                else "Check the selected port, USB cable and firmware; close any serial monitor. ")
                    self._message = f"Connection failed: {exc}. " + guidance + "No render command was sent." + cleanup
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
                self._archive_evidence()
                report_id = self._evidence.begin(
                    plan=asdict(plan), source=entry.get("source"), device_id=self._adapter.device_id,
                    capabilities=asdict(self._adapter.capabilities), simulated=self._simulated,
                )
                self._recorded.evidence = self._evidence
                self._execution = {"state": "sending", "report_id": report_id, "duration": plan.duration,
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
                        self._execution.update(state=self.unconfirmed_send_state, detail=str(exc))
                        self._busy_until = self._clock() + plan.duration
                        cleanup = self._close_transport()
                        self._message = (f"Execution {self.unconfirmed_send_state}: the command may have reached the device. {exc}. "
                                         "The connection was closed; no automatic retry." + cleanup)
                raise HardwareError(self._message, 502) from exc
            with self._state_lock:
                self._execution.update(state="accepted", response=response)
                self._busy_until = self._clock() + plan.duration
                self._message = "Command accepted. The device does not report completion or LED state."
        return self.status()

    def _archive_evidence(self):
        # Called under the state lock, before replacing the current execution.
        report = self._evidence.snapshot(self._execution)
        if report is None:
            return
        size = len(json.dumps(report, ensure_ascii=False).encode("utf-8"))
        self._evidence_history.append((report, size))
        self._history_bytes += size
        # Nine archived reports plus the current report; large sources can evict
        # earlier. The current report retains the existing import/trace limits.
        while len(self._evidence_history) > 9 or self._history_bytes > 8 * 1024 * 1024:
            _, removed = self._evidence_history.pop(0)
            self._history_bytes -= removed
            self._evicted_reports += 1

    def _history_summary(self):
        reports = [report for report, _ in self._evidence_history]
        if self._evidence.report is not None:
            reports.append({**self._evidence.report, "execution": self._execution})
        return {
            "reports": [{"report_id": r["report_id"], "started_at": r["started_at"],
                         "device_id": r["device_id"], "state": r["execution"]["state"],
                         "duration": r["plan"]["duration"]} for r in reversed(reports)],
            "evicted_reports": self._evicted_reports,
            "max_reports": 10, "max_archived_bytes": 8 * 1024 * 1024,
            "persistent": False,
        }

    def evidence_bundle(self):
        # One passive, coherent snapshot, including custom adapter metadata.
        with self._state_lock:
            if self._operation.locked():
                raise HardwareError("Wait for the current operation before exporting evidence.")
            history = self._history_summary()
            return {
                "format": "opensmell.local-execution-history.v1", "experimental": True,
                "retention": history,
                "reports": [self.evidence(item["report_id"]) for item in history["reports"]],
                "limitations": ["Volatile client-side snapshots, not authenticated telemetry.",
                                "Evicted reports are not included. No command replay or measured olfactory result."],
            }

    def evidence(self, report_id):
        # Snapshot only: deliberately do not call status(), which can poll a simulator.
        with self._state_lock:
            if self._operation.locked():
                raise HardwareError("Wait for the current operation before exporting evidence.")
            result = self._evidence.snapshot(self._execution)
            if result is not None and report_id == result["report_id"]:
                return result
            for archived, _ in self._evidence_history:
                if archived["report_id"] == report_id:
                    return deepcopy(archived)
            raise HardwareError("Evidence is unavailable or evicted from the bounded history.", 409)

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
