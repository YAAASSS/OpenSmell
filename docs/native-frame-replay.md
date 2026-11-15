# Replay a caller-owned frame export in the native bench

The installed experimental `replay-frame` command consumes a frame export from
`encode-frame` and a **trusted native harness executable chosen explicitly**.
It records native protocol acceptance/refusal, capabilities and simulated output
observations. It has no serial/device discovery, flashing or physical output path.
The executable is not sandboxed; selecting a different program is the caller's
responsibility. Hashing its file is not an authenticated code attestation.

## Normal installed entry

Build the actual-sketch host using the pinned dependency and instructions in the
[frame guide](https://github.com/YAAASSS/OpenSmell/blob/main/docs/protocol-frame-export.md).
With your own exported `frame.json` and the installed wheel:

```sh
opensmell replay-frame frame.json --native-host /absolute/path/opensmell-firmware-host --output native-transcript.json
```

`-` reads a frame export from stdin. A **new** output file is required; existing
paths, including the input, are refused before launching software. The output
is reserved with an incomplete marker and checkpointed around every exchange.
An interrupted/incomplete file is not success; there is no automatic retry or
persistent exactly-once guarantee. A different report path is a new explicit trial.
Output is also printed as JSON on completion. Inputs remain unchanged.

Before process launch, the SDK validates the export envelope, original-byte
snapshots/hashes/counts, target context and exact encoded frame. It recomputes
mapping from the embedded source/profile/request using the existing encoder.
Altered frame bytes (even with an updated frame hash) or inconsistent context
fail. Unknown outer fields are not interpreted and survive in the exact input
snapshot. Export input is bounded to 24 MiB; original plan/target bounds remain
8 MiB / 1 MiB. Source/profile hashes remain supplied declarations, not evidence
that the original files or chemistry are authentic or fresh.

The child receives a hello and capability request first. Known device identity,
duration and channel capability values must match the supplied target description;
a mismatch produces `incompatible` and no selected render command. This first
bench profile requires the reference three channels 0–2 at intensity 0–1 and
0.1–30 s durations, so its fixed 31-second negative control is meaningful.
A matching but different capability range is also refused before render; this
is not a universal adapter for every native program. Each trial
uses a fresh process; fake PWM outputs must initially be off. The line submitted
for the selected frame is **exactly** the validated `frame.line`, including LF.
Only one selected frame is submitted, without retries.

## What the bench does

The transcript labels all actions:

1. `hello`, `capabilities`, `before_frame` negotiate and observe the native host.
2. `selected_frame` records the supplied command and exact reply; `after_frame`
   records simulated PWM values.
3. If accepted, a **separate labeled negative control** uses the same command with
   duration 31 s. The reference must refuse it without changing active outputs.
4. The fake clock advances beyond the selected duration (ceil(milliseconds)+1),
   then outputs must be off. This is not an exact electrical timing measurement.

A selected refusal is preserved as rejected and must leave fake outputs unchanged;
its negative control/clock trial is skipped. A lost or malformed reply stops the
trial, closes the child and retains a partial transcript without retry. Bounded
malformed response bytes are kept as base64; incomplete/oversized captures are
explicitly marked incomplete. Per-response bounds are 5 s for the first reply,
2 s thereafter, at most 65,536 response bytes including LF. Stderr is discarded.
No deadline from the existing lifecycle SDK has been increased.

`acceptance` is independent of `status`: a valid `ok` reply remains known accepted
if a later PWM/clock observation fails. `status: unknown` then means the overall
bench trial could not finish. `execution: not_observed` and
`physical_validation: false` always remain explicit. Output transitions in a fake
host are not a board execution observation or an odor result. Device Protocol 0.1
has acceptance only; RFC-0014 software lifecycle/Stop is separate.

Exit codes: 0 native acceptance plus bench checks completed; 3 explicit selected
refusal or pre-send incompatibility; 1 invalid export or incomplete/failed runtime
trial; 2 input/report I/O or usage error. The report retains input bytes, selected
executable identity, ordered request/reply lines, partial failures and fake outputs.
Statuses and hashes are local observations, not signatures or certification.

## SDK, proof and kit

```python
from pathlib import Path
from opensmell.experimental.native_replay import replay_frame
report = replay_frame(Path("frame.json").read_bytes(), "/absolute/path/opensmell-firmware-host")
```

`on_progress(report_copy)` can persist snapshots; callbacks are application-owned.
The CLI handles exclusive output reservation and checkpoints. `validate_frame_export`
is also available for passive validation before choosing any executable.

The extended fresh-wheel verifier also imports a caller-selected synthetic CSV
record, changes its profile to channel 1 at 0.8, bridges/plans/exports it through
the installed CLI, deletes preparation files, then replays the self-contained
export. Observed fake PWM is `[0,204,0]`, retained through negative-control refusal
and off after fake-clock advance. This is pipeline data, not a new measurement.

The verifier uses the installed normal CLI on semantic and
perceptual exports against the actual compiled sketch, checks unchanged selected
line bytes and fake outputs, and retains both transcripts. A valid export for a
different target stops after negotiation; a corrupt frame is rejected before the
command path. Unit cases also cover explicit refusal, lost/malformed replies,
known acceptance followed by lost observations, timeout and report collision.

```sh
python -m pytest tests/test_native_replay.py -q
python -m tools.build_esp32_host --arduinojson /path/to/ArduinoJson --output /tmp/opensmell-firmware-host
python -m build --wheel
python -m tools.verify_installed_frames dist/opensmell-0.1.0-py3-none-any.whl --host /tmp/opensmell-firmware-host
```

The portable kit includes this guide as `NATIVE_REPLAY.md` and the installed CLI;
it does not bundle a native executable. The caller must build/select the trusted
host explicitly. Current proof is on the Ubuntu/Node22/Python reference CI and
native C++ build; physical bench observations remain separately NOT RUN. No
third-party adoption, stable release or hardware compatibility follows from this
repository-maintained software trial.
