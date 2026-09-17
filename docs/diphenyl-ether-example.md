![Official OpenSmell logo](images/OpenSmell_Official_Logo_Full.png)

# Diphenyl ether — a second real Local Explorer example

This **experimental pre-alpha** example reuses the existing import workflow,
two mapping policies and three-channel ESP32 reference profile. It demonstrates
reuse on a second input, not universal compatibility or odor reproduction.

Import [multisource_diphenyl_ether.osmell](../examples/multisource_diphenyl_ether.osmell)
using **Import graph** in [Local Explorer](../apps/local_demo/README.md).
**Open demo** still opens the original beta-pinene example. No catalogue,
interface redesign, SDK, mapper, protocol or firmware change is involved.

## Selection and identity evidence

The existing [candidate selector](../tools/select_multisource_candidate.py)
found 404 usable source-record candidates in the local inputs on 17 September
2026. Diphenyl ether ranked third overall and first among candidates with
`floral` present, with a selection score of 4060.15. The ranking's averages
only helped select a demonstration; **no mean is used in this fixture**.

| Identity | Value from the selected records |
| --- | --- |
| Keller name | `Diphenyl ether` |
| OdorNet enriched title | `Diphenyl Ether` |
| PubChem CID / cache key | `7583` / `cid:7583` |
| Complete shared InChIKey | `USIUVYZYUHIAEV-UHFFFAOYSA-N` |
| CAS | `101-84-8` |
| Original OdorNet SMILES | `c1ccc(Oc2ccccc2)cc1` |

The join compares the **complete** InChIKey from the resolved Keller identity
cache entry with the enriched OdorNet record. No name matching or partial-key
matching is used. The cache was read locally; no new PubChem lookup was made.
This is evidence supplied by those source files, not an independent chemical
identity measurement or a claim that the source vocabularies are equivalent.

There is exactly one matching OdorNet row and one resolved cache key for this
InChIKey in the files used. Keller contains 110 rows for CID 7583, representing
multiple observations. Only two have all three selected descriptor values:

| Keller row index | Study participant | Dilution | FLOWER | GRASS | WOOD |
| --- | --- | --- | --- | --- | --- |
| **34028 — selected** | **35** | **1/1,000** | **47** | **18** | **15** |
| 51028 | 52 | 1/1,000 | 1 | 1 | 1 |

Row 34028 has the largest within-observation spread of the three ratings and
gives a differentiated plan. The CID/participant/dilution combination for that
selected row is unique in this file. Other observations are not averaged,
deduplicated into it or treated as conflicting molecular identities. The
exporter refuses duplicate OdorNet matches, duplicate resolved cache keys,
ambiguous row indexes and an inconsistent selected Keller CID.

## Source files and row conventions

Fingerprints were calculated from the **exact bytes loaded** for export, not
from a reserialized table. Paths below are relative to the repository root.
The complete datasets and identity cache remain local and are not redistributed
with this example. Their existing source licenses remain applicable.

| Input | Bytes | SHA-256 |
| --- | --- | --- |
| `examples/odornet_enriched.csv` | 1,762,609 | `f0248b02c34fa58ddc38760e8454bf75dca6ca9764c27577401060a1d2f8bf3a` |
| `examples/keller_vosshall.xlsx` | 9,461,137 | `efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62` |
| `examples/keller_pubchem_identity_cache.json` | 145,461 | `a0580274144b994871f15b58275e0df5032383697570a33c2e54e2a5feadefec` |

- **OdorNet row 6065** is the zero-based pandas data-row index, excluding the
  header: data record 6066, or CSV row 6067 including the header in this file.
  The source-local resource identity remains the original SMILES.
- **Keller row 34028** is the zero-based index after loading worksheet `data`
  with `header=2`. The header is worksheet row 3; the selected observation is
  worksheet row **34032**, using one-based spreadsheet numbering. The observation
  identity remains its source row, not its participant, CID or dilution.
- The selected Keller observation declares participant **35**, dilution
  **`1/1,000`**, vial **590**, catalogue **`W36670-6`**, and the responses
  **`I smell something`**, **`I don't know what the odor is`**, **`No Answer`**.
  Its additional source metadata, including the missing DREAM participant ID,
  is preserved without filling missing fields.

