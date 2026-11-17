# Observation tables and an optional Pandas consumer

The installed SDK and `opensmell observation-table` project known perceptual
measurements from a Generic ResourceGraph0.1 into an experimental analysis
artifact. No mapper, adapter or device is created. This is development-main
functionality, not a new public package release or a full scientific validator.

```sh
opensmell observation-table observation.osmell --output analysis.json
```

The equivalent installed API has no Pandas dependency:

```python
from opensmell.experimental.observation_table import observation_table
artifact = observation_table(open("observation.osmell", "rb").read())
rows = artifact["tables"]["measurements"]
```

## Projection contract

`org.opensmell.experimental.observation-table` version0.1 contains:

| Field | Meaning |
| --- | --- |
| `source` | Exact input bytes in base64, SHA-256 and byte count; not a signature |
| `context` | Complete decoded source graph, including provenance, conditions, target identifiers, unknown extensions and rejected payloads |
| `tables.measurements` | One row per valid known perceptual0.1 measurement, in source order |
| `tables.observations` | Observation IDs/references and exported measurement counts, including zero-row observations |
| `tables.categorical` | Separate raw semantic Annotation0.1 and observation categories0.1 payloads; no numerical encoding or text inference |
| `coverage` | Counts and explicit source paths/reasons for unsupported or invalid data |

Measurement rows retain the source hash, observation/stimulus/target IDs,
result/measurement indexes, JSON source path, property, exact decoded numeric
value and scale bounds, and optional unit. `unit_presence` distinguishes missing,
explicit null and a supplied nonblank string. Units are transported, not converted
or authenticated. Arbitrary integer values are not converted to floats in the SDK.

Only `org.opensmell.perceptual.measurements` version0.1 is numerically projected.
Missing measurements create no numeric row; measured zero remains zero. Invalid
values/scales/units produce coverage entries instead of becoming zero or null.
Other Result schemes/versions, unknown resources/annotations and unavailable
stimulus/target context remain identified as uninterpreted. Original values and
bytes remain recoverable from context/snapshot. Empty numeric results are reported;
an observation with no numerical Result remains an observation with zero rows.

Status `projected` means the supported projection found no coverage issue, not
that chemistry, provenance, subjective results or every extension were validated.
Status `partial` retains usable rows alongside explicit coverage issues. No
normalization, identity joining, averaging, unit conversion or imputation occurs.
Relationships follow explicit graph references only; no chemical/person merge.

Input: strict UTF-8 JSON, at most8MiB; duplicate members/nonfinite numbers and
invalid graph structure refuse. Stdin `-` works. `--output` exclusively creates a
new file; input and existing outputs are never replaced. Exit codes:0 projected,
3 partial artifact written,1 invalid input,2 usage/I/O/collision. Outputs are
passive: execution/physical validation remain unobserved/false.

## Try real Pandas outside the checkout

Install the current wheel and Pandas separately, then copy
`examples/pandas_analysis/analyze.py` into your own project:

```sh
python -m pip install /path/to/opensmell-0.1.0-py3-none-any.whl pandas
python analyze.py observation.osmell --output-directory new-analysis
```

The optional consumer uses the installed API, explicit Pandas nullable `Float64`,
`Int64` and string dtypes, and source-local stimulus references for the complete
opaque dilution-condition list. It does not join samples by CID/person. Output:
`analysis.json` (authoritative snapshot/context), `measurements.csv` (derived
numeric view), `categorical.json` (separate exact JSON payloads) and `summary.json`
(dtypes, coverage and source identity). Existing directories refuse replacement.

No mean, filling of missing cells or rescaling is applied. If a numeric value
cannot be represented exactly by the consumer's Float64 conversion (e.g.
2**53+1), it refuses **before creating output**. The SDK JSON artifact can still
preserve that integer. CSV is a derived view, not an original-byte interchange or
a replacement for provenance/context. A partial analysis returns3 with outputs.
See Pandas documentation on [explicit nullable dtypes](https://pandas.pydata.org/docs/user_guide/integer_na.html)
and [DataFrame records](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.from_records.html).

Pandas is not a new SDK runtime dependency and is not added to the offline kit's
pinned wheelhouse. The kit includes this example/guide so consumers can choose
their own separately installed analysis environment. Repository dev tests provide
Pandas explicitly; that optional proof inherits its available test dependency.

## Reproducible installed proof

```sh
python -m build --wheel
python -m tools.verify_installed_analysis dist/opensmell-0.1.0-py3-none-any.whl
```

A fresh installed wheel outside the checkout imports three declared synthetic
observations, exports4/2/0 measurement rows, retains zero grass/absent pleasantness
and the unmeasured observation, and runs the actual Pandas consumer. The existing
real multisource graph produces7 measurements with missing units and a separate
categorical Annotation. Unknown schemes retain partial coverage and exact input;
output collisions and lossy Float64 conversion refuse.

The same proof on the [pinned publisher-source preparation](perceptual-csv-import.md#pinned-published-source-trial)
was executed with:

```sh
python -m tools.verify_installed_analysis dist/opensmell-0.1.0-py3-none-any.whl \
  --published-preparation /path/to/public-prepared
```

Its prepared source observations2500/2501/0 yield8/0/3 measurement rows,
respectively, each with its separate categorical payload. The first retains
flower26/grass38/wood89 at the declared scale/unit and opaque dilution. Familiarity
remains excluded by the documented preparation's scale limitation; no new
scientific meaning or corpus validation is inferred. External corpus bytes are
not bundled. This is a project-maintained external-library interoperability trial,
not observed independent adoption or physical/olfactory evidence.
