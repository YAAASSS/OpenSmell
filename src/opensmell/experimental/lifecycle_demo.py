"""Installed standalone lifecycle proof. Software simulations only."""
from dataclasses import asdict
import hashlib
from pathlib import Path
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
    parser.add_argument("--graph", help="Generic ResourceGraph .osmell source")
    parser.add_argument("--profile", help="Explicit mapping profile JSON")
    parser.add_argument("--resource-id", help="Resource to map")
    args = parser.parse_args()
    supplied = (args.graph, args.profile, args.resource_id)
    if any(supplied) and not all(supplied):
        parser.error("--graph, --profile and --resource-id must be supplied together")
    source = None
    def make_plan(duration):
        return RenderingPlan([DeviceCommand(0, 0.25)], duration)
    if args.graph:
        from opensmell.cli import _decode, _graph_registry, inspect_bytes
        from .generic_graph import generic_graph_from_dict
        from .planning import plan_with_profile
        from .rendering import RenderRequest
        raw = Path(args.graph).read_bytes()
        profile_raw = Path(args.profile).read_bytes()
        source = {"inspection": inspect_bytes(raw),
                  "profile_sha256": hashlib.sha256(profile_raw).hexdigest(),
                  "profile": _decode(profile_raw), "resource_id": args.resource_id}
        graph = generic_graph_from_dict(_decode(raw), registry=_graph_registry())
        def make_plan(duration):
            return plan_with_profile(graph, RenderRequest(args.resource_id, duration), source["profile"])
    # Map both plans before launching the trusted endpoint.
    short_plan, long_plan = make_plan(0.1), make_plan(5)
    transport = ProcessTransport(["node", args.node], startup_timeout=5.0) if args.node else SimulatedEndpoint()
    identity = "opensmell-node-simulator-001" if args.node else SIMULATOR_ID
    results = {}
    with LifecycleAdapter(transport, expected_device_id=identity) as client:
        plan = short_plan
        run = client.render(plan, request_id="complete")
        deadline = time.monotonic() + 3
        while run["state"] in {"accepted", "running"} and time.monotonic() < deadline:
            time.sleep(0.02)
            run = client.status(run["execution_id"])
        assert run["state"] == "completed", run
        results["completion"] = run
        run = client.render(long_plan, request_id="stop")
        run = client.stop(run["execution_id"])
        assert run["state"] == "stopped", run
        results["stop"] = run
        run = client.render(plan, request_id="disconnect")
        client.close()
        assert client.execution["state"] == "unknown", client.execution
        results["disconnect"] = client.execution
    print(json.dumps({"experimental": True, "physical_validation": False, "source": source,
                      "plans": {"short": asdict(short_plan), "long": asdict(long_plan)},
                      "results": results}, indent=2))


if __name__ == "__main__":
    main()
