"""App-local lifecycle experiment, not an extension of Device Protocol 0.1.

No serial access. The simulated endpoint owns execution timing and identifiers.
Lifecycle messages are JSON across the same recorded exchange boundary.
"""
import json
import time
import uuid

from opensmell.experimental.device_capabilities import DeviceCapabilities, DeviceChannelCapability
from opensmell.experimental.device_protocol import (
    hello_response, capabilities_response, ok_response, parse_render_request, error_response,
)
from .hardware import HardwareService, HardwareError

SIMULATOR_ID = "opensmell-local-simulator-001"
LIFECYCLE = "local-simulator-lifecycle-v1"
ERROR_PROFILE = "local-simulator-errors-v1"


class Rejection(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class SimulatedEndpoint:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.closed = False
        self.execution = None
        self.deadline = 0
        self.capabilities = DeviceCapabilities(
            device_id=SIMULATOR_ID,
            channels=[DeviceChannelCapability(channel=i) for i in range(3)],
            min_duration=0.1, max_duration=30,
        )

    def exchange(self, message):
        if self.closed:
            raise OSError("Simulated link is closed")
        request = None
        try:
            request = json.loads(message)
            return json.dumps(self._handle(request))
        except (ValueError, TypeError, KeyError) as exc:
            reply = {**error_response(getattr(exc, "code", "invalid_request"), str(exc)),
                     "error_profile": ERROR_PROFILE}
            if isinstance(request, dict):
                for field in ("type", "execution_id"):
                    value = request.get(field)
                    if isinstance(value, str) and 0 < len(value) <= 128:
                        reply["request_type" if field == "type" else field] = value
            return json.dumps(reply)

    def _handle(self, request):
        if not isinstance(request, dict):
            raise ValueError("Object required")
        kind = request.get("type")
        if not isinstance(kind, str) or not kind:
            raise ValueError("Request type required")
        if kind in ("hello", "get_capabilities", "render") and request.get("protocol_version") != "0.1":
            raise ValueError("Unsupported protocol")
        if kind == "hello":
            reply = hello_response(SIMULATOR_ID)
        elif kind == "get_capabilities":
            reply = capabilities_response(self.capabilities)
        elif kind == "lifecycle_capabilities":
            reply = {"profile": LIFECYCLE, "status": True, "stop": True, "errors": ERROR_PROFILE}
        elif kind == "render":
            self._advance()
            if self.execution and self.execution["state"] == "running":
                raise Rejection("busy", "An execution is already running")
            plan = parse_render_request(request)
            self.capabilities.require_plan(plan)
            self.execution = {"execution_id": uuid.uuid4().hex, "state": "running"}
            self.deadline = self.clock() + plan.duration
            reply = {**ok_response(), "execution_id": self.execution["execution_id"]}
        elif kind in {"execution_status", "stop"}:
            if request.get("profile") != LIFECYCLE:
                raise Rejection("unsupported_profile", "Unsupported lifecycle profile")
            if not self.execution or request.get("execution_id") != self.execution["execution_id"]:
                raise Rejection("unknown_execution", "Unknown execution identifier")
            self._advance()
            if kind == "stop" and self.execution["state"] == "running":
                self.execution["state"] = "stopped"
            reply = {"profile": LIFECYCLE, **self.execution}
        else:
            raise Rejection("unsupported_request", "Unsupported simulator request")
        return reply

    def _advance(self):
        if self.execution and self.execution["state"] == "running" and self.clock() >= self.deadline:
            self.execution["state"] = "completed"

    def close(self):
        self.closed = True


class SimulatedHardwareService(HardwareService):
    unconfirmed_send_state = "unknown"
    endpoint_port = "SIMULATED"
    endpoint_description = "Software only; no physical output"
    endpoint_label = "Simulated device"
    endpoint_scope = "No physical output."

    def __init__(self, *, clock=time.monotonic, factory=None, expected_device_id=SIMULATOR_ID):
        super().__init__(factory=factory or (lambda _: SimulatedEndpoint(clock)),
                         available=lambda: True,
                         ports=lambda: [{"port": self.endpoint_port, "description": self.endpoint_description}],
                         clock=clock, simulated=True, expected_device_id=expected_device_id)
        self._lifecycle = None

    def connect(self, port):
        if port != self.endpoint_port:
            raise HardwareError(f"This software mode accepts only {self.endpoint_port}.", 400)
        super().connect(port)
        with self.operation(), self._state_lock:
            try:
                reply = json.loads(self._recorded.exchange(json.dumps({"type": "lifecycle_capabilities"})))
                if (not isinstance(reply, dict)
                        or any(reply.get(k) != v for k, v in {"profile": LIFECYCLE, "status": True, "stop": True}.items())
                        or reply.get("errors", ERROR_PROFILE) != ERROR_PROFILE):
                    raise ValueError("Unsupported lifecycle capabilities")
                self._lifecycle = reply
            except Exception as exc:
                self._close_transport()
                raise HardwareError(str(exc), 502) from exc
        return self.status()

    def _observe(self, action="execution_status"):
        execution = self._execution
        if not self._adapter or not self._lifecycle or not execution or execution["state"] not in {"accepted", "running"}:
            return
        try:
            execution_id = execution["response"]["execution_id"]
            reply = json.loads(self._recorded.exchange(json.dumps({
                "type": action, "profile": LIFECYCLE, "execution_id": execution_id,
            })))
            if (reply.get("profile") != LIFECYCLE or reply.get("execution_id") != execution_id
                    or reply.get("state") not in {"running", "completed", "stopped"}):
                raise ValueError("Invalid or mismatched execution response")
            execution.update(state=reply["state"], execution_id=execution_id, observation=reply)
            if reply["state"] != "running":
                self._busy_until = 0
            self._message = self.endpoint_label + " reports: " + reply["state"] + ". " + self.endpoint_scope
        except Exception as exc:
            execution.update(state="unknown", detail=str(exc))
            self._close_transport()
            self._message = "Execution unknown after link or response failure. No automatic retry."

    def _require_idle_execution(self):
        self._observe()
        if self._execution and self._execution["state"] == "running":
            raise HardwareError("The software endpoint reports an active execution. Wait or use Stop.")
        super()._require_idle_execution()

    def status(self):
        with self._state_lock:
            # Do not race a render exchange. All endpoint exchanges are serialized.
            if not self._operation.locked():
                self._observe()
            result = super().status()
            result["lifecycle_capabilities"] = self._lifecycle if self._adapter else None
            return result

    def stop(self, execution_id):
        with self.operation(), self._state_lock:
            if not self._adapter or not self._lifecycle:
                raise HardwareError("No connected lifecycle-capable software endpoint.")
            if not self._execution or execution_id != self._execution.get("execution_id"):
                raise HardwareError("Stale or unknown execution identifier.")
            self._observe("stop")
        return self.status()

    def disconnect(self):
        with self.operation(), self._state_lock:
            if self._execution and self._execution["state"] in {"accepted", "running"}:
                self._execution.update(state="unknown", detail="Link closed before terminal confirmation")
            self._close_transport()
            self._lifecycle = None
            self._message = "Software link closed. Unconfirmed executions remain unknown."
        return self.status()
