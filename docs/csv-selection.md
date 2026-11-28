# Select prepared CSV records with bounded memory (experimental)

The installed `select-keller-csv` entry scans a regular local UTF8 prepared CSV
once to EOF, fingerprints its complete byte stream and retains only caller-chosen
logical data records. It produces a small input for the existing
[quantitative cohort importer](perceptual-cohort.md), without raising its512KiB
bound or loading the complete original CSV into Python memory.

## Normal installed path

With this revision installed, supply your explicit source/license/preparation/
scale declaration under the [existing prepared Keller contract](perceptual-csv-import.md):

```sh
opensmell select-keller-csv large-prepared.csv --source original-source.json \
  --rows 10002 1 --output-directory selected
opensmell import-keller-cohort selected/observations.csv --source selected/source.json \
  --rows 2 1 --output cohort.osmell
opensmell observation-table cohort.osmell --output table.json
opensmell extract-keller-source cohort.osmell --output recovered-selection.csv
```

The example row numbers require a source containing those records. Use your own
explicit selection; no first/default/eligible rows are inferred. `--rows` is unique,
one-based logical data records after the header; quoted multiline cells count as
one, not a spreadsheet/physical line. Requested order is retained. The cohort
command's row numbers refer to the **new selected CSV**, not the large source.
Here selected row1 came from source10002, selected row2 from source1; the explicit
second command reorders them back for the cohort. Read the recorded mapping.

The newly created directory has:

- `observations.csv`: original header and selected raw records, including unknown
  cells, quoting, UTF8 spelling/BOM and LF/CRLF/CR; no numeric reserialization.
- `source.json`: the source declaration with a preparation note and reserved
  `org.opensmell.experimental.csv-selection` context. Existing unknown fields and
  source/scale declarations remain retained as supplied values.
- `original-source.json`: exact original declaration bytes, preserving formatting.
- `selection.json`: passive report, complete-input digest/byte count/data-record
  count, selected order/offsets/raw-record hashes, and output file identities.

Records without a final terminator can be selected before another record. A single
LF is then added **outside the cells** as a declared separator; `separator_added`
records this. Original record bytes remain an unchanged slice of the selected file,
with original byte count/hash and source/selected byte offsets in the mapping.
No other newline normalization, imputation, averaging, participant/CID join, scale
conversion or measurement validation occurs. Unknown/unselected numeric values
are not interpreted. Semantically invalid selected rows can be retained and later
refused explicitly by the normal cohort importer; selection is not certification.

## Full scan and provenance

Every record must parse under the standard-library CSV profile with the same field
count as the unique unpadded prepared header; blank/ragged records, invalid UTF8,
duplicate/missing required headers and malformed quoting anywhere refuse. A late
error still causes no output directory even if all requested rows were seen early.
This is intentionally stricter globally than the single-row importer. Header needs
the exact identity columns and at least one recognized rating column; other columns
are retained without invented semantics. No dialect/worksheet/header guessing.

The scanner compares file-descriptor and path size/inode/timestamps before/after
reading and rejects observed changes. This is best-effort consistency checking,
not a locked/immutable filesystem snapshot, source authentication or a signature.
Only the complete observed input fingerprint is retained: **the large input is
not embedded and cannot be recovered from this selection**. `extract-keller-source`
recovers the small CSV embedded in the downstream cohort, never the unretained
large original. Import occurrence IDs belong to the new selected CSV/source and
assert no original participant or chemical equivalence.

The derived context maps each selected row to its source row, original byte span
and SHA256. Original filename is a label, not a path to reopen. Context and hashes
remain unverified declarations to downstream consumers; no new schema or implicit
source-consistency validator is added to ordinary graph/Node/plan entries.
A source already containing the reserved selection context refuses, preserving it
rather than overwriting or guessing a chained selection. This first slice does not
compose selection histories automatically.

## Bounds, errors and SDK

Input: regular local file within1GiB; no stdin, sockets, compressed input or Excel.
Logical record/header:64KiB raw UTF8 including terminators;1..100 selected records;
selected CSV512KiB; original/derived declarations1MiB each. The parser uses bounded
line reads and a bounded current record, not an unbounded `read()`/`readline()` or
list of all records. Selected storage is bounded independently of original size.
All scanning/validation completes before exclusive output-directory creation.
A later IO failure may leave an incomplete marker; no transactional/crash-safe
persistence or automatic retry is promised. Existing output/input files survive.
Exit0 prepared,1 invalid input/selection/bounds/change,2 IO/collision.

```python
from opensmell.experimental.csv_selection import select_keller_csv
report = select_keller_csv(local_path, rows=[10002, 1], source_raw=declaration_bytes,
                          directory=new_selection_directory)
```

The output uses the existing prepared dialect, not a new scientific importer.
Core planning still requires caller profile/selection and source units/scales;
software acceptance/completion and any physical/olfactory measurement stay separate.

## Installed end-to-end proof

```sh
python -m build --wheel
python -m tools.verify_installed_csv_selection dist/opensmell-0.1.0-py3-none-any.whl --output /absolute/new/proof
```

The verifier generates a10,320,157-byte declared synthetic source with10002records,
multiline/Unicode/BOM/unterminated-final-row cases and unselected out-of-range values.
Fresh installed SDK and CLI select10002 then1, retain exact records, record the
whole-input hash and declare the separating LF. The installed SDK's Python
allocation peak is measured **after imports**, gated below4MiB for this fixture;
this is not total process RSS, OS cache, all input shapes or every platform.
After removing the large source/declaration paths, existing installed cohort ->
real packed/offline-installed Node graph/Core transfer -> table -> two explicit
Python plans produce .26/0/.89 and .8/.2. The small selected CSV recovers exactly.
Late syntax/no-output and collision guards are checked. No endpoint is launched.
Python dependencies are inherited, not a new clean closure, physical proof or
outside adoption. Historical importers/consumer bounds and experimental status remain.
