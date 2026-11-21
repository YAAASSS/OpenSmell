# Optional Lab Streaming Layer software markers (experimental example)

The copied `examples/lsl_markers/bridge.py` consumer uses the **installed SDK** to
run explicit plans and publish observed software states through real Lab Streaming
Layer (LSL). `receive.py` uses only pylsl and the Python standard library, without
OpenSmell imports. This is a runnable optional scientific integration example,
not a new SDK dependency or a demonstrated third-party deployment.

The SDK's experimental wire contract remains unchanged. Source/profile/plan data
never select an executable. Every software command, endpoint identity and stream
source ID is explicitly supplied by the caller. No serial port/GPIO/flash or
physical diffusion is involved. The selected child process is trusted, not sandboxed.

## Install the optional runtime and prepare explicit inputs

Install the SDK from this checkout or its local wheel. In a dedicated environment:

```sh
python -m pip install . pylsl==1.18.7 numpy==2.2.6
opensmell prepare-experiment examples/experiment/trials.csv \
  --graph examples/multisource_diphenyl_ether.osmell \
  --profile examples/offline_perceptual_profile.json --output-directory my-experiment
```

Pinned optional runtime verified on Linux x86_64 CPython3.12 with the platform
pylsl wheel and its bundled liblsl. The generic pure-Python wheel may require a
separate liblsl installation; other targets are not established by this proof.
Neither optional package is added to the SDK default or offline-kit dependencies.
Use the official [pylsl installation/runtime guide](https://github.com/labstreaminglayer/pylsl)
for platform-specific requirements. The proof records `library_info()` rather
than treating a Python package version as proof of its loaded native binary.

## Run an independent receiver, then the SDK bridge

Start the receiver in one terminal:

```sh
python examples/lsl_markers/receive.py --source-id my-unique-opensmell-trial \
  --output received-markers.json
```

Then start the bridge within the receiver's 10-second discovery window:

```sh
python examples/lsl_markers/bridge.py my-experiment/plan-001.json my-experiment/plan-002.json \
  --software-command-json '["node","examples/lifecycle_adapter/device.cjs"]' \
  --expected-device-id opensmell-node-simulator-001 \
  --source-id my-unique-opensmell-trial --output sender-report.json
```

Use a fresh source ID per run and fresh evidence filenames. The scripts can be
copied outside the checkout with the standalone software endpoint and prepared
plans. In the extracted developer kit they are `lsl_bridge.py`, `lsl_receive.py`,
and the Node endpoint is `software/device.cjs`; optional dependencies still need
explicit installation. The source ID is a selection label, not authentication.

The bridge explicitly configures machine-scope discovery before creating LSL
objects. It waits up to five seconds for a consumer before launching the trusted
software endpoint. Missing consumer or output collision means no child is launched.
Machine-scope discovery is **not a security boundary** or proof that sockets bind
only to loopback; do not transmit sensitive trial IDs on an untrusted host/network.
See the official [liblsl configuration guide](https://labstreaminglayer.readthedocs.io/projects/liblsl/guide/configuration.html).

The receiver disables recovery and requires exactly one matching stream. It
retains raw received samples, stops on `run_finished`, and otherwise bounds its
wait to 180 seconds / 512 samples. A partial reception is not a completed trial.
The publisher briefly allows queued samples to leave before exit. A successful
`push_sample` or consumer connection is not a receipt acknowledgement: **compare
the receiver file**. There is no delivery retry, automatic reconnect or replay.

## Meaning of markers

Each irregular-rate string sample contains JSON with a run ID, event index,
kind and explicit `physical_validation:false`. Trial IDs come from the prepared
plan's opaque trial annotation, or fall back to SDK step IDs. Duplicate trial IDs
are refused before launch. Exact plan/source context stays in the sender's SDK
report; the stream carries IDs and state/correlation summaries, not full data.

| Kind | Meaning |
|---|---|
| `run_started` | SDK snapshot processing started; not device execution |
| `step_snapshot` | Changed passive SDK snapshot: trial/state, local request ID, endpoint execution ID and uncertainty detail |
| `run_finished` | Sequence runner returned this overall status; not physical success |

Repeated identical snapshots are suppressed. `unknown` can represent **pre-send
intent** with no execution ID, as well as later uncertain I/O. Do not translate
it into a confirmed endpoint event. Only the corresponding accepted/running/
completed/stopped receipt has that meaning. Refused and unattempted later steps
remain distinct. Callback/marker failure aborts the runner, closes uncertainty
and prevents later sends; no missing marker is fabricated to make a complete log.

Timestamps use `pylsl.local_clock()` at the software callback. The independent
receiver keeps the raw LSL timestamp (no time correction/smoothing configured).
They do not identify valve activation, stimulus arrival, biological response or
measured olfactory onset, and no latency/precision guarantee is made. Consult
[LSL time synchronization](https://labstreaminglayer.readthedocs.io/info/time_synchronization.html)
when integrating actual acquisition systems; this example does not validate them.

For the deterministic cooperative Stop demonstration, prepare a **5-second**
first plan in a new trial table, keep the second explicit, and add
`--stop-after-first-acceptance`. Expected software states: `stopped`,
`not_attempted`. Stop racing completion can instead report completion/cancellation;
never infer an emergency or physical Stop guarantee. Bridge exit: 0 completed,
3 other returned sequence outcomes, 1 startup/marker/I/O failure. Evidence uses
exclusive files; interrupted writes can leave an incomplete/partial report.

## Reproduce actual installed interoperability evidence

```sh
python -m build --wheel
python -m pip download --only-binary=:all: --dest dist/lsl-dependencies pylsl==1.18.7 numpy==2.2.6
python -m tools.verify_installed_lsl dist/opensmell-0.1.0-py3-none-any.whl \
  --dependency-directory dist/lsl-dependencies --evidence-directory dist/lsl-proof
```

The proof installs the wheel and explicitly selected optional dependency wheels
in a new environment outside the checkout. It copies the scripts, prepares two
caller-identified plans, runs separate actual LSL inlet/outlet processes, and
compares every received marker and raw timestamp against the sender. It checks
Python/Node completion, cooperative Stop on both references, refusal and lost
reply; unattempted later plans remain unattempted. It also checks no-consumer and
collision guards before child launch. Full sender/receiver files and native
library information are retained. Build-environment dependencies are inherited;
this is not the clean offline-kit proof or independent outside adoption.

Exit criterion: this normal copied-consumer path with actual external library,
explicit IDs and correct terminal/uncertain outcomes. Close this first LSL slice
when CI passes; no acquisition-device driver, recording format, new timing claims
or marker diagnostics by default. A human hardware bench remains separate.
