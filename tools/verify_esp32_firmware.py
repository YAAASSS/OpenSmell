"""Run actual ESP32 sketch logic in a native, software-only harness.

Pass a compiled host executable, never a serial port. No hardware access.
"""
import argparse
import json
from pathlib import Path
import subprocess

from opensmell.cli import _decode, _graph_registry
from opensmell.experimental.generic_graph import generic_graph_from_dict
from opensmell.experimental.planning import plan_with_profile
from opensmell.experimental.rendering import RenderRequest
from opensmell.experimental.device_protocol import (
    parse_hello_response, parse_capabilities_response, render_request_message,
)


def verify(executable):
    lines, checks = [], []
    def add(line, expected):
        lines.append(line if isinstance(line, str) else json.dumps(line))
        checks.append(expected)
    def msg(kind, **values):
        return {"protocol_version": "0.1", "type": kind, **values}
    def pins(values):
        add("!pins", {"host_pwm": values})
    add(msg("hello"), {"type": "hello_response"})
    pins([0, 0, 0])
    add(msg("get_capabilities"), {"type": "capabilities"})
    root = Path(__file__).resolve().parents[1]
    graph = generic_graph_from_dict(_decode((root / "examples/multisource_diphenyl_ether.osmell").read_bytes()),
                                    registry=_graph_registry())
    for mapper, resource, expected in [
        ("semantic", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b", [64, 153, 0]),
        ("perceptual", "219ef28c-9b58-52f2-93a7-0807f5897857", [120, 46, 38]),
    ]:
        profile = _decode((root / f"examples/offline_{mapper}_profile.json").read_bytes())
        plan = plan_with_profile(graph, RenderRequest(resource, 5), profile)
        add(render_request_message(plan), {"type": "ok"})
        pins(expected)
        # Invalid requests cannot alter an existing valid render.
        for bad, code in [
            (msg("render", duration=31, commands=[]), "invalid_plan"),
            (msg("render", duration=5, commands=[{"channel": 3, "intensity": 0.2}]), "unsupported_channel"),
            (msg("render", duration=5, commands=[{"channel": 0, "intensity": 0.2}] * 2), "invalid_plan"),
            (msg("render", duration=5, commands=[{"channel": 0, "intensity": 1.1}]), "invalid_plan"),
        ]:
            add(bad, {"type": "error", "code": code})
            pins(expected)
        add("!advance 4999", {"host": "advanced"})
        pins(expected)
        add("!advance 1", {"host": "advanced"})
        pins([0, 0, 0])
    add("{", {"type": "error", "code": "invalid_json"})
    # Exactly 1024 bytes is accepted; 1025 discarded, then hello resynchronizes.
    hello = json.dumps(msg("hello"))
    add(hello + " " * (1024 - len(hello)), {"type": "hello_response"})
    add(hello + " " * (1025 - len(hello)), {"type": "error", "code": "message_too_large"})
    add(hello + "\r", {"type": "hello_response"})
    add(msg("stop"), {"type": "error", "code": "unknown_message_type"})
    add(msg("render", duration=0.1, commands=[{"channel": 2, "intensity": 1}]), {"type": "ok"})
    pins([0, 0, 255])
    add("!advance 100", {"host": "advanced"})
    pins([0, 0, 0])
    # Maximum duration remains non-blocking and expires at the boundary.
    add(msg("render", duration=30, commands=[{"channel": 1, "intensity": 1}]), {"type": "ok"})
    add(msg("hello"), {"type": "hello_response"})
    add("!advance 30000", {"host": "advanced"})
    pins([0, 0, 0])
    result = subprocess.run([str(Path(executable).resolve(strict=True))],
                            input="\n".join(lines) + "\n", text=True,
                            capture_output=True, timeout=10, check=True)
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    if len(replies) != len(checks):
        raise AssertionError(f"Expected {len(checks)} responses, received {len(replies)}")
    for index, (actual, expected) in enumerate(zip(replies, checks)):
        if any(actual.get(key) != value for key, value in expected.items()):
            raise AssertionError(f"Case {index}: {actual!r} != {expected!r}")
    assert parse_hello_response(replies[0]) == "opensmell-esp32-led-3ch-001"
    caps = parse_capabilities_response(replies[2])
    assert caps.device_id == "opensmell-esp32-led-3ch-001"
    assert caps.min_duration == 0.1 and caps.max_duration == 30
    return {"checks": len(checks), "result": "passed", "firmware": "actual sketch",
            "physical_access": False,
            "scope": "Fake serial/PWM/clock, not electrical timing or odor validation"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable")
    args = parser.parse_args()
    print(json.dumps(verify(args.executable), indent=2))


if __name__ == "__main__":
    main()
