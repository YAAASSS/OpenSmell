# OpenSmell local developer-kit trial

Experimental development build, not a published release. Python 3.10+,
Node.js 22+ and npm are required. Extract into a **new directory**, then work
there. The archive contains only the declared synthetic CSV fixture, source
manifest, illustrative profile, software endpoint, local packages and trial scripts.
No external corpus, board command, flashing or odor diffusion is included.

The archive also includes `PERCEPTUAL_IMPORT.md`, a synthetic prepared
psychophysical CSV/declaration in `data/synthetic_keller*`, and
`profiles/perceptual.json`. After installation, try the separate passive entry:

```sh
opensmell import-keller data/synthetic_keller.csv --row 1 \
  --source data/synthetic_keller_source.json --output observation.osmell
opensmell inspect observation.osmell --json
```

Follow `PERCEPTUAL_IMPORT.md` for selection, ratings, planning and software bench
limits. In its commands, use the kit paths above and `profiles/perceptual.json`
in place of `offline_perceptual_profile.json`. `try_kit.py` retains its categorical
cohort contract; it does not guess the kind of scientific input.

## Install and try

```sh
python -m venv .venv
# Activate .venv using your platform's normal command.
python -m pip install packages/opensmell-0.1.0-py3-none-any.whl
npm install --offline --ignore-scripts --no-save --no-audit --no-fund --package-lock=false ./packages/opensmell-graph-reader-0.1.0-experimental.0.tgz ./packages/opensmell-lifecycle-client-0.1.0-experimental.0.tgz
python try_kit.py --report first-trial.json
```

Python installation may download `jsonschema` and its dependencies from your
configured package index. These dependencies are **not** in this archive;
for an offline installation, prepare your own dependency wheelhouse first.
The JavaScript package has no dependencies and installs from the local tarball.
CI tests with Python dependencies already available in the test environment.

Expected result: `result: "passed"`, two accepted CSV records, two explicit
refusals (invalid label and absent record), byte-identical JavaScript graph
transfer, original Core recovery, and different five-second passive plans:

| CSV data record | Plan | Software observations, Python and Node |
| --- | --- | --- |
| 1 | channel 0 at 0.25 | completed / stopped / unknown after disconnect |
| 3 | channel 1 at 0.6 | completed / stopped / unknown after disconnect |

The report retains raw batch/source context, JS inspection, passive plans and
correlated software observations. It is created exclusively; use a new report
name for another trial. Intermediate artifacts are temporary. The trial checks
manifest hashes before using the included bytes. A changed/missing kit file
fails; the manifest is not a signature or authenticated provenance record.
The scripts execute the included trusted Node software endpoint without a sandbox.

## Explore the installed tools

```sh
python -m opensmell --help
node_modules/.bin/opensmell-inspect-js --help
```

The trial calls the installed Python CLI and JavaScript API from another temporary
directory, with no source-checkout or app imports. To keep individual artifacts,
follow the same `import-odornet-batch`, `extract-csv-record`, `bridge-core`,
`plan` and `extract-core` commands described in the repository guides.

## What the result means

`data/source.json` declares Apache-2.0 handwritten pipeline data. Present/absent/
unknown labels are deliberately synthetic, not OdorNet observations or chemical
measurements. Raw cells and unknown fields are retained. The semantic profile
uses illustrative channel bindings and supplied capabilities. The source manifest,
local-build metadata and hashes identify declarations/bytes, not authenticity.

The JavaScript reader supports a limited Generic ResourceGraph 0.1 profile;
partial results retain opaque content and original numeric tokens. It does not
validate every representation or interpret the CSV batch. Python imports the
CSV and plans supported graph content. Neither tool infers scientific equivalence.
A plan is separate from acceptance; software completion is separate from physical
execution and a measured odor outcome. There is no hardware or third-party
compatibility/adoption evidence. ESP32 manual bench observations remain separate.

The project source/code license is in `LICENSE`; the data fixture's declaration
is in `data/source.json`. No stable SDK, npm/PyPI publication or release is implied.

The installed JavaScript lifecycle client also consumes each explicit plan and
records completed/stopped/unknown against both included software endpoints.
These observations are retained as `javascript_client_observations` beside the
Python-client observations. Both JavaScript packages are installed in one npm
command so neither local dependency is pruned as extraneous.

## Use your own selected cohort

Keep included kit files unchanged. Supply a small OdorNet-shaped CSV (8 MiB max),
source/license declaration and mapping profile (1 MiB each) from another directory:

```sh
python try_kit.py --csv /absolute/path/my.csv --source /absolute/path/source.json --rows 1 3 9 --profile /absolute/path/profile.json --report plans.json
```

Custom-input mode is passive: rows keep import/planning refusals rather than
being silently dropped. Add `--simulate` and choose a **new** report path to try
eligible rows with both clients against both included software endpoints. This
requires the profile to support the 0.1s/5s demonstration durations and channels
0–2. All planning/preflight completes first. A software failure stops later
attempts and remains unknown without retry. Exit 3 means retained per-row refusals;
0 means all rows planned/verified, 1 failure, 2 usage/I/O error.

Reports are reserved exclusively before work and checkpointed around simulation.
An incomplete report is not success and must not be retried automatically. It
contains selected raw values, graph/plan snapshots and supplied declarations;
full CSV bytes are not embedded. Hashes do not authenticate the source. The same
CSV/source/profile options are required together; select 1–1000 unique positive
one-based data-record indexes. The selected order is retained.


Offline protocol export is available through the installed `opensmell encode-frame`
command. See `PROTOCOL_FRAMES.md` and the included
`profiles/esp32-led-capabilities.json`. It generates data only, never sends to a
board, and does not establish acceptance/execution or an odor outcome.


Use the installed `opensmell replay-frame frame.json --native-host /absolute/path/to/host --output native-transcript.json`
entry to try your own export with a native harness you explicitly trust. See
`NATIVE_REPLAY.md`. The kit does not ship an executable. This launches software,
records native acceptance/refusal and fake outputs, and never accesses a board.


## Caller-owned graphs

`python try_kit.py --graph /path/to/input.osmell --resource-id ID --profile /path/to/profile.json --report graph-trial.json`
runs the common passive installed reader/plan path for categorical or perceptual
graphs. Explicit `--simulate` adds fixed Python/Node software trials only.
See `CALLER_GRAPH.md` for snapshots, refusals and limits.
