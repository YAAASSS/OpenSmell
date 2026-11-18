# Experimental firmware lifecycle: installed clients to actual sketch

The opt-in ESP32 LED target implements the existing **Draft RFC-0014** lifecycle
profile. Installed Python and Node clients can observe correlated completion and
Stop against the actual C++ sketch in a native software harness. The separate
legacy target remains Device Protocol0.1 acceptance-only, with its original ID.
Neither compilation nor fake PWM observations establish physical LED behavior,
electrical correctness, actuator compatibility or odor reproduction.

## Build and run the complete software proof

From a checkout with the normal Python build dependencies, g++, Node22+/npm and
an explicitly acquired ArduinoJson7.2.1 checkout:

```sh
python -m pip install . "build>=1.2"
git clone https://github.com/bblanchon/ArduinoJson.git /tmp/ArduinoJson
git -C /tmp/ArduinoJson checkout f9fe8557f13d8949eafd49ebd93a2929c4e5065f
python -m tools.build_esp32_host --lifecycle --arduinojson /tmp/ArduinoJson --output /tmp/opensmell-lifecycle-host
python -m tools.verify_firmware_lifecycle /tmp/opensmell-lifecycle-host --output /tmp/led-native-proof.json
python -m build --wheel
python -m tools.verify_installed_firmware_lifecycle dist/opensmell-0.1.0-py3-none-any.whl --host /tmp/opensmell-lifecycle-host --evidence-directory /tmp/led-installed-proof
```

Use new evidence paths each time; existing reports/directories are refused.
The raw bench exercises57 request/reply exchanges including fake outputs,
duration/channel/malformed/busy refusals, correlated Stop, terminal-state
stability, stale-ID refusal, fresh-process IDs and uint32 clock rollover.
The installed proof copies the consumers outside the checkout, installs the
wheel and locally packed JS client, and tries both semantic/perceptual plans
from the real multisource diphenyl ether example. Both clients must observe
`completed`, `stopped` and `unknown` after closing a running link. Duplicate
client request IDs and existing report paths are refused before another send.
Python dependencies are inherited in this bounded client proof; the separate
[clean offline kit proof](offline-kit.md) establishes its own distribution scope.
No registry publishing or network dependency acquisition occurs in the verifier.

The firmware CI compiles both targets, runs the legacy bench and both new normal
entries, and retains `experimental-led-lifecycle-native-proof` for14 days. The
Python transcript records each request/reply plus source/profile/native hashes;
Node records the explicit plan and three observed outcomes. These are software
observations, not authenticated device telemetry.

## Use the Python consumer independently

The installed [`opensmell lifecycle-trial`](lifecycle-trial.md) command also
accepts the native executable and an explicit offline plan directly, with no
consumer file to copy. The standalone example below remains useful for SDK
application authors.

Install the locally built wheel in your chosen environment. Copy
[`try_native.py`](../examples/firmware_lifecycle/try_native.py), the `.osmell`
fixture and the explicit mapping profile to a separate directory. The executable
must be a trusted native harness you selected; it is never a serial device.

```sh
python -I try_native.py --native-host /tmp/opensmell-lifecycle-host \
  --graph multisource_diphenyl_ether.osmell --profile offline_perceptual_profile.json \
  --resource-id 219ef28c-9b58-52f2-93a7-0807f5897857 --output new-proof.json
```

This entry maps before launch, reserves/checkpoints a new report, negotiates
identity/capabilities, and uses the installed `LifecycleAdapter` and
`ProcessTransport`. It never imports Local Explorer. It sends a0.1-second plan
for completion, then separate5-second plans for Stop and closed-link uncertainty.
The JS [standalone client](../examples/lifecycle_client/try_client.cjs) works
with command JSON `["/tmp/opensmell-lifecycle-host","--realtime"]`, identity below
and an explicitly selected plan object. The verifier demonstrates both routes.

## Selection, semantics and limits

| Target | Explicit selection | Identity | Execution evidence |
|---|---|---|---|
| Legacy LED | default `esp32-led`, native builder without `--lifecycle` | `opensmell-esp32-led-3ch-001` | Device Protocol0.1 acceptance only |
| Lifecycle experiment | `esp32-led-lifecycle`, native builder `--lifecycle` | `opensmell-esp32-lifecycle-led-001` | Draft profile, software-tested status/Stop |

The experimental macro is `OPENSMELL_EXPERIMENTAL_LIFECYCLE`. It reuses
`local-simulator-lifecycle-v1` and `local-simulator-errors-v1`; capability metadata
also announces `implementation: experimental-esp32-led-lifecycle-v1`. The profile
name is historical. This explicit source experiment does not upgrade the
standard0.1 contract, the default board firmware or RFC maturity. A legacy device
fails lifecycle negotiation. The LED pinout and declared0.1–30 second/0–1
intensity bounds remain unchanged; whole plans validate before output changes,
unmentioned channels turn off, and another render while running is refused.

Execution IDs combine a128-bit per-boot random namespace and a monotonic32-bit
counter. Exhaustion refuses new renders. Random namespaces are probabilistic,
not persistent authentication or durable reconciliation. Only the latest run is
retained; old or superseded IDs cannot stop a new run. Completion and Stop turn
all outputs off; repeated terminal Stop does not rewrite the terminal state.
The endpoint uses uint32 elapsed time across `millis()` rollover and rounds
duration up to milliseconds (floating parsing can add up to1ms). The timer is
checked while receiving/discarding frames as well as each main-loop iteration.
This is not a calibrated real-time timing or electrical safety guarantee.

Serial frames remain bounded to1024 bytes excluding LF; overlong frames are
discarded through LF, with the inherited0.1 framing error, then the next frame
can be processed. Structured lifecycle refusals use the Draft error profile.
`request_id` duplicate protection belongs to each installed client; it is not a
wire idempotency key. A raw repeated plan after termination is a new execution.
No retries, automatic resend/reconnect, delivery exactly-once guarantee or
recovery of a previous physical run is supplied. A closed/lost link leaves the
client outcome unknown and is not proof that an MCU stopped.

In the native harness `--realtime` samples host monotonic time when an input line
arrives. Fake-clock mode uses `!advance`; `!pins` reports fake PWM. These harness
controls are not wire protocol messages. Idle autonomous expiry, continuous
serial flood timing and actual boot entropy were not observed on a board.

## Cross-compile and manual bench boundary

```sh
python -m pip install platformio==6.1.18
pio run --project-dir hardware/esp32 --environment esp32-led --environment esp32-led-lifecycle
```

This command builds only; no upload, serial monitor or physical command is
invoked. For the BOM, resistor wiring, pinout and existing human procedure use
[the LED bench guide](../hardware/esp32/BENCH.md). This new firmware's manual
bench is **NOT RUN**. A human-led trial must explicitly select the experimental
binary/identity, verify all LEDs initially off, correlate a short accepted run
with status and observed LED extinction, verify a5-second run/Stop and all LEDs
off, then reject31 seconds and an old-ID Stop without changing a current run.
Keep firmware hash, actual board/wiring, exchanges and independent timed LED
observations. Close a link during a bounded run and independently observe expiry;
do not infer extinction from the host's `unknown`. No odor claim follows from
these LED observations. Physical access and flashing require a separate human
session; this software walkthrough performs neither.
