# Local Explorer with ESP32 control — documentation audit

Audit date: **17 September 2026**. Implementation reviewed:
`4b1ddd329d7c30819ba6cc50c4fe9a52c8f6c1e4`, on `main`. This is a non-normative
record of the **experimental pre-alpha** application, not a new specification.
The documentation update leaves application behavior, official logos,
scientific data, calculations, SDK and firmware unchanged.

The audit below is historical. The later
[import-size fix and verification](#import-size-fix-and-verification) records
the resolution of its application discrepancy separately.

## Documents and implementation reviewed

The audit covers the [main README](../README.md), the
[application guide](../apps/local_demo/README.md), the
[ESP32 guide](../hardware/esp32/README.md), the
[Core 0.1 specification](../spec/opensmell-0.1.md), relevant Draft RFCs below,
and the [CI workflow](../.github/workflows/tests.yml). Contribution guidance
lives in the main README; its milestone checklist now covers tests, README,
RFC consistency and verified publication.

Code review covers [graph loading and preview](../apps/local_demo/service.py),
[shared demo rules](../tools/multisource_demo.py),
[preview tickets](../apps/local_demo/preview_store.py),
[hardware lifecycle](../apps/local_demo/hardware.py),
[HTTP boundaries](../apps/local_demo/__main__.py),
[preview UI](../apps/local_demo/static/app.js),
[hardware UI](../apps/local_demo/static/hardware.js), SDK mappers and device
adapters, the existing firmware and the two application test modules.

| Reference | Contract or context used | Application boundary |
| --- | --- | --- |
| [Core 0.1](../spec/opensmell-0.1.md) | Device-independent odor/representations document. | Core files such as `examples/coffee.osmell` are not supported imports here. |
| [RFC-0003](../rfcs/RFC-0003.md), [RFC-0006](../rfcs/RFC-0006.md), [RFC-0013](../rfcs/RFC-0013.md) | Provenance, resource identifiers, separate scientific source branches. | Displays supplied identifiers, sources, records and derivation context; does not verify source truth or regenerate IDs. |
| [RFC-0004](../rfcs/RFC-0004.md) | Semantic annotations 0.1; present, absent and unknown are distinct. | Fixed channel bindings and levels apply only to matching `present` entries; they are demo policy. |
| [RFC-0005](../rfcs/RFC-0005.md) | Perceptual measurements 0.1 with explicit numeric scales. | Existing mapper normalizes `(value - min) / (max - min)` and skips unusable or out-of-range entries. This is a mapping choice, not a universal perceptual conversion. |
| [RFC-0007](../rfcs/RFC-0007.md), [RFC-0008](../rfcs/RFC-0008.md) | Observation, Stimulus and target resources; versioned Generic ResourceGraph envelope and type registry. | Requires a specific connected Molecule/Observation/Annotation profile; does not accept the older closed RFC-0007 envelope. |
| [RFC-0009](../rfcs/RFC-0009.md), [RFC-0010](../rfcs/RFC-0010.md) | Molecule and Annotation type 0.1; Annotation subject references and opaque scheme data. | Exactly one recognized Molecule and Observation; matching annotations and a usable perceptual plan. Unknown types/versions are preserved but do not satisfy those prerequisites. |
| [RFC-0011](../rfcs/RFC-0011.md) | Structural references in known fields. | Semantic mapping follows Annotation subject references; it does not infer links from arbitrary opaque data. |
| [RFC-0012](../rfcs/RFC-0012.md), [RFC-0013](../rfcs/RFC-0013.md) | RenderingPlan, capabilities, device adapter/protocol, and two independent mappings from one graph. | Existing components are composed directly; explicit user actions, preview tickets and execution-window blocking are app policies. |

Only RFC-0012 and RFC-0013 need additions to their implementation-evidence
sections. Their status remains **Draft**. No new RFC is needed: there is no new
portable graph, rendering, capability or device contract, nor an architectural
change to the existing separation of data, mapping and hardware. Private HTTP
routes and application safeguards do not establish a new interoperability
standard. The functional discrepancy below is recorded without changing a
contract to accommodate it.

## Import and mapping findings

The accepted envelope is
`org.opensmell.experimental.generic-resource-graph`, version `0.1`. The
[application guide](../apps/local_demo/README.md) lists the exact resource and
reference prerequisites. The `.osmell` suffix alone does not determine the
format, and the separate Geraniol Core-to-graph bridge is not used by this app.
Generic loading validates containers and preserves extensions; it does not
validate all opaque scheme payloads. The mappers filter entries they can use.
Both plans are calculated for every successful preview; a graph with no usable
perceptual command is refused even if Semantic is selected. An empty semantic
plan can be previewed but not sent.

The shared policy binds semantic `floral`, `green&herbal`, `woody&mossy` to
CH0/CH1/CH2 at fixed levels 0.25/0.60/1.00. Perceptual `flower`, `grass`, `wood`
use the same channel order with explicit-scale normalization. Each mapper keeps
the first usable entry for a channel; neither averages duplicates nor merges
the two source branches. Missing, absent, unknown, null, numeric zero and an
omitted command remain distinct. Duration is positive and finite and does not
rescale intensities. These choices match the existing helpers and mappers.

## Rendering, connection and failure findings

- `RenderingPlan` requires a positive finite duration and unique non-negative
  integer channels with finite normalized levels. Its metadata is not part of
  the Device Protocol `render` message. The shared contract permits an empty
  command list; the app refuses to send one.
- Connect explicitly opens the selected port at 115200 baud, with a 2-second
  startup delay and 2-second read/write timeouts. It performs `hello` and
  `get_capabilities`, checks identity consistency and restricts the app to
  `opensmell-esp32-led-3ch-001`. Received duration and channel ranges are used;
  the view does not invent capabilities while disconnected.
- A complete concrete plan is checked before sending and again by the SDK
  adapter. Incompatible channels, levels or durations cause rejection without
  clipping or partial submission. The app does not use `render_pipeline`'s
  optional whole-mapper-configuration check; it validates the selected plan.
- Browser changes invalidate the preview. Server revisions reject late
  calculations and stale tickets; only server-generated plans are retained.
  Tickets expire after ten minutes, with at most 64 client entries. Sending
  accepts a ticket, not browser-generated device commands, and consumes it
  before the serial exchange. A new explicit send requires recalculation.
- A shared connection and non-blocking operation lock reject overlapping
  hardware actions. After acceptance or an uncertain exchange, a local wait
  prevents a new render during the estimated duration. This is stricter than
  the firmware's ability to accept a replacement plan; it is application policy.
- A structured device error is a rejection; the connection stays open. An
  absent, malformed or unusable response leaves execution uncertain, closes
  the link and does not trigger retry. The command may already have reached
  the board. Connection failures also close the failed link.
- The reference firmware acknowledges acceptance before its timed execution
  ends. Status polling reads cached server state, not device telemetry. The
  local countdown begins after the response and cannot certify completion.
  Unplugging is detected at the next serial exchange, not by status polling.
- Disconnect releases the serial port; there is no protocol Stop command.
  An accepted command may continue. The estimated wait survives Disconnect
  within the server session; restarting the server loses this tracking.
- The HTTP server binds only to loopback and checks Host/Origin for requests.
  Preview and status do not issue render commands. Port listing only enumerates;
  opening a port requires Connect, and rendering requires Send to device.

## Evidence and remaining validation limits

**Historical software results:** the earlier implementation report recorded
1,890 passing Python tests, including 119 targeted tests, and successful
Python/JavaScript interoperability checks. Earlier browser checks used clearly
labelled software doubles for connection, both policies, incompatible duration,
invalid duration, Core import, disconnect, identity failure, rejection and
timeout. These results were not rerun as a full suite for this documentation
audit. The [application guide](../apps/local_demo/README.md) retains the original
environment, commands and simulated-test context.

**Physical confirmation supplied by the user:** Semantic at 5 seconds and
Perceptual at 5 seconds produced LED behavior matching the expected plans; a
31-second request was correctly refused against the advertised 30-second
maximum. These are attributed user observations, not new agent-run tests.
The refusal does not establish that a 31-second render reached the firmware:
the app also enforces the received limit before sending. No electrical
measurement, serial trace or physical screenshot is claimed.

The milestone validates LED control for the confirmed cases, not odor
reproduction. Acceptance is distinct from observed execution; estimated time
is distinct from completion telemetry; Disconnect is distinct from hardware
stop. Those protocol and validation limits remain open beyond this milestone.

## Historical functional discrepancy

**At audit commit `fd2dd59000c8bde7ef3ba2ac3380b6ea2341a009`, import-size
enforcement differed between the browser and server.** The browser rejected a
file larger than 1 MiB. The HTTP handler limited the entire JSON body to 2 MiB
but did not independently enforce a 1 MiB source-file limit. A direct local
`/api/preview` request could therefore bypass the browser limit while remaining
within the server limit. The README described both boundaries, and the issue
was left open for an implementation fix; no code changed in the documentation
audit. The later resolution is recorded below without replacing this evidence.

Reproduction during this audit used the bundled fixture plus a synthetic
top-level extension, entirely in memory. The source was **1,052,643 bytes** and
the HTTP body **1,053,233 bytes**; an isolated loopback server returned **200**.
Serial availability was disabled and serial factory/port enumeration were
replaced with functions that fail if called. No physical port was opened and
the normal application server was not used.

## Checks for this documentation intervention

The review covers repository instructions, branch, clean starting state,
remotes, the outgoing implementation commit and refreshed remote references.
The initial fetch showed `main` one commit ahead of `origin/main`
(`f9ecd0cf4dee8f79cf115f9f3c54a2bca1eea8ff`), with no incoming commits.

Checks performed for this intervention:

- All **65 local Markdown/HTML links**, including **11 anchors**, in the six
  added or modified documents resolved successfully.
- `python -m apps.local_demo --help`,
  `python hardware/esp32/osmell_multisource_demo.py --help` and
  `python hardware/esp32/esp32_physical_render.py --help` completed successfully
  using the existing virtual environment, without opening a physical port.
- Documented launch paths, the repository-root requirement and the optional
  `serial` extra were checked against entry points and `pyproject.toml`.
- The documentation diffs and Git whitespace checks passed review; the change
  contains no application, SDK, firmware, logo or scientific-data edit.
- The isolated HTTP reproduction above confirmed the import-size discrepancy.

That reproduction is the only new application-behavior probe. No new physical
test, complete Python suite or interoperability run is claimed. The unchanged
CI workflow remains configured to run on push; local documentation checks do
not establish its eventual result.

Publication is a separate Git operation: inspect every outgoing commit, push
normally to the existing remote branch and compare the expected commit with
the remote branch reference. The final publication report records that result;
this document does not treat a local commit as proof of publication.

## Import-size fix and verification

The subsequent fix on 17 September 2026 starts from the clean, published audit
commit `fd2dd59000c8bde7ef3ba2ac3380b6ea2341a009`. It resolves the discrepancy
with application-only byte limits; the existing graph loader, scientific data,
calculations, SDK, firmware, English interface and official logos are preserved.
The project remains an **experimental pre-alpha**.

The inclusive import limit is **1,048,576 UTF-8 bytes**, enforced independently
by the browser's File byte size and the server's encoding of the received
`text`. The server does not trust size metadata, compact the source or parse
the graph before checking. The browser preserves the UTF-8 BOM during decoding
and transport. The server counts its **three bytes** before ignoring one leading
BOM for parsing; embedded BOM characters are preserved as data.

The independent inclusive HTTP-body limit is **6,356,992 bytes**, checked before
body reading. Its budget is **6 × 1,048,576 + 65,536**: JSON can escape each ASCII
source character as six bytes (`\uXXXX`), with an additional 64 KiB for the
request fields. Unicode escaping never requires a larger ratio per original
UTF-8 byte. Tests include valid 1 MiB graphs transported in bodies larger than
the former 2 MiB limit, including fully escaped ASCII source text. Arbitrarily
large metadata or envelope whitespace is not exempt from the HTTP-body cap.

Oversized imported text and oversized HTTP bodies both return **413**, with
distinct English errors. An oversized file in a tracked request revokes the
previous preview before rejection; a pending older calculation cannot publish
after it. An oversized envelope is rejected without parsing or publishing it.
The UI invalidates its prior preview before reading any newly selected file.
Valid subsequent imports work normally, including at the exact file limit.

RFC-0008's graph format and RFC-0012/0013's mapper, rendering and device
boundaries remain unchanged. RFC-0012 and RFC-0013 only link the resolved
application issue in their implementation evidence; both remain Draft.
No new architecture or portable contract is introduced, so no new RFC is needed.

Verification uses the new
[HTTP regression tests](../tests/test_local_demo_import_limits.py) and
[JavaScript import tests](../tests/local_demo_import.test.cjs), alongside existing
application and mapper tests. Servers are isolated, serial factory/enumeration
are disabled with failing doubles, and the JavaScript handler runs with DOM
doubles. These are software tests, not new browser-on-device or physical tests.
The CI interoperability job now also runs the JavaScript import tests.

Results actually obtained locally for the fix on Windows, Python **3.13.14**
and Node.js **24.19.0**:

- **138 targeted Python tests passed**, including 19 new HTTP import tests.
- **1,909 Python tests passed** in the full regression suite.
- **8 JavaScript import tests passed**, plus syntax checks for both app scripts.
- **16 remaining CI interoperability commands passed**, including vector
  regeneration with no changes and Python/JavaScript round trips. The CI's
  Python conformance selections were already covered by the full Python run.
- Local Markdown links and anchors, the app's English launch help, exact change
  scope and Git whitespace checks passed review.

No new physical measurements or ESP32 commands accompanied this fix. The earlier
1,890/119-test report and user-confirmed LED checks above remain historical.
The GitHub run for the eventual commit is checked after publication and reported
separately; local success is not presented as proof of remote CI completion.
