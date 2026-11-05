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

## Prioritized next work

| Priority | Outcome | Acceptance criterion |
| --- | --- | --- |
| 1 | Minimal independent lifecycle adapter example and reference cases | A second implementation passes normal completion, correlated Stop, stale-ID and lost-link cases; do not claim third-party compatibility before observation. |
| 2 | Reproducible visual walkthrough | Exercise five-second completion, Stop and disconnect through the actual browser when an accessible local browser is available. |
| 3 | Assess lifecycle contract promotion | Use independent implementation evidence to revise Draft RFC-0014 before any physical firmware support. |

The RFC-0007 integrity fix is merged via PR #3. HTTP-envelope duplicate keys and
Core parsing remain scoped follow-ups, below the active product milestone unless
a concrete critical regression is demonstrated. No daily microfix quota.
