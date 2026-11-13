# Installed JavaScript reader and Python exchange

The private local package [`@opensmell/graph-reader`](../packages/javascript/README.md)
reuses the independent reader from the browser demo. It provides CJS/ESM imports,
type declarations and an installed CLI without Python, an app or runtime dependencies.
Node.js 22+ is required. Nothing has been published to npm.

## Pack once, consume outside the checkout

From the repository root (POSIX shell example):

```sh
npm pack ./packages/javascript --ignore-scripts
# Record the absolute path printed for the tarball and for the example below.
# Choose a new empty directory for your consumer, then cd into it.
npm init -y
npm install --offline --ignore-scripts --no-audit --no-fund /absolute/path/to/opensmell-graph-reader-0.1.0-experimental.0.tgz
```

Copy `examples/multisource_diphenyl_ether.osmell` and
`examples/offline_semantic_profile.json` into that directory. With its
`node_modules/.bin` on PATH (or call that explicit path):

```sh
node_modules/.bin/opensmell-inspect-js multisource_diphenyl_ether.osmell --copy transfer.osmell
```

The JSON report is `inspected` for this fixture and includes four resolved known
references plus original file hash/size. The new copy is byte-identical.
`partial` (exit 3) still permits byte transfer but discloses uninterpreted or
limited content; `rejected` (exit 1) creates no copy. I/O/usage errors are exit 2.
Existing outputs and the input path are refused. The file limit is 1 MiB including BOM.

For an API consumer, save `inspect.mjs` beside the installed package:

```js
import fs from "node:fs/promises";
import {inspectBytes} from "@opensmell/graph-reader";
const result = await inspectBytes(await fs.readFile("multisource_diphenyl_ether.osmell"));
console.log(result.report.status, result.report.references);
if (result.report.status !== "rejected")
  await fs.writeFile("api-transfer.osmell", result.copyBytes(), {flag: "wx"});
```

Run `node inspect.mjs`. CommonJS consumers use
`const {inspectBytes} = require("@opensmell/graph-reader")`.
See the package README for full API, error and browser entry details.

## Continue with the installed Python kit

Install the source Python project into your normal virtual environment first
(`python -m pip install /absolute/path/to/OpenSmell`). Back in the consumer:

```sh
opensmell validate transfer.osmell --json
opensmell inspect transfer.osmell --json
opensmell plan transfer.osmell --profile offline_semantic_profile.json --resource-id e6ad8ce3-dc6e-5d94-9287-57665d48fc0b --duration 5
```

Expected plan: channel 0 at 0.25 and channel 1 at 0.6, duration 5 seconds,
`execution: "not_attempted"`. The source/profile hashes identify supplied bytes;
they do not authenticate provenance. The [installed lifecycle SDK](lifecycle-sdk.md)
can then exercise completion, Stop and lost-link uncertainty on a software endpoint.
No physical action follows inspection or planning.

## Reproduce the integration proof

With the normal Python development dependencies and Node/npm installed, from a
checkout, choose a **new** exchange output directory:

```sh
node --test tests/graph_viewer_js.test.cjs tests/js_sdk.test.cjs
node tools/verify_js_sdk.cjs /tmp/opensmell-js-exchange
python -m build --wheel
python -m tools.verify_installed_cli dist/opensmell-0.1.0-py3-none-any.whl --js-exchange-directory /tmp/opensmell-js-exchange
```

The first verifier packs an allowlisted archive, installs it offline into a new
consumer outside the checkout, imports CJS and ESM, runs the installed CLI and
checks byte identity, partial/rejected content, size and no-overwrite refusals.
It retains only the two example graph copies. The wheel verifier installs Python
into a separate fresh environment, verifies both exchanged files against their
source fixtures, then consumes them through validation/inspection, both offline
mapping profiles and Python/Node software lifecycle paths. The browser demo route
is also checked against the same engine. CI repeats this on Node 22.

This reader does not implement Core, CSV batch bundles, graph editing or a complete
normative validator. Unknown representations, numeric tokens and missing/null values
keep the existing explicit limitations. The package and Python endpoints are
maintained in this repository: this proves reuse/interoperability, not independent
third-party adoption, chemical equivalence, physical compatibility or an odor result.
