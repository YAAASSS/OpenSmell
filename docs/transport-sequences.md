# Transport-neutral bounded sequences (experimental)

Explicit offline plans can now run through a caller-supplied lifecycle transport,
without an Explorer application or software-process dependency. The existing
`opensmell run-sequence --software-command-json ...` entry and report envelope
remain compatible. This SDK addition reuses existing Draft lifecycle/error profiles,
not a new wire protocol. A receipt is not an electrical or olfactory measurement.

## Installed SDK entry

```python
from threading import Event
from opensmell.experimental.transport_sequence import run_transport_sequence

stop = Event()
report = run_transport_sequence(
    [first_plan_bytes, second_plan_bytes],
    make_owned_transport,  # callable: create/open only when invoked
    expected_device_id="explicit-device-id",
    transport_context={"application": "caller-owned context"},
    on_progress=save_checkpoint,
    stop_requested=stop.is_set,
)
```

The application explicitly supplies a trusted lazy factory returning a fresh
`exchange(str) -> str` / `close()` transport. The core exclusively owns it and
closes it once; do not share it or pre-open a transport expecting preflight to
undo outside actions. No command, port, factory or executable is selected from
plan data. Optional transport context is copied passive JSON (≤1 MiB), not
connection configuration. No diagnostic attribute is required of the transport.

All offline artifacts are recomputed/validated before factory invocation. Every
live capability is checked for every plan before the first render. Existing
bounds remain 1–16 steps, ≤120 s summed duration, 8 MiB per input/16 MiB total;
endpoint-specific channel/duration/frame limits still apply. Original plan bytes,
source/profile/request context, unknown extensions and caller trial-table record
stay in each step's retained snapshot. A changed source/projection/plan refuses
through normal frame validation, not a new permissive parser.

A sequence advances only on correlated `completed`. Stop, refusal or unknown
halts later sends and retains earlier receipts. IDs are consumed within one fresh
exclusive session, not durable reconciliation across restarts. The SDK publishes progress before possible acceptance; without `on_progress`,
its report is memory-only. The CLI supplies a writer and flushes checkpoints.
Applications supply their own persistence callback; no crash-safe durability is
implied by a callback or flush. Callback/storage failure closes the session
and never permits later renders. Partial output is not success. No retry,
reconnect, discovery or automatic resume is supplied.

`stop_requested()` is a caller-controlled cooperative predicate, checked at
progress checkpoints. It may be an Event set by a separate application control
or the progress callback. It prevents later sends and requests correlated Stop
when an active ID is known. It cannot interrupt blocked synchronous I/O and must
not perform endpoint exchanges. Ctrl-C closes with uncertainty; it is not Stop.
Closing serial may leave a device running its own bounded plan.

## Explicit human serial entry

The optional `serial` extra is required for serial use, not for the general core.
Install this revision/wheel with that extra separately; importing/preparing plans
never opens a port. Prepare a passive caller experiment with the ordinary
`opensmell prepare-experiment` entry, then explicitly list its plan files in the
manifest's caller order. Never infer scientific validity from preparation.

The installed module accepts an explicitly chosen **human** port and identity:

```sh
python -m opensmell.experimental.serial_sequence first-plan.json second-plan.json \
  --port HUMAN_SELECTED_PORT --expected-device-id EXPECTED_ID \
  --action complete --output new-sequence-report.json
```

This is a manual recipe, not an autonomous hardware test. No port discovery or
flashing occurs. `--startup-delay` explicitly selects 0–30 s of settling when a
board resets on open; it does not arm hardware or guarantee reset behavior.
For dry-load firmware the operator must handle low-then-high enable separately;
unarmed refusal must not be retried automatically. Choose the new target's
actual identity/capabilities, not a legacy LED default.

`--action stop-first` explicitly sends the first plan, waits for its acceptance
and cooperatively requests Stop; later plans remain unattempted. A race with
completion can produce a different terminal state; inspect the report instead of
relabeling it. Both actions exclusively create a fresh report and checkpoint
before I/O. Exit0 expected completion/Stop,3 invalid/incompatible/refused,1 other outcome (including unexpected Stop,
cancellation or unknown),2 file/checkpoint error. A failed write after possible
acceptance is not replaced by a fabricated invalid/no-send report.

The SDK convenience API is
`run_serial_sequence(inputs, port, expected_device_id=..., startup_delay=0,
on_progress=..., stop_requested=...)` from
`opensmell.experimental.serial_sequence`. Connection arguments are explicit,
validated before opening, and copied into passive transport context. Observed
endpoint state never changes the report's `physical_validation:false`.

## Reproduce without hardware

Autonomous verification uses only pseudo-terminals created by the verifier,
connected to actual compiled native sketches with fake GPIO/clock. Build the
lifecycle LED and dry-load host targets per the native bench guide, then:

```sh
python -m tools.verify_installed_serial_sequence \
  dist/opensmell-0.1.0-py3-none-any.whl \
  --host /tmp/opensmell-lifecycle-host --dry-host /tmp/opensmell-dry-load-host \
  --output new-serial-sequence-proof
```

This outside-checkout wheel proof prepares a caller CSV with distinct durations,
deletes original caller inputs, explicitly selects retained plans, then observes
the ordered sequence on both native targets. Stop-first, second reply loss,
software-proxy refusal, invalid late input/no connection, late live capability/no
render, wrong identity and report collisions are checked. The proxy records
actual downstream replies separately; a lost client receipt stays unknown even
when the harness saw acceptance. Proxy refusal is a declared injected software
fault, not an observed native/hardware refusal. POSIX PTY/software evidence only;
no physical port, electrical timing, delivery, odor or outside adoption claim.

Close this first core/manual-sequence slice after installed proof and CI. Keep
human electrical evidence and external adoption as separate gates; no scheduler,
auto-arming, reconnect or diagnostic UI extension by default.
