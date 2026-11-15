"""Replay a validated export against an explicit trusted software native harness.

No serial/device discovery or physical transport. Host executables are not sandboxed.
"""
import base64
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import queue
import stat
import subprocess
import threading

from .._json import decode_bytes
from .frame_export import encode_plan_frame, _snapshot
from .device_protocol import parse_capabilities_response, parse_hello_response


def _same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def _recover(snapshot, limit):
    if not isinstance(snapshot, dict) or snapshot.get("encoding") != "base64":
        raise ValueError("Missing original-byte snapshot")
    data = snapshot.get("data")
    if not isinstance(data, str) or len(data) > 4 * ((limit + 2) // 3):
        raise ValueError("Snapshot exceeds input bound")
    raw = base64.b64decode(data, validate=True)
    if (len(raw) > limit or type(snapshot.get("byte_count")) is not int
            or snapshot["byte_count"] != len(raw) or snapshot.get("sha256") != hashlib.sha256(raw).hexdigest()):
        raise ValueError("Snapshot byte identity mismatch")
    return raw


def validate_frame_export(raw):
    """Check export identities, recomputed mapping and exact frame before process launch."""
    if not isinstance(raw, bytes):
        raise TypeError("Export must be bytes")
    if len(raw) > 24 * 1048576:
        raise ValueError("Export exceeds 24 MiB")
    value = decode_bytes(raw)
    if not isinstance(value, dict) or not isinstance(value.get("frame"), dict):
        raise ValueError("Expected a frame export")
    original = _recover(value.get("input"), 8 * 1048576)
    target = _recover(value.get("target"), 1048576)
    expected = encode_plan_frame(original, target, max_message_bytes=value["frame"].get("max_message_bytes"))
    for key in ("format", "version", "status", "transport", "acceptance", "execution",
                "physical_validation", "context", "frame"):
        if not _same(value.get(key), expected[key]):
            raise ValueError(f"Export contradicts its input snapshots: {key}")
    for key in ("basis", "device_id"):
        if not _same(value["target"].get(key), expected["target"][key]):
            raise ValueError("Target context mismatch")
    return value, decode_bytes(target)


class _ReplyError(ValueError):
    def __init__(self, raw, complete, detail):
        super().__init__(detail)
        self.raw, self.complete = raw, complete


class _NativePipe:
    """One bounded line exchange, including native-only !pins/!advance controls."""
    def __init__(self, executable):
        self.child = subprocess.Popen([str(executable)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL, shell=False)
        self.first = True

    def exchange(self, line):
        data = line.encode("utf-8")
        if not data.endswith(b"\n") or b"\n" in data[:-1] or b"\r" in data or len(data) > 65537:
            raise ValueError("Expected one bounded LF line")
        result = queue.Queue(maxsize=1)
        def transact():
            try:
                self.child.stdin.write(data); self.child.stdin.flush()
                raw = self.child.stdout.readline(65537)
                if not raw or not raw.endswith(b"\n") or len(raw) > 65536:
                    raise _ReplyError(raw, False, "Missing or oversized native response")
                try:
                    value = decode_bytes(raw)
                    if not isinstance(value, dict):
                        raise ValueError("Native reply must be an object")
                except (ValueError, TypeError) as error:
                    raise _ReplyError(raw, True, str(error)) from error
                result.put((raw.decode("utf-8"), value))
            except Exception as error:
                result.put(error)
        worker = threading.Thread(target=transact, daemon=True)
        worker.start()
        failed = True
        try:
            response = result.get(timeout=5.0 if self.first else 2.0)
            if isinstance(response, Exception):
                raise response
            self.first = False
            failed = False
            return response
        except queue.Empty as error:
            raise TimeoutError("Native response deadline exceeded; no retry") from error
        finally:
            # The owning replay always closes this process after any error.
            if failed:
                self.close()
            worker.join(timeout=0.1)

    def close(self):
        if self.child.poll() is None:
            self.child.terminate()
            try:
                self.child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.child.kill(); self.child.wait(timeout=1)
        for stream in (self.child.stdin, self.child.stdout):
            try:
                if not stream.closed:
                    stream.close()
            except OSError:
                pass  # Cleanup cannot erase a partial observation transcript.


def _capability_key(value):
    caps = parse_capabilities_response(value)
    return (caps.device_id, caps.min_duration, caps.max_duration,
            sorted((c.channel, c.min_intensity, c.max_intensity) for c in caps.channels))


def replay_frame(raw, native_host, *, on_progress=None):
    """Observe a caller-selected native harness. Validates before launching it.

    Includes a labeled 31-second negative control and virtual-clock expiration.
    Returns unknown on failed exchanges, retaining partial transcript with no retry.
    """
    exported, target = validate_frame_export(raw)
    host = Path(native_host).resolve(strict=True)
    if not stat.S_ISREG(host.stat().st_mode):
        raise ValueError("Native host must be a regular trusted executable file")
    digest = hashlib.sha256()
    with host.open("rb") as source:
        for chunk in iter(lambda: source.read(1048576), b""):
            digest.update(chunk)
    report = {"format": "org.opensmell.experimental.native-frame-replay", "version": "0.1",
              "experimental": True, "scope": "caller_selected_trusted_native_software",
              "status": "incomplete", "acceptance": "not_attempted", "execution": "not_observed",
              "physical_validation": False, "input": _snapshot(raw),
              "native_host": {"path": str(host), "sha256": digest.hexdigest()},
              "transcript": [], "fake_outputs": {},
              "limitations": ["Selected executable is trusted, not sandboxed or authenticated as the actual sketch.",
                             "Native serial/PWM/clock observations are not board, electrical timing, diffusion or odor evidence.",
                             "Protocol 0.1 acceptance is separate from software lifecycle; no physical execution is observed.",
                             "Supplied source/profile identities remain declarations. No retries or restart recovery.",
                             "An interrupted or failed transcript must not be treated as acceptance or retried automatically."]}
    def checkpoint():
        if on_progress:
            on_progress(deepcopy(report))
    pipe = None
    def exchange(role, line):
        entry = {"role": role, "request_line": line}
        report["transcript"].append(entry); checkpoint()
        try:
            entry["response_line"], entry["response"] = pipe.exchange(line)
        except Exception as error:
            entry["error"] = str(error)
            if isinstance(error, _ReplyError):
                entry["response_bytes"] = _snapshot(error.raw)
                entry["response_complete"] = error.complete
            checkpoint(); raise
        checkpoint()
        return entry["response"]
    def pins(role):
        reply = exchange(role, "!pins\n")
        values = reply.get("host_pwm")
        if (not isinstance(values, list) or len(values) != 3
                or any(type(v) is not int or not 0 <= v <= 255 for v in values)):
            raise ValueError("Invalid native PWM observation")
        return values
    try:
        checkpoint()
        pipe = _NativePipe(host)
        hello = exchange("hello", '{"protocol_version":"0.1","type":"hello"}\n')
        observed = exchange("capabilities", '{"protocol_version":"0.1","type":"get_capabilities"}\n')
        report["capabilities_observed"] = observed
        if parse_hello_response(hello) != observed.get("device_id") or _capability_key(observed) != _capability_key(target):
            report.update(status="incompatible", detail="Native identity/capabilities differ from supplied target")
            checkpoint(); return report
        reference_bounds = (0.1, 30.0, [(0, 0.0, 1.0), (1, 0.0, 1.0), (2, 0.0, 1.0)])
        if _capability_key(observed)[1:] != reference_bounds:
            report.update(status="incompatible", detail="Native bench requires the three-channel 0.1–30s LED reference bounds")
            checkpoint(); return report
        before = pins("before_frame")
        report["fake_outputs"]["before"] = before
        if before != [0, 0, 0]:
            report.update(status="incompatible", detail="Fresh native outputs are not off")
            checkpoint(); return report
        # Once the frame exchange starts, loss of a reply is unknown, never a refusal.
        report["acceptance"] = "unknown"; checkpoint()
        reply = exchange("selected_frame", exported["frame"]["line"])
        if reply.get("protocol_version") != "0.1" or reply.get("type") not in {"ok", "error"}:
            raise ValueError("Invalid protocol acceptance/refusal")
        if reply["type"] == "error":
            if not isinstance(reply.get("code"), str) or not reply["code"] or not isinstance(reply.get("message"), str) or not reply["message"]:
                raise ValueError("Invalid native refusal")
            report["acceptance"] = "rejected"
        else:
            report["acceptance"] = "accepted"
        checkpoint()
        after = pins("after_frame")
        report["fake_outputs"]["after"] = after
        if reply["type"] == "error":
            if after != before:
                raise ValueError("Refused frame changed fake outputs")
            report["status"] = "rejected"
        else:
            report["acceptance"] = "accepted"
            negative = json.loads(exported["frame"]["line"]); negative["duration"] = 31
            control = exchange("negative_control_duration_31", json.dumps(negative, separators=(",", ":")) + "\n")
            if control.get("protocol_version") != "0.1" or control.get("type") != "error" or control.get("code") != "invalid_plan":
                raise ValueError("Native negative control did not refuse invalid duration")
            unchanged = pins("after_negative_control")
            report["fake_outputs"]["after_negative_control"] = unchanged
            if unchanged != after:
                raise ValueError("Negative control changed active fake outputs")
            # Overshoot the declared duration; no exact electrical timing claim.
            ms = math.ceil(json.loads(exported["frame"]["line"])["duration"] * 1000) + 1
            report["fake_clock_advance_ms"] = ms
            if exchange("advance_fake_clock", f"!advance {ms}\n").get("host") != "advanced":
                raise ValueError("Invalid fake-clock observation")
            off = pins("after_duration")
            report["fake_outputs"]["after_duration"] = off
            if off != [0, 0, 0]:
                raise ValueError("Fake outputs did not turn off after duration")
            report["status"] = "accepted"
        checkpoint()
    except Exception as error:
        report.update(status="unknown", error=str(error))
        checkpoint()
    finally:
        if pipe:
            pipe.close()
    return report
