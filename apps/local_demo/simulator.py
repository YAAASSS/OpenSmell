"""Local Explorer binding for the experimental SDK simulator."""
import json
import time
from .hardware import HardwareService, HardwareError
from opensmell.experimental.lifecycle_simulator import (
    SimulatedEndpoint, Rejection, SIMULATOR_ID, LIFECYCLE, ERROR_PROFILE,
)


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
