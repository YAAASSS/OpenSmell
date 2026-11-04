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

## Prioritized next work

| Priority | Problem and bounded next action | Success criterion / dependencies |
| --- | --- | --- |
| 1 | Verify the first scheduled run's tools and finish any pending bootstrap PR. | Actual clone, execution and authenticated publication available; lease respected; report any missing capability once. No extra test run just to trigger automation. |
| 2 | Audit duplicate-member handling at the remaining Core/RFC-0007 and HTTP boundaries. Reproduce first, then choose a compatibility-aware bounded fix. | No silent value choice in the selected boundary; explicit producer guidance and meaningful rejection/recovery tests. Depends on current contracts, not assumptions from this fix. |
| 3 | Improve installation/first-run reproducibility. Test a clean source install and both documented launch paths, then fix one demonstrated obstacle. | A new contributor can inspect a shipped example without serial hardware; no new runtime dependency unless justified. |
| 4 | Evaluate a small offline diagnostic CLI from the existing roadmap. First define one user scenario and reuse existing validators. | Useful input diagnostics and predictable exit status without sending commands; keep Core and experimental graph profiles explicit. Proceed only after higher-priority gaps. |

Keep this list short. Add new work only with a concrete problem, benefit, cost,
dependencies and verification plan; do not repeat a complete audit each day.
