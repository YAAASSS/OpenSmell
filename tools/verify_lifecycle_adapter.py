"""Run live software lifecycle reference cases and emit a JSON exchange report."""
import argparse
import json
import sys
import time

from apps.local_demo.preview_store import PreviewStore
from apps.local_demo.service import FIXTURE, preview
from apps.local_demo.simulator import LIFECYCLE, SIMULATOR_ID, SimulatedEndpoint, SimulatedHardwareService
from apps.local_demo.process_transport import NODE_DEVICE_ID, ProcessTransport, node_transport


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(factory, device_id):
    """factory(port) returns an exchange(str)/close() software-only transport."""
    trace, cases, transports = [], [], []
    class Recorded:
        def __init__(self, transport):
            self.transport = transport
        def exchange(self, message):
            entry = {"request": json.loads(message)}
            trace.append(entry)
            try:
                response = self.transport.exchange(message)
                entry["response"] = json.loads(response)
                return response
            except Exception as exc:
                entry["transport_error"] = type(exc).__name__ + ": " + str(exc)
                raise
        def close(self):
            self.transport.close()
    def open_device(port):
        endpoint = Recorded(factory(port))
        transports.append(endpoint)
        return endpoint
    hardware = SimulatedHardwareService(factory=open_device, expected_device_id=device_id)
    store = PreviewStore()
    def send(revision, duration):
        payload = {"client_id": "lifecycle-reference-client", "revision": revision}
        store.begin(payload)
        result = preview(FIXTURE.read_text(encoding="utf-8"), duration=duration)
        return hardware.send(store, store.publish(payload, result))["execution"]
    report = {"profile": LIFECYCLE, "device_id": device_id, "software_only": True,
              "passed": False, "cases": cases, "exchanges": trace}
    try:
        hardware.connect("SIMULATED")
        first = send(1, 0.1)
        deadline = time.monotonic() + 3
        while hardware.status()["execution"]["state"] == "running" and time.monotonic() < deadline:
            time.sleep(0.02)
        completed = hardware.status()["execution"]
        require(completed["state"] == "completed", "Completion was not observed")
        require(completed["execution_id"] == first["execution_id"], "Completion ID mismatch")
        cases.append("normal_completion")
        # Stop after completion cannot turn it into an interruption.
        terminal = json.loads(transports[-1].exchange(json.dumps({"type": "stop", "profile": LIFECYCLE,
                                                                 "execution_id": first["execution_id"]})))
        require(terminal.get("state") == "completed" and terminal.get("execution_id") == first["execution_id"], "Terminal state changed")
        cases.append("terminal_state_stable")
        second = send(2, 5)
        require(second["execution_id"] != first["execution_id"], "Execution ID reused")
        # Exercise the endpoint itself, not just the service's stale-ID guard.
        try:
            stale_text = transports[-1].exchange(json.dumps({"type": "stop", "profile": LIFECYCLE,
                                                            "execution_id": first["execution_id"]}))
        except ValueError:
            # The original in-process endpoint reports rejection by exception.
            pass
        else:
            stale = json.loads(stale_text)
            require(isinstance(stale, dict) and stale.get("type") == "error", "Endpoint accepted stale Stop")
        require(hardware.status()["execution"]["state"] == "running", "Stale Stop interrupted current execution")
        cases.append("stale_stop_rejected")
        stopped = hardware.stop(second["execution_id"])["execution"]
        require(stopped["state"] == "stopped" and stopped["execution_id"] == second["execution_id"], "Stop not confirmed")
        cases.append("correlated_stop")
        send(3, 5)
        transports[-1].close()
        require(hardware.status()["execution"]["state"] == "unknown", "Link loss was not unknown")
        cases.append("lost_link_unknown")
        report["passed"] = True
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        hardware.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", choices=["python", "node"], default="node")
    parser.add_argument("--device-id", help="Expected identity for a custom software command")
    parser.add_argument("--command", nargs=argparse.REMAINDER,
                        help="Explicit local software command speaking JSON lines; never use a physical driver")
    args = parser.parse_args()
    if args.command is not None:
        if not args.command or not args.device_id:
            parser.error("--command requires a command and --device-id")
        factory, identity = lambda _: ProcessTransport(args.command), args.device_id
    elif args.endpoint == "node":
        factory, identity = node_transport, NODE_DEVICE_ID
    else:
        factory, identity = lambda _: SimulatedEndpoint(), SIMULATOR_ID
    report = verify(factory, identity)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
