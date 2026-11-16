# Try a caller-owned graph in the installed kit

The extracted kit's normal `try_kit.py` entry accepts an existing Generic
ResourceGraph 0.1, an explicit resource ID and an explicit mapping profile. This
connects categorical/Core imports and perceptual observations to the same trial
without guessing a source kind or importing the source CSV again. Experimental,
repository-maintained interoperability only; no stable API or third-party adoption
is implied.

Install the wheel and both local npm packages as described in `START_HERE.md`.
Keep your caller files outside the immutable kit. From the kit directory:

```sh
python try_kit.py --graph /path/to/observation.osmell \
  --resource-id YOUR_EXPLICIT_RESOURCE_ID --profile /path/to/profile.json \
  --duration 5 --report passive-graph.json
```

For example, first run the installed `opensmell import-keller` on
`data/synthetic_keller.csv` with `data/synthetic_keller_source.json`, selecting
row 1. Use the resulting import context's `primary_resource_id` and
`profiles/perceptual.json`. Or use an existing `bridge-core` graph and its
`org.opensmell.experimental.core-import.primary_resource_id` with an explicit
semantic profile. No resource is chosen automatically.

The entry verifies kit bytes, exclusively reserves the required report, snapshots
each caller file once, validates with the installed Python CLI, transfers exact
graph bytes through the installed JavaScript reader, then calls installed `plan`.
There is no endpoint during this passive path. Limited/partial JS inspection is
retained as such; opaque schemes and unknown fields are not claimed validated.
Invalid graphs, missing resources, empty mappings or unsupported capabilities/
durations retain a phase-specific refusal. A successfully validated graph can
still have no usable plan. Source/license/scale and channel meanings remain
supplied declarations, not chemical or measured odor evidence.

`--simulate` explicitly adds the existing fixed software walkthrough:

```sh
python try_kit.py --graph /path/to/observation.osmell \
  --resource-id YOUR_EXPLICIT_RESOURCE_ID --profile /path/to/profile.json \
  --duration 5 --simulate --report simulated-graph.json
```

Simulation preflights both the requested five-second Stop plan and the 0.1-second
completion/disconnect plan, plus reference channels 0–2 at intensity 0–1. Other
walkthrough durations refuse before endpoint launch. Both installed clients
(Python and JavaScript) try both fixed kit endpoints (Python and Node), retaining
completed, stopped and unknown-after-disconnect observations separately. This
walkthrough does not execute an arbitrary-duration single plan or a physical
Device Protocol 0.1 frame. No executable/serial device is inferred from a graph.

Reports contain exact graph/profile bytes as base64 with SHA-256 and byte length,
input paths, explicit request, validation, reader report, passive plan/refusal,
and any software observations. Snapshots preserve original formatting, unknown
extensions and supplied provenance even when caller files subsequently change.
Plan identity is tied to those snapshots; it is not a future preview or a durable
exactly-once execution record. Reports include all supplied source fields, so
choose their sharing scope accordingly.

Required reports use exclusive creation and checkpoints before simulation and
after each client. An interruption leaves incomplete/uncertain evidence; failures
stop without retry, and known observations remain retained. Existing paths refuse
before subprocesses; use a deliberate new report for a new trial. A bad kit
manifest refuses before the workflow. CSV options cannot be mixed with graph mode.

Limits: each input at most 1 MiB, Python 3.10+, Node 22+ reference; subprocess
steps bounded to 30 seconds. Exit codes: 0 planned/software-verified, 3 rejected
without simulation, 1 workflow/software failure, 2 usage/report collision. No
physical execution or olfactory reproduction is established.

## Reproducible proof

Build and verify a fresh extracted installation:

```sh
python -m tools.build_developer_kit --output dist/opensmell-developer-kit.zip
python -m tools.verify_developer_kit dist/opensmell-developer-kit.zip
```

The verifier uses graphs from both installed import routes, changes semantic
intensity and perceptual channel bindings, checks passive plans and missing-ID
refusals, then verifies both clients/endpoints. Original cohort trials and
no-overwrite/altered-kit protections remain covered. Python third-party
dependencies are inherited for this test, not bundled for offline distribution.
This completes the caller-graph slice; further trial flags or reader UI changes
require an observed integration need. Human hardware observations remain separate.
