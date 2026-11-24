"""Offline plans to an exclusively owned caller-supplied lifecycle transport."""
from copy import deepcopy
import json

from .._json import decode_bytes
from ..exceptions import OpenSmellError
from .frame_export import _snapshot, encode_plan_frame
from .lifecycle_adapter import LifecycleAdapter
from .rendering import DeviceCommand, RenderingPlan
from .sequence import MAX_STEPS, SequenceStep, SequenceRunner

MAX_BYTES = 8 * 1048576
MAX_INPUT_BYTES = 16 * 1048576


def prepare_steps(inputs):
    """Validate all offline artifacts, preserve their bytes, never open transport."""
    if not 1 <= len(inputs) <= MAX_STEPS:
        raise ValueError("A sequence requires 1–16 offline plan artifacts")
    if any(not isinstance(raw, bytes) for raw in inputs):
        raise TypeError("Offline plans must be bytes")
    if any(len(raw) > MAX_BYTES for raw in inputs) or sum(map(len, inputs)) > MAX_INPUT_BYTES:
        raise ValueError("Offline plans exceed 8 MiB each or 16 MiB combined")
    steps = []
    for index, raw in enumerate(inputs):
        artifact = decode_bytes(raw)
        try:
            capabilities = artifact["profile"]["document"]["capabilities"]
        except (KeyError, TypeError):
            raise ValueError("Expected offline plan with an explicit capability profile") from None
        exported = encode_plan_frame(raw, json.dumps(capabilities, allow_nan=False).encode())
        message = decode_bytes(exported["frame"]["line"].encode())
        plan = RenderingPlan([DeviceCommand(c["channel"], c["intensity"]) for c in message["commands"]], message["duration"])
        steps.append(SequenceStep(f"step-{index + 1}", plan,
                                  {"input": _snapshot(raw), **exported["context"]}))
    if sum(s.plan.duration for s in steps) > 120:
        raise ValueError("Summed plan duration exceeds 120 seconds")
    return steps


def run_transport_sequence(inputs, transport_factory, *, expected_device_id,
                           transport_context=None, on_progress=None, stop_requested=None):
    """Preflight all inputs before calling a lazy, trusted transport factory.

    Own/close the returned exchange(str)->str / close() object exclusively. No
    transport is selected from input data. Context is passive JSON, not connection
    configuration. stop_requested() is checked at cooperative progress checkpoints;
    it cannot interrupt synchronous I/O. Ctrl-C closes with uncertainty, not Stop.
    Endpoint receipts never establish physical execution or an odor measurement.
    """
    def context():
        value = {} if transport_context is None else deepcopy(transport_context)
        if not isinstance(value, dict) or len(json.dumps(value, allow_nan=False).encode()) > 1048576:
            raise ValueError("Transport context must be a JSON object up to 1 MiB")
        return {"transport_context": value}
    report = {"format": "org.opensmell.experimental.transport-sequence", "version": "0.1",
              "experimental": True, "physical_validation": False, "status": "incomplete",
              "phase": "preflight", "transcript": [], "sequence": None,
              "scope": "Explicit caller-selected transport; endpoint observations are not physical measurements"}
    return _run_sequence(inputs, transport_factory, expected_device_id=expected_device_id,
                         on_progress=on_progress, stop_requested=stop_requested,
                         report=report, validate_context=context)


def _run_sequence(inputs, transport_factory, *, expected_device_id, on_progress,
                  stop_requested, report, validate_context):
    callback_error = None
    def save():
        nonlocal callback_error
        if callback_error:
            raise callback_error
        if on_progress:
            try:
                on_progress(deepcopy(report))
            except BaseException as error:
                callback_error = error
                raise
    save()
    try:
        context = validate_context()
        if not callable(transport_factory):
            raise TypeError("A lazy transport factory is required")
        if stop_requested is not None and not callable(stop_requested):
            raise TypeError("stop_requested must be a callable")
        if not isinstance(expected_device_id, str) or not expected_device_id.strip() or len(expected_device_id) > 128:
            raise ValueError("Expected device identity of 1–128 characters required")
        steps = prepare_steps(inputs)
        report.update(context, expected_device_id=expected_device_id)
    except (OpenSmellError, ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        report.update(status="invalid", detail=str(error)); save(); return report
    transport = client = runner = None
    closed = False
    def close_transport():
        nonlocal closed
        if transport is not None and not closed:
            closed = True
            transport.close()
    class Recorded:
        def exchange(self, text):
            entry = {"phase": report["phase"], "request_line": text + "\n"}
            report["transcript"].append(entry)
            save()  # Persist intent before possible acceptance, never infer a receipt.
            try:
                response = transport.exchange(text)
                entry["response_line"] = response
                return response
            except Exception as error:
                entry["error"] = str(error)
                diagnostic = getattr(transport, "last_exchange", None)
                if diagnostic is not None:
                    entry["diagnostic"] = deepcopy(diagnostic)
                raise
            finally:
                save()
        def close(self):
            close_transport()
    def progress(sequence):
        report["sequence"] = sequence
        report["status"] = sequence["status"]
        save()
        if stop_requested is not None and stop_requested():
            runner.request_stop()
    try:
        report["phase"] = "connect"; save()
        transport = transport_factory()
        client = LifecycleAdapter(Recorded(), expected_device_id=expected_device_id)
        runner = SequenceRunner(client, steps, on_progress=progress)
        report["phase"] = "sequence"
        report["sequence"] = runner.run()
        report["status"] = report["sequence"]["status"]
    except (Exception, KeyboardInterrupt) as error:
        report.update(status="unknown" if report["phase"] == "sequence" else "incompatible",
                      detail=str(error) or type(error).__name__)
        if report["phase"] == "connect" and any("error" in e for e in report["transcript"]):
            report["status"] = "unknown"
    finally:
        if client:
            client.close()
        if transport:
            close_transport()
        report["phase"] = "finished"
        save()
    return report
