# Import a selected OdorNet-shaped CSV record

Install the current checkout with `python -m pip install .`. The installed CLI
and SDK then accept a locally supplied UTF-8 CSV without pandas, network access,
PubChem enrichment or Local Explorer.

## Reproducible example

The checked-in CSV is **synthetic**: handwritten test labels, not OdorNet
measurements. Its manifest declares that fact and the fixture's Apache-2.0
license. It exists to let anyone reproduce the software path without obtaining
or redistributing upstream data.

```sh
opensmell import-odornet examples/synthetic_odornet.csv --row 1 \
  --source examples/synthetic_odornet_source.json --output imported-core.osmell
opensmell validate imported-core.osmell
opensmell bridge-core imported-core.osmell --output imported-graph.osmell
opensmell inspect imported-graph.osmell --json
```

Use the `primary_resource_id` inside the graph's
`org.opensmell.experimental.core-import` extension:

```sh
opensmell plan imported-graph.osmell --profile examples/offline_semantic_profile.json \
  --resource-id PRIMARY_RESOURCE_ID --duration 5
```

Expected plan: channel 0 at intensity 0.25 for five seconds. The profile is
illustrative; it does not reproduce the source's odor. To exercise a software
endpoint with the same graph, use the installed
`python -m opensmell.experimental.lifecycle_demo` with `--graph`, `--profile`
and `--resource-id`. Add `--node examples/lifecycle_adapter/device.cjs` for
the independent Node endpoint. The wheel proof runs this complete import path
against both endpoints, checking completion, Stop and unknown after disconnect.

## Your source and license declaration

Supply a local JSON manifest, for example:

```json
{
  "name": "Your prepared dataset export",
  "kind": "dataset",
  "url": "https://example.org/replace-with-your-actual-source",
  "license": "Replace with the applicable upstream license",
  "preparation": "Describe your export or normalization"
}
```

Replace these placeholders before importing your data. Nonempty `name`, `url`
and `license` strings plus `kind` (`dataset` or `synthetic`) are required.
Additional manifest fields are retained. Declarations are supplied by the caller,
not verified or fetched. Importing data grants no license rights and does not
apply OpenSmell's code license to upstream data. Obtain the source you are
authorized to use, check its terms and document any preparation. This bounded
importer does not promise compatibility with every published OdorNet release
or an arbitrary downloaded spreadsheet. No full upstream corpus is bundled.

## Supported CSV contract

- UTF-8, optionally with a UTF-8 BOM; comma-separated, standard CSV quoting.
- First record is the header. Header names must be unique, nonempty and have no
  leading/trailing whitespace; exact case is significant.
- Required columns: `SMILES` and the twelve labels below.
- `--row` is a **one-based logical data-record index**, excluding the header.
  Quoted multiline fields belong to one record. This differs from old
  repository demo scripts using zero-based rows.
- All required label columns must exist. Their cells accept `0`, `0.0`,
  `1`, `1.0` or blank after trimming. Blank means unknown; 0 means absent;
  1 means present. Other tokens fail instead of being silently recoded.
- The selected record must have exactly as many cells as the header and a
  nonblank SMILES string. SMILES text is carried without chemical validation.
- Additional columns and every selected cell's original string are retained,
  including empty values. Only known label columns are interpreted.
- The selected record and preceding CSV syntax are parsed. Unselected records
  are not semantically validated, including records after the selected one.
  This is not a batch importer or full-file validation service.

Required label columns:

`animalic&ambery`, `sweety&gourmand`, `floral`, `fruity&vegetable`,
`pungent&disagreeable`, `green&herbal`, `nutty`, `woody&mossy`,
`resinous&balsamic`, `cooked`, `odorless`, `spice`.

## SDK and preservation

```python
import json
from pathlib import Path
from opensmell.experimental.csv_import import import_odornet_csv

document = import_odornet_csv(
    Path("examples/synthetic_odornet.csv").read_bytes(),
    row=1,
    source=json.loads(Path("examples/synthetic_odornet_source.json").read_bytes()),
)
print(document.odor.id)
```

The resulting Core Document contains chemical SMILES and experimental semantic
annotations using the existing OdorNet adapter. Each representation's provenance
uses the declared source name/kind; a synthetic row is not attributed to the
real OdorNet corpus. The document extension
`org.opensmell.experimental.csv-import` retains the source manifest, its
canonical JSON SHA-256, complete CSV byte hash/count, selected data-record index,
ordered headers and raw selected cell strings. Record IDs are deterministic
from CSV hash, record index and manifest hash. They identify import records,
not canonical chemical entities; editing another row or metadata changes the ID.

The full CSV bytes and original quoting are **not** embedded. This metadata
supports selected-record traceability, not byte-for-byte reconstruction of CSV.
The existing Core-to-graph bridge subsequently retains exact generated Core
bytes, including this import metadata. Whole input bytes are read into memory;
Python's normal CSV parser field-size limits apply.

Without `--output`, raw Core JSON goes to stdout; `-` reads CSV from stdin.
`--output` exclusively creates a new path. Existing files are refused. Input
errors are detected before output creation; errors are JSON on stderr.
Exit codes: 0 success, 1 invalid/unsupported data, 2 I/O/usage error.
Do not redirect stdout onto your input file; shell redirection is caller-owned.

This is experimental, repository-maintained interoperability evidence. The
bundled synthetic fixture proves no scientific measurement, chemical identity,
upstream corpus compatibility, physical diffusion or third-party adoption.
See [Draft RFC-0017](../rfcs/RFC-0017.md).
