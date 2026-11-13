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

## Custom adapter entry point — 2026-11-09 manual

Custom software adapters can be selected at CLI startup with a pinned device ID,
connected explicitly, run/stopped and inspected/exported in Local Explorer. The
executable is never accepted from HTTP or graph input. Missing commands and
incompatible identities/capabilities fail before render; broken execution
exchanges remain unknown without retry. This is not a sandbox or physical
certification. The Node reference and a renamed external copy exercise the entry
point. The lifecycle profile remains Draft; durable recovery is not implemented.

## Active direction — developer kit and concrete prototype (2026-11-10)

The maintainer explicitly redirected work toward OpenSmell as a whole. The
software lifecycle / evidence milestone is delivered; adding more Explorer
inspection screens is deferred. Explorer is a demonstration client of the
project, not its default roadmap. The next milestone is an installable developer
kit that can consume documented data and produce an explicit device plan without
requiring Explorer. No new stable release or physical odor capability is implied.

| Order | Deliverable | Exit criterion / evidence |
| --- | --- | --- |
| 1 | Installed SDK and CLI workflow | Delivered: a wheel installed outside the checkout validates/inspects Core and graph files and produces semantic/perceptual dry-run plans with explicit mapping, capabilities and source provenance. Core import/source recovery delivered in the 2026-11-12 slice below. |
| 2 | Reusable device integration | Delivered in PR #13, with bounded startup correction #14: installed SDK and standalone Python/Node graph-to-execution walkthrough. |
| 3 | Reproducible hardware bench | Audit the existing ESP32 build/wiring evidence, supply the missing build configuration, bill of materials and manual acceptance procedure, and compile firmware. Record actual physical results separately; no unattended flashing or diffusion. |
| 4 | Data and adoption | Ship a complete documented import-to-plan example with source/license information and explicit scientific limits; prepare a contributor quickstart and release checklist. Third-party adoption requires observed independent use. |

Complete a usable vertical slice and its exit criterion before opening an adjacent
refinement. Reorder for actual dependencies or demonstrated regressions. Prioritize
an Explorer change only when it directly unlocks this milestone. Keep the broader
scientific roadmap (mixtures, namespaces, canonicalization, MPEG-V) visible but
require a reproducible interoperability use case before changing Core.

The installed CLI starts this milestone with `opensmell validate` and
`opensmell inspect`, plus `python -m opensmell`. Validation/inspection accept Core
0.1 and generic ResourceGraph 0.1, report unknown
contracts and supplied provenance, support batch files/stdin, and offer JSON output
and exit codes. `opensmell plan` and the experimental SDK `plan_with_profile` then
produce semantic/perceptual plans from graphs and explicit mapping/capability
profiles. Source and profile snapshots/hashes accompany CLI plans; unsupported
channels, intensities, durations and empty mappings fail. No device command is
sent or source file rewritten. See [the CLI guide](cli.md) and Draft RFC-0015.

The ESP32 software/build slice is delivered; human bench observations remain
independent. Finish the installed Core import slice below, then advance external
contributor onboarding and a reproducible upstream-data import example.

## Retained execution history — 2026-11-10

Local Explorer now retains up to ten execution reports with an additional 8 MiB
archive budget. The normal UI selects earlier completed/stopped/unknown reports
and exports each independently or all retained reports as one passive JSON bundle. Old records freeze at the next send; later
reconnections and exchanges cannot rewrite them. Evictions are counted and
missing IDs fail explicitly. History is volatile, shared across tabs and lost
at shutdown; neither durable recovery nor physical validation is claimed.

## Offline evidence diagnostics — 2026-11-10 evening

`python -m tools.diagnose_execution_evidence history.json` checks individual
exports and history bundles without a running server or device. Text and JSON
results distinguish internally consistent records, incomplete evidence and
contradictory claims, with paths/codes and scriptable exit statuses. Actual HTTP
exports cover completion, Stop and lost-link uncertainty; altered fixtures expose
plan, identity and snapshot contradictions. No replay, authentication, full schema
validation or physical compatibility is claimed.

The earlier proposed browser diagnostics follow-up is deferred by the project-wide
redirection above. The standalone graph-to-dry-run-plan workflow is delivered in
the developer-kit slice; follow the project-wide backlog above.

## Installed lifecycle SDK — 2026-11-11

The software lifecycle boundary is now reusable from the installed experimental
SDK: LifecycleAdapter, ProcessTransport and SimulatedEndpoint do not import apps.
A standalone module exercises completion, correlated Stop and unknown outcome on
disconnect with Python and the independent Node endpoint. The installed-wheel
check runs this proof outside the checkout; interoperability CI requires Node.
See [the SDK guide](lifecycle-sdk.md). This completes the bounded reusable-client
slice; further Explorer refinements remain deferred. Next: reproducible ESP32
bench configuration, compilation and manual acceptance procedure.
The same installed client also runs semantic/perceptual plans from the documented
multi-source diphenyl ether graph against Python and Node, preserving source
inspection, source/profile hashes, explicit bindings and correlated observations.

