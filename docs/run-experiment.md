# Run a prepared experiment (experimental)

`opensmell prepare-experiment` produces a passive portable dossier. The installed
`run-experiment` entry verifies that whole dossier, then runs its caller-ordered
trials on separately selected trusted software. It does not discover hardware,
select commands from data, randomize trials or establish scientific validity.

After installation, prepare a dossier using your explicit CSV/graph/profile:

```sh
opensmell prepare-experiment caller.csv --graph caller.osmell \
  --profile profile.json --output-directory experiment
```

Move `experiment` anywhere; original caller files are no longer required. Keep
all retained files together. Explicitly choose the installed software simulator
(replace `python` with your installed environment's Python executable):

```sh
opensmell run-experiment experiment \
  --software-command-json '["python","-m","opensmell","simulate-device"]' \
  --expected-device-id opensmell-local-simulator-001 \
  --action complete --output new-experiment-report.json
```

The supplied profile must match this endpoint's capabilities. The command is a
trusted executable/argument array, not sandboxed; arguments appear in the report.
Use `--action stop-first` and a new output to request cooperative Stop after first
acceptance. A short execution can finish before Stop; its actual terminal state
is preserved. Nothing runs when a dossier is imported or prepared.

## SDK and evidence

```python
from opensmell.experimental.experiment_run import run_prepared_experiment
report = run_prepared_experiment(
    "experiment", make_owned_transport,
    expected_device_id="explicit-device-id",
    on_progress=save_checkpoint,
    stop_requested=stop_event.is_set,
)
```

The trusted lazy factory returns `exchange(str)->str` / `close()`. It is never
selected from manifest contents. The SDK owns the resulting transport; reuse and
[sequence bounds/Stop/uncertainty rules](transport-sequences.md) still apply.
Invalid dossiers raise before invoking the factory. All bytes are read once and
retained before connection; subsequent file changes cannot alter a running trial.

The loader checks the bounded inventory, exact hashes and byte counts, then
recomputes preparation from retained CSV/source/profile with the normal compiler.
It compares caller order, trial IDs/records, request, mapping, plan and provenance,
including trial/table bindings. Recomputed hashes alone cannot make an inconsistent
plan actionable. Filenames come from recomputation; symlinked files, arbitrary
inventory paths and incomplete dossiers refuse. Current preparation versions 0.1 (shared profile) and 0.2 ([explicit per-trial profiles](trial-profiles.md))
is supported; artifacts incompatible with the installed compiler refuse rather
than being silently migrated. Recomputing uses disposable local temporary files.

Extra passive manifest and top-level plan fields survive exact snapshots. Source
and profile unknown data remain preserved and subject to ordinary planning rules;
unknown data never configures execution. This is consistency checking, not source
or device authentication. Hand-edited required fields/records must be prepared
again through the normal entry.

`prepared_experiment` in each progress/final report retains exact manifest, CSV,
source and profile snapshots and explicit trial order. Each sequence step includes
its caller `trial_id`, separate from session execution/request identifiers. Original
plan snapshots and earlier receipts remain after Stop, refusal or unknown. Later
steps are not attempted. No retry, reconciliation or automatic restart is offered.

The CLI exclusively creates its report before connection and flushes checkpoints;
invalid dossiers can leave a new empty output. Existing output is never replaced.
The SDK is memory-only without a persistence callback. Flush/callback success does
not guarantee fsync/crash durability. Callback/storage failure closes the transport
and must be treated as potentially uncertain; closing is not emergency Stop.
CLI exit: 0 completed/requested Stop; 3 invalid live configuration/refusal;
1 other incomplete/uncertain result or invalid dossier; 2 filesystem/launch error.
No physical execution or measured odor follows from a software receipt.

## Reproduce the software proof

From a checkout with development dependencies and committed ArduinoJson headers
available locally, compile the real lifecycle sketch for the host, build a wheel,
then exercise the installed entry outside the checkout:

```sh
python -m tools.build_esp32_host --lifecycle --arduinojson /explicit/ArduinoJson --output /tmp/lifecycle-host
python -m build --wheel
python -m tools.verify_installed_experiment_run dist/opensmell-0.1.0-py3-none-any.whl \
  --host /tmp/lifecycle-host --output /tmp/new-experiment-proof
```

The proof creates a fresh venv with inherited build dependencies (not clean offline
closure), prepares three distinct-duration caller trials, relocates the dossier,
removes originals and runs completion, Stop, second reply loss and an explicitly
injected software refusal. Receipts retain trial order and bytes; output collision
and hash-consistent trial corruption refuse without new process traffic. The
fault wrapper is explicitly selected by the verifier, never by dossier data.
Actual native sketch software is used; ESP32 electrical/serial/odor observations
and independent third-party adoption remain unobserved.
