# Try a caller-owned CSV cohort with the installed kit

The extracted experimental developer kit now accepts an explicitly selected small
OdorNet-shaped CSV cohort, a source/license declaration and a mapping profile.
It preserves per-record refusals through import, graph bridging and planning.
This reuses the existing [CSV contract](csv-import.md), [batch contract](csv-batch.md)
and [offline planning profile](cli.md); it does not support arbitrary CSV schemas.
No new wire format, chemical validation or physical compatibility is implied.

## Normal entry point outside the repository

Build/download and extract the [portable kit](developer-kit.md), then follow its
`START_HERE.md` to install the wheel and both local npm tarballs. Keep the included
files unchanged and put caller files elsewhere. From the extracted directory:

```sh
python try_kit.py --csv /absolute/path/to/my.csv --source /absolute/path/to/source.json --rows 3 1 4 2 99 --profile /absolute/path/to/profile.json --report my-plans.json
```

All four input options are required together. Record indexes are one-based data
records after the header, not physical lines; select 1–1000 unique positive indexes.
The selected order is retained. Caller CSV is limited to 8 MiB, source/profile to
1 MiB each; these are this example workflow's limits, not new format limits.
See `data/source.json` and `profiles/semantic.json` for the supported examples.
`kind: "dataset"` is a caller declaration, not an independently observed fact.
Unknown selected columns and source declarations remain in the batch/Core context.

**Custom-input mode is passive by default.** It snapshots the supplied bytes,
records their identity and calls the installed Python CLI for import, checked Core
extraction, bridging, validation, exact Core recovery and five-second planning.
Every selected row remains represented: import failures are `import_rejected`;
bridge/validation/planning failures retain their phase and response; usable rows
are `planned`. Import acceptance alone does not guarantee a usable mapping.
No endpoint is launched during passive planning. With no custom-input options,
`try_kit.py` retains its original synthetic software self-test behavior.

The report embeds the batch with raw selected cells/Core documents, generated
graphs and complete passive planning artifacts with supplied profile/source
snapshots. It does not embed the entire original CSV. Intermediate filesystem
paths disappear after the trial; embedded values and hashes remain available.
Source/profile byte hashes identify the input snapshots, not authenticated origin.

## Explicit software simulation

Use a **new report path** to request the fixed software reference trials:

```sh
python try_kit.py --csv /absolute/path/to/my.csv --source /absolute/path/to/source.json --rows 3 1 4 2 99 --profile /absolute/path/to/profile.json --simulate --report my-software-trial.json
```

All passive planning finishes first. Only eligible records proceed. Simulation
preflight requires the profile to support the demonstration's 0.1-second
completion/disconnect and five-second Stop plans, and the fixed reference
channels 0–2 at intensities 0–1. A technically valid offline plan may therefore
remain `simulation_preflight_rejected`, with no execution attempt.

For each eligible row, the installed JavaScript reader transfers the original
graph bytes, which must compare equal. The Python and JavaScript lifecycle
clients each try the plan against Python and Node software endpoints. The report
retains all four observation groups as `software_observations`; successful
records become `software_verified`. Source/mapping, plan, acceptance, completed/
stopped/unknown observations and measured physical output remain distinct.
The trials use a supplied five-second plan plus the disclosed 0.1-second variant.
They execute only the included trusted software commands, without a sandbox.

Before any command is launched, a new report is exclusively reserved. An existing
report or input file cannot be overwritten. The initial marker says incomplete;
progress is written before simulation and after each observation. An interrupted
report is not proof of success. After an operational software failure, that row
remains unknown/failed, later prepared rows stay unattempted, and no retry occurs.
A separate explicit run with a different report path is a new trial: there is no
durable exactly-once or automatic restart recovery guarantee.

## Outcomes and proof

Exit codes: 0 all selected rows planned/verified; 3 retained per-record refusals;
1 workflow or software failure; 2 usage/I/O error. A partial report still contains
the usable plans and all refused entries; nothing is silently dropped. Configuration
failure stops the workflow and produces an error report where reservation succeeded.

The outside-checkout verifier creates caller CSV/source/profile files separate
from the kit, changes mapping strengths and selects rows in a different order.
It checks two distinct plans, invalid/missing rows and an accepted-but-unmappable
row, then runs both clients/endpoints. It also checks simulation preflight and
exclusive report creation. Reproduce from the development checkout:

```sh
python -m pytest tests/test_caller_cohort.py tests/test_developer_kit.py -q
python -m tools.build_developer_kit --output dist/opensmell-developer-kit.zip
python -m tools.verify_developer_kit dist/opensmell-developer-kit.zip
```

The custom fixture is explicitly synthetic; it demonstrates caller configuration,
not a third-party dataset trial or adoption. Dependencies are installed as described
in the kit guide; no complete offline dependency wheelhouse is bundled. The kit is
experimental, not a stable release. Human ESP32 trials remain separate and NOT RUN.
