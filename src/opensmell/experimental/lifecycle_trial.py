"""Explicit installed adapter-author trial over trusted software process pipes.

This runs three bounded plans. It never chooses a device, retries, reconnects or
opens serial/GPIO. The selected executable is trusted and is not sandboxed.
"""
from copy import deepcopy
from dataclasses import asdict
import json
import time

from .._json import decode_bytes
from ..exceptions import OpenSmellError
from .frame_export import _snapshot, encode_plan_frame
from .lifecycle_adapter import LifecycleAdapter
from .process_transport import ProcessTransport
from .rendering import DeviceCommand, RenderingPlan

MAX_BYTES = 8 * 1048576


class _TrialEnd(Exception):
    def __init__(self, status, detail):
        self.status, self.detail = status, detail


def lifecycle_trial(raw, command, *, expected_device_id, on_progress=None):
    """Try completion, Stop and explicit link closure using one offline-plan0.1.

    Require an explicit 5-second plan, recomputed from its embedded snapshots.
    A declared 0.1-second derivative uses the same commands for completion; the
    original plan is used for Stop and closure. Preflight both durations against
    live capabilities before any render. Preserve exact input bytes and actual
    exchanges. Only a received terminal response establishes completion/Stop.
    """
    if not isinstance(raw, bytes):
        raise TypeError("Offline plan must be bytes")
    if len(raw) > MAX_BYTES:
        raise ValueError("Offline plan exceeds 8 MiB")
    report = {"format": "org.opensmell.experimental.lifecycle-trial", "version": "0.1",
              "status": "incomplete", "experimental": True, "physical_validation": False,
              "scope": "Explicit trusted software process; no physical output observations",
              "input": _snapshot(raw), "phase": "preflight", "transcript": [], "results": {},
              "acceptance": "not_attempted", "execution": None,
              "limitations": ["Source/profile hashes are declarations; exact input bytes are retained, not authenticated.",
                              "Supplied commands have application-defined channel meaning; no odor result is established.",
                              "One software process, latest execution only; no retry, reconnect or durable reconciliation.",
                              "The command is trusted and not sandboxed; arguments and source data appear in this report."]}
    def save():
        if on_progress:
            on_progress(deepcopy(report))
    save()
    try:
        if (not isinstance(command, (list, tuple)) or not 1 <= len(command) <= 64
                or any(not isinstance(arg, str) or "\0" in arg for arg in command)
                or not command[0].strip() or sum(len(arg) for arg in command) > 16384):
            raise ValueError("Explicit command JSON must be an executable/argument array (max64 items/16KiB)")
        if not isinstance(expected_device_id, str) or not expected_device_id.strip() or len(expected_device_id) > 128:
            raise ValueError("Expected device identity of 1–128 characters is required")
        artifact = decode_bytes(raw)
        try:
            target = artifact["profile"]["document"]["capabilities"]
        except (KeyError, TypeError):
            raise ValueError("Expected an offline-plan with an explicit mapping/capability profile") from None
        exported = encode_plan_frame(raw, json.dumps(target, allow_nan=False).encode())
        message = decode_bytes(exported["frame"]["line"].encode())
        long_plan = RenderingPlan([DeviceCommand(c["channel"], c["intensity"]) for c in message["commands"]], message["duration"])
        if long_plan.duration != 5:
            raise ValueError("This bounded trial requires an explicit 5-second offline plan")
        short_plan = RenderingPlan(long_plan.commands, 0.1)
        report.update(command=list(command), expected_device_id=expected_device_id,
                      context=exported["context"], plans={"completion": asdict(short_plan),
                                                       "stop": asdict(long_plan), "disconnect": asdict(long_plan)})
    except (OpenSmellError, ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        report.update(status="invalid", detail=str(error)); save(); return report

    transport = None
    client = None
    class Recorded:
        def exchange(self, text):
            entry = {"phase": report["phase"], "request_line": text + "\n"}
            report["transcript"].append(entry)
            if decode_bytes(text.encode()).get("type") == "render":
                report["acceptance"] = "unknown"
            save()
            try:
                reply = transport.exchange(text)
                entry["response_line"] = reply
                return reply
            except Exception as error:
                entry.update(error=str(error), diagnostic=deepcopy(transport.last_exchange))
                raise
            finally:
                save()
        def close(self):
            transport.close()
    def expect(run, state):
        if run["state"] in {"accepted", "rejected"}:
            report["acceptance"] = run["state"]
        report["execution"] = deepcopy(run)
        report["results"][report["phase"]] = deepcopy(run)
        save()
        if run["state"] != state:
            status = run["state"] if run["state"] in {"unknown", "rejected"} else "failed"
            raise _TrialEnd(status, f"Expected {state}; received {run['state']}")
    try:
        report["phase"] = "connect"; save()
        transport = ProcessTransport(list(command), startup_timeout=5)
        client = LifecycleAdapter(Recorded(), expected_device_id=expected_device_id)
        report["capabilities"] = asdict(client.capabilities)
        # Every plan is checked before the first execution, including derived duration.
        client.capabilities.require_plan(short_plan)
        client.capabilities.require_plan(long_plan)
        report["phase"] = "completion"; save()
        run = client.render(short_plan, request_id="trial-completion")
        expect(run, "accepted"); report["acceptance"] = "accepted"
        deadline = time.monotonic() + 3
        while run["state"] in {"accepted", "running"} and time.monotonic() < deadline:
            time.sleep(0.02)
            run = client.status(run["execution_id"])
            report["execution"] = deepcopy(run); save()
        if run["state"] in {"accepted", "running"}:
            client.close()
            expect(client.execution, "completed")
        expect(run, "completed")
        before = len(report["transcript"])
        try:
            client.render(short_plan, request_id="trial-completion")
        except ValueError:
            report["duplicate_request_refused_before_io"] = len(report["transcript"]) == before
        else:
            raise _TrialEnd("failed", "Duplicate client request ID was accepted")
        report["phase"] = "stop"; save()
        run = client.render(long_plan, request_id="trial-stop")
        expect(run, "accepted"); report["acceptance"] = "accepted"
        expect(client.stop(run["execution_id"]), "stopped")
        report["phase"] = "disconnect"; save()
        run = client.render(long_plan, request_id="trial-disconnect")
        expect(run, "accepted"); report["acceptance"] = "accepted"
        client.close()
        expect(client.execution, "unknown")
        report.update(status="passed", phase="finished")
    except _TrialEnd as error:
        report.update(status=error.status, detail=error.detail)
    except Exception as error:
        failed_exchange = any("error" in entry for entry in report["transcript"])
        report.update(status="incompatible" if report["phase"] == "connect" and transport and not failed_exchange else "unknown",
                      detail=str(error))
    finally:
        if client:
            client.close()
            report["execution"] = client.execution
        if transport:
            transport.close()
        save()
    return report
