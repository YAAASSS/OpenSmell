"""Experimental RFC-0014 software lifecycle client, independent of applications.

Owns its transport. No automatic retry, reconnection, scheduling or physical
isolation guarantee. Terminal snapshots are passive and remain stable.
"""
from copy import deepcopy
import threading

from .device_protocol import (
    dumps_message, loads_message, render_request_message, require_ok_response,
    error_response,
)
from .protocol_device_adapter import ProtocolDeviceAdapter
from .lifecycle_simulator import LIFECYCLE, ERROR_PROFILE


class LifecycleAdapter:
    """Serialized, explicit connect/render/status/stop/close software session.

    Construct with a trusted transport and a pinned expected device ID. Each
    render requires a caller-owned unique request_id (never reused in a session).
    Repeated request IDs fail before I/O, including after an ambiguous reply.
    """

    def __init__(self, transport, *, expected_device_id):
        self._transport = transport
        self._lock = threading.RLock()
        self._closed = False
        self._execution = None
        self._used = set()
        self._execution_ids = set()
        try:
            if not isinstance(expected_device_id, str) or not expected_device_id.strip():
                raise ValueError("Expected device ID required")
            self._adapter = ProtocolDeviceAdapter(transport)
            if self._adapter.device_id != expected_device_id:
                raise ValueError("Unexpected device identity")
            reply = self._exchange({"type": "lifecycle_capabilities"})
            if (reply.get("profile") != LIFECYCLE or reply.get("status") is not True
                    or reply.get("stop") is not True
                    or reply.get("errors", ERROR_PROFILE) != ERROR_PROFILE):
                raise ValueError("Unsupported lifecycle capabilities")
        except BaseException:
            self.close()
            raise

    @property
    def device_id(self):
        return self._adapter.device_id

    @property
    def capabilities(self):
        return deepcopy(self._adapter.capabilities)

    @property
    def execution(self):
        """Passive copy, including after close; never polls the endpoint."""
        with self._lock:
            return deepcopy(self._execution)

    def _exchange(self, request):
        return loads_message(self._transport.exchange(dumps_message(request)))

    def _require_open(self):
        if self._closed:
            raise ValueError("Session closed; no automatic reconnect")

    def render(self, plan, *, request_id):
        with self._lock:
            self._require_open()
            if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
                raise ValueError("A request ID of 1–128 characters is required")
            if request_id in self._used:
                raise ValueError("Request ID already consumed; no duplicate send")
            if self._execution and self._execution["state"] in {"accepted", "running"}:
                raise ValueError("Execution active; observe completion or Stop first")
            self._adapter.capabilities.require_plan(plan)
            if not plan.commands:
                raise ValueError("Empty plans cannot be sent")
            message = render_request_message(plan)
            self._used.add(request_id)
            self._execution = {"request_id": request_id, "state": "unknown",
                               "execution_id": None}
            try:
                reply = self._exchange(message)
                if reply.get("type") == "error":
                    expected = error_response(reply.get("code"), reply.get("message"))
                    if not all(reply.get(k) == v for k, v in expected.items()):
                        raise ValueError("Invalid refusal")
                    self._execution.update(state="rejected", response=reply)
                    return self.execution
                require_ok_response(reply)
                eid = reply.get("execution_id")
                if not isinstance(eid, str) or not eid or len(eid) > 128 or eid in self._execution_ids:
                    raise ValueError("Missing or reused execution ID")
                self._execution_ids.add(eid)
                self._execution.update(state="accepted", execution_id=eid, response=reply)
            except Exception as exc:
                self._execution["detail"] = str(exc)
                self.close()
            return self.execution

    def _observe(self, action, execution_id):
        with self._lock:
            if not self._execution or execution_id != self._execution["execution_id"] or execution_id is None:
                raise ValueError("Stale or unknown execution ID")
            if self._execution["state"] not in {"accepted", "running"}:
                return self.execution
            self._require_open()
            try:
                reply = self._exchange({"type": action, "profile": LIFECYCLE,
                                        "execution_id": execution_id})
                if (reply.get("profile") != LIFECYCLE or reply.get("execution_id") != execution_id
                        or reply.get("state") not in {"running", "completed", "stopped"}):
                    raise ValueError("Invalid or mismatched execution observation")
                self._execution.update(state=reply["state"], observation=reply)
            except Exception as exc:
                self._execution.update(state="unknown", detail=str(exc))
                self.close()
            return self.execution

    def status(self, execution_id):
        return self._observe("execution_status", execution_id)

    def stop(self, execution_id):
        return self._observe("stop", execution_id)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._execution and self._execution["state"] in {"accepted", "running"}:
                self._execution.update(state="unknown", detail="Link closed before terminal confirmation")
            try:
                self._transport.close()
            except Exception:
                pass  # Closing cannot turn an unknown execution into a terminal one.

    def __enter__(self):
        self._require_open()
        return self

    def __exit__(self, *_):
        self.close()
