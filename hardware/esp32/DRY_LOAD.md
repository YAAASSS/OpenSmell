# Experimental 5 V resistive dry-load bench

This opt-in **source and software simulation** slice prepares a three-channel
low-side driver bench beyond the LED reference. Board wiring, gate waveforms,
load current, supply behavior and reset behavior are **NOT RUN**. No valve, pump,
liquid, odorant, diffusion or human exposure is part of this target. A resistor
is an electrical dummy load, not a scent cartridge. Historical LED observations
do not validate this new circuit or firmware.

## Declared target and boundary

| Property | Proposed dry-load target |
|---|---|
| PlatformIO environment | `esp32-dry-load` (never the default) |
| Identity | `opensmell-esp32-dry-load-001` |
| Implementation | `experimental-esp32-dry-load-v1` |
| Channels / GPIO | 0 / 23, 1 / 22, 2 / 21 |
| Values | 0–1 electrical PWM duty, rounded to 0–255 |
| Duration | 0.1–5 seconds; expired output set to zero by the sketch loop |
| Permission input | GPIO32, 3.3 V logic, external pulldown; observed low then high after boot |
| Framing | Existing bounded 1024-byte UTF-8 JSON line implementation |
| Lifecycle | Existing experimental `local-simulator-lifecycle-v1` / `local-simulator-errors-v1` |

A high input at boot refuses rendering until the firmware samples low, then
high. Low clears output and changes a running execution to `stopped`; raising
it again cannot restart that execution. A fresh explicit command is required.
While unarmed, a render returns existing `busy` refusal. Five seconds is a
per-command limit, not an accumulated energy limit: explicit successive commands
remain possible while armed. Unsupported duration/command values never change
outputs. Completion/Stop retain the existing execution-ID correlation rules.
There is no wire command to arm this target.

This input is a **sampled software permissive**, not a hardware emergency stop,
watchdog, fault detector or guaranteed response time. It is sampled by the main
loop and during serial reception. Brief transitions between samples, CPU stalls,
reset/boot glitches, failed MOSFETs and electrical faults are not detected or
proven safe by native tests. A load supply disconnect remains independent of the
firmware. `completed` means the firmware deadline was observed and its output
commands were cleared; it does not measure current, flow or odor.

## Software-only entry

From a checkout with the SDK and build tools installed, obtain the pinned
ArduinoJson dependency as described in [BENCH.md](BENCH.md). Compile without upload:

```sh
pio run --project-dir hardware/esp32 --environment esp32-dry-load
python -m tools.build_esp32_host --dry-load \
  --arduinojson /tmp/ArduinoJson --output /tmp/opensmell-dry-load-host
python -m tools.verify_dry_load /tmp/opensmell-dry-load-host \
  --output new-dry-native.json
```

The executable includes the actual sketch with fake GPIO, serial and clock. It
cannot access physical GPIO or serial devices. `!enable 0`, `!enable 1`, `!pins`
and `!advance MILLISECONDS` are **native harness controls only**, never firmware
wire messages. `--boot-enable-high` tests startup refusal. Native-only
`--simulate-enable` explicitly samples low then high before the first request;
it is not a bypass in the ESP32 binary. Without it the native endpoint is unarmed.

With OpenSmell installed, produce a passive five-second plan from the documented
example, then separately select the trusted native executable:

```sh
set -C # Refuse an existing plan file (shell noclobber).
opensmell plan examples/multisource_diphenyl_ether.osmell \
  --profile hardware/esp32/dry_load_profile.json \
  --resource-id e6ad8ce3-dc6e-5d94-9287-57665d48fc0b \
  --duration 5 > new-dry-plan.json
opensmell lifecycle-trial new-dry-plan.json \
  --software-command-json '["/tmp/opensmell-dry-load-host","--realtime","--simulate-enable"]' \
  --expected-device-id opensmell-esp32-dry-load-001 --output new-dry-trial.json
```

Expected: the normal installed CLI observes `completed`, `stopped`, `unknown`
for its short completion, explicit Stop and deliberate link-close cases.
Disconnect is uncertainty, not Stop. The illustrative semantic profile maps
floral to CH0 duty 0.25 and green&herbal to CH1 duty 0.6. These labels do not
establish a physical odor relationship. The source graph/profile/provenance
remain retained by the normal passive plan and trial entries. Capabilities in a
profile are supplied declarations; execution independently checks live identity
and limits. A plan exceeding five seconds is refused before transmission by the
SDK and independently by the sketch if sent directly.

