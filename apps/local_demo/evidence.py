"""Bounded last-execution evidence; snapshots never contact a device."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import threading
import uuid

MAX_EVENTS = 256
MAX_TEXT = 65536
MAX_TRACE_BYTES = 1024 * 1024


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class ExecutionEvidence:
    def __init__(self):
        self.lock = threading.RLock()
        self.report = None
        self.trace_bytes = 0

    def begin(self, *, plan, source, device_id, capabilities, simulated):
        with self.lock:
            self.trace_bytes = 0
            self.report = {
                "format": "opensmell.local-execution-evidence.v1", "experimental": True,
                "report_id": uuid.uuid4().hex, "started_at": utc_now(),
                "simulated": simulated, "device_id": device_id,
                "capabilities": deepcopy(capabilities), "source": deepcopy(source),
                "plan": deepcopy(plan), "exchanges": [], "omitted_events": 0,
                "limitations": ["Client-side record, not independently authenticated telemetry.",
                                "Acceptance is not completion. No measured olfactory result.",
                                "Only the latest send is retained in memory; export before the next send or server shutdown."],
            }
            return self.report["report_id"]

    def record(self, request, response=None, error=None):
        with self.lock:
            if self.report is None:
                return
            event = {"observed_at": utc_now(), "request_text": request[:MAX_TEXT]}
            if isinstance(response, str):
                event["response_text"] = response[:MAX_TEXT]
            elif response is not None:
                event["invalid_response_type"] = type(response).__name__
            if error is not None:
                event["transport_error"] = str(error)[:MAX_TEXT]
            event["text_truncated"] = any(len(s) > MAX_TEXT for s in (request, response if isinstance(response, str) else "", str(error or "")))
            size = len(json.dumps(event, ensure_ascii=False).encode("utf-8"))
            if len(self.report["exchanges"]) >= MAX_EVENTS or self.trace_bytes + size > MAX_TRACE_BYTES:
                self.report["omitted_events"] += 1
                return
            self.trace_bytes += size
            self.report["exchanges"].append(event)

    def snapshot(self, execution):
        with self.lock:
            if self.report is None:
                return None
            result = deepcopy(self.report)
            result["snapshot_at"] = utc_now()
            result["execution"] = deepcopy(execution)
            result["measured_olfactory_result"] = None
            return result
