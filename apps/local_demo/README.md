# OpenSmell — Local Explorer

A local data explorer with optional ESP32 control. **English is the default language.**
The application remains an **experimental pre-alpha**.
It reads the bundled β-pinene sample offline, keeps the sources separate and
calculates both RenderingPlans using the existing Python mappers.

The illustrations represent planned commands for the LED prototype, never its
physical state. Preview works without a device or PySerial. Opening a serial port
requires **Connect**; transmitting a plan requires **Send to device**. Loading,
importing, recalculating and switching policies never send render commands.

## Run on this computer

From PowerShell:

```powershell
cd D:\OpenSmell
.\.venv\Scripts\python.exe -m apps.local_demo
```

The browser opens at **http://127.0.0.1:8765**. If it does not open automatically,
open this address yourself. Press **Ctrl+C** in the server terminal to stop.

To use another port or skip opening the browser:

```powershell
.\.venv\Scripts\python.exe -m apps.local_demo --port 8766 --no-browser
```

In that case, open http://127.0.0.1:8766. The server always listens on 127.0.0.1;
there is no option to expose it to the network.

For a fresh checkout with Python 3.10+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m apps.local_demo
```

On Linux/macOS, use `.venv/bin/python` instead of
`.\.venv\Scripts\python.exe`, from the repository root.

Initial installation may require Internet access for SDK dependencies. After
installation, the sample and interface work offline. No external datasets,
accounts, PubChem calls, web framework, Node.js or PySerial are needed for
preview. The server uses the Python standard library; mandatory SDK
dependencies are unchanged.

## Connect the ESP32

The supported reference prototype is **opensmell-esp32-led-3ch-001**, running
its existing three-LED firmware. No firmware update is part of this application.

Install the existing optional serial extra in the environment used to launch
the server, if needed:

```powershell
cd D:\OpenSmell
.\.venv\Scripts\python.exe -m pip install -e ".[serial]"
.\.venv\Scripts\python.exe -m apps.local_demo
```

1. Plug in the ESP32 with a USB data cable. Close any serial monitor or other
   program using its port, including the CLI demo or another server instance.
2. Click **Open demo**. In **ESP32 · LED prototype**, click **Refresh ports**.
   Select the correct port from the field's suggestions, or type it (for example
   `COM3`, `/dev/ttyUSB0` or `/dev/cu.usbserial-...`). Refresh only enumerates
   ports; it never opens them, probes devices or chooses a port automatically.
3. Click **Connect**. The link uses 115200 baud, 2-second read/write timeouts,
   a 2-second startup delay and initial input-buffer cleanup, matching the CLI.
   Opening the port may reset the board. Wait for **Connected**.
4. Check the received **Device ID**, duration range and channel ranges.
   **View received capabilities** shows the SDK-parsed device capabilities.
   Values are obtained by `hello` / `get_capabilities`, not assumed by the view.
5. Calculate a preview. **Ready to send** means that the complete selected plan
   matches the connected device's capabilities. Click **Send to device** only
   when you want those displayed commands transmitted.
6. **Command accepted** means an `ok` response was received. The remaining wait
   is a local estimate. Once it expires, completion is still **not confirmed**
   by the device. Observe the physical LEDs yourself.
7. Click **Disconnect** to release the serial port. This does **not** stop an
   accepted command. There is no Stop button because the protocol has no such
   command. Ctrl+C also closes the link when shutting down the server.

Changing source, policy or duration invalidates the sendable preview until a
fresh calculation succeeds. Each preview can be submitted once and expires
after ten minutes; click **Recalculate** for a new explicit send. The server
checks freshness and all capabilities again immediately before transmission.
Unsupported plans are rejected whole, without clipping values or dropping
commands. Empty semantic plans remain visible but cannot be sent.

The server maintains one shared connection across browser tabs and serializes
hardware operations. Simultaneous sends are rejected. A new plan cannot replace
one during its estimated execution window; wait, observe the LEDs, then
recalculate and send explicitly. This wait also survives Disconnect within the
same server session. Reloading the page neither reconnects nor resends anything.

## Short physical test

After connecting and checking the actual capabilities:

1. Choose **Semantic**, set **Plan duration** to **5**, then **Recalculate**.
   Check CH1 = **0.60**, CH2 = **1.00**, CH0 = **No command**. Click **Send to
   device**. Expect **Command accepted**; observe CH0 off and CH1/CH2 driven
   for the requested duration with the reference firmware.
2. Wait for the estimated window to end and observe the LEDs. Choose
   **Perceptual**, keep **5** seconds, and send the new preview. Check CH0 =
   **0.01**, CH1 = **0.86**, CH2 = **0.97**. CH0 may be hard to see at 0.01.
3. If the received maximum duration is **30 seconds**, wait for the previous
   window to end, enter **31**, and recalculate. Preview still works, but a
   duration incompatibility appears and **Send to device** remains disabled.
   Nothing should be transmitted. Restore **5** seconds to continue.
4. Click **Disconnect** and verify **Disconnected**. To demonstrate its meaning,
   you may also disconnect after a successful send while the LEDs are active:
   closing the link does not request a stop.

This procedure can be used to repeat the checks on your own board. The user's
confirmed results are recorded under **Hardware validation — user confirmation**
below. Software tests alone cannot establish physical LED behavior or electrical
accuracy, and this is not an odor-reproduction validation.

## Common connection and send errors

| Message or condition | What to do |
| --- | --- |
| Hardware unavailable | Install `.[serial]` in the server's Python environment; restart the server. Preview remains available. |
| No ports found | Check the USB data cable and operating-system port listing; refresh or enter the known port manually. |
| Port busy / access denied | Close serial monitors and other programs using the selected port; check OS permissions. |
| Connection failed / unexpected identity / invalid capabilities | Check the selected port, USB connection and existing firmware. The failed connection is closed. No render was sent by Connect. |
| Plan incompatible / empty plan | Read the received limits; correct the source, policy or duration and recalculate. Nothing was sent. |
| Preview outdated / expired / already submitted | Recalculate; review the new preview before a new explicit send. |
| Command rejected | Read the device's error code/message under **View command response**. No automatic retry occurs. |
| Execution uncertain | The command may have reached the board, but no usable response arrived. The link is closed. Observe the LEDs and wait before explicitly reconnecting; never assume nothing happened. |
| Local server unreachable | Connection and execution state cannot be confirmed. Check the server and device before repeating any action. |

There is no automatic reconnect or resend. Cable removal is detected only on
the next serial exchange, not by the status display, which reads cached state.
There is no LED telemetry or completion notification. Server restart loses
in-memory execution tracking; observe the board and allow any prior command to
finish before sending again. Keep a single server instance for the device.

## Try the interface

1. Click **Open demo** to load
   `examples/multisource_beta_pinene.osmell` from the repository.
2. Explore the 12 OdorNet annotations and 11 Keller/Vosshall measurements.
   Their values and scales come directly from the graph.
3. Switch between **Semantic** and **Perceptual**. Each switch asks Python
   to recalculate both plans for comparison.
4. Set **Plan duration** to **7.5** and click **Recalculate**. The plan duration
   changes; command levels still depend on the data and the mapping policy.
5. Expand **View demo rules** and **View the calculated RenderingPlan**.
   This JSON describes the application plan, not a Device Protocol message.
6. Open **Provenance** to inspect declared sources, records, derivation methods,
   dilution, context and complete resources. **Graph JSON** shows the graph
   serialized by the experimental generic API.
7. Enter a duration of **0**. An error appears and the previous plan is hidden.
   Correct the duration to continue without reloading the data.
8. Import `examples/coffee.osmell`. The diagnostic explains that this Core
   document is not a supported generic graph. **Open demo** restores the sample
   and the default duration of 5 seconds.

Verified reference values:

| Channel | Semantic | Perceptual |
| --- | --- | --- |
| 0 | No command | 0.01 |
| 1 | 0.60 | 0.86 |
| 2 | 1.00 | 0.97 |

These results are not hardcoded in the view. The interface displays the commands
returned by the mappers. A command with a value of zero remains in the plan;
an omitted channel is shown as “No command”. The reference firmware turns off
omitted channels when applying a plan.

Interface labels, accessibility text, status messages, validation diagnostics
and launch messages are in English. Displayed numbers use English formatting.
Scientific data, source text, identifiers, schemes, JSON keys and JSON values
are preserved as supplied, regardless of their language. “Absent”, “Unknown”,
“Not provided”, “Not specified (null)” and a numeric zero remain distinct.

## Supported imports

This application is not a universal `.osmell` reader. Import requires a UTF-8
JSON file of at most 1 MiB, in
`org.opensmell.experimental.generic-resource-graph` format, version `0.1`, with:

- exactly one `org.opensmell.molecule` 0.1 and one `observation`;
- the observation’s referenced `stimulus`, whose `source` references the molecule;
- a resolved `observation_target` if a target is referenced;
- at least one `org.opensmell.annotation` 0.1 for that molecule, using
  `org.opensmell.semantic.annotations` 0.1;
- at least one `flower`, `grass` or `wood` measurement that
  `PerceptualChannelMapper` can interpret, in
  `org.opensmell.perceptual.measurements` 0.1, with a numeric value and a valid
  explicit scale.

An empty semantic plan is valid, for example when all categories are absent.
The existing mapper skips unusable measurements; they remain available in the
data view and JSON. A result with no perceptual commands is diagnosed as
incompatible with this demo. Source names such as OdorNet and Keller/Vosshall
are displayed only when declared in the file’s provenance.

Imports are sent only to the server on this computer and processed in memory,
without saving the file. The server exposes no arbitrary filesystem paths or
directory listings and limits JSON requests to 2 MiB. The interface uses no
CDNs, remote fonts or persistent browser storage.

## Implementation and hardware boundary

- `service.py`: graph loading through `generic_graph_loads`, with Molecule and
  Annotation types registered; application prerequisites, mapping and view data.
- `__main__.py`: local HTTP server, `/api/preview`, and explicit hardware routes.
- `preview_store.py`: bounded in-memory, revisioned, single-use preview tickets.
  Late calculations cannot replace newer previews. Only server mapper results
  are retained for sending; a browser-supplied command list is never forwarded.
- `hardware.py`: connection ownership, lazy serial imports, serialized exchanges,
  full capability checks and accepted/rejected/uncertain execution states. It
  reuses `ProtocolDeviceAdapter` and `SerialDeviceTransport` without SDK changes.
- `static/`: HTML/CSS/JavaScript interface, with no build step.
- `../../tools/multisource_demo.py`: application rules and helpers shared with
  the existing CLI demo.
- `../../hardware/esp32/osmell_multisource_demo.py`: the original CLI and its
  existing hardware path. The local interface does not import it.
- `../../tests/test_local_demo.py`: integration tests for mappers, imports,
  diagnostics, HTTP, unmodified logos and absence of transport dependencies.
- `../../tests/test_local_demo_hardware.py`: software transport/serial doubles,
  lifecycle, exact plans, capability failures, stale previews, concurrent sends,
  timeout ambiguity and the local HTTP boundary. No physical port is opened.

The official logos are served unchanged from
`docs/images/OpenSmell_Official_Logo_Full.png` and
`docs/images/OpenSmell_Official_Logo_Small.png`.

Core, scheme and Device Protocol contracts, mappers, the sample graph and
firmware are unchanged by the hardware addition. The duration must be finite
and greater than zero. The application does not invent capabilities for a
disconnected device. All hardware mutations use JSON POST requests guarded by
the same loopback Host/Origin checks as preview. GET status is read-only and
GET ports only enumerates. No arbitrary render or hardware-stop endpoint exists.

## Software verification — historical results

The implementation was previously verified on 17 September 2026, using Windows,
Python **3.13.14** and Node.js **24.19.0**. The results below are historical;
the full suite and interoperability checks were not rerun for the subsequent
documentation-only validation update. Other Python versions in the CI matrix
were not run locally.

- Targeted application, shared-demo and mapper tests: **119 passed**.
- Full Python regression suite: **1,890 passed**.
- JavaScript syntax, English CLI help and whitespace checks passed.
- CI interoperability checks passed: regenerated RFC-0007 vectors unchanged;
  Python/JavaScript round trips and JavaScript checks for identifiers,
  ResourceGraphs, Molecule, Annotation, references, enriched OdorNet and
  Device Protocol 0.1.
- A separate Python environment without PySerial launched the full application;
  both previews remained available and the installation help was displayed.
- Browser checks with a **clearly labelled software simulator** covered port
  listing, connection/identity/capabilities, both 5-second sends, execution-window
  blocking, a 31-second incompatible plan, duration 0, incompatible Core import,
  disconnect, unexpected identity, device rejection and response timeout.
- Reference mapping values and source/provenance preservation remain covered
  by the existing integration tests. The official logos remain byte-for-byte
  served from the original files.

**Automated tests and agent-driven browser tests used software doubles only;
they issued no physical commands.** At that stage, the agent had not verified
physical LED behavior. Separately, the normal application was observed reporting
a connection on COM8 and an accepted 5-second command; that connection was left
intact. An acknowledgement alone did not confirm LED behavior. The user's
subsequent physical confirmations are recorded separately below.

Commands used for the earlier implementation verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_local_demo.py tests/test_local_demo_hardware.py tests/test_multisource_demo.py tests/test_experimental_semantic_channel_mapper.py tests/test_perceptual_channel_mapper.py -q
.\.venv\Scripts\python.exe -m pytest -q
node --check apps/local_demo/static/app.js
node --check apps/local_demo/static/hardware.js
.\.venv\Scripts\python.exe -m apps.local_demo --help
git diff --check
```

