# Development status

Current bounded backlog for [autonomous maintenance](autonomous-development.md).
The broader roadmap remains in the [README](../README.md#roadmap).
Operational checkpoints and the short session log live in `state.json` on the
`automation/control` branch; follow its pending PR before starting new work.

## Initial audit — 2026-11-04

- Starting `main`: `52d4504f2b99d0557cbfacf7b81f6fc7dd22f4ca`.
  The exact-head [Tests run](https://github.com/YAAASSS/OpenSmell/actions/runs/35275662405)
  was successful. No open issues or PRs were returned at audit time.
- No repository `AGENTS.md` was present. The README, contribution checklist,
  CI workflow and relevant graph/app contracts were inspected.
- Source clone, local installation and Python/Node execution worked. Shell Git
  push has no credentials in this environment; authenticated GitHub connector
  writes work. Repository metadata reports push permission, `main` unprotected
  and no rulesets; recheck before each merge because these settings may change.
- Existing functionality includes Core, experimental graphs, two real multi-source
  examples, independent JavaScript inspection/original-byte exchange and the local
  mapping/device UI. Historical physical LED evidence remains attributed to the
  maintainer; no hardware was accessed during this audit.
- A fresh runtime must restore source/dependencies. The first scheduled execution
  still needs to establish that its inherited tools can execute and publish;
  scheduler registration alone does not prove that capability.

## Initial improvement — ambiguous JSON

Reproduced: Python silently retained the second value of a repeated object key
inside a graph extension; the JavaScript reader already rejected it.

The Python generic graph text loader now rejects duplicates recursively before
dict construction and resource dispatch. The Local Explorer reports the error,
revokes the prior tracked preview and recovers after a valid import. Escaped key
spellings cannot evade rejection. Separate objects and case-sensitive names are
unchanged. Producers must resolve ambiguity from source data, not choose a value
automatically. Core/RFC-0007 text loaders and HTTP envelope parsing are outside
this bounded fix; already-decoded dictionaries cannot recover discarded members.

Verification executed locally: **164 targeted Python tests passed** (31 import,
duplicate-key and cross-language cases; 133 generic-graph/conformance/numeric
boundary cases). The existing JavaScript reader suite passed **33 tests**.
The full Python suite then passed **1,939 tests** in this environment (Python 3.12).
No UI code, mapping calculation, firmware or physical behavior changed. Read
the linked PR/check runs in the operational state for subsequent CI/merge evidence.

## Active product milestone — simulated execution lifecycle (2026-11-05)

External developers should be able to reproduce an exchange and distinguish
acceptance from device-reported execution, without special hardware. Local
Explorer now has `--simulate`: explicit connection, a five-second plan, normal
completion, correlated Stop, and unknown outcome after loss of connection.
The endpoint supplies execution IDs and terminal replies across JSON exchanges.
The UI exposes received status and keeps physical Device Protocol 0.1 unchanged.
See the [walkthrough](../apps/local_demo/README.md#try-execution-and-stop-without-hardware)
and [Draft RFC-0014](../rfcs/RFC-0014.md).

Local verification: 1,946 Python tests passed, including five new HTTP lifecycle
cases; eight JavaScript import tests and one lifecycle UI test passed. JavaScript
syntax and whitespace checks passed. The CLI simulator launched successfully.
The browser environment could not reach the local server (connection refused),
so no visual browser verification is claimed. No physical device was accessed.
CI and merge evidence are recorded on `automation/control`, not inferred here.

## Independent software adapter — 2026-11-06

Local Explorer now offers `--simulate-node`, using a distinct Node.js endpoint
in a separate process without importing the Python implementation. The common
live checker is `python -m tools.verify_lifecycle_adapter --endpoint node`
(or `--endpoint python`). It emits actual exchanges and checks completion,
terminal-state stability, stale Stop, correlated Stop and lost-link uncertainty.
A custom software-only command can run the same cases. See the
[starter example](../examples/lifecycle_adapter/README.md).

This is repository-maintained cross-language evidence, not third-party adoption
or physical validation. RFC-0014 remains Draft. Subprocess failures close the
link without retry, including timeout, EOF, malformed and oversized output.
Normal CLI/HTTP integration is tested; no UI markup or JavaScript changed.
Publication and exact-head CI evidence live in the control record.

## Execution evidence export — 2026-11-07

Local Explorer now exposes View evidence / Download evidence JSON for the latest
send, including after disconnect. A report correlates the parsed source and its
provenance, mapping policy/bindings, submitted plan, transport exchanges and last
execution state. It preserves raw response text and makes omissions explicit.
Export is passive; a superseded ID is rejected rather than returning a new run.
The report is an app-local experimental snapshot, not authenticated telemetry.

HTTP cases cover completion, Stop, unknown, rejection, timeout, stale report IDs
and passive reads; JS cases exercise downloaded bytes and late-response gating.
The Node CLI/HTTP flow also exports each outcome. Visual browser QA remains
unavailable in this environment (connection refused); no visual result is claimed.

## Restart reference walkthrough — 2026-11-08

The public adapter verifier now runs eight cases including fresh-process restart,
old-ID rejection and preservation of unknown evidence through reconnect. Reports
label exchanges by connection; custom software commands use the same checks.
The normal Node CLI/HTTP path also reconnects, exports the old unknown report,
starts a new execution, rejects stale Stop and exports the new stopped report.
This is fresh-process isolation, not durable recovery or physical validation.

## Inspectable software refusals — 2026-11-09

Python and Node now announce the same experimental error profile and return
coded JSON refusals with request type/execution ID correlation. The public
checker runs ten cases, including invalid duration, busy render and wrong-profile
Stop, then proves normal operations on the same link. Local Explorer exports a
render refusal as rejected and permits a fresh preview/send after the endpoint
becomes available; lost links and invalid observations remain unknown.

## Prioritized next work

Custom software adapters can now be selected at CLI startup with a pinned
device ID, connected explicitly, run/stopped and inspected/exported in the normal
Local Explorer UI. The selected executable is never accepted from HTTP or graph
input. Missing commands and incompatible identities/capabilities fail before
render; broken execution exchanges remain unknown without retry. The software
mode is not a sandbox and does not certify physical effects. The Node reference
and a renamed external copy exercise the same user entry point.

| Priority | Outcome | Acceptance criterion |
| --- | --- | --- |
| 1 | Compare execution evidence across runs | Retain and export a bounded history of completed/stopped/unknown runs without mixing their sources, IDs or exchanges. |
| 2 | Adapter onboarding and visual walkthrough | Exercise the normal browser flow and document any remaining environment-specific limitation. |
| 3 | SDK lifecycle boundary | Extract only the contract demonstrated by both implementations; preserve legacy physical protocol behavior. |

The profile remains Draft. Physical compatibility and third-party adoption
remain unclaimed. No durable execution recovery is implemented.