## Bounded software-process startup — 2026-11-11 manual fix

Two initial SDK CI runs failed in the evidence walkthrough while awaiting Node's
first response; subsequent green runs did not resolve that intermittent timeout.
A deterministic 2.2-second Node bootstrap reproduces the same HTTP 503 before
this fix. Example clients now allow five seconds for the first response and keep
the two-second bound for later exchanges. The transport exposes an optional
startup_timeout; existing callers retain their timeout unless they opt in.
The HTTP walkthrough allows the full connection handshake to finish. Tests cover
slow startup, subsequent-response deadlines, child cleanup and no command retry.


## Reproducible ESP32 LED bench — 2026-11-11 evening

The prototype has a pinned PlatformIO build entry point and a native harness
that includes the actual sketch. The host verifier maps the multi-source
diphenyl ether graph using both profiles and checks 44 serial/PWM/clock
observations, including refusals without output mutation, expiration, frame
limits and recovery. The dedicated firmware workflow cross-compiles the ESP32
target and runs the native bench. Compilation evidence is recorded in the PR
and control state, rather than assumed from configuration.

The [bench guide](../hardware/esp32/BENCH.md) supplies proposed components,
GPIO wiring and deliberate manual trials; the results sheet remains NOT RUN.
No board, flash, GPIO or scent output was accessed. Device Protocol 0.1 remains
acceptance-only; SDK software lifecycle/Stop must not be inferred for this board.
After successful compilation and host proof, the remaining hardware exit
criterion is a human-recorded trial; independent development proceeds to
documented installed data import/Core-to-graph-to-plan interoperability.


## Installed Core-to-graph interoperability — 2026-11-12

The installed `bridge-core` command and SDK `bridge_core_bytes` produce a
normal experimental graph using the existing exactly-one-SMILES projection.
A complete original-byte snapshot preserves document/odor/metadata extensions
and unknown representations, even where the typed projection is partial.
`extract-core` / `extract_core_bytes` verify its hash/count/document and recover
the exact original. Extraction never applies later graph edits to Core.
Output paths are exclusively created, so existing files and inputs are refused.

The fresh-wheel walkthrough validates the exported graph, plans its geraniol
semantic mapping and executes it through Python and Node software endpoints,
then recovers the original bytes. No app import or physical access is required.
See [the guide](core-interchange.md) and Draft RFC-0016. This completes the
bounded Core import/export slice; extending the importer to every data source
is not implied. Next: documented upstream-data import and contributor quickstart
with an explicit supported input contract, provenance and scientific limits.


## Installed selected-record CSV import — 2026-11-12 evening

`import-odornet` and SDK `import_odornet_csv` accept an explicitly selected
OdorNet-shaped CSV record and source/license manifest. The existing annotation
adapter preserves present/absent/unknown; unsupported tokens and ambiguous
headers fail. Raw selected cells, unknown columns, ordered headers, file hash,
record index and declared source context survive in Core and its graph snapshot.
A synthetic fixture is explicitly distinguished from real measurements.

The fresh-wheel path runs import → Core validation → graph → plan →
Python/Node lifecycle plus original Core recovery. See [the CSV contract](csv-import.md),
Draft RFC-0017 and [developer quickstart](developer-quickstart.md). No claim is made
that every upstream release or a full corpus was validated. This bounded slice
does not expand automatically into batch import. Next: test one authorized,
documented real source export and its preparation, then choose batch/multisource
support based on that reproducible need. Human hardware results remain NOT RUN.

The bounded public-source trial is now documented: unmodified NKU-DOIE processed
CSV at commit 88d146360dfc548462a5ebd6a081ea0590f2819e, selected record 1,
source/license attribution retained, expected channel-1 plan and Node lifecycle
passed. This completes one source-export trial, not corpus-wide validation.
Next: choose a concrete batch/multisource use case with deterministic source
tracking; retain the observed occasional Node startup timeout as unresolved.

## Explicit multi-record data workflow — 2026-11-13

The installed batch importer parses an explicit cohort once, embeds accepted
Core documents and retains per-record refusals/raw cells plus missing-record
results. A single JSON artifact preserves source/status context without
overwriting existing files. Accepted documents can be extracted, validated,
bridged and planned independently; their IDs match the single-record API.
See [the batch workflow](csv-batch.md) and the Draft RFC-0017 addition.

The bounded exit criterion is two accepted records, an invalid record and a
missing record retained together, followed by distinct plans and installed
Python/Node lifecycle proof for both accepted records. This is not full-corpus
validation, chemical deduplication or batch physical execution.

The public pinned-source cohort trial selected records 1/2/3/99999: three Core
imports, one missing-record refusal; records 1/2 planned and passed Node
completion/Stop/disconnect, while record 3 had no supported positive mapping and
was refused at planning. First-response timings were captured without a timeout
in this trial; earlier intermittent startup failures remain unexplained.
The cohort import/extraction exit criterion is complete. Further importer
polish is deferred in favor of a reusable JavaScript SDK boundary for developers
outside the Python checkout; preserve existing format maturity and reader limits.
