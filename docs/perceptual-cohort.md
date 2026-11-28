# Import an explicit quantitative cohort (experimental)

`import-keller-cohort` turns a caller-selected set of prepared Keller/Vosshall-shaped
CSV records into one ordinary Generic ResourceGraph0.1. It reuses the installed
[single-observation importer](perceptual-csv-import.md), its source declaration,
validation and occurrence IDs. No participant/CID join, averaging, normalization,
unit conversion or device action occurs. Existing single-row behavior is unchanged.

With this revision installed, try the declared synthetic fixture:

```sh
opensmell import-keller-cohort examples/synthetic_keller.csv \
  --source examples/synthetic_keller_source.json --rows 2 1 3 4 99 --output cohort.osmell
opensmell inspect cohort.osmell --json
opensmell observation-table cohort.osmell --output table.json
opensmell extract-keller-source cohort.osmell --output original.csv
```

Use your own paths outside checkout. Record selection is mandatory, one-based
logical CSV data records (quoted multiline cells count as one), unique and kept
in caller order. The example retains three accepted observations and two explicit
refusals: row3 is accepted without numeric results, row4 refuses rating101, and
row99 does not exist. Empty ratings remain absent; zero remains measured zero.
Rows2 and1 retain distinct dilution occurrences even with matching subject/CID.

The root `org.opensmell.experimental.perceptual-csv-cohort` extension includes
`requested_records`, ordered `results`, accepted/refused `counts`, and overall
`status` (`complete`, `partial`, `refused`). Each accepted result records
`observation_id` and the existing complete single-row `import_context`, including
raw cells, omitted ratings and source declarations. Refusals carry the selected
record and a human-readable error; errors are not a stable machine-code taxonomy.
No accepted observation is silently dropped or assigned zero for missing data.
An all-refused selection still produces an empty graph and explicit refused manifest.

**CLI exit0 means a cohort graph was produced, including partial/all-refused
cohorts. Inspect the manifest before using accepted records.** Exit1 means invalid
selection/global source, syntax, header or size; exit2 means IO/output collision.
Global refusal creates no output; valid output exclusively creates a new file.
Stdin `-` and graph/CSV stdout work. No overwrite or automatic fallback is provided.
The whole CSV is syntax-checked; semantically invalid unselected rows are passive.
This differs from single-row import's selected-prefix syntax check.

## Continue with analysis, Core and Node

The graph works with `observation-table`, explicit graph plans and selected
`export-observation-core`. Read each accepted `results[].observation_id` and
inspect its results. The current importer places categorical context before
quantitative results (normally result index1). Never substitute another result
when an explicitly selected unmeasured result refuses.

Follow [Core export](observation-core.md) and [installed Node inspection](javascript-core.md)
with explicit caller odor ID/profile. For these synthetic rows, a caller profile
binding flower/grass/wood produces .26/0/.89 for row1; row2 requires a separate
flower/grass profile and produces .8/.2. Wood is absent in row2, not zero.
The accepted unmeasured row has no numeric plan. The table retains its observation
with measurement_count0. Categories remain separate from numerical measurements.

For a larger prepared CSV, first use [bounded streaming selection](csv-selection.md)
to create a small explicit selection and source-row provenance. The large input
is fingerprinted, not embedded or recovered by the cohort.

## Source recovery, scope and bounds

The manifest retains the **whole exact CSV**, Base64/SHA256/byte count, including
unselected and refused records. This is not a redacted selected-data export;
prepare an appropriate source before sharing. Unknown source fields and original
CSV byte spelling/BOM/CRLF are preserved. Source/license/identity remain caller
declarations, not authentication or authorization supplied by OpenSmell.

`extract-keller-source` recomputes the cohort from retained CSV/source/selection,
compares all outcomes, resources and metadata, then recovers exact original bytes.
Contradictory changes refuse; re-import after edits. Outer JSON whitespace can
change. This unsigned convention is consistency checking, not source authenticity.
**Ordinary graph/table/plan/Node consumers do not recompute this cohort convention**;
they interpret the supplied graph. Use extraction to check consistency explicitly.

Bounds: CSV512KiB, declaration1MiB, 1..100 selected records, serialized graph2MiB.
Serialized overflow refuses without truncation. Prepare a smaller explicit source
or cohort if necessary. Parser field/syntax limits also apply. Graph consumers
have independent limits: the JS graph profile is1MiB, Core export input2MiB and
Core output4MiB. A small cohort does not prove arbitrary dataset-scale operation.
The first slice keeps this established dialect and existing contracts experimental;
there is no new stable graph/schema, physical outcome or third-party adoption claim.

SDK:

```python
from opensmell.experimental.perceptual_cohort import import_keller_cohort, extract_keller_source
raw_graph = import_keller_cohort(csv_bytes, rows=[2, 1, 3, 4], source=source_declaration)
assert extract_keller_source(raw_graph) == csv_bytes
```

Reproduce the actual installed Python/npm CJS/ESM/CLI exchange, exact CSV recovery,
analysis, two distinct Core plans, unmeasured refusal and tamper/collision guards:

```sh
python -m build --wheel
python -m tools.verify_installed_keller_cohort dist/opensmell-0.1.0-py3-none-any.whl --output /absolute/new/proof-directory
```

Fresh installations run outside checkout. npm installs the real locally packed
package offline, with scripts disabled; Python dependencies are inherited, not a
new clean dependency closure. All input is declared synthetic, not observed results
from an experiment performed by this software. No endpoint is launched.

## Pinned publisher-source cohort trial

The same path also runs on the previously documented pinned Keller/Vosshall
workbook, using [the existing explicit preparation](perceptual-csv-import.md#try-the-installed-entry).
Supply your locally authorized copy with SHA256
`efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62`:

```sh
python -m tools.verify_installed_public_cohort dist/opensmell-0.1.0-py3-none-any.whl --workbook /path/to/12868_2016_287_MOESM1_ESM.xlsx --output /absolute/new/public-proof
```

Observed prepared CSV hash:
`57e9cd4b41bc69d8813726ae80442b177ae52b4e6100ac56872c546db94f991c`.
All three selected records import, in order, with measurement counts8/0/3. The
first has flower26/grass38/wood89; the second is unmeasured; the third lacks those
three bound properties. Import acceptance therefore does not guarantee a numeric
plan. Installed Node partial inspection/copy and installed Python table/exact
CSV recovery pass after the preparation directory is removed. No source download
or data redistribution is performed by this verifier; the evidence retains hashes
and counts, not the workbook/participant records. This optional local trial does
not run in CI without the workbook. Source attribution and unresolved familiarity
header1..100 versus article0..100 remain as documented by the existing preparation;
columnR stays omitted, without silent rescaling or new source-authentication claim.