The graph's `export` extension records file fingerprints, explicit row choices,
the selected source records and the single selected cache entry. Structured
provenance identifies OdorNet on the Molecule/Annotation and Keller/Vosshall on
the Observation. File location/fingerprint metadata does not replace source
record identity. Resource IDs use the existing deterministic SDK functions.

## All selected scientific values

The 12 OdorNet annotations are preserved, including unmapped categories:

| Category | Source cell | Annotation state |
| --- | --- | --- |
| animalic&ambery | 0 | absent |
| sweety&gourmand | missing | unknown |
| floral | 1 | present |
| fruity&vegetable | 0 | absent |
| pungent&disagreeable | missing | unknown |
| green&herbal | 1 | present |
| nutty | 0 | absent |
| woody&mossy | 0 | absent |
| resinous&balsamic | 0 | absent |
| cooked | 0 | absent |
| odorless | 0 | absent |
| spice | 0 | absent |

The existing adapter maps empty cells to `unknown`. The shared exporter now
normalizes pandas `NaN` to `None` before passing records to that adapter. This
handles the two missing cells without changing any category value or SDK code.
The beta-pinene source row has no such missing categories; its output is unchanged.

All seven available Keller measurements are retained with their existing
explicit 0–100 scales and no invented unit:

| Measurement | Source value | Used by the current channel policy? |
| --- | --- | --- |
| intensity | 95 | No |
| pleasantness | 2 | No |
| familiarity | **0** | No; the recorded zero is preserved |
| wood | 15 | CH2 |
| grass | 18 | CH1 |
| flower | 47 | CH0 |
| chemical | 1 | No |

The other 16 descriptor cells are missing, not zero; the existing adapter omits
them from the measurements array. Their source cells remain JSON `null` in the
selected-record snapshot. The literal response `No Answer` remains a string.
Neither the source ratings nor the normalized commands represent luminosity,
chemical concentration or olfactory intensity delivered by a device.

## Independently derived plans at 5 seconds

Semantic mapping uses the unchanged fixed bindings: `floral` present → CH0
at 0.25, `green&herbal` present → CH1 at 0.60, `woody&mossy` present → CH2 at 1.00.
For diphenyl ether the last category is absent, so CH2 is **omitted**, not sent
with intensity zero.

Perceptual mapping uses each measurement's declared scale:

```text
CH0 = (47 - 0) / (100 - 0) = 0.47
CH1 = (18 - 0) / (100 - 0) = 0.18
CH2 = (15 - 0) / (100 - 0) = 0.15
```

| Input | Policy | CH0 | CH1 | CH2 | Shared duration |
| --- | --- | --- | --- | --- | --- |
| Beta-pinene | Semantic | **No command** | 0.60 | 1.00 | 5 s |
| Beta-pinene | Perceptual | 0.01 | 0.86 | 0.97 | 5 s |
| Diphenyl ether | Semantic | 0.25 | 0.60 | **No command** | 5 s |
| Diphenyl ether | Perceptual | 0.47 | 0.18 | 0.15 | 5 s |

The beta-pinene perceptual expectations are independently 1/100, 86/100 and
97/100. Test expectations are based on these selected source values and rules,
not copied solely from the mapper's output. The two policies are independent
interpretations; similar descriptor names do not make the datasets equivalent.

## Reproduce the export