The installed standalone consumer also works with `--dry-load`:
[try_native.py](../../examples/firmware_lifecycle/try_native.py). For the ordinary
installed JavaScript client, use the same command JSON and expected identity with
[try_client.cjs](../../examples/lifecycle_client/try_client.cjs) and the explicit
`plan` object from the passive plan report. No Explorer dependency is required.
These are explicit trusted software executables, not sandboxed arbitrary programs.

To repeat the outside-checkout wheel and packed npm proof:

```sh
python -m build --wheel
python -m tools.verify_installed_firmware_lifecycle --dry-load \
  dist/opensmell-0.1.0-py3-none-any.whl --host /tmp/opensmell-dry-load-host \
  --evidence-directory new-dry-installed
```

It verifies Python/Node and the installed CLI for both explicit semantic and
perceptual duty mappings, duplicate-send protection and report collision refusal.
The installed serial module is also verified through an owned pseudo-terminal.
This additional proof needs the optional `serial` extra, or an explicitly supplied
local PySerial wheel through `--serial-wheel`; it never selects a physical port:

```sh
python -m tools.verify_installed_serial_bench --dry-load \
  dist/opensmell-0.1.0-py3-none-any.whl --host /tmp/opensmell-dry-load-host \
  --evidence-directory new-dry-serial
```

Completion/Stop, deliberately lost/partial replies, wrong identity, altered-plan
refusal and existing report collisions are checked on that software path only.
Build dependencies are inherited in these proofs; it is not the separate clean
offline starter target. Evidence is created exclusively and marked incomplete
until success. Native values are software observations only.

## Proposed electrical BOM and wiring — NOT RUN

Scope is **regulated 5.0 V nominal**, three **100 ohm, at least 1 W resistors**,
and a classic ESP32 DevKit-compatible board exposing GPIO21/22/23/32. This is
not a design for arbitrary actuators. Use the board's own USB supply for the
ESP32; a separate current-limited load supply powers only the dummy resistors.
Do not connect its positive rail to a GPIO, 3V3 rail or USB 5 V rail. Join grounds.
A switched load supply, set to 5 V and initially off, with a 0.20 A current limit
is the proposed bench setting, not a measured protection threshold.

| Quantity | Part / declared value | Purpose |
|---|---|---|
| 1 | Existing classic ESP32 development board | Exact board/pin labels must be recorded before wiring |
| 3 | AOS AO3400A N-channel MOSFET, labeled SOT23 breakout | One low-side switch per load; verify G/S/D orientation against manufacturer drawing |
| 3 | 100 ohm resistor, ≥1 W, 5% or better | Dry resistive dummy load; retain exact part/rating/tolerance |
| 3 | 330 ohm resistor | GPIO to gate series resistor |
| 3 | 100 kilohm resistor | Gate-to-source pulldown, physically near MOSFET |
| 1 | 10 kilohm resistor | GPIO32-to-ground external pulldown |
| 1 | Manual switch/jumper | Connect GPIO32 to board 3V3 when enabled; open = low |
| 1 | Regulated current-limited 5 V supply and manual load-supply disconnect | Independent energy removal; no automatic supply control |
| As needed | Rated wires, labeled breakout/terminal board, meter and oscilloscope | Verify actual pinout, voltage/current/duty; retain instrument identity |

Repeat this connection table independently for each channel. G/S/D mean the
actual AO3400A terminals shown by its manufacturer, not a guessed breakout order.
Do not use a visually similar module with an unknown active level or circuit.

| From | To |
|---|---|
| GPIO23 / 22 / 21 respectively | 330 ohm series resistor, then that channel's MOSFET G |
| Each MOSFET G | 100 kilohm resistor to its S |
| Each MOSFET S | Common ground (ESP32 GND and load supply negative) |
| Each MOSFET D | Its 100 ohm dummy-load resistor |
| Other end of each dummy-load resistor | Switched +5 V load rail |
| GPIO32 | 10 kilohm resistor to common ground; manual switch to board 3V3 |

