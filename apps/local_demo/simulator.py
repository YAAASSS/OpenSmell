"""App-local lifecycle experiment, not an extension of Device Protocol 0.1.

No serial access. The simulated endpoint owns execution timing and identifiers.
Lifecycle messages are JSON across the same recorded exchange boundary.
"""
import json
import time
import uuid

from opensmell.experimental.device_capabilities import DeviceCapabilities, DeviceChannelCapability
from opensmell.experimental.device_protocol import (
    hello_response, capabilities_response, ok_response, parse_render_request,
)
from .hardware import HardwareService, HardwareError

SIMULATOR_ID = "opensmell-local-simulator-001"
LIFECYCLE = "local-simulator-lifecycle-v1"


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
        request = json.loads(message)
        kind = request["type"]
        if kind == "hello":
            reply = hello_response(SIMULATOR_ID)
        elif kind == "get_capabilities":
            reply = capabilities_response(self.capabilities)
        elif kind == "lifecycle_capabilities":
            reply = {"profile": LIFECYCLE, "status": True, "stop": True}
        elif kind == "render":
            self._advance()
            if self.execution and self.execution["state"] == "running":
                raise ValueError("An execution is already running")
            plan = parse_render_request(request)
            self.capabilities.require_plan(plan)
            self.execution = {"execution_id": uuid.uuid4().hex, "state": "running"}
            self.deadline = self.clock() + plan.duration
            reply = {**ok_response(), "execution_id": self.execution["execution_id"]}
        elif kind in {"execution_status", "stop"}:
            if request.get("profile") != LIFECYCLE:
                raise ValueError("Unsupported lifecycle profile")
            if not self.execution or request.get("execution_id") != self.execution["execution_id"]:
                raise ValueError("Unknown execution identifier")
            self._advance()
            if kind == "stop" and self.execution["state"] == "running":
                self.execution["state"] = "stopped"
            reply = {"profile": LIFECYCLE, **self.execution}
        else:
            raise ValueError("Unsupported simulator request")
        return json.dumps(reply)

    def _advance(self):
        if self.execution and self.execution["state"] == "running" and self.clock() >= self.deadline:
            self.execution["state"] = "completed"

    def close(self):
        self.closed = True


class SimulatedHardwareService(HardwareService):
    def __init__(self, *, clock=time.monotonic, factory=None, expected_device_id=SIMULATOR_ID):
        super().__init__(factory=factory or (lambda _: SimulatedEndpoint(clock)),
                         available=lambda: True,
                         ports=lambda: [{"port": "SIMULATED", "description": "Software only; no physical output"}],
                         clock=clock, simulated=True, expected_device_id=expected_device_id)
        self._lifecycle = None

    def connect(self, port):
        if port != "SIMULATED":
            raise HardwareError("Simulator mode accepts only SIMULATED.", 400)
        super().connect(port)
        with self.operation(), self._state_lock:
            try:
                reply = json.loads(self._recorded.exchange(json.dumps({"type": "lifecycle_capabilities"})))
                if reply != {"profile": LIFECYCLE, "status": True, "stop": True}:
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
            self._message = "Simulated device reports: " + reply["state"] + ". No physical output."
        except Exception as exc:
            execution.update(state="unknown", detail=str(exc))
            self._close_transport()
            self._message = "Execution unknown after link or response failure. No automatic retry."

    def _require_idle_execution(self):
        self._observe()
        if self._execution and self._execution["state"] == "running":
            raise HardwareError("The simulator reports an active execution. Wait or use Stop.")
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
                raise HardwareError("No connected lifecycle-capable simulator.")
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
            self._message = "Simulated link closed. Unconfirmed executions remain unknown."
        return self.status()
