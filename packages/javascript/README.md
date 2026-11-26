# OpenSmell JavaScript graph reader SDK

Experimental, limited graph inspection and original-byte exchange for Node.js 22+
(CommonJS/ESM) or a browser providing Web Crypto and TextDecoder.
No dependencies, Python, UI, network upload or device commands.

This package is private and intended for **local packing and installation**.
It has not been published to npm. From the OpenSmell checkout:

```sh
npm pack ./packages/javascript --ignore-scripts
```

Install the resulting opensmell-graph-reader-0.1.0-experimental.0.tgz into your
own project with `npm install --offline --ignore-scripts --no-audit --no-fund /absolute/path/to/the.tgz`.
The package contains the reader, CJS/ESM entries, type declarations, CLI, README
and Apache-2.0 license; it does not depend on the checkout.

## API

```js
// ESM; CommonJS: const {inspectBytes} = require("@opensmell/graph-reader");
import {inspectBytes} from "@opensmell/graph-reader";
import {readFile, writeFile} from "node:fs/promises";

const bytes = await readFile("sample.osmell");
const result = await inspectBytes(bytes, "sample.osmell");
console.log(result.report.status, result.report.file.sha256);
if (result.report.status !== "rejected")
  await writeFile("transfer.osmell", result.copyBytes(), {flag: "wx"});
```

Exports: `LIMIT` (1,048,576 bytes), `FORMAT` (experimental Generic
ResourceGraph identifier) and async `inspectBytes(Uint8Array, name?)`.
A Buffer is acceptable in Node. Returned reports include file identity,
diagnostics, interpreted resources/references and explicit checks/limits.
The report preserves its historical reader-specific version; it is not a
normative OpenSmell schema-validation certificate.

Statuses are `inspected`, `partial` and `rejected`.
Partial means opaque or limited content remains: it does not certify all
representations. `copyBytes()` returns a fresh copy of the original private
byte snapshot after inspected/partial results, with no JSON reserialization.
Rejected results cannot export bytes, even if the caller edits the report.
Modifying returned bytes never changes subsequent copies.

Files over LIMIT reject the Promise with an error carrying `code: "file_too_large"`.
Wrong input types reject with TypeError. Invalid UTF-8, malformed/ambiguous JSON,
invalid recognized resources and unresolved required references produce a
rejected report. Unknown types/versions/schemes remain opaque, with diagnostics.
The profile and numeric/Unicode limitations are disclosed in each report.
The original graph entry reads Generic ResourceGraph 0.1. Core requires the
explicit additional entry below. Neither reads batch bundles/arbitrary JSON or
performs editing, mapping or physical output.

## Installed CLI

```sh
opensmell-inspect-js sample.osmell --copy transfer.osmell
```

Prints a JSON report. Exit: 0 inspected; 3 partial (original-byte copy permitted);
1 rejected/oversized; 2 I/O or usage error. Existing outputs, including the input,
are refused. Rejected inputs create no copy. File reads are bounded to LIMIT+1.
No stdin, overwrite flag, graph mutation or implicit device action is provided.

The browser asset is `reader.cjs` (also exported as `@opensmell/graph-reader/browser`).
Serve it as a classic script to expose `globalThis.OpenSmellReader`, or use a
compatible bundler. Native browser module import of the CommonJS entry is not
promised. Browser code supplies bytes; there is no file/network API in the engine.

Source format, declared provenance, mapping, device acceptance, execution and
measured odor outcome are separate evidence. This repository-maintained limited
SDK slice does not demonstrate third-party adoption or physical compatibility.

## Explicit Core inspection (experimental)

The additional `inspectCoreBytes(Uint8Array, name?)` entry reads Core0.1, bounded
by the separately exported `CORE_LIMIT` (4,194,304 bytes including any UTF-8 BOM).
The original `inspectBytes`/`LIMIT` graph profile and CLI default are retained.
Both entries reject competing Core/graph envelope discriminators; no fallback or
format guessing occurs. Use the [complete Python/Node walkthrough](../../docs/javascript-core.md).

```js
import {inspectCoreBytes} from "@opensmell/graph-reader";
const result = await inspectCoreBytes(bytes, "selected-core.osmell");
if (result.report.status !== "rejected") {
  for (const representation of result.report.core.representations)
    console.log(representation.index, representation.type, representation.entries);
  // result.copyBytes() remains the exact input, not a reconstructed document.
}
```

```sh
opensmell-inspect-js --core selected-core.osmell --copy transfer-core.osmell
```

The report exposes odor ID, metadata, supplied provenance and ordered
representations with raw `scheme`, `data`, `provenance` display fields and complete
`representation_json` slices. Only the exact `perceptual` type plus provisional
`org.opensmell.perceptual.measurements`0.1 receives quantitative inspection.
Other type/scheme/version combinations stay opaque, including chemical/semantic
payloads. No normalization, unit conversion, identity inference or mapping occurs.

Measurement display fields distinguish absent, explicit null and supplied values.
Use `value.json`, never `Number(value.json)`, when exact precision matters.
All number tokens remain text. Range checks apply only to safe integral tokens
and usable explicit min/max scales; fractions, exponents, unsafe integers and
negative zero produce `numeric_limit` warnings without decimal interpretation.
Null/missing values or bounds produce `unavailable_measurement` warnings.
Unknown fields and representations remain in original bytes; returned views are
partial reports, not editable or round-trip JSON object models.

The envelope/metadata checks mirror the listed structural fields of Core0.1,
**not full Python schema/registry conformance**. In particular the reader does not
validate chemical/semantic schemes, extensions, scientific provenance or the
reserved observation-export consistency convention. Embedded source data is not
decoded or authenticated. Use the installed Python extraction/planning entry to
check that convention before downstream use. `inspected` means listed checks
only; `partial` marks opaque/numerically limited/unavailable content. Neither is
a certificate of source authenticity, scientific validity or device suitability.
The same exit codes, exclusive-copy behavior and rejection rules apply to Core.
