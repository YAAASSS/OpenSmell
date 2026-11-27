# Prepare an ordered experiment from a trial table (experimental)

`opensmell prepare-experiment` turns a caller-owned CSV, explicit ResourceGraph
and explicit mapping/capability profile into a portable **passive** dossier.
It prepares all trials together; it never launches a process or opens a device.
The output plans work unchanged with the existing installed `encode-frame` and
`run-sequence` entries. This is an experimental application convention, not a
new RFC, randomized study designer or scientifically validated protocol.

## Normal installed entry

Install from this checkout with `python -m pip install .`, or install its locally
built wheel. Run:

```sh
opensmell prepare-experiment examples/experiment/trials.csv \
  --graph examples/multisource_diphenyl_ether.osmell \
  --profile examples/offline_perceptual_profile.json \
  --output-directory my-experiment
```

Supply your own files to use the same command outside the checkout. The sample
is a declared demonstration with two durations for one observation; it makes no
claim of different odors or real experimental subjects. CSV required columns:

```csv
trial_id,resource_id,duration,condition
short,219ef28c-9b58-52f2-93a7-0807f5897857,0.1,declared-short
longer,219ef28c-9b58-52f2-93a7-0807f5897857,0.2,declared-longer
```

Each row explicitly selects a resource in the supplied graph and a duration in
seconds. The historical `--profile` mode applies one supplied profile to all rows.
Use [explicit per-trial profiles](trial-profiles.md) for the separate opt-in dossier0.2 mode. CSV order is retained;
there is no sorting, shuffling, implicit selection, default duration or skipped
invalid row. Trial IDs must be unique (1–128 characters) and are metadata, never
filenames. Additional columns are retained as opaque strings; they do not change
mapping or execution. Quoted fields, UTF-8 BOM and CRLF are supported; duplicate/
empty headers, blank/ragged rows and invalid UTF-8 are refused.

## Portable preparation and explicit software execution

The new directory contains exact `trials.csv`, `source.osmell`, `profile.json`,
numbered normal offline-plan artifacts and `experiment.json`. The manifest lists
trials in order, row annotations and hashes/lengths of retained files. Each plan
also contains its trial record/table hash as an opaque extension, so the normal
sequence receipt retains the connection to the caller's trial design. Unknown
source/profile context is preserved. Hashes identify supplied bytes; they are
not signatures, authentication or evidence that a scientific claim is correct.

All rows, source/profile contracts, mapping and durations are validated before
creating the directory. Every actionable plan passes the existing offline frame
checks. Invalid late rows refuse the entire preparation; there is no partial
accepted subset. Existing directories are never overwritten. I/O failure can
leave a directory with an `incomplete` marker; do not treat it as prepared. The
final marker is replaced after files are written, without crash durability/fsync
or a tamper-proof guarantee. Exit codes: 0 prepared, 1 invalid, 2 file/I/O error.

Bounds: 1–16 trials, at most 120 seconds summed requested duration; table 64 KiB,
graph 8 MiB, profile 1 MiB; plans 16 MiB combined. Each frame must meet the existing
1024-byte export bound. Empty/unmapped plans and unsupported supplied capabilities
are refused. Live capability/identity checks remain the execution entry's job.

Inspect the dossier, then independently select a **trusted software** endpoint:

```sh
opensmell run-sequence my-experiment/plan-001.json my-experiment/plan-002.json \
  --software-command-json '["node","examples/lifecycle_adapter/device.cjs"]' \
  --expected-device-id opensmell-node-simulator-001 --output my-receipts.json
```

List plan files explicitly in the manifest order; no glob order or automatic
manifest execution is assumed. The CSV/source/profile never select an executable.
The dossier can be moved and the original preparation files deleted; retained
plans are self-contained. Reprepare from the three retained inputs to reproduce
identical bytes. Changing a profile requires explicit repreparation in a new
directory; do not edit generated plans to bypass recomputation checks.

See the [software sequence guide](https://github.com/YAAASSS/OpenSmell/blob/main/docs/software-sequence.md) for cooperative Stop, correlation,
uncertainty and exclusively owned SDK clients. Preparation is not a command;
acceptance is not completion; software completion is not physical diffusion or a
measured olfactory result. No autonomous physical sequencing is provided.

In the extracted developer kit, use `data/trials.csv`,
`data/multisource_diphenyl_ether.osmell` and `profiles/perceptual.json` as inputs.
For execution, select `["node","software/device.cjs"]`; the expected Node identity
is unchanged. `SOFTWARE_SEQUENCE.md` is the bundled sequence guide. The wheel,
fixture and standalone software endpoint are included; no checkout path is needed.

## Reproduce the complete installed path

```sh
python -m build --wheel
python -m tools.verify_installed_experiment dist/opensmell-0.1.0-py3-none-any.whl \
  --evidence-directory dist/experiment-proof
```

The proof installs the wheel outside the checkout and uses a caller-modified graph
with an explicitly declared synthetic second observation, opaque extensions,
reversed CSV trial order and distinct durations. It relocates the dossier, deletes
original inputs, checks all retained bytes with the Python standard library, and
runs the normal sequence CLI on Python and independent Node. Repreparation from
retained inputs must be byte-identical; a bad final selection must create no
output; an existing dossier must survive a collision. Evidence retains the dossier
and raw software receipts. This is a repository-run interoperability demonstration,
not an observed third-party repeat. Local build dependencies are inherited; the
separate clean offline-kit CI gate establishes its own narrower target.

Exit criterion: installed caller table -> passive portable plans -> normal
software receipts, exact inputs and byte-identical repreparation, global refusal
and collision guards. Close this slice when it passes; no trial scheduling,
randomization/statistics or additional dossier formats by default.
