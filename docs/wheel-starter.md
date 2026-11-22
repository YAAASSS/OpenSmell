# Start from the installed wheel alone (experimental)

The SDK now contains a minimal synthetic software workspace and a JSON-lines
simulator entry. No checkout, copied endpoint script, Node, browser, serial port
or optional scientific package is required for this path. The SDK's normal
`jsonschema` dependency closure is still required; the wheel does not bundle
third-party dependencies or constitute a new registry release.

## Create a passive workspace

Install the locally built wheel into your chosen Python environment, then run
from any directory outside the checkout:

```sh
python -m pip install /absolute/path/to/opensmell-0.1.0-py3-none-any.whl
opensmell init-workspace my-first-workspace
cd my-first-workspace
```

`python -m opensmell` is equivalent to `opensmell` for every command below.
The directory must be new, even if an existing one is empty. Existing contents
are never merged, reset or overwritten. Parent directories can be created.
The command creates only `README.md`, `sample.osmell`, `profile.json` and
`workspace.json`. It does **not** plan, launch a child or connect/send anything.

The Core sample is explicitly synthetic semantic data plus an opaque unknown
representation. The profile declares software-only bindings/capabilities with
no universal channel meaning. Template hashes/lengths in `workspace.json`
identify original packaged bytes, not signatures or continuing approval of
edited inputs. A write failure can leave an incomplete marker/directory; use a
new directory after diagnosing it. No crash-durability/fsync guarantee is made.

## Inspect, plan, then explicitly choose software execution

```sh
opensmell validate sample.osmell
opensmell inspect sample.osmell --json
opensmell plan-core sample.osmell --representation-index 0 --profile profile.json --duration 0.1 --output plan.json
opensmell run-sequence plan.json --software-command-json '["python","-I","-m","opensmell","simulate-device"]' --expected-device-id opensmell-local-simulator-001 --output receipt.json
```

The plan is passive (`execution:not_attempted`). Only the last command explicitly
launches the installed software endpoint. `python` must resolve to the environment
where you installed OpenSmell; substitute its absolute executable path in the JSON
array if needed. Process arguments are passed without a shell. Expected sequence
status: `completed`, supported by a correlated endpoint observation. Nothing here
establishes physical output or an odor result.

Changing your input/profile requires explicit repreparation into a new plan file.
The opaque sample index1 is valid Core but intentionally not mappable; selecting
it refuses without falling back to index0. Duration31 is also refused by this
explicit profile. Original Core bytes, including unknown fields, stay in the
normal plan artifact; the downstream boundary checks the Core projection against
that snapshot. See the [Core planning guide](https://github.com/YAAASSS/OpenSmell/blob/main/docs/core-planning.md).

For completion, cooperative Stop and uncertain link closure, use the existing
installed trial rather than a new starter-specific execution engine:

```sh
opensmell plan-core sample.osmell --representation-index 0 --profile profile.json --duration 5 --output trial-plan.json
opensmell lifecycle-trial trial-plan.json --software-command-json '["python","-I","-m","opensmell","simulate-device"]' --expected-device-id opensmell-local-simulator-001 --output trial-receipts.json
```

Expected `status:passed`: received completion, received Stop, and `unknown` after
an intentionally closed active link. The trial explicitly declares a 0.1-second
completion derivative; Stop and closure use the supplied 5-second plan. Request IDs
cannot be reused within the session. There is no automatic retry, reconnect or
resume, and Stop is not emergency/physical preemption. Choose fresh output names.

## Installed simulator boundary

`opensmell simulate-device` exposes the existing SDK `SimulatedEndpoint` through
stdin/stdout, with its existing identity `opensmell-local-simulator-001`, three
channels 0–2, duration 0.1–30 seconds and experimental lifecycle/error profiles. It has no
hardware backend, port/path selection or physical mode. The SDK model and wire
profiles are unchanged; standalone repository Python/Node endpoints remain usable.

This is a protocol service, **not** a REPL or user-facing shell. It writes only
one JSON response plus LF per complete request and no stdout banner. Stderr is
reserved for fatal framing errors. Requests require UTF-8 JSON and LF, at most
65536 bytes excluding LF. Complete invalid JSON, duplicate members, NaN/Infinity,
invalid UTF-8 and BOM receive a protocol refusal; the next complete request can
still be processed. Oversized/missing-LF frames terminate the process without
accepting the partial request. EOF closes the simulator; it does not confirm a
completion or Stop. Capability/duration, busy, identity and execution-ID behavior
comes from the reused SDK endpoint. Its time advancement is software-observed,
not a physical timing guarantee or odor measurement.

## Reproduce the clean outside-checkout proof

For the existing first pinned dependency target (Linux x86_64, CPython3.12,
glibc>=2.28):

```sh
python -m build --wheel
python -m tools.offline_dependencies --output dist/starter-dependencies
python -m tools.verify_installed_starter dist/opensmell-0.1.0-py3-none-any.whl --dependency-directory dist/starter-dependencies --evidence-directory dist/starter-proof
```

Dependency acquisition is explicit and networked. The verifier checks the existing
pinned dependency inventory, creates a clean venv with system/user sites disabled,
installs only the SDK and normal dependency wheels with `--no-index`, removes
Node from `PATH`, and checks optional imports are absent. No checkout resources
or helper endpoint scripts are copied into the workspace. It creates/validates/
inspects the installed workspace, uses caller-edited synthetic Core data, completes
two distinct plans, runs completion/Stop/link-closure, and verifies collision,
unknown-selection, duration and wrong-identity refusals. Evidence retains runtime
versions, the workspace and actual receipts. CI repeats this under an empty network
namespace; the separate portable kit and optional integrations keep their own scope.
Other Python versions are covered by the normal suite, not by this narrow clean
binary-dependency closure proof. No tag, registry release or outside adoption is
inferred from repository-run tests.

Exit: a user with the wheel and its normal dependencies can complete this entire
path without a checkout, Node or optional runtime. Close this first starter slice
when CI passes; no template catalog, new protocol, auto-send wizard or simulator
diagnostics by default. Human hardware observations remain a separate gate.
