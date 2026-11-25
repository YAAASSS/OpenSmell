# Analyze trial observations (experimental)

`analyze-experiment` passively joins a selected prepared dossier, its retained
`run-experiment` receipt report and **separately supplied** observation data.
Explicit CSV bindings select `trial_id,observation_id`; neither equal names nor
execution completion infer a measurement. No transport is constructed or opened.

## Installed entry

Prepare/run a dossier through [run-experiment](run-experiment.md), then supply a
Generic ResourceGraph0.1 containing your observations and a UTF-8 binding CSV:

```csv
trial_id,observation_id,caller_note
first,EXPLICIT_OBSERVATION_ID_A,declared association
second,EXPLICIT_OBSERVATION_ID_B,declared association
```

Use the **observation resource ID**, not a stimulus, subject or molecule ID. CSV
order does not reorder trials. Additional columns remain opaque caller context.
IDs are explicit nonblank strings up to128 characters. A trial can have several
observations; each observation can bind exactly once. Repeated observation IDs,
including duplicate pairs, are ambiguous: all competing associations are retained
in diagnostics and excluded from joined measurement/category rows. No first/last
winner or averaging is chosen.

```sh
opensmell analyze-experiment experiment --report execution-report.json \
  --observations supplied-observations.osmell --bindings associations.csv \
  --output-directory new-analysis
```

Original preparation inputs need not exist; the dossier can be relocated. The
whole dossier is reverified. The report must retain that exact dossier manifest,
inputs, caller order and per-step plans. A stale/different dossier, altered plan
snapshot or contradictory step/execution state refuses before output creation.
This checks declared consistency, **not authenticity of a receipt**. A report
without sequence receipts is retained as `unrecorded`, never `not_attempted` or
`completed`. Accepted/running/future states and unfinished reports remain partial.

Outputs in a new exclusive directory:

| File | Content |
| --- | --- |
| `analysis.json` | Exact input snapshots, complete observation projection/context, explicit bindings, joined numeric/category rows and coverage issues |
| `trials.csv` | Caller order, original record, receipt state/IDs, selected observation IDs and result counts |
| `measurements.csv` | Joined known perceptual0.1 numeric rows with trial, receipt state, source path/digest, scale/unit and binding context |

Unknown observation contracts, invalid/unmeasured results, unmatched IDs and
ambiguous bindings stay in the original snapshots/context and coverage diagnostics.
They are never guessed, skipped silently or coerced to numeric rows. Recognized
observation categories stay opaque in JSON, separate from numeric CSV. Semantic
annotations are not observation measurements and are not joined by coincident ID.

`status=joined` means complete coverage **within this projection**; it does not
mean successful scientific design, authenticated data or reproduced odor. Partial
coverage still produces usable tables and complete retained input. Exit0 joined;
3 partial;1 invalid;2 filesystem error/collision. Invalid input creates no output;
a write failure after exclusive creation leaves an incomplete marker. Existing
directories/reports are never overwritten. Analysis never rewrites its inputs.

Units and scales are not converted. Zero remains zero, absent measurements produce
no row, and absent/null unit fields have distinct `unit_presence` values. Mixed
units are not pooled. Integer values are not converted to floats. CSV exports raw
caller strings (including opaque fields); choose appropriate types and spreadsheet
import settings. For a loss-preserving Pandas consumer:

```python
import pandas as pd
rows = pd.read_csv("new-analysis/measurements.csv", dtype="string", keep_default_na=False)
# Select explicit property/unit/scale groups before any caller-chosen conversion.
```

## SDK

```python
from opensmell.experimental.trial_analysis import analyze_experiment, write_analysis_directory
result = analyze_experiment("experiment", report_bytes, observation_graph_bytes, binding_csv_bytes)
write_analysis_directory(result, "new-analysis")
```

Inputs are bounded at64MiB for the report,8MiB for observations and64KiB/4096rows
for bindings; existing dossier/sequence bounds still apply. Exact report, graph,
bindings, dossier input and plan bytes remain available. Source/provenance/unknown
fields and excluded rows are retained, not reduced to the CSV projection. Files
are local and the dossier check uses disposable compiler temporary files.

## Evidence and limits

```sh
python -m build --wheel
python -m tools.verify_installed_trial_analysis dist/opensmell-0.1.0-py3-none-any.whl \
  --output /tmp/new-trial-analysis-proof
```

The proof installs a wheel outside the checkout, imports **declared synthetic**
Keller-style rows through the normal entry, prepares/runs a relocated dossier on
the explicitly selected installed software simulator, then analyzes it through
the normal CLI and an optional Pandas consumer. Caller trial order survives reversed
observation graph order. Zero, missing values, categorical context, unknown fields,
exact source bytes, uncertain receipts, duplicate associations, stale reports and
output collisions are checked. Build/Pandas dependencies are inherited; this is
not a new clean offline dependency proof or independent third-party adoption.

The supplied observations can predate the software run. Binding is a caller claim,
not inferred stimulus equivalence, synchronization, causation or efficacy. An
unknown/not-attempted trial can still have caller-supplied observation rows; these
are retained beside the receipt state, not relabeled as an execution result.
This entry does not generate observations, normalize ratings, estimate statistics,
contact participants, run hardware, validate a device or measure an olfactory
outcome. Human electrical/olfactory validation remains a separate unobserved gate.
