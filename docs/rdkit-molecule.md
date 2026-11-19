# Optional installed-SDK molecular workflow with RDKit

This executable scientific consumer selects one explicitly declared Molecule0.1
SMILES, interprets it with RDKit, and exports a re-readable SDF plus a computation
report and the exact original graph. It reuses the installed SDK; no new schema,
chemical identity join, protocol or olfactory inference is introduced.

OpenSmell's molecule model deliberately transports SMILES as opaque text. RDKit
interpretation is separate: accepting a graph does not establish chemical validity,
and a successful RDKit parse does not authenticate source identity or predict odor.

## Normal entry outside the repository

Install the current locally built OpenSmell wheel with its normal dependencies,
and install optional `rdkit==2025.9.6` in your chosen scientific environment. Copy
`examples/rdkit_molecule/analyze.py` as `analyze_molecule.py` and
`examples/rdkit_molecule/read_sdf.py` as `read_molecule_sdf.py` (both names are
already included in the developer kit). Choose your graph and resource explicitly:

```sh
python analyze_molecule.py caller.osmell --resource-id YOUR_MOLECULE_ID \
  --output-directory new-molecular-result
python read_molecule_sdf.py new-molecular-result/molecule.sdf
```

For the documented real fixtures:

| Graph | Explicit molecule ID | RDKit formula | Specified stereo centers |
|---|---|---|---|
| multisource_beta_pinene.osmell | 2d5a1039-904c-5b19-a60f-71c1ada5bac2 | C10H16 | 2 |
| multisource_diphenyl_ether.osmell | e6ad8ce3-dc6e-5d94-9287-57665d48fc0b | C12H10O | 0 |

These values describe the declared structure as interpreted by the pinned library,
not chemical authentication, purity or a measurement of a physical sample. The
existing supplied identifiers/provenance are retained, not looked up or verified.
The SDF reader imports RDKit only, not OpenSmell, and returns the selected ID,
source hash, original SMILES property and a fresh calculation from the SDF.

## Inputs, policy and refusal

The consumer uses the SDK's strict UTF-8/JSON graph boundary, limited to8MiB,
then requires the selected resource to be a known Molecule0.1 with a declared
nonempty SMILES. It never infers selection from observation targets, chemical
names, IDs or a field called smiles in an opaque resource. Identifier-only,
missing or unsupported-version resources are refused without external lookup.

Only plain SMILES is supported. Whitespace/control characters, name suffixes and
CXSMILES metadata are refused rather than silently stripped. RDKit parsing uses
sanitize=True, removeHs=False, parseName=False and allowCXSMILES=False. Invalid
valence or another RDKit parse failure produces an explicit refusal, separately
from SDK graph validation. Disconnected components, explicit H/isotopes and
specified stereochemistry are handled according to this library policy; the
fragment count is reported, not interpreted as a verified single substance.

The policy follows RDKit's
[documented parsing and molecule/SDF APIs](https://www.rdkit.org/docs/GettingStartedInPython.html).
Sanitization/aromaticity and canonical isomeric SMILES are explicitly versioned
computations; they never replace the original declared string. A canonical
string is not a universal identity proof. No tautomer/salt standardization,
conformer generation, similarity search or cross-source merge is performed.

## Output and preservation

The directory must be new. Refusals produce JSON on stdout and no output directory.
An existing output prevents replacement. Interrupted exports keep an incomplete
report and must not be treated as successful analyses.

| File | Meaning |
|---|---|
| source.osmell | Exact original input bytes, preserving unknown representations, graph context and supplied provenance |
| molecule.sdf | One RDKit-interpreted structure, with JSON-escaped resource ID/declared SMILES and source SHA-256 properties |
| report.json | Selected original resource, original SMILES, parser policy/version, computed descriptors, file hashes and re-read result |

Computed descriptors are the RDKit formula, ExactMolWt descriptor, atom/heavy-atom
counts, fragment count and specified stereo-center count. They are computations
from the interpreted structure, not source measurements or odor descriptors.
Any SDF coordinates are serialization output, not experimentally measured geometry.
Before successful export, RDKit re-reads the SDF and its computed canonical
isomeric structure must match the pre-export interpretation; otherwise it refuses.
This is a same-library serialization check, not general chemical equivalence.

Unknown graph/source/representation content remains in source.osmell; SDF is not
a full OpenSmell graph serialization and no reverse graph reconstruction is supplied.
Hashes identify bytes, not signatures or source authenticity. No input is rewritten.
Exit codes:0 analyzed,1 refused/invalid input,2 dependency/file/output collision.
The script's analyze_graph/export_analysis functions are example code, not new
stable SDK contracts. The Molecule0.1 model and RFC maturity remain unchanged.

## Reproduce the installed proof

```sh
python -m build --wheel
python -m tools.verify_installed_rdkit dist/opensmell-0.1.0-py3-none-any.whl \
  --evidence-directory /tmp/new-rdkit-proof
```

Use the explicit optional RDKit environment above. The verifier installs a fresh
SDK wheel into a new target directory outside the checkout and runs copied
consumers in isolated Python with that target first on sys.path. It verifies the
SDK import location; RDKit/dependencies are inherited from the selected scientific
runtime. This is not a clean/offline closure proof. Nothing is downloaded by the
verifier. The default SDK and offline kit do not add RDKit, NumPy or Pillow.

The proof includes both real fixtures, a clearly synthetic explicit-H/isotope/
unknown-context variant, independent SDF reads, exact-byte preservation and output
collision refusal, then seven missing/unsupported/invalid input cases. CI runs a
separate Python3.12 scientific job with pinned RDKit2025.9.6 and retains
`rdkit-molecular-interoperability-proof` for14 days. Base CI does not require
RDKit; its optional chemistry tests skip where the dependency is absent.

This is project-maintained interoperability with an external library, not outside
adoption. No device command, physical sample, odor measurement, image/media, flash,
tag, release or registry publication is part of this workflow.
