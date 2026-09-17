![Official OpenSmell logo](../../docs/images/OpenSmell_Official_Logo_Full.png)

# JavaScript Graph Reader

An **experimental pre-alpha** offline reader, developed within OpenSmell. It
independently inspects a limited experimental Generic ResourceGraph profile in
JavaScript, then downloads the **original bytes** for transfer to
[Python Local Explorer](../local_demo/README.md). This is not a third-party
integration, certification, full SDK or generic JSON editor.

## Launch

From the repository root, with Node.js 22 or later:

```powershell
node apps/graph_viewer_js/server.cjs
```

Open `http://127.0.0.1:8766`. Use `--port 8767` for another port; Ctrl+C stops
the server. It binds only to loopback and serves a fixed list of local assets,
including the two unchanged official logos. There is no package installation,
framework, external font, CDN or new runtime dependency.

The server does **not** receive or analyze imported files. File reading, UTF-8
decoding, JSON inspection and SHA-256 calculation happen in the browser.
The browser's content policy blocks network connections; this application has
no `/api/preview`, upload, Python subprocess, SDK or device endpoint.

1. Click **Open graph file** and select one of the two real examples:
   [beta-pinene](../../examples/multisource_beta_pinene.osmell) or
   [diphenyl ether](../../examples/multisource_diphenyl_ether.osmell).
2. Inspect the file name, byte count, SHA-256, declared identity, separate source
   branches, diagnostics and structural references. Reference links reveal the
   matching resource under **Resources and declared provenance**.
3. Use **Download intact copy** to save `NAME-transfer.osmell` and
   **Download inspection report** for a separate `NAME-inspection.json`.
4. In Local Explorer, use **Import graph** to open the downloaded `.osmell`,
   select a 5-second duration and review both plans.

The [exchange guide](../../docs/js-python-exchange.md) supplies exact expectations,
hash checks, actual screenshots, a 40-second filming outline and a separate
manual LED procedure. Reading or downloading never sends a hardware command.

## Explicit inspection profile

The envelope must be `org.opensmell.experimental.generic-resource-graph`,
version `0.1`, with a `resources` array. Every resource must have nonempty string
`id` and `type`; optional `type_version` must also be a nonempty string. IDs are
case-sensitive opaque strings, not necessarily UUIDs. Duplicate IDs are rejected.

| Recognized wire type | Required wire version | Fields interpreted by this reader |
| --- | --- | --- |
| `org.opensmell.molecule` | `type_version: "0.1"` | Nonempty SMILES or external identifiers; identifier scheme/value strings; declared label/provenance |
| `org.opensmell.annotation` | `type_version: "0.1"` | Subject reference, scheme envelope and supported categorical entries |
| `stimulus` | `type_version` absent | Optional source reference, external identifiers; conditions retained in the report as original JSON text |
| `observation_target` | `type_version` absent | External identifier scheme/value strings |
| `observation` | `type_version` absent | Stimulus reference, optional target, result envelopes and supported quantitative entries |

A future version or unknown type is **opaque**, even when its name resembles a
recognized type. Its generic envelope is checked; its payload and references
are not interpreted. In particular, explicit `type_version: "0.1"` on a legacy
`stimulus` is not the same dispatch key as an absent version. This follows the
existing Python registry and portable JavaScript experiments.

Only these known structural paths create edges: `Annotation.subject`,
`Stimulus.source`, `Observation.stimulus`, `Observation.target`. Required
references must be objects with nonempty `resource_id`; optional absent/null
references are not invented. Unresolved references are errors. The reader's
observation path requires recognized stimulus/target endpoints of the appropriate
kind; a reference to an opaque endpoint resolves with an interpretation warning.
Reference-looking fields in arbitrary extensions never create edges.

Supported scheme payloads are limited to:

- `org.opensmell.semantic.annotations` version `0.1`: an `annotations` array,
  nonempty category values, explicit `present` / `absent` / `unknown` states,
  and optional nonempty/null language. No default state or translation is added.
- `org.opensmell.perceptual.measurements` version `0.1`: a `measurements` array
  of named properties, numeric/null/missing values, optional object/null scales,
  numeric/null/missing `min` and `max`, and nonempty/null/missing units.
  Missing or null data is displayed explicitly and warned about; it is not a
  declaration of full scheme conformance. When value and bounds are exact safe
  integers, the reader checks `min < max` and inclusion in the scale. It never
  normalizes values or generates RenderingPlans.

Unknown scheme envelopes are checked for nonempty ID/version and object data;
their scientific payload remains opaque. The UI and report enumerate performed
checks and exclusions, without an overall “everything is valid” badge.

