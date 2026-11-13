# Selected-record batch import

Import an explicit list of CSV records into one reviewable JSON bundle:

```sh
opensmell import-odornet-batch examples/synthetic_odornet_batch.csv \
  --rows 1 2 3 9 --source examples/synthetic_odornet_source.json --output batch.json
```

This synthetic fixture has two valid records, an invalid label in record 2 and
no record 9. Expect exit code **3**, a published bundle with status `partial`,
two accepted and two rejected results. Code 3 is a usable report with per-record
refusals, not a fatal input failure. It lets a scientific workflow retain valid
records while accounting explicitly for exclusions.

```sh
opensmell extract-csv-record batch.json --row 1 --output record-1.osmell
opensmell extract-csv-record batch.json --row 3 --output record-3.osmell
opensmell validate record-1.osmell record-3.osmell
opensmell bridge-core record-1.osmell --output record-1-graph.osmell
```

Then use the explicit main resource ID with `opensmell plan`, as in the
[Core walkthrough](core-interchange.md). The two synthetic records produce
channel 0 at 0.25 and channel 1 at 0.6 respectively with the existing semantic
profile. The installed-wheel proof extracts and plans each record and runs both
through Python and Node software endpoints. Import never opens a transport.

Trying to extract rejected record 2 or missing record 9 fails without a Core
file. Existing outputs are refused. Both commands accept stdin as `-`, default
to raw stdout and use JSON stderr errors. A new single bundle avoids publishing
a directory of partially imported files; all validation and JSON serialization
finish before an output file is exclusively created. I/O failures can still
interrupt writing a newly created file; source files are never overwritten.

## Contract

- The [single-record CSV/source contract](csv-import.md) remains unchanged.
- Select 1–1000 unique positive, one-based logical data-record indexes. No
  implicit full-corpus import or range expansion occurs. Requested order is
  preserved; individual document IDs match the single-record API.
- CSV is parsed once through the largest requested index. Header, UTF-8, source
  manifest and CSV syntax failures are fatal: no bundle is emitted.
- Selected records with invalid field counts, labels or SMILES are rejected
  individually. Their original cell strings remain in `raw_cells`, including
  excess or missing cells. Out-of-file selections receive `missing_record`.
- Records outside the selection are not semantically validated. Syntax is
  parsed only as far as needed; this is not corpus-wide validation.
- Accepted entries embed validated Core documents and canonical document
  SHA-256 values, including the existing source/row context and unknown columns.
  All-rejected batches are still reviewable artifacts.
- Exit codes: 0 all accepted; 3 one or more per-record refusals; 1 fatal/invalid
  input or unavailable extraction; 2 I/O or command usage error.
- `extract-csv-record` checks envelope/version, selection/result alignment,
  statuses/counts, the selected document hash, Core validity, source context and
  deterministic import ID before emitting a Core file. Extraction does not
  recover the exact CSV or apply bundle edits to upstream data.

## SDK

```python
import json
from pathlib import Path
from opensmell.experimental.csv_import import import_odornet_csv_batch, extract_batch_record

batch = import_odornet_csv_batch(
    Path("examples/synthetic_odornet_batch.csv").read_bytes(),
    rows=[1, 2, 3, 9],
    source=json.loads(Path("examples/synthetic_odornet_source.json").read_bytes()),
)
print(batch["counts"])
core_bytes = extract_batch_record(json.dumps(batch).encode("utf-8"), row=1)
```

The bundle format is `org.opensmell.experimental.csv-import-batch` version 0.1;
see [Draft RFC-0017](../rfcs/RFC-0017.md). It is a tool artifact, not a Core odor,
graph or device wire message. Hashes are integrity bookkeeping, not authenticated
provenance. Recomputing hashes can forge a modified bundle. Source manifests
remain caller declarations. The input and selected documents are held in memory;
Python's CSV field limits still apply.

This completes explicit cohort import and extraction. It does not add batch
device execution, automatic duplicate chemical merging, source authentication
or measured odor output. Real source trials and their limits belong in the
verification record; synthetic fixtures never substitute for scientific data.
