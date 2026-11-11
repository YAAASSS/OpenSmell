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
and response in `exchanges`, labeled by client connection number; failure returns exit code 1. Redirect stdout to keep
a report. IDs and the number of status polls vary, so reports are evidence rather
than byte-identical golden files. The common cases are:

| Case | Required observation |
| --- | --- |
| normal_completion | Device reports completion with the accepted ID |
| terminal_state_stable | Endpoint Stop after completion preserves completed |
| stale_stop_rejected | Endpoint rejects the old ID while the new execution stays running |
| correlated_stop | Stop yields stopped with the current ID |
| invalid_plan_rejected | An oversized duration is rejected before a valid execution succeeds on the same link |
| rejections_preserve_active_execution | Busy render and wrong-profile Stop are rejected without altering the current run |
| lost_link_unknown | Closing the transport during execution makes the client report unknown |
| reconnect_preserves_unknown_evidence | Reconnecting after the duration guard preserves the old unknown outcome and evidence |
| restart_rejects_old_execution | A fresh endpoint rejects status and Stop for the previous process's ID |
| restart_new_execution_isolated | New execution/report IDs, old requests rejected, new execution remains running and can be stopped |

The live verifier uses a 0.1-second plan for completion and five-second plans for
Stop and link loss; the interactive walkthrough uses five seconds for every plan.
The full run takes about six seconds. The factory is called twice and must create
a fresh software endpoint each time; custom commands are terminated and relaunched.
The lost-link case closes the software transport, not a physical cable. This is a
bounded smoke contract, not exhaustive conformance or certification. It cannot
prove that an endpoint tells the truth about hardware or odor production.

## Implement your own software endpoint

Start from `device.cjs`, which imports no OpenSmell implementation. Use one UTF-8
JSON request and response per line over stdin/stdout, no logs on stdout. Commands
are sequential. Keep requests/responses within 65,536 bytes (response newline
included). The example clients allow five seconds for the first response,
including process startup, then two seconds per exchange. The client closes the
process on malformed output, EOF or timeout; it never retries a command. Log to stderr when running the
example manually; the application discards stderr to prevent pipe backpressure.

Implement hello/get_capabilities/render as Device Protocol 0.1, plus the explicitly
experimental RFC-0014 lifecycle messages. Advertise a distinct identity, supported
channels and duration limits, and lifecycle support. Generate a new ID for each
accepted execution. Keep completed/stopped stable and reject stale IDs. Use a
monotonic clock. Never treat acceptance or elapsed client time as a completion
reply. Both endpoints announce `errors: local-simulator-errors-v1` and return JSON
`type: error` rejections. See the error contract below; the profile remains Draft.

To run the same checks against a local **software-only** executable you trust:

```sh
python -m tools.verify_lifecycle_adapter --device-id opensmell-node-simulator-001 --command node examples/lifecycle_adapter/device.cjs
```

Put `--command` last. The command is launched directly, without a shell. Do not
point this verifier at a physical driver: it actively submits render and Stop
requests. In Python, `verify(factory, device_id)` accepts a factory returning an
`exchange(str) -> str` / `close()` transport; it returns the same report.

Then use the same executable and identity in the interactive Explorer:

```sh
python -m apps.local_demo --software-device-id opensmell-node-simulator-001 --software-command node examples/lifecycle_adapter/device.cjs
```

Replace both the ID and command when implementing your own endpoint. Put
`--software-command` last; arguments and paths with spaces retain their normal
CLI boundaries and are never interpreted by an application shell. **Connect**
starts a fresh process; **Send to device**, **Stop**, and **Download evidence JSON**
use the same guarded path as the built-in simulators. The UI labels this as a
custom software adapter, not the built-in simulator. See the
[complete custom adapter walkthrough](../../apps/local_demo/README.md#connect-your-own-software-adapter).
This is a trusted local process with your permissions, not a sandbox. Do not
put secrets in arguments or protocol messages. No HTTP endpoint can set commands.

## Scope of the evidence

These are two implementations maintained in this repository, one Python and one
JavaScript in a separate process. Successful runs establish observed local
cross-language exchange, not third-party adoption or physical compatibility.
No SDK-standard lifecycle interface, firmware changes, network transport,
reconnect reconciliation or durable execution log is introduced here. Restart means
a fresh software process, not recovery of an old execution. Download old evidence
before sending again: only the latest send remains available. Closing the Explorer
server itself discards its in-memory evidence.

## Inspect a refusal and keep working

The live checker now runs ten cases and requires the advertised error profile.
Its transcript contains actual rejected requests and replies, followed by valid
status/Stop exchanges on the same connection. For example, an old Stop yields:

```json
{"protocol_version":"0.1","type":"error","error_profile":"local-simulator-errors-v1","code":"unknown_execution","message":"Unknown execution identifier","request_type":"stop","execution_id":"old-id"}
```

Codes are `invalid_request` (malformed input/invalid plan/protocol), `busy`
(render during a run), `unsupported_profile`, `unknown_execution`, and
`unsupported_request`. Messages are diagnostic text and need not match between
languages. `request_type` echoes a string request type and `execution_id` echoes
a supplied string ID, each only when nonempty and at most 128 characters. A
rejection never supplies a successful execution state. These fields correlate
sequential exchanges; they are not authentication or general request IDs.

A valid refusal leaves the endpoint usable and never replaces its active run.
Local Explorer records render refusals as **rejected**, keeps its connection,
and allows a newly previewed send; the consumed ticket cannot be resent.
Lifecycle observation errors still conservatively become **unknown** and close
the client link: an error cannot prove the state of the requested execution.
Transport failures also remain distinct and are never retried automatically.

Migration: Python callers must now inspect returned JSON instead of catching
ValueError for request rejection. Closed transports still raise OSError.
Local Explorer accepts the original lifecycle capability reply without `errors`,
but the strengthened checker requires this error profile; unknown advertised
error profiles are refused. Existing physical Device Protocol 0.1 is unchanged.