The complete interoperability command list is in `.github/workflows/tests.yml`.

## Hardware validation — user confirmation

Recorded on 17 September 2026. The user performed the following checks with
their real ESP32 and explicitly confirmed the results. These are user-reported
physical observations, separate from the automated tests and simulated browser
checks above. No additional hardware test was run for this documentation update.

| Check | Expected plan or limit | Result confirmed by the user |
| --- | --- | --- |
| Semantic, 5 seconds | CH0 omitted; CH1 = 0.60; CH2 = 1.00 | LED behavior matched the expected plan. |
| Perceptual, 5 seconds | CH0 = 0.01; CH1 = 0.86; CH2 = 0.97 | LED behavior matched the expected plan. |
| Duration of 31 seconds | Device-advertised maximum duration: 30 seconds | The request was correctly refused in accordance with the advertised limit. |

The levels in this table are expected command values, not electrical
measurements. This record is based on the user's confirmation; it does not add
measurements, screenshots or serial traces as evidence. This milestone validates
LED control for these checks, **not odor reproduction**. The project retains its
**experimental pre-alpha** status.

The protocol limitations remain unchanged:

- No telemetry confirms the end of execution or reports the physical LED state.
- The displayed remaining duration is a local estimate, not a device measurement
  or a completion acknowledgement.
- **Disconnect** closes the serial link; it does not stop an accepted command.

For this documentation update, verification is limited to reviewing the wording,
the exact commit contents and Git whitespace checks. Redundant blank lines at
the end of the shared demo helper were removed to satisfy the whitespace check.
Application behavior, tests, logos, scientific data, calculations, SDK and
firmware are unchanged by this update. The historical software results above
are not presented as newly run tests.
