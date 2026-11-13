# OpenSmell local developer-kit trial

Experimental development build, not a published release. Python 3.10+,
Node.js 22+ and npm are required. Extract into a **new directory**, then work
there. The archive contains only the declared synthetic CSV fixture, source
manifest, illustrative profile, software endpoint, local packages and trial scripts.
No external corpus, board command, flashing or odor diffusion is included.

## Install and try

```sh
python -m venv .venv
# Activate .venv using your platform's normal command.
python -m pip install packages/opensmell-0.1.0-py3-none-any.whl
npm install --offline --ignore-scripts --no-save --no-audit --no-fund --package-lock=false ./packages/opensmell-graph-reader-0.1.0-experimental.0.tgz
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
