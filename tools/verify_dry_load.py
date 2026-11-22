"""Exercise actual dry-load sketch with fake GPIO/clock, never physical hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from opensmell.experimental.native_replay import _NativePipe
from opensmell.experimental.lifecycle_adapter import LifecycleAdapter
from opensmell.experimental.rendering import RenderingPlan, DeviceCommand

DEVICE = "opensmell-esp32-dry-load-001"
PROFILE = "local-simulator-lifecycle-v1"


def verify(host):
    transcript = []
    pipe = _NativePipe(host)
    def exchange(request):
        line = json.dumps(request, separators=(",", ":")) if isinstance(request, dict) else request
        raw, value = pipe.exchange(line + "\n")
        transcript.append({"request_line": line + "\n", "response_line": raw})
        return value
    def render(duration=5, commands=None):
        return {"protocol_version": "0.1", "type": "render", "duration": duration,
                "commands": commands if commands is not None else [{"channel": 0, "intensity": .25}, {"channel": 2, "intensity": .8}]}
    def observe(eid, kind="execution_status"):
        return exchange({"type": kind, "profile": PROFILE, "execution_id": eid})
    def pins(expected):
        assert exchange("!pins")["host_pwm"] == expected
    try:
        assert exchange({"protocol_version": "0.1", "type": "hello"})["device_id"] == DEVICE
        caps = exchange({"protocol_version": "0.1", "type": "get_capabilities"})
        assert caps["min_duration"] == .1 and caps["max_duration"] == 5
        assert exchange({"type": "lifecycle_capabilities"})["implementation"] == "experimental-esp32-dry-load-v1"
        pins([0, 0, 0])
        assert exchange(render())["code"] == "busy"; pins([0, 0, 0])
        assert exchange("!enable 1")["host_enable"] is True
        for request in [render(5.001), render(.099), render(True), render(1, []), render(1, [None]),
                        render(1, [{"channel": True, "intensity": 1}]), render(1, [{"channel": 3, "intensity": 1}]),
                        render(1, [{"channel": 0, "intensity": 1}, {"channel": 0, "intensity": 0}]),
                        render(1, [{"channel": 0, "intensity": False}]), render(1, [{"channel": 0, "intensity": 1.1}])]:
            assert exchange(request)["type"] == "error"; pins([0, 0, 0])
        first = exchange(render())["execution_id"]
        assert first.startswith("dry-exp-")
        pins([64, 0, 204]); assert observe(first)["state"] == "running"
        assert exchange(render())["code"] == "busy"
        assert observe("stale", "stop")["code"] == "unknown_execution"; pins([64, 0, 204])
        # The sketch loop is called without serial data by this fake input control.
        assert exchange("!enable 0")["host_enable"] is False
        pins([0, 0, 0]); assert observe(first)["state"] == "stopped"
        assert exchange(render())["code"] == "busy"
        exchange("!enable 1"); pins([0, 0, 0])
        assert observe(first)["state"] == "stopped"  # No restart on rearm.
        second = exchange(render())["execution_id"]; assert second != first
        exchange("!advance 4999"); assert observe(second)["state"] == "running"
        exchange("!advance 1"); assert observe(second)["state"] == "completed"; pins([0, 0, 0])
        third = exchange(render(.1, [{"channel": 1, "intensity": .6}]))["execution_id"]
        pins([0, 153, 0]); assert observe(third, "stop")["state"] == "stopped"; pins([0, 0, 0])
        assert observe(third, "stop")["state"] == "stopped"
        # Input drop remains stopped after the deadline; never relabel it completed.
        fourth = exchange(render(.1))["execution_id"]
        exchange("!enable 0"); exchange("!advance 100")
        assert observe(fourth)["state"] == "stopped"; pins([0, 0, 0])
        exchange("!enable 1"); exchange("!advance " + str(2**32 - 50 - 5100))
        fifth = exchange(render(.1))["execution_id"]
        exchange("!advance 101"); assert observe(fifth)["state"] == "completed"; pins([0, 0, 0])
        assert exchange("{")["type"] == "error"
        assert exchange("x" * 1025)["type"] == "error"
        assert exchange({"protocol_version": "0.1", "type": "hello"})["device_id"] == DEVICE
    finally:
        pipe.close()
    # High at startup cannot arm, including a second high; must sample low first.
    frames = [render(), "!enable 1", render(), "!enable 0", "!enable 1", render()]
    boot_input = "".join((json.dumps(x) if isinstance(x, dict) else x) + "\n" for x in frames)
    boot = subprocess.run([str(host), "--boot-enable-high"], input=boot_input, text=True,
                          capture_output=True, timeout=5, check=True)
    replies = [json.loads(line) for line in boot.stdout.splitlines()]
    assert len(replies) == 6
    assert replies[0]["code"] == replies[2]["code"] == "busy"
    assert replies[1]["host_enable"] is False and replies[4]["host_enable"] is True
    assert replies[5]["type"] == "ok" and replies[5]["execution_id"] not in {first, second, third, fourth, fifth}
    # Real SDK receives correlated stopped after a separately injected fake input.
    pipe = _NativePipe(host)
    class NativeTransport:
        def exchange(self, message):
            return json.dumps(exchange(json.loads(message)))
        def close(self):
            pipe.close()
    with LifecycleAdapter(NativeTransport(), expected_device_id=DEVICE) as client:
        plan = RenderingPlan([DeviceCommand(0, .25)], 5)
        refused = client.render(plan, request_id="unarmed")
        assert refused["state"] == "rejected" and refused["response"]["code"] == "busy"
        exchange("!enable 0"); exchange("!enable 1")
        active = client.render(plan, request_id="armed"); assert active["state"] == "accepted"
        exchange("!enable 0"); pins([0, 0, 0])
        tripped = client.status(active["execution_id"])
        assert tripped["state"] == "stopped" and tripped["execution_id"] == active["execution_id"]
    return {"result": "passed", "physical_validation": False,
            "scope": "Actual compiled dry-load sketch; fake serial/input/PWM/clock only",
            "native_sha256": hashlib.sha256(host.read_bytes()).hexdigest(),
            "exchanges": len(transcript), "boot_high_replies": replies, "sdk_trip": tripped,
            "transcript": transcript}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New checkpointed software evidence")
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8") as output:
        output.write('{"result":"incomplete","physical_validation":false}\n'); output.flush()
        report = verify(args.host.resolve(strict=True))
        output.seek(0); output.truncate(); json.dump(report, output, indent=2); output.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"transcript", "boot_high_replies"}}))


if __name__ == "__main__":
    main()
