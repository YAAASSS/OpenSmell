# Independent software lifecycle adapter

Experimental pre-alpha, [RFC-0014 Draft](../../rfcs/RFC-0014.md). This example
lets you implement a software device in another language, inspect the actual
JSON exchanges, and run the same reference cases as the Python simulator.
It does not certify physical devices or measure odor reproduction.

## Run it in Local Explorer

Install OpenSmell from this checkout (`python -m pip install -e .`) and Node.js
22 or later. No npm install is required; only Node built-ins are used.

```sh
python -m apps.local_demo --simulate-node
```

Open demo, keep five seconds, Connect (SIMULATED), Send to device. Observe
Simulator completed. Recalculate, send again, and use Stop before five seconds:
Simulator stopped. Send once more and disconnect before completion: Execution
unknown. The received identity is **opensmell-node-simulator-001**. A separate
Node process owns execution timing and IDs; the Python app receives its replies.
The existing `--simulate` uses the original in-process Python implementation.
The two flags are mutually exclusive. Missing Node is reported on Connect and
leaves preview usable. No process is launched until explicit Connect.

## Run the reference cases

From the repository root with the installed Python environment:

```sh
python -m tools.verify_lifecycle_adapter --endpoint python
python -m tools.verify_lifecycle_adapter --endpoint node
```

Both commands print a JSON report with `passed`, named `cases`, and every request
and response in `exchanges`; failure returns exit code 1. Redirect stdout to keep
a report. IDs and the number of status polls vary, so reports are evidence rather
than byte-identical golden files. The common cases are:

| Case | Required observation |
| --- | --- |
| normal_completion | Device reports completion with the accepted ID |
| terminal_state_stable | Endpoint Stop after completion preserves completed |
| stale_stop_rejected | Endpoint rejects the old ID while the new execution stays running |
| correlated_stop | Stop yields stopped with the current ID |
| lost_link_unknown | Closing the transport during execution makes the client report unknown |

The live verifier uses a 0.1-second plan for completion and five-second plans for
Stop and link loss; the interactive walkthrough uses five seconds for every plan.
The lost-link case closes the software transport, not a physical cable. This is a
bounded smoke contract, not exhaustive conformance or certification. It cannot
prove that an endpoint tells the truth about hardware or odor production.

## Implement your own software endpoint

Start from `device.cjs`, which imports no OpenSmell implementation. Use one UTF-8
JSON request and response per line over stdin/stdout, no logs on stdout. Commands
are sequential. Keep requests/responses within 65,536 bytes (response newline
included). The client closes the process on malformed output, EOF or a two-second
exchange timeout; it never retries a command. Log to stderr when running the
example manually; the application discards stderr to prevent pipe backpressure.

Implement hello/get_capabilities/render as Device Protocol 0.1, plus the explicitly
experimental RFC-0014 lifecycle messages. Advertise a distinct identity, supported
channels and duration limits, and lifecycle support. Generate a new ID for each
accepted execution. Keep completed/stopped stable and reject stale IDs. Use a
monotonic clock. Never treat acceptance or elapsed client time as a completion
reply. The Node example returns `type: error` rejections; the original Python
in-process endpoint can raise ValueError instead. This difference is documented
rather than claimed as a finalized wire error contract.

To run the same checks against a local **software-only** executable you trust:

```sh
python -m tools.verify_lifecycle_adapter --device-id opensmell-node-simulator-001 --command node examples/lifecycle_adapter/device.cjs
```

Put `--command` last. The command is launched directly, without a shell. Do not
point this verifier at a physical driver: it actively submits render and Stop
requests. In Python, `verify(factory, device_id)` accepts a factory returning an
`exchange(str) -> str` / `close()` transport; it returns the same report.

## Scope of the evidence

These are two implementations maintained in this repository, one Python and one
JavaScript in a separate process. Successful runs establish observed local
cross-language exchange, not third-party adoption or physical compatibility.
No SDK-standard lifecycle interface, firmware changes, network transport,
reconnect reconciliation or durable execution log is introduced here.
