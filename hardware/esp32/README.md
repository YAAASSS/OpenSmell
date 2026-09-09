# OpenSmell ESP32 Prototype

This directory contains the first physical OpenSmell Device Protocol 0.1
prototype.

The prototype demonstrates communication between the experimental OpenSmell
rendering stack and a physical device over a serial transport. The current
hardware exposes three independently controlled LED channels and has been used
to exercise both semantic and perceptual rendering paths.

It does **not** reproduce a physical odor. LEDs are used as simple, observable
stand-in actuators.

## Architecture

The demonstrated path is:

```text
RenderingPlan
    ->
ProtocolDeviceAdapter
    ->
Device Protocol 0.1
    ->
SerialDeviceTransport
    ->
ESP32
    ->
LED
```

Scientific interpretation and mapping to device channels are performed
outside the device.

The ESP32 firmware only understands device-level concepts such as channels,
intensities, and rendering duration. It does not assign universal odor
semantics to channels 0, 1, or 2.

## Hardware

The current prototype uses:

- an ESP32 development board;
- USB serial communication;
- three LED or equivalent test outputs;
- channel `0` on GPIO23;
- channel `1` on GPIO22;
- channel `2` on GPIO21;
- a common ground.

The firmware exposes:

- protocol version: `0.1`;
- device ID: `opensmell-esp32-led-3ch-001`;
- channels: `0`, `1`, and `2`;
- intensity range per channel: `0.0` to `1.0`;
- rendering duration range: `0.1` to `30.0` seconds;
- serial baud rate: `115200`.

## Firmware

The Arduino firmware is located at:

```text
hardware/esp32/opensmell_device_protocol_0_1/
    opensmell_device_protocol_0_1.ino
```

It requires the ArduinoJson library.

The firmware implements the experimental OpenSmell Device Protocol 0.1
messages required by the prototype:

- `hello`;
- `get_capabilities`;
- `render`;
- `ok`;
- `error`.

Rendering is non-blocking. After accepting a valid rendering request, the
device returns an `ok` response immediately and continues driving the
actuator for the requested duration.

The physical device validates the complete rendering plan before changing
outputs. It independently validates requested channels, intensities, and
duration. Duplicate channel commands are rejected, omitted channels remain
off, and valid commands in one plan are executed simultaneously for the shared
duration.

### Serial framing

The current ESP32 implementation uses UTF-8 JSON messages framed by a
newline over a `115200` baud serial connection.

Serial input is received incrementally into a fixed-size buffer. A single
message may contain at most `1024` bytes before its terminating newline.

If a message exceeds this implementation limit, the ESP32 discards the
remainder of that frame, waits for the terminating newline to restore frame
synchronization, and returns an error with code:

```text
message_too_large
```

The next complete serial frame can then be processed normally.

The `1024`-byte limit is a constraint of this experimental ESP32 prototype.
It is **not** a universal limit of OpenSmell Device Protocol 0.1.

This behavior has been physically validated on the ESP32 by sending an
oversized frame followed immediately by a valid `hello` frame. The oversized
frame was rejected and the following frame was processed successfully.

## Physical validation script

The manual hardware validation script is:

```text
hardware/esp32/esp32_physical_render.py
```

It is intentionally outside the automated `tests/` directory because it
requires physical hardware.

With the OpenSmell development environment installed and the firmware
running on the ESP32:

```powershell
python hardware\esp32\esp32_physical_render.py --port COM8
```

Replace `COM8` with the serial port assigned to the ESP32.

The script:

1. opens and synchronizes the serial connection;
2. performs device discovery;
3. reads the device capabilities;
4. sends a valid rendering plan;
5. verifies local rejection of an unsupported channel;
6. verifies local rejection of an unsupported duration.

Additional physical experiments have exercised simultaneous commands on all
three channels and confirmed device-side rejection of duplicate-channel plans.

## Geraniol end-to-end demonstration

A separate example demonstrates a longer experimental pipeline:

```powershell
python examples\geraniol_esp32_render.py --port COM8
```

The demonstrated path is:

```text
geraniol.osmell
    ->
Core OpenSmell Odor
    ->
ResourceGraph
    ->
SemanticChannelMapper
    ->
RenderingPlan
    ->
Device Protocol 0.1
    ->
ESP32
    ->
LED
```

For this demonstration, the application-level mapping is:

```text
floral -> channel 0
```

This mapping is only demonstration policy.

It does **not** mean that OpenSmell defines channel 0 as floral, nor that the
LED or current ESP32 prototype physically reproduces the smell of Geraniol.

## Multi-source (-)-beta-pinene demonstrations

The current three-channel endpoint has also been used with the experimental
multi-source (-)-beta-pinene fixture documented by RFC-0013.

That graph preserves two scientifically different branches:

```text
Molecule
  |
  +-- OdorNet Annotation
  |
  +-- Keller/Vosshall Stimulus -> ObservationTarget -> Observation
```

The branches can be interpreted by two materially different mapping policies:

```text
OdorNet categorical annotations
    -> SemanticChannelMapper
    -> RenderingPlan

Keller/Vosshall quantitative perceptual measurements
    -> PerceptualChannelMapper
    -> RenderingPlan
```

For the current reference experiment, the semantic demonstration policy
produces:

```text
channel 1 -> 0.6
channel 2 -> 1.0
```

The perceptual demonstration policy produces:

```text
channel 0 -> 0.01
channel 1 -> 0.86
channel 2 -> 0.97
```

Both plans target the same three-channel ESP32 endpoint. The mappings are
experimental application policy, not universal OpenSmell channel semantics.

In particular, the experiment does **not** claim that OdorNet categorical
states are equivalent to Keller/Vosshall quantitative measurements, that
related descriptor names are universally equivalent, or that either rendering
plan physically reproduces (-)-beta-pinene.

The experiment validates interoperability across heterogeneous source data,
different mapping policies, a common RenderingPlan boundary, Device Protocol
0.1, serial transport, and the same physical control endpoint.

See RFC-0012 for the rendering/device architecture and RFC-0013 for the
multi-source and multi-mapper interoperability experiment.

## Status

This hardware integration is experimental and non-normative.

The ESP32 prototype validates that the current software architecture can
reach and control a real physical endpoint through the experimental device
protocol and serial transport.

It should not be interpreted as validation of physical odor reproduction,
odor synthesis, or a universal olfactory hardware model.