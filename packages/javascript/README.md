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
This slice reads Generic ResourceGraph 0.1, not Core files, batch bundles,
arbitrary JSON, graph editing, mapping or physical output.

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