Import and CI tests need only the published fixture. Re-exporting from the
original local files needs pandas and the Excel reader openpyxl. The verified
environment used Python 3.13.14, pandas 3.0.5 and openpyxl 3.1.5. If needed,
install the export-only packages in your environment; they are not new app or
SDK runtime dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install pandas openpyxl
.\.venv\Scripts\python.exe -m tools.select_multisource_candidate
.\.venv\Scripts\python.exe -m tools.export_multisource_diphenyl_ether --odornet examples/odornet_enriched.csv --keller examples/keller_vosshall.xlsx --identity-cache examples/keller_pubchem_identity_cache.json --odornet-row 6065 --keller-row 34028 --output examples/multisource_diphenyl_ether.osmell
```

Run from the repository root. The selector writes an ignored local ranking CSV;
it does not generate or average the fixture. The exporter reads and fingerprints
all three inputs, validates identity and rows, and reuses the graph assembly
extracted from [the beta-pinene exporter](../tools/export_multisource_beta_pinene.py).
The original exporter entry point and its default output remain available.

The generated fixture is **11,413 UTF-8 bytes** with LF line endings, below the
inclusive 1,048,576-byte import limit. Its SHA-256 for canonical LF bytes is
`453c5577d7d90597efa201ab0d3f41d59f761bd036f5e0e89f4a677fccd248d8`.
Git checkout line-ending conversion may change a working file's byte hash;
the exporter itself always writes LF. Do not change source data to reproduce
a hash: use the identified input bytes and inspect any differences.

## Verification and its limits

On 17 September 2026, local verification passed **1,927 Python tests**, including
**163 targeted tests** and 18 new offline cases. The **8 JavaScript import tests**,
vector regeneration with an unchanged diff and all **16 other interoperability
commands** in the CI workflow passed too (19 workflow commands in total).
Python 3.13.14 and Node.js 24.19.0 were used locally. App JavaScript syntax,
export/launch help, local documentation links and Git whitespace were also checked.
These results are separate from the earlier import-size fix's 1,909/138 Python
results; no previous physical confirmation is extended to this new input.

The new [offline regression tests](../tests/test_multisource_diphenyl_ether.py)
check identity, graph references, provenance, all source states/ratings, missing
values and zero, lossless serialization, reconstruction from selected records,
identity/duplicate rejection, service and direct HTTP import, both expected
plans and the unchanged historical beta-pinene export. A Node.js JSON round trip
is read back by the Python graph loader. No full dataset, network or physical
port is required by these tests.

Local source verification regenerated the second export twice with identical
bytes and reproduced the published beta-pinene Git blob from the original
source files. Browser verification used a **real in-app browser** and an isolated
loopback app server whose serial factory and enumeration were disabled. It
covered Open demo, Import graph, source values, provenance, policy switching
and both displayed plans; the browser reported no console errors. These are
software/browser checks, not a new physical ESP32 test.

The earlier user-confirmed hardware observations concern **beta-pinene only**:
Semantic 5 s, Perceptual 5 s and refusal at 31 s against the advertised 30-second
maximum. **Diphenyl ether physical behavior remains to be confirmed by the user.**

[RFC-0004](../rfcs/RFC-0004.md)/[0005](../rfcs/RFC-0005.md) describe the representations,
[RFC-0006](../rfcs/RFC-0006.md) and [RFC-0008](../rfcs/RFC-0008.md)–[0011](../rfcs/RFC-0011.md)
the IDs, graph and resources, and [RFC-0012](../rfcs/RFC-0012.md)/[0013](../rfcs/RFC-0013.md)
the rendering and multi-source architecture.
This is a second example of the same contracts. Only RFC-0013's implementation
evidence needs updating; it remains Draft. No new RFC or protocol is introduced.

## Short manual ESP32 procedure — not yet performed for this input

1. Launch Local Explorer from the repository root with
   `python -m apps.local_demo`. Use **Import graph** to open
   `examples/multisource_diphenyl_ether.osmell`; verify the displayed identity
   and participant/dilution under **Provenance**.
2. Connect the reference ESP32 using the existing explicit **Connect** action.
   Inspect its received capabilities before any send. Set **Plan duration** to
   **5** seconds.
3. Select **Semantic**, recalculate and check CH0 **0.25**, CH1 **0.60**, CH2
   **No command**. Click **Send to device** once. With the reference firmware,
   CH2 should be off and CH0/CH1 driven for the requested duration; **confirm this
   by observing the real LEDs**.
4. Wait for the local estimated window to expire **and observe LED extinction**
   before the next trial. Choose **Perceptual** at 5 seconds, review CH0 **0.47**,
   CH1 **0.18**, CH2 **0.15**, then send once. Observe and record whether the
   three LED outputs behave as expected. The levels are command values, not
   measured brightness.
5. Wait for extinction, then Disconnect to release the port. Report the two
   observed results separately. **Command accepted** acknowledges acceptance;
   there is no completion telemetry, the countdown is estimated, and Disconnect
   does not stop an accepted command.

No substance or odor-producing actuator is involved in this LED procedure.

![Official OpenSmell symbol](images/OpenSmell_Official_Logo_Small.png)
