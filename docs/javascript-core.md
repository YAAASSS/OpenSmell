# Read Core with an installed JavaScript consumer (experimental)

A developer can now inspect Core0.1 directly from the locally packed
`@opensmell/graph-reader` package. No Python process, network or checkout import
runs inside the reader. The original graph API remains available; select Core
explicitly through `inspectCoreBytes` or `opensmell-inspect-js --core`.

## Try the normal installed entry

Pack the current revision from the checkout, then install that archive in a
separate project (Node22+ and npm required):

```sh
npm pack ./packages/javascript --ignore-scripts --pack-destination /absolute/existing/output-directory
# In your own project:
npm install --offline --ignore-scripts --no-audit --no-fund /absolute/existing/output-directory/opensmell-graph-reader-0.1.0-experimental.0.tgz
```

The package is private, locally packable and has not been published to npm.
With the Python SDK from the same revision installed, you can create a selected
Core file using [the observation export](observation-core.md), or use the bundled
`examples/core_perceptual_only.osmell`. Supply your own absolute paths outside
checkout. In the project where you installed the Node package:

```sh
npx --no-install opensmell-inspect-js --core /path/to/core_perceptual_only.osmell --copy transferred.osmell
opensmell plan-core transferred.osmell --representation-index 0 \
  --profile /path/to/offline_core_perceptual_profile.json --duration 0.1 --output selected-plan.json
```

The supplied synthetic fixture returns a **partial report (exit3)** with three
ordered representations: two quantitative selections and one opaque future
payload. The first selection reports flower `2.5` rating, grass `0` with null unit,
and wood `100` with absent unit. Unknown large-integer tokens remain intact.
The explicit Python policy produces illustrative intensities .25/.5/1; selecting
index1 gives .75/.5/1. These are passive demonstration plans, not odor measurements.
Shell scripts must handle expected exit3 before continuing; it permits the copy.

CJS/ESM consumer:

```js
import {readFile, writeFile} from "node:fs/promises";
import {inspectCoreBytes} from "@opensmell/graph-reader";
// CJS: const {inspectCoreBytes} = require("@opensmell/graph-reader");
const result = await inspectCoreBytes(await readFile("selected-core.osmell"));
if (result.report.status === "rejected") throw new Error("Inspection refused");
for (const r of result.report.core.representations) {
  console.log(r.index, r.type, r.status);
  for (const m of r.entries ?? [])
    console.log(m.property, m.value.presence, m.value.json, m.unit.presence);
}
await writeFile("copied-core.osmell", result.copyBytes(), {flag: "wx"});
```

Reports have source byte length/SHA256, raw JSON slices for metadata/provenance/
representations and explicit checks/limits. Number displays preserve lexical
spelling as text, including decimals, exponents and integers beyond JS precision.
Safe integral ranges alone are checked; no decimal arithmetic, normalization,
unit conversion, imputation or automatic selection is performed. The report does
not expose a parsed document to reserialize. Original-byte copying preserves BOM,
whitespace, extensions and representations; fresh copies cannot change later ones.

## Bounds and interpretation

Core input is inclusively bounded at4MiB, including BOM; graph input stays1MiB.
Fatal UTF8, valid JSON, unique object keys, depth64, Core0.1 envelope, declared
metadata fields and representation envelopes are checked. Competing `format`
(Core entry) or `opensmell` (graph entry) discriminators refuse ambiguous files.
Malformed known quantitative fields refuse. Unknown type/scheme/version payloads
stay opaque. Opaque/numerically limited/unavailable content yields partial status.
CLI exit0 inspected,3 partial,1 rejected/oversized,2 usage/IO/collision. Reads stop
at limit+1; copies exclusively create new files and never overwrite an input.

This is limited independent inspection, **not full Core/scheme validation**.
The provisional perceptual scheme remains experimental; RFC0005/0015 stay Draft.
Chemical/semantic payloads, source authenticity, reserved export-marker consistency
and scientific interpretations are not validated. Embedded Base64 source is not
decoded. A report can inspect an inconsistent export: Python
`extract-observation-source`/`plan-core` must verify that convention. Byte hashes
identify supplied files; they do not authenticate them. There is no device access,
command, acceptance, observed physical execution or olfactory result in this path.

## Reproduce the installed cross-language proof

```sh
python -m build --wheel
python -m tools.verify_installed_js_core dist/opensmell-0.1.0-py3-none-any.whl --output /absolute/new/proof-directory
```

The verifier uses a fresh Python venv and actual npm pack/offline install outside
checkout. It imports one declared synthetic CSV observation, explicitly exports
its quantitative result, deletes the source paths, inspects/copies with installed
Node, then recovers the exact embedded graph and replans in installed Python.
Separate CJS/ESM consumers check absent/null/zero units/values, opaque schemes and
unsafe/exponent tokens without rounding. Ambiguous/invalid/duplicate/oversized
inputs and copy collisions refuse. Evidence includes original/transfer lexical
files, Core/graph recovery, inspection report, passive plan and package hash.
Python dependencies are inherited for this proof; it is not a clean dependency
closure, third-party adoption trial or physical compatibility claim.
