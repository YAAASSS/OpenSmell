"""Offline protocol frame export from a checked, explicit planning artifact.

No transport is opened. Snapshots/hashes identify supplied bytes, not authenticity.
"""
import base64
from copy import deepcopy
import hashlib
import re

from .._json import decode_bytes
from .core_interchange import interchange_registry
from .generic_graph import generic_graph_from_dict
from .planning import plan_with_profile
from .rendering import DeviceCommand, RenderingPlan, RenderRequest
from .device_protocol import dumps_message, parse_capabilities_response, render_request_message


def _snapshot(raw):
    return {"encoding": "base64", "data": base64.b64encode(raw).decode("ascii"),
            "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}


def encode_plan_frame(raw, capabilities_raw, *, max_message_bytes=1024):
    """Recompute a CLI plan, check supplied target capabilities, export one LF frame.

    Supports experimental offline-plan 0.1 only. Unknown input fields remain in
    exact original-byte snapshots, never in the protocol command. The framing
    bound excludes LF and is application-supplied (1024 is the ESP32 reference).
    """
    if not isinstance(raw, bytes) or not isinstance(capabilities_raw, bytes):
        raise TypeError("Artifact and target capabilities must be bytes")
    if len(raw) > 8 * 1048576 or len(capabilities_raw) > 1048576:
        raise ValueError("Artifact exceeds 8 MiB or target capabilities exceed 1 MiB")
    if type(max_message_bytes) is not int or not 1 <= max_message_bytes <= 65536:
        raise ValueError("max_message_bytes must be an integer from 1 through 65536")
    artifact, target = decode_bytes(raw), decode_bytes(capabilities_raw)
    if (not isinstance(artifact, dict) or artifact.get("format") != "org.opensmell.experimental.offline-plan"
            or artifact.get("version") != "0.1" or artifact.get("status") != "planned"
            or artifact.get("execution") != "not_attempted"
            or artifact.get("capability_basis") != "supplied_profile_not_live_device"):
        raise ValueError("Expected an unexecuted offline-plan 0.1 artifact")
    for name in ("source", "profile"):
        context = artifact.get(name)
        if (not isinstance(context, dict) or not isinstance(context.get("document"), dict)
                or not isinstance(context.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", context["sha256"])):
            raise ValueError(f"Missing {name} snapshot or declared SHA-256")
    request, supplied = artifact.get("request"), artifact.get("plan")
    if not isinstance(request, dict) or not isinstance(supplied, dict):
        raise ValueError("Missing request or plan")
    if not isinstance(supplied.get("commands"), list) or not supplied["commands"]:
        raise ValueError("A nonempty plan is required")
    if any(not isinstance(command, dict) for command in supplied["commands"]):
        raise ValueError("Plan commands must be objects")
    plan = RenderingPlan([DeviceCommand(c.get("channel"), c.get("intensity")) for c in supplied["commands"]],
                         supplied.get("duration"))
    from .core_planning import validate_core_projection
    validate_core_projection(artifact["source"]["document"])
    graph = generic_graph_from_dict(artifact["source"]["document"], registry=interchange_registry())
    recomputed = plan_with_profile(graph, RenderRequest(request.get("resource_id"), request.get("duration")),
                                   artifact["profile"]["document"])
    if plan.duration != recomputed.duration or plan.commands != recomputed.commands:
        raise ValueError("Plan does not match its source/profile/request snapshots")
    capabilities = parse_capabilities_response(target)
    capabilities.require_plan(plan)
    message = render_request_message(plan)
    text = dumps_message(message)
    payload = text.encode("utf-8")
    if len(payload) > max_message_bytes:
        raise ValueError("Encoded message exceeds the supplied framing bound")
    line = payload + b"\n"
    return {
        "format": "org.opensmell.experimental.protocol-frame-export", "version": "0.1",
        "status": "encoded", "experimental": True,
        "transport": "not_opened", "acceptance": "not_observed", "execution": "not_observed",
        "physical_validation": False,
        "input": _snapshot(raw), "target": {"basis": "supplied_not_live_device", **_snapshot(capabilities_raw),
                                           "device_id": capabilities.device_id},
        "context": {"source_sha256_declared": artifact["source"]["sha256"],
                    "profile_sha256_declared": artifact["profile"]["sha256"],
                    "request": deepcopy(request), "plan": deepcopy(supplied)},
        "checks": ["Strict JSON byte boundary; supported unexecuted planning artifact.",
                   "Actionable plan recomputed from embedded source/profile/request.",
                   "Nonempty unique commands, finite duration/intensities and supplied target capability bounds.",
                   "UTF-8 message bound excludes one LF terminator."],
        "frame": {"line": line.decode("utf-8"), "message_bytes": len(payload), "line_bytes": len(line),
                  "sha256": hashlib.sha256(line).hexdigest(), "max_message_bytes": max_message_bytes},
        "limitations": ["Source/profile hashes inside the input are declarations; original source/profile bytes are not reauthenticated.",
                        "Raw input and target bytes are retained exactly, including unknown extensions; frame uses only protocol command fields.",
                        "Supplied capabilities and framing are not live observations; identity is not authenticated.",
                        "Device Protocol 0.1 reports acceptance only; no lifecycle/Stop or physical odor reproduction is established.",
                        "Snapshots may contain source data and increase artifact size. No transport, scheduling or automatic send occurs."],
    }
