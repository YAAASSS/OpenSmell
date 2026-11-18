# Explicit serial lifecycle LED bench (experimental)

The installed SDK now provides a one-plan serial bench, using the existing
`SerialDeviceTransport` and `LifecycleAdapter`. It negotiates an explicitly
selected identity, validates an offline plan against its embedded source/profile
and live declared capabilities, then observes completion or explicitly requests
Stop. No port discovery, flash, retry, reconnect or automatic Stop on failure.

## Human-operated entry

Install the current locally built wheel with the `serial` extra (PySerial).
Prepare a plan using `opensmell plan` with an explicit graph/resource/profile and
duration. Build the separate experimental firmware following the
[firmware guide](firmware-lifecycle.md); default firmware is acceptance-only and
fails lifecycle negotiation. The new target's physical bench remains **NOT RUN**.
Only a human should flash/select a real board and execute this example:

```sh
python -m opensmell.experimental.serial_bench plan.json \
  --port YOUR_EXPLICIT_PORT --expected-device-id opensmell-esp32-lifecycle-led-001 \
  --action complete --output new-completion.json
```

`--action stop` explicitly requests correlated Stop immediately after acceptance.
It is a separate new invocation/report, not an automatic recovery action. Use a
short plan for completion and a five-second plan for Stop. Opening some ESP32
boards resets them; select `--startup-delay 2` explicitly when needed (default0,
finite0–30 seconds). Serial exchanges use115200 baud and a two-second timeout.
No startup bytes are silently discarded. Unexpected boot chatter fails the
connection; review it and the board state rather than resending automatically.

An existing output path prevents port opening. Before opening a port, the plan
is recomputed from its embedded source/profile/request; changed actionable plans
are refused. Up to8MiB input and1024-byte render frame excluding LF. Original
source/profile hashes are declarations; the exact plan artifact, including unknown
content, is preserved. No chemical equivalence or odor interpretation is inferred.

The report checkpoints request lines, decoded complete response text and the last
execution state. `observed` means a correlated `completed` or `stopped` reply for
the chosen action, not independent electrical measurement. An incomplete line,
lost reply, mismatch or expired observation window leaves uncertainty. A response
must end with LF (CRLF also accepted); timeout-delimited JSON is no longer accepted
as a complete serial message. This corrects a demonstrated false-completion path.
The completion window is plan duration plus three seconds, with bounded exchanges,
not a hard process deadline. Closing the serial connection is **not Stop**: the
board may continue its bounded plan. Reading a report is passive.

Exit codes:0 observed expected response,3 incompatible/refused,1 invalid or
uncertain outcome,2 input/report filesystem error or report collision. The SDK
entry `run_bench` in the same module accepts explicit bytes/port/identity/action
and an optional passive progress callback; callers own exclusive report storage.

## Reproduce without a board

On POSIX/Linux, compile the actual native lifecycle sketch, build the wheel and
run the verifier with a new evidence directory:

```sh
python -m tools.build_esp32_host --lifecycle --arduinojson /path/to/ArduinoJson-7.2.1 --output /tmp/opensmell-lifecycle-host
python -m build --wheel
python -m tools.verify_installed_serial_bench dist/opensmell-0.1.0-py3-none-any.whl \
  --host /tmp/opensmell-lifecycle-host --evidence-directory /tmp/new-serial-proof
```

The verifier installs the wheel outside the checkout. It inherits host Python
runtime dependencies; `--serial-wheel /path/to/pyserial.whl` optionally installs an
explicit local wheel without an index. This is not a clean/offline dependency
closure proof. Its bridge creates its own POSIX pseudo-terminal, relays raw bytes
to the actual native sketch, and opens only that owned slave through PySerial.
Both semantic and perceptual plans exercise completion, Stop, lost reply, missing
LF, wrong identity, changed-plan refusal and existing-report suppression.

The missing-LF experiment originally returned a false successful completion;
with the corrected transport it ends unknown after one render. No later plan or
Stop is sent. The firmware CI retains these reports with native lifecycle proof.
Pseudo-terminal bytes/PySerial framing do not establish USB-driver/reset behavior,
MCU idle timing, wiring, LED accuracy, physical actuator compatibility or measured
olfactory results. This proof is maintained by the project, not third-party adoption.

## Manual observation boundary

For actual wiring/BOM/resistors use the existing
[human LED bench](../hardware/esp32/BENCH.md). Record the exact binary hash,
board/port/wiring, serial report and independently timed LED observations. Verify
all LEDs initially off, extinction after short completion, and extinction after
explicit Stop on a five-second plan. Independently observe expiry after link loss;
never infer it from `unknown`. Do not resend an uncertain command without checking
the board. No physical experiment, flash or serial command was performed while
preparing this software proof. LED behavior never proves odor reproduction.