At ideal 5 V / 100 ohm, full-duty current is 50 mA and resistor power is 0.25 W
per channel (150 mA / 0.75 W total); tolerance and actual supply voltage change
these calculations. A ≥1 W load rating supplies margin, not a temperature
measurement. Ideal average current scales with duty for this resistor only.
MOSFET on-resistance, gate switching, wiring and rail droop still need measurement.
No analog voltage accuracy, PWM frequency/edge timing or 0–1 flow linearity is
promised. Nothing here establishes an inductive-load/flyback design.

### Primary design references

Consulted 2026-11-22. These justify a **proposed** component/pin choice, not circuit
validation or procurement. No components were ordered.

- [AOS AO3400A datasheet, Rev 3.1 July 2023, pp. 1–2](https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf):
  N-channel, SOT23 G/D/S drawing and specified maximum RDS(on) 48 milliohm at
  VGS 2.5 V. That low-voltage specification, rather than threshold voltage, is the
  basis for proposing a 3.3 V gate drive at this small resistive load. Published
  maximum current/thermal ratings are not this bench's allowable load.
- [Espressif ESP32 series datasheet v5.3, pin overview and electrical characteristics](https://documentation.espressif.com/esp32_datasheet_en.html):
  GPIO21/22/23 and GPIO32 are GPIO-capable on the classic ESP32; verify the actual
  DevKit/module schematic and conflicts. This does not cover C3/S3 boards.
  GPIO logic uses the board's 3.3 V domain; no 5 V logic connection is proposed.

## Manual evidence procedure — no result yet

This document does not authorize autonomous flash or physical commands. An
operator's separately authorized manual session must first record the source
commit, compiled binary SHA256, exact target/board, component part markings,
resistor values, wiring photos, instruments and supply settings in
[DRY_LOAD_RESULTS.md](DRY_LOAD_RESULTS.md). Do not attach pumps, solenoids or odorants.

1. With both supplies disconnected, verify G/S/D orientation, grounds, gate
   pulldowns, enable pulldown and absence of shorts. Keep load disconnect open.
2. After independently arranging the new target firmware, leave loads disconnected
   and enable open. Power/reset the board and measure all gates low. Repeat with
   enable already high: a render must refuse until low then high is sampled.
   Measure reset/boot transients too; firmware-only claims cannot substitute.
3. Set load supply to the declared settings while disconnected. Attach only the
   three specified resistors. Close the load supply disconnect with enable low;
   verify no unintended current. If readings contradict the proposal, disconnect
   and record failure rather than continuing.
4. Manually enable low then high. Through an explicitly selected manual serial
   client, check the exact new identity/capabilities before any render. The old
   LED-target identity/client defaults must not be silently substituted. Send one
   explicit short plan per channel and compare measured gate duty/current against
   declared values. Record actual raw serial replies separately from instruments.
5. The installed manual entry is `python -m opensmell.experimental.serial_bench`
   from the [existing manual guide](../../docs/serial-lifecycle-bench.md), using
   the new passive plan, operator-selected `--port`, explicit
   `--expected-device-id opensmell-esp32-dry-load-001`, `--action complete` or
   `--action stop`, and a fresh `--output`. Install the optional `serial` extra
   first. If opening the port resets this board, select an explicit settling
   interval with `--startup-delay` (0–30 seconds): keep enable low through reset,
   then manually raise it during that interval before the first render. Otherwise
   expect refusal; do not retry automatically. No actual board/reset behavior is
   claimed. CI exercises this same installed module only on its own POSIX
   pseudo-terminal, explicitly connected to the fake-enabled native sketch.
6. For a manual five-second command, observe gate/load shutoff at deadline, then
   explicit Stop, then opening enable during a run. Record electrical traces and
   the correlated execution IDs/states separately. Re-enabling must not restart
   prior output. Verify a direct >5 s request refuses with no output change.
7. Repeat loss of serial link: it must not be labeled Stop; the firmware's own
   deadline should still clear output. Finally open the independent load disconnect
   and power down. Record failures/unknowns; no automatic retry or resume.

Exit for this source slice: all three ESP32 targets compile, actual dry-load
native harness passes startup/arm/trip/duration/Stop tests, and installed Python/
Node/CLI clients use the same profile. Close after those checks; do not grow a
new diagnostics UI. Next hardware gate is a **human-recorded electrical dummy-load
bench**, followed by a separately justified actuator design. Calibrated delivery,
olfactory measurement and outside adoption remain independent future evidence.
