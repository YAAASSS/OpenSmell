# Installed selected perceptual observation import

`opensmell import-keller` and
`opensmell.experimental.perceptual_import.import_keller_csv(raw, row=..., source=...)`
import one explicitly selected **prepared Keller/Vosshall-shaped CSV** record into
an experimental Generic ResourceGraph 0.1. This is a development-main capability,
not a new published package or a general spreadsheet importer. No network,
chemical lookup, participant join, aggregation or device connection occurs.

## Prepare the supported input

For an authorized local scientific source, export the intended worksheet/table
to UTF-8 CSV with one header record and document the extraction in the source
declaration. The existing repository research tool
`tools/analyze_keller_vosshall_resource_graph.py` reads its local workbook's
`data` sheet with `header=2`; that tool's external workbook is **not bundled**.
The installed importer neither reads Excel nor guesses worksheets/header rows.
Inspect the actual source/version before preparing it. Do not replace missing
ratings with zero, average participants or infer chemical identity during export.

Required exact, unique, unpadded headers:

| Column | Prepared interpretation |
| --- | --- |
| `CID` | Nonblank positive decimal integer, declared PubChem CID; not verified |
| `Odor` | Nonblank source stimulus name, retained without chemical validation |
| `Odor dilution` | Nonblank opaque presentation condition, e.g. `1/1,000`; no concentration/unit conversion |
| `Subject # (this study)` | Nonblank source-local subject token; never a global person identifier |

Include at least one known rating column. Supported global columns are
`HOW STRONG IS THE SMELL?` → `intensity`, `HOW PLEASANT IS THE SMELL?` →
`pleasantness`, and `HOW FAMILIAR IS THE SMELL?` → `familiarity`.
Descriptor columns (lowercased as measurement properties) are `EDIBLE`, `BAKERY`,
`SWEET`, `FRUIT`, `FISH`, `GARLIC`, `SPICES`, `COLD`, `SOUR`, `BURNT`, `ACID`,
`WARM`, `MUSKY`, `SWEATY`, `AMMONIA/URINOUS`, `DECAYED`, `WOOD`, `GRASS`,
`FLOWER`, `CHEMICAL`. A subset is allowed; omitted columns remain unmeasured.

Numeric cells must be finite values in **0..100**. Blank/whitespace cells are
omitted, not zero. Other missing-value tokens (`NA`, `NaN`, etc.) are refused;
the preparer must explicitly document any transformation into blank cells.
Each measurement carries `scale: {min: 0, max: 100}` and `unit: "rating"`:
a dimensionless subjective rating, never ppm, concentration or physical intensity.
Other scales/units are refused rather than silently rescaled.

Optional `CAN OR CAN'T SMELL` and `KNOW OR DON'T KNOW THE SMELL` cells are
retained verbatim in a separate categorical Result's `source_fields`.
Its `detection` remains `unknown`; arbitrary free text is not classified.
All other columns remain uninterpreted in `raw_record`. An all-blank rating row
can import successfully, but cannot produce a perceptual plan with no commands.

Supply a JSON declaration with nonempty `name`, `url`, `license`, `preparation`,
`kind` (`dataset` or `synthetic`), and
`rating_scale: {"min": 0, "max": 100, "unit": "rating"}`. Preserve the actual
source version, attribution, authorization/license context and preparation steps
in additional fields. These are caller declarations, not authentication or a
redistribution license supplied by OpenSmell. Unknown declaration fields survive.

## Try the installed entry

Install the current checkout with `python -m pip install .`, then copy the three
example files to any working directory (the portable kit includes them too):

```sh
opensmell import-keller synthetic_keller.csv --row 1 \
  --source synthetic_keller_source.json --output observation.osmell
opensmell validate observation.osmell
opensmell inspect observation.osmell --json
python -c 'import json; g=json.load(open("observation.osmell")); print(g["org.opensmell.experimental.perceptual-csv-import"]["primary_resource_id"])'
opensmell plan observation.osmell --profile offline_perceptual_profile.json \
  --resource-id OBSERVATION_ID_FROM_ABOVE --duration 5 > plan.json
```

The reference is **synthetic**, not a Keller/Vosshall observation. Row 1 produces
CH0=0.26, CH1=0, CH2=0.89; row 2 produces CH0=0.8, CH1=0.2 with a different
dilution; row 3 imports but has no numerical plan; row 4 refuses rating 101.
Different source/CSV/selection identities produce different resource IDs, even
when the declared CID/subject match. This deliberately avoids cross-record joins.
The graph contains a declared molecule, stimulus, source-local target and
observation; categorical and perceptual Result schemes remain separate.

The namespaced import context records the primary observation ID, source
declaration, its canonical JSON hash, exact CSV hash/byte count, logical row,
ordered headers, every selected raw cell, omitted rating columns and limitations.
Full CSV bytes and original declaration formatting are **not embedded**. Their
hashes are identities, not signatures or recovery snapshots. Share retained
participant/source fields only as your input permissions allow.

Stdin `-` works. `--row` is one-based excluding the header, counting CSV records
including quoted multiline cells, not spreadsheet line numbers. Only the selected
row is semantically checked. CSV syntax before it must parse; later records are
not validated. CSV limit 8 MiB; declaration limit 1 MiB; individual cells use the
Python CSV parser's default field-size limit. Outputs exclusively create new files.
Exit codes: 0 imported, 1 invalid/unsupported input, 2 usage or I/O collision/error.

## Follow the source boundary through software

Use [encode-frame](protocol-frame-export.md) on `plan.json`, then
[replay-frame](native-frame-replay.md) with an explicitly selected trusted native
harness and a new transcript. Rating normalization and channel bindings are an
illustrative policy; no odor reproduction follows from them.

The repository proof uses a fresh wheel and locally packed JavaScript reader
outside the checkout, copies the graph through the installed reader without byte
changes, produces two distinct plans, checks empty/invalid/overwrite refusals,
then replays the exact row-1 frame against the actual compiled sketch after
deleting temporary preparation files. Native fake PWM is `[66, 0, 227]`, the
31-second negative control preserves outputs and advancing the fake clock turns
them off. These are software observations; physical execution remains unobserved.
The JavaScript reader correctly reports **partial** inspection: categorical
results stay opaque and no Annotation branch is supplied. Three known references
resolve and original bytes remain intact; no full scheme validation is inferred.

```sh
python -m build --wheel
python -m tools.verify_installed_perceptual dist/opensmell-0.1.0-py3-none-any.whl \
  --host /tmp/opensmell-firmware-host
```

Exit criterion for this slice: installed selected import, preserved source/stimulus/
rating context, unchanged JavaScript transfer, distinct perceptual plans and native
frame proof. This does **not** validate an external corpus or demonstrate independent
adoption. Defer more importer dialects/batch flags until a concrete source trial
requires them. Manual ESP32/odor observations remain separate and NOT RUN.
