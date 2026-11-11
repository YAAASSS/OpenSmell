"""Installed standalone lifecycle proof. Software simulations only."""
import argparse
import json
import time
from .lifecycle_adapter import LifecycleAdapter
from .lifecycle_simulator import SimulatedEndpoint, SIMULATOR_ID
from .process_transport import ProcessTransport
from .rendering import RenderingPlan, DeviceCommand


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", metavar="DEVICE_CJS", help="Explicit trusted Node reference script")
    args = parser.parse_args()
    transport = ProcessTransport(["node", args.node]) if args.node else SimulatedEndpoint()
    identity = "opensmell-node-simulator-001" if args.node else SIMULATOR_ID
    results = {}
    with LifecycleAdapter(transport, expected_device_id=identity) as client:
        plan = RenderingPlan([DeviceCommand(0, 0.25)], 0.1)
        run = client.render(plan, request_id="complete")
        deadline = time.monotonic() + 3
        while run["state"] in {"accepted", "running"} and time.monotonic() < deadline:
            time.sleep(0.02)
            run = client.status(run["execution_id"])
        assert run["state"] == "completed", run
        results["completion"] = run
        run = client.render(RenderingPlan([DeviceCommand(1, 0.5)], 5), request_id="stop")
        run = client.stop(run["execution_id"])
        assert run["state"] == "stopped", run
        results["stop"] = run
        run = client.render(plan, request_id="disconnect")
        client.close()
        assert client.execution["state"] == "unknown", client.execution
        results["disconnect"] = client.execution
    print(json.dumps({"experimental": True, "physical_validation": False, "results": results}, indent=2))


if __name__ == "__main__":
    main()
