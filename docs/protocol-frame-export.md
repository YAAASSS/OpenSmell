# Offline plan-to-protocol frame export

The installed experimental `encode-frame` command turns a CLI offline-plan 0.1
artifact into one Device Protocol 0.1 render frame. It opens no transport and sends
nothing. A frame is data, not acceptance, execution, or an observed odor outcome.

## Normal installed workflow

Install development main (`python -m pip install .`). With the supplied examples:

```sh
opensmell plan examples/multisource_diphenyl_ether.osmell --profile examples/offline_semantic_profile.json --resource-id e6ad8ce3-dc6e-5d94-9287-57665d48fc0b --duration 5 > plan.json
opensmell encode-frame plan.json --capabilities hardware/esp32/led_capabilities.json --output frame.json
```

These installed commands also work outside the checkout with your own copied
inputs. `-` reads one planning artifact from stdin. The output is a new JSON
**export artifact**, not a raw serial frame. Its `frame.line` contains the exact
UTF-8 JSON command and one LF terminator. `frame.sha256` identifies those line
bytes; `message_bytes` excludes LF and `line_bytes` includes it. For example:

```json
{"protocol_version":"0.1","type":"render","duration":5.0,"commands":[{"channel":0,"intensity":0.25},{"channel":1,"intensity":0.6}]}
```

The encoder checks the supported unexecuted artifact envelope, recomputes its
mapping from embedded source/profile/request snapshots and compares actionable
plan values. It then checks nonempty/unique commands, finite numbers, duration,
channels and intensities against the **separate supplied target capabilities**.
A changed plan, incompatible target or framing bound is refused. Mapping profile
capabilities and target device capabilities serve different stages and need not
have the same descriptive device ID. No target is discovered or queried.

The target JSON in `hardware/esp32/led_capabilities.json` describes the three-channel
LED reference. Native bench CI checks it against the actual sketch's reply. That
comparison is software evidence, not a live board capability observation.
`--max-message-bytes` defaults to its 1024-byte limit excluding LF; it is an
application framing constraint, not a universal protocol maximum. Choose 1–65536
only when justified by another explicitly supplied target. Raising it does not
change the reference ESP32 firmware's fixed 1024-byte receive limit.

Existing output files, including inputs, are refused. Exit: 0 encoded, 1 invalid
input/plan/target/bound, 2 I/O error. No rejected input creates a frame artifact.
Artifact input is bounded to 8 MiB and target to 1 MiB; reads include at most one
additional byte to detect excess. Full snapshots increase the export's size.

## SDK and preservation

```python
from pathlib import Path
from opensmell.experimental.frame_export import encode_plan_frame

result = encode_plan_frame(Path("plan.json").read_bytes(),
                           Path("target.json").read_bytes())
line = result["frame"]["line"].encode("utf-8")  # Data only; no automatic send.
```

`input` and `target` retain exact original bytes as base64 with hash/count,
including unknown extensions, numeric spellings and whitespace. Only recognized
command fields go into the frame; no unknown source representation is converted
to an actuator meaning. `context` records declared source/profile identities,
request and original plan. Raw plan metadata survives even if not acted upon.

Source/profile hashes inside the input remain **declarations**: the embedded
JSON documents cannot reconstruct their original source/profile file whitespace
or authenticate those files. Recomputing mapping checks internal consistency,
not authenticity, chemical identity or that the caller selected fresh inputs.
Callers own freshness/provenance policy. Output records `transport: not_opened`,
`acceptance: not_observed`, `execution: not_observed`, `physical_validation: false`.
The report is an experimental application envelope under Draft RFC-0015, not a
new Device Protocol wire format or normative certification.

## Actual-sketch proof with the installed wheel

From a development checkout with a C++17 compiler and the pinned ArduinoJson
7.2.1 checkout (commit `f9fe8557f13d8949eafd49ebd93a2929c4e5065f`):

```sh
python -m tools.build_esp32_host --arduinojson /path/to/ArduinoJson --output /tmp/opensmell-firmware-host
python -m build --wheel
python -m tools.verify_installed_frames dist/opensmell-0.1.0-py3-none-any.whl --host /tmp/opensmell-firmware-host
```

The verifier installs the wheel into a fresh environment outside the checkout,
checks its import location, generates semantic and perceptual plans through the
normal installed CLI, and encodes their frames. The exact emitted line bytes go
to the existing actual-sketch native harness over process stdin. It verifies the
sketch's capability reply against the supplied target file, `ok` acceptance and
fake PWM values `[64,153,0]` / `[120,46,38]`. A raw 31-second request is refused
without changing the active fake outputs; advancing the fake clock by five seconds
turns them off. It also checks altered-plan and existing-output refusals.
The existing 44-case sketch bench remains in CI, plus ESP32 cross-compilation.
Python dependencies for the isolated proof are inherited from the test environment.

The native harness explicitly supplied by `--host` is a trusted executable, not
a serial port or sandbox. Its fake serial/PWM/clock cannot validate board wiring,
electrical timing, diffusion or measured odor. Device Protocol 0.1 has acceptance
only; the separate Draft RFC-0014 software lifecycle and Stop do not apply to this
board. No flash or hardware command is part of this workflow. Physical bench
results remain a separately recorded human trial.

## Use from the portable kit

The kit includes this guide as `PROTOCOL_FRAMES.md` and the target description as
`profiles/esp32-led-capabilities.json`. Save one passive plan artifact from your
caller-cohort report, then invoke the installed encoder:

```sh
python -c "import json; from pathlib import Path; r=json.loads(Path('my-plans.json').read_bytes()); p=next(x['plan'] for x in r['records'] if 'plan' in x); Path('selected-plan.json').open('x').write(json.dumps(p))"
opensmell encode-frame selected-plan.json --capabilities profiles/esp32-led-capabilities.json --output frame.json
```

Choosing a plan is explicit; encoding has no automatic execution step. A valid
offline plan may still be refused by this target. Native compilation/proof uses
the source checkout and pinned build dependencies, not an executable shipped in
the portable kit. See the repository [bench guide](https://github.com/YAAASSS/OpenSmell/blob/main/hardware/esp32/BENCH.md)
for prerequisites and the manual observation boundary.
