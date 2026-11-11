"""Experimental SDK software lifecycle endpoint, not an extension of Device Protocol 0.1.

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


