"""Bounded, one-shot sequencing over an exclusively owned lifecycle client.

No new wire protocol, retries, reconnects, physical scheduling or odor claims.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import json
from itertools import islice
import threading
import time
import uuid

from .rendering import RenderingPlan

MAX_STEPS = 16
MAX_TOTAL_DURATION = 120


@dataclass(frozen=True)
class SequenceStep:
    """An explicit plan and caller-owned JSON context; copied by SequenceRunner."""
    step_id: str
    plan: RenderingPlan
    context: dict = field(default_factory=dict)


class SequenceRunner:
    """Own a negotiated LifecycleAdapter, run once, close on every exit.

    request_stop() is cooperative and serialized with synchronous exchanges. It
    prevents subsequent sends when processed; it cannot preempt a blocked I/O.
    on_progress receives passive copies and may request_stop(). A failing callback
    aborts the sequence. Never share the owned client with another caller.
    """
    def __init__(self, client, steps, *, on_progress=None):
        steps = deepcopy(list(islice(steps, MAX_STEPS + 1)))
        if not 1 <= len(steps) <= MAX_STEPS:
            raise ValueError("A sequence requires 1–16 explicit steps")
        ids = set()
        for step in steps:
            if not isinstance(step, SequenceStep) or not isinstance(step.plan, RenderingPlan):
                raise TypeError("SequenceStep with RenderingPlan required")
            if (not isinstance(step.step_id, str) or not step.step_id.strip()
                    or len(step.step_id) > 128 or step.step_id in ids):
                raise ValueError("Unique step IDs of 1–128 characters required")
            ids.add(step.step_id)
            if not step.plan.commands or not isinstance(step.context, dict):
                raise ValueError("Nonempty plan and JSON object context required")
            # Reconstruct mutable plans: validation must not depend on prior construction.
            step.plan.__post_init__()
            json.dumps({"plan": asdict(step.plan), "context": step.context}, allow_nan=False)
        if sum(s.plan.duration for s in steps) > MAX_TOTAL_DURATION:
            raise ValueError("Summed plan duration exceeds 120 seconds")
        current = client.execution
        if current and current["state"] in {"accepted", "running", "unknown"}:
            raise ValueError("Cannot own a client with active or uncertain execution")
        self._client, self._steps, self._callback = client, steps, on_progress
        self._lock = threading.RLock()
        self._started = self._finished = self._stop = self._callback_failed = False
        self._index = None
        self._report = {
            "format": "org.opensmell.experimental.sequence", "version": "0.1",
            "experimental": True, "physical_validation": False, "status": "not_started",
            "run_id": uuid.uuid4().hex, "device_id": client.device_id,
            "capabilities": asdict(client.capabilities), "stop_requested": False,
            "steps": [{"step_id": s.step_id, "plan": asdict(s.plan),
                       "context": s.context, "state": "not_attempted", "execution": None}
                      for s in steps],
            "limitations": ["Exclusive one-shot software session; no retry, reconnect or durable reconciliation.",
                            "Only correlated endpoint observations establish completion or Stop; no physical or odor result.",
                            "Stop is cooperative and cannot interrupt synchronous transport exchanges.",
                            "Caller context and endpoint identity are declarations, not authenticated provenance."]}

    @property
    def report(self):
        with self._lock:
            return deepcopy(self._report)

    def request_stop(self):
        """Cancel later steps; stop a known active execution at the next checkpoint."""
        with self._lock:
            if self._finished:
                return False
            self._stop = self._report["stop_requested"] = True
            return True

    def _publish(self):
        if self._callback and not self._callback_failed:
            try:
                self._callback(self.report)
            except BaseException:
                self._callback_failed = True
                raise

    def _record(self, execution):
        step = self._report["steps"][self._index]
        step.update(state=execution["state"], execution=deepcopy(execution))
        self._publish()

    def run(self):
        with self._lock:
            if self._started:
                raise ValueError("Sequence already consumed; create a new explicit session")
            self._started = True
        try:
            # All live capability checks precede every render, including late steps.
            for step in self._steps:
                self._client.capabilities.require_plan(step.plan)
            with self._lock:
                self._report["status"] = "running"
                self._publish()
            for index, step in enumerate(self._steps):
                with self._lock:
                    if self._stop:
                        self._report["status"] = "cancelled"
                        break
                    self._index = index
                    self._publish()
                    # A callback can cancel at this pre-send checkpoint.
                    if self._stop:
                        self._report["status"] = "cancelled"
                        break
                    request_id = f"{self._report['run_id']}-{index}"
                    pending = self._report["steps"][index]
                    pending.update(request_id=request_id, state="unknown",
                                   execution={"request_id": request_id, "state": "unknown", "execution_id": None})
                    self._publish()  # Durable intent is uncertainty until an actual receipt.
                    if self._stop:
                        pending.update(state="not_attempted", execution=None)
                        pending.pop("request_id")
                        self._report["status"] = "cancelled"
                        break
                    execution = self._client.render(step.plan, request_id=request_id)
                    self._record(execution)
                deadline = time.monotonic() + step.plan.duration + 3
                while execution["state"] in {"accepted", "running"}:
                    with self._lock:
                        if self._stop:
                            execution = self._client.stop(execution["execution_id"])
                            if execution["state"] in {"accepted", "running"}:
                                self._client.close()
                                execution = self._client.execution
                            self._record(execution)
                            break
                        if time.monotonic() >= deadline:
                            self._client.close()
                            execution = self._client.execution
                            self._record(execution)
                            break
                        execution = self._client.status(execution["execution_id"])
                        self._record(execution)
                    if execution["state"] in {"accepted", "running"}:
                        time.sleep(0.02)
                with self._lock:
                    if execution["state"] != "completed":
                        self._report["status"] = execution["state"]
                        break
                    if self._stop:
                        self._report["status"] = "cancelled"
                        break
            else:
                with self._lock:
                    self._report["status"] = "completed"
        except (Exception, KeyboardInterrupt) as error:
            with self._lock:
                self._client.close()
                current = self._client.execution
                if (self._index is not None and current
                        and current["request_id"] == self._report["steps"][self._index].get("request_id")):
                    self._report["steps"][self._index].update(state=current["state"], execution=current)
                self._report.update(status="unknown" if self._index is not None else "invalid", detail=str(error) or type(error).__name__)
        finally:
            with self._lock:
                self._client.close()
                current = self._client.execution
                if (self._index is not None and current
                        and current["request_id"] == self._report["steps"][self._index].get("request_id")):
                    self._report["steps"][self._index].update(state=current["state"], execution=current)
                self._finished = True
                self._publish()
        return self.report
