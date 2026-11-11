# Installed software lifecycle SDK (experimental)

The wheel now includes a reusable RFC-0014 client, bounded JSON-lines process
transport and Python simulator. They never import Local Explorer. RFC-0014 stays
Draft: its legacy profile identifiers are intentionally unchanged for Node
compatibility; Device Protocol 0.1 and physical ESP32 behavior are unchanged.

Install from a source checkout with `python -m pip install .`. This does not
publish a new package version. From any directory, run:

```sh
python -m opensmell.experimental.lifecycle_demo
python -m opensmell.experimental.lifecycle_demo --node /absolute/path/to/device.cjs
```

The second command takes the repository's
`examples/lifecycle_adapter/device.cjs` (Node required). Both proofs assert
completed, stopped and unknown outcomes and print their observations. Neither
commands hardware nor demonstrates odor reproduction. The custom process
transport executes trusted commands without a shell, but is **not a sandbox**.

## Use in another application

```python
from opensmell.experimental.lifecycle_adapter import LifecycleAdapter
from opensmell.experimental.lifecycle_simulator import SimulatedEndpoint, SIMULATOR_ID
from opensmell.experimental.rendering import RenderingPlan, DeviceCommand

with LifecycleAdapter(SimulatedEndpoint(), expected_device_id=SIMULATOR_ID) as client:
    # Alternatively use the RenderingPlan from plan_with_profile.
    plan = RenderingPlan([DeviceCommand(channel=0, intensity=0.25)], duration=5)
    run = client.render(plan, request_id="my-unique-request-1")
    if run["state"] == "accepted":
        run = client.stop(run["execution_id"])
    print(run)
```

For another trusted software endpoint, supply
`ProcessTransport(["executable", "argument"], timeout=2)` from
`opensmell.experimental.process_transport` and pin its expected identity.
Construction performs hello/capability/profile negotiation and owns the transport,
closing it on failure or context exit. Capabilities are checked before sending;
an empty plan cannot be sent. A live endpoint may reject a valid plan.

Every send consumes a caller-provided request ID. Reusing it within the same
client fails before I/O, even after rejection or an ambiguous reply. This is
session-local duplicate suppression, not durable exactly-once delivery.
Callers must keep their own source/profile provenance and preview freshness
policy; this client accepts explicit plans, not Explorer tickets.

`render` returns accepted, rejected or unknown. Acceptance is not completion.
`status(execution_id)` and `stop(execution_id)` validate correlation and expose
device-reported running/completed/stopped. A stale identifier fails locally.
Terminal snapshots remain stable. Loss of a reply or a mismatched observation
closes the link and leaves the result unknown, with no automatic retry.
`execution` is a passive copy; closing is not a Stop. Operations are serialized.
No reconnect/recovery, persistent journal, authentication, scheduling, measured
physical output or third-party compatibility is supplied.

The former app imports for ProcessTransport and SimulatedEndpoint remain as
compatibility bindings. The app retains its preview/evidence/UI policy.
