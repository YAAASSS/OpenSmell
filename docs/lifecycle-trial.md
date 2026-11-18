# Try your software adapter from the installed CLI

`opensmell lifecycle-trial` connects an explicit offline plan to a trusted
software command and expected device identity. No copied or edited Python client
is required. It uses the installed experimental lifecycle SDK, without Local
Explorer. RFC-0014 remains Draft; this is a bounded adapter-author walkthrough,
not arbitrary-duration execution, device authentication or physical validation.

## Normal entry outside the checkout

Install the current locally built wheel with its runtime dependencies. Create a
five-second plan from your explicitly selected graph/resource/profile, or retain
an existing unexecuted `opensmell plan` artifact. Example with the documented
multisource fixture and the separate opt-in native sketch from
[the firmware guide](firmware-lifecycle.md):

```sh
opensmell plan multisource_diphenyl_ether.osmell \
  --profile offline_perceptual_profile.json \
  --resource-id 219ef28c-9b58-52f2-93a7-0807f5897857 --duration 5 > plan.json
opensmell lifecycle-trial plan.json \
  --software-command-json '["/tmp/opensmell-lifecycle-host","--realtime"]' \
  --expected-device-id opensmell-esp32-lifecycle-led-001 --output trial.json
```

`python -m opensmell` is equivalent. `-` reads the plan from stdin. Choose a new
report path: the CLI reserves it before process launch and never overwrites an
existing file, including after an interrupted or ambiguous trial. The report may
contain source data and command arguments; keep it private where appropriate.

The same CLI accepts the repository-maintained reference software endpoints:

| Endpoint | Explicit command JSON | Expected identity |
|---|---|---|
| Python reference | `["/absolute/venv/bin/python","-I","-u","/absolute/python_device.py"]` | `opensmell-local-simulator-001` |
| Node reference | `["node","/absolute/device.cjs"]` | `opensmell-node-simulator-001` |
| Compiled native experiment | `["/absolute/opensmell-lifecycle-host","--realtime"]` | `opensmell-esp32-lifecycle-led-001` |

The reference files are `examples/lifecycle_adapter/python_device.py` and
`device.cjs`. Copy them as needed; the native executable is built separately.
For your own adapter, explicitly replace the command and expected identity.
The process is trusted, launched without a shell and **not sandboxed**. Select
software-only endpoints; the CLI never discovers hardware or chooses a port.

## What the trial actually sends

Before launch, it strictly parses the bounded offline-plan0.1 artifact and
recomputes the selected commands from the embedded graph/profile/request. An
altered actionable plan is refused; exact input bytes retain unknown context.
Original source/profile hashes are supplied declarations, not reauthenticated
original files. Input is limited to8MiB; the selected frame must fit1024 bytes
excluding LF. The original plan must explicitly request five seconds.

After hello, capability and Draft-profile negotiation, both0.1-second and
five-second plans must fit the live declared channel/intensity/duration bounds
before the first render. The original offline capability identity is descriptive;
the separately supplied expected endpoint identity is checked on connection.

The trial sends three plans with the same commands:

1. A declared0.1-second derivative, then status polls until a received correlated
   `completed` response. Waiting alone is never completion. The observation window
   is three seconds, with bounded exchanges; it is not a hard process deadline.
2. The original five-second plan, then an explicit correlated Stop and a received
   `stopped` observation.
3. The original five-second plan, then explicit process closure. The retained
   execution must become `unknown`. Closing a link is not a Stop.

A reused client request ID is also refused before I/O. Any unexpected refusal or
uncertain outcome ends the walkthrough; later renders are not attempted. No
resend, recovery, reconnect or background polling is supplied. ProcessTransport
bounds the first exchange to five seconds and later exchanges to two seconds,
and closes on failure. The client retains only the latest run; the report keeps
each phase's observations.

## Reports and SDK API

`trial.json` is passive: reading it never contacts an endpoint. It checkpoints
the exact input snapshot, explicit command/identity, original request context,
all three declared plans, live declared capabilities, request lines, validated
response lines and last execution state. Failed exchanges retain an error and
available transport timing diagnostic; malformed response bytes are not exposed
by this transport. An interrupted file is incomplete, never presumed passing.

`status: passed` means this software walkthrough observed its three expected
outcomes, including deliberate final uncertainty. `incompatible` means identity,
profile or live-capability preflight refused before rendering; `rejected` is an
explicit render refusal; `unknown` retains an uncertain outcome; `failed` means a
different known behavior. Exit codes:0 passed,3 incompatible/rejected,1 other
trial/validation failure,2 file/access/output collision. No result establishes
physical output, odor reproduction or independent third-party adoption.

Python applications can call
`opensmell.experimental.lifecycle_trial.lifecycle_trial(plan_bytes, command,
expected_device_id="...", on_progress=checkpoint)` directly. The callback receives
independent passive snapshots; callers own exclusive report creation/persistence.
CLI errors before launch never authorize an automatic retry.

The wheel verifier exercises the normal installed entry outside the checkout
with both mapping paths and both reference endpoints. The firmware verifier adds
the actual compiled native sketch and retains its reports in the lifecycle CI
artifact. These are project-maintained interoperability observations.
