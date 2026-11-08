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
            self.connection = len(transports) + 1
        def exchange(self, message):
            entry = {"connection": self.connection, "request": json.loads(message)}
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
    def reject_old_id(execution_id, action):
        try:
            response = transports[-1].exchange(json.dumps({
                "type": action, "profile": LIFECYCLE, "execution_id": execution_id,
            }))
        except ValueError:
            # Original in-process endpoint rejection; not a wire error contract.
            return
        reply = json.loads(response)
        require(isinstance(reply, dict) and reply.get("type") == "error",
                "Endpoint accepted stale " + action)

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
        reject_old_id(first["execution_id"], "stop")
        require(hardware.status()["execution"]["state"] == "running", "Stale Stop interrupted current execution")
        cases.append("stale_stop_rejected")
        stopped = hardware.stop(second["execution_id"])["execution"]
        require(stopped["state"] == "stopped" and stopped["execution_id"] == second["execution_id"], "Stop not confirmed")
        cases.append("correlated_stop")
        lost = send(3, 5)
        old_report_id = lost["report_id"]
        old_id = lost["execution_id"]
        reconnect_after = time.monotonic() + 5
        transports[-1].close()
        require(hardware.status()["execution"]["state"] == "unknown", "Link loss was not unknown")
        cases.append("lost_link_unknown")
        old_evidence = hardware.evidence(old_report_id)
        # Preserve the client's duration guard; elapsed time is not completion.
        time.sleep(max(0, reconnect_after - time.monotonic()))
        reconnected = hardware.connect("SIMULATED")
        require(reconnected["execution"]["state"] == "unknown", "Reconnect resolved old uncertainty")
        new_snapshot = hardware.evidence(old_report_id)
        old_evidence.pop("snapshot_at")
        new_snapshot.pop("snapshot_at")
        require(new_snapshot == old_evidence, "Reconnect changed old evidence")
        cases.append("reconnect_preserves_unknown_evidence")
        # The factory must start a fresh software endpoint, not resume old state.
        for action in ("execution_status", "stop"):
            reject_old_id(old_id, action)
        cases.append("restart_rejects_old_execution")
        fresh = send(4, 5)
        require(fresh["execution_id"] not in {first["execution_id"], second["execution_id"], old_id},
                "Restart reused an execution ID")
        require(fresh["report_id"] != old_report_id, "Restart reused an evidence ID")
        for action in ("execution_status", "stop"):
            reject_old_id(old_id, action)
        current = hardware.status()["execution"]
        require(current["state"] == "running" and current["execution_id"] == fresh["execution_id"],
                "Old request affected new execution")
        fresh_report = hardware.evidence(fresh["report_id"])
        require(fresh_report["execution"]["execution_id"] == fresh["execution_id"],
                "Evidence identifies the wrong execution")
        for event in fresh_report["exchanges"]:
            request = json.loads(event["request_text"])
            require(request.get("execution_id") != old_id, "Old execution leaked into new evidence")
        stopped = hardware.stop(fresh["execution_id"])["execution"]
        require(stopped["state"] == "stopped" and stopped["execution_id"] == fresh["execution_id"],
                "New execution could not be stopped")
        cases.append("restart_new_execution_isolated")
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