This is **not** complete validation of every recognized resource contract:
stimulus conditions, arbitrary context, provenance schema, duplicate descriptor
semantics, chemical identity, SMILES chemistry and unknown extension meanings
are not validated. Provenance/context excerpts are original JSON text from the
file, not independently verified claims. Connecting branches does not establish
scientific equivalence. Local Explorer has its own narrower import/mapping
requirements; successful inspection alone does not guarantee its acceptance.

## Bytes, numbers and rejection behavior

- Maximum file size is **1,048,576 bytes inclusive**, including a UTF-8 BOM.
  The UI checks the file before reading it; the independent byte reader also
  checks the actual byte array. UTF-8 decoding is fatal, without replacement.
- A leading BOM is removed only from the parsing copy. Original bytes,
  whitespace, line endings, Unicode, unknown fields and versions remain intact.
- JSON syntax and duplicate object keys are checked. Duplicate keys are rejected
  because ordinary JavaScript parsing would discard their ambiguity. A nesting
  limit of **64 levels** is an application reading limit, not an OpenSmell contract.
- A token scan retains original numeric spellings for display/report fields.
  Safe integers, including forms such as `95.0`, support the limited range check.
  Non-integral decimals, exponent forms, unsafe integers, extreme values and
  negative zero receive a `numeric_limit` diagnostic; they are shown as their
  original JSON tokens and are not used for exact arithmetic or range validation.
  Escaped lone Unicode surrogates are diagnosed and displayed escaped.
- The **copy is never built with `JSON.stringify`** or reconstructed from
  recognized resources. A private snapshot of the imported bytes supplies each
  download. The inspection report is separate application-specific JSON; it is
  not a standard, schema certificate or replacement for the original graph.
- Structural/content errors reject the inspection and disable the intact-copy
  button. The separate diagnostic report remains available after a bounded file
  was read. Oversize/read failures have no active report or transfer. A new
  import immediately clears the previous result; late reads cannot restore it.
  A subsequent valid file works normally.

Reports have `inspected`, `partial` or `rejected` status. `inspected` means only
that the enumerated checks completed without warnings/errors; opaque extensions
still have no validated meaning. `partial` permits byte transfer while exposing
specific limits. Rejection does not change the user's original file.

## Offline command-line reproduction

The companion uses the **same JavaScript reader**, without Python, and writes
only to new output files:

```powershell
node apps/graph_viewer_js/inspect.cjs examples/multisource_diphenyl_ether.osmell diphenyl-transfer.osmell diphenyl-inspection.json
Get-FileHash examples/multisource_diphenyl_ether.osmell -Algorithm SHA256
Get-FileHash diphenyl-transfer.osmell -Algorithm SHA256
```

Input, copy and report must be distinct paths; existing outputs are not
overwritten. A rejected inspection writes its diagnostic report but no copy.
This CLI is useful for reproducibility, but is not evidence that a browser
download was exercised; the exchange guide records that separately.

## Tests and relationship to earlier verifiers

```powershell
node --test tests/graph_viewer_js.test.cjs
python -m pytest tests/test_graph_viewer_js_exchange.py -q
```

The first command runs **33 tests**: independent expected identities/states/all
ratings for both real fixtures, exact original-byte transfer, references,
duplicate IDs/keys, opaque resources/versions/schemes, unknown fields, numeric
limits, Unicode, BOM and exact byte boundaries, invalid UTF-8/Core documents,
DOM-double recovery/stale-read protection, safe text rendering and static-server
boundaries. Its DOM doubles are not a real browser.

The **four Python exchange cases** run Node.js independently, compare its
interpretation with the Python loader, verify original/copy hashes and bytes,
then import each real example with and without a BOM through isolated Local
Explorer HTTP servers. Both 5-second plans and the selected preview ticket are
checked against independent expectations. Serial enumeration/access are disabled.
Only the published fixtures are needed, not full datasets or network access.

The new tests supplement, rather than replace,
`tools/verify_multisource_beta_pinene_interop.js`, the diphenyl ether JSON round
trip and all existing portable conformance verifiers. The older round trips
exercise reserialization for their fixtures; this reader additionally exercises
visible independent interpretation and original-byte transfer over a broader
numeric/extension boundary. Their contract rules informed the reader; the old
fixture-specific executables were not extracted or changed.

Both new commands run in the existing [CI interoperability job](../../.github/workflows/tests.yml),
which supplies Node.js 22. The full Python suite also discovers the four exchange
cases (skipped only if Node is unavailable outside that required job).

![Official OpenSmell symbol](../../docs/images/OpenSmell_Official_Logo_Small.png)
