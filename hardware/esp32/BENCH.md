# Reproducible ESP32 LED bench

Experimental reference build and manual acceptance procedure. This is a
three-channel **LED** bench; channel intensities are illustrative normalized
commands, not chemical concentrations or measured odor output.

## Build without a board

From the checkout root, with Python 3.10+:

```sh
python -m pip install platformio==6.1.18
pio run --project-dir hardware/esp32 --environment esp32-led
```

The configuration pins Espressif32 platform 6.9.0, the generic classic ESP32
`esp32dev` build target, Arduino framework and ArduinoJson 7.2.1. Platform 6.9.0
selects Arduino-ESP32 2.0.17 and Xtensa 8.4.0+2021r2-patch5. See
[platform metadata](https://github.com/platformio/platform-espressif32/blob/v6.9.0/platform.json)
and [board target](https://docs.platformio.org/en/stable/boards/espressif32/esp32dev.html).
This is a repeatable source build configuration, not a bit-identical binary
guarantee or proof that the maintainer used this exact board/SDK historically.

The normal build produces `hardware/esp32/.pio/build/esp32-led/firmware.bin`
and `firmware.elf`; it does not upload or open a serial port. Dependencies are
downloaded on first use. A checksum failure must be resolved by a valid download,
never by disabling verification. ESP32-C3/S2/S3 targets are not interchangeable:
the bench assumes a classic ESP32 exposing GPIO21, GPIO22 and GPIO23.

## Exercise the real sketch without hardware

Requires a C++17 compiler (g++ in the example), git and an installed checkout
(`python -m pip install .`). Obtain the exact ArduinoJson source used by the host:

```sh
git clone https://github.com/bblanchon/ArduinoJson.git /tmp/ArduinoJson
git -C /tmp/ArduinoJson checkout f9fe8557f13d8949eafd49ebd93a2929c4e5065f
python -m tools.build_esp32_host --arduinojson /tmp/ArduinoJson --output /tmp/opensmell-firmware-host
python -m tools.verify_esp32_firmware /tmp/opensmell-firmware-host
```

Choose writable local paths on your OS. The commit corresponds to ArduinoJson
7.2.1; the build helper also checks its version header. Dependencies are external,
not vendored into OpenSmell. The harness includes the actual .ino file; no second
firmware implementation is maintained. It replaces only Arduino serial, PWM,
GPIO mode setup and the clock. Its `!advance` / `!pins` controls exist solely in
the host executable, never in the physical firmware protocol.

The verifier maps the documented multi-source graph using both profiles, feeds
the resulting Device Protocol 0.1 frames through the sketch's serial parser and
checks PWM values, timing boundaries, rejected requests, 1024/1025-byte frames,
CRLF resynchronization and responsive hello during a long render. Its success
does not validate real electrical timing, wiring, flashing or physical behavior.
The GitHub **ESP32 firmware bench** workflow builds the target and runs this proof.

## Proposed reference bill of materials and wiring

This is a reproducible suggested LED assembly, not an inventory of the
maintainer's board. Confirm the markings and pinout before powering it.

| Quantity | Part | Required property |
| --- | --- | --- |
| 1 | Classic ESP32 development board | ESP32-WROOM style, exposed GPIO21/22/23, USB programming interface |
| 1 | USB data cable | Matches the board; data capable |
| 3 | Ordinary indicator LEDs | Low-current discrete LEDs, identify anode/cathode |
| 3 | 1 kΩ resistors | One series resistor per LED |
| 1 | Breadboard and jumper wires | Common ground; no external actuator supply |

Disconnect USB while wiring. Each GPIO goes through its own resistor to an LED
anode; its cathode goes to board GND. Do not connect LEDs directly without series
resistors. GPIO labels below are chip GPIO numbers, not header position numbers.

| OpenSmell channel | GPIO | Connection |
| --- | --- | --- |
| 0 | 23 | GPIO23 → 1 kΩ → LED0 anode; cathode → GND |
| 1 | 22 | GPIO22 → 1 kΩ → LED1 anode; cathode → GND |
| 2 | 21 | GPIO21 → 1 kΩ → LED2 anode; cathode → GND |

These outputs are for indicator LEDs. Pumps, heaters, valves, motors and
cartridges require a separately designed driver/power/safety system; attaching
one does not establish compatibility or a physical scent capability.

## Manual acceptance procedure

A person must deliberately prepare/program their board using their normal
tooling before this procedure. Compilation and CI never flash it. Start with
LEDs only, close all other serial clients, and record board markings, source SHA,
tool versions and wiring. Use a serial terminal at 115200 baud, newline framing.
Send one line at a time; wait for the observation before proceeding.

1. On boot all three LEDs should be off. Send
   `{"protocol_version":"0.1","type":"hello"}`.
   Expect device ID `opensmell-esp32-led-3ch-001`.
2. Send `{"protocol_version":"0.1","type":"get_capabilities"}`.
   Expect channels 0/1/2, intensities 0–1 and durations 0.1–30 seconds.
3. For each channel separately send (substitute channel 0, then 1, then 2):
   `{"protocol_version":"0.1","type":"render","duration":5,"commands":[{"channel":0,"intensity":1}]}`.
   Expect immediate `ok`, just the selected LED on, then off after about five
   seconds. Record observed duration separately from the acceptance reply.
4. Send
   `{"protocol_version":"0.1","type":"render","duration":5,"commands":[{"channel":0,"intensity":0.25},{"channel":1,"intensity":0.6}]}`.
   Expect LED0/LED1 activation and LED2 off. Visual brightness is not calibrated
   intensity; the host's expected PWM counts are 64/153/0.
5. Send the perceptual example:
   `{"protocol_version":"0.1","type":"render","duration":5,"commands":[{"channel":0,"intensity":0.47},{"channel":1,"intensity":0.18},{"channel":2,"intensity":0.15}]}`.
   Expected PWM counts are 120/46/38, with all LEDs off after the window.
6. Once all LEDs are off, repeat with duration 31. Expect `invalid_plan`,
   without LED activation. Repeat a five-second request to prove recovery.
7. While a five-second render is active, send hello and an invalid channel 3
   render. Expect hello plus `unsupported_channel`; the original window must
   remain intact. Wait for extinction before proceeding.
8. Send a known oversized frame followed by hello, using the existing
   [physical validation script](esp32_physical_render.py) only as a deliberate
   manual action. Expect `message_too_large`, then successful hello.

The script above also sends LED render commands; review its CLI/help/source
before using it. Device Protocol 0.1 returns acceptance only. There is no device
completion telemetry, correlated Stop or lifecycle profile on this firmware.
Closing USB/serial is not a Stop. A valid subsequent render replaces the active
LED targets/timer; this prototype does not queue plans. Use one client and wait
for observed extinction between normal trials. No physical trial was performed
by the automated development session.

## Results to retain

Copy [BENCH_RESULTS.md](BENCH_RESULTS.md), complete it manually and retain the
actual observations. A software PASS cannot fill in a physical PASS. Historical
maintainer confirmations remain in the README; this new configuration creates no
new physical evidence. Record failures and exact responses rather than inferring
successful LED output from `ok`. Odor reproduction requires separate measured
experiments and is outside this LED bench.
