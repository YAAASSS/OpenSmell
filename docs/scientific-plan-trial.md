# Linked molecular/observation trial to a passive plan

This complete installed-SDK example connects explicitly selected scientific data
to two **separate** results: RDKit's molecular interpretation and the SDK's
application-defined mapping plan. It verifies the graph link between the selected
observation, stimulus and molecule before producing any output. No chemical
identifier join, guessed selection, physical transport or descriptor-to-channel
inference is performed.

## Run outside the checkout

Use the same optional environment as the
[RDKit molecular consumer](https://github.com/YAAASSS/OpenSmell/blob/main/docs/rdkit-molecule.md).
Copy `examples/rdkit_molecule/science_to_plan.py` and `analyze.py` into a working
directory, naming the latter `analyze_molecule.py`. The extracted developer kit
already includes both files under those names. Install the current SDK wheel
and optional RDKit2025.9.6 separately.

With the real diphenyl ether graph and explicit perceptual profile:

```sh
python science_to_plan.py multisource_diphenyl_ether.osmell \
  --molecule-id e6ad8ce3-dc6e-5d94-9287-57665d48fc0b \
  --observation-id 219ef28c-9b58-52f2-93a7-0807f5897857 \
  --resource-id 219ef28c-9b58-52f2-93a7-0807f5897857 \
  --profile offline_perceptual_profile.json --duration 5 \
  --output-directory new-scientific-trial
```

The mapping resource is always explicit. For this fixture's semantic path, use
`offline_semantic_profile.json` and set `--resource-id` to the selected molecule
ID. The chosen observation and molecule remain the same; the example never
switches the mapping resource based on the profile automatically.

| Path | Resource explicitly mapped | Expected plan,5 seconds |
|---|---|---|
| Semantic | Selected molecule | CH0=.25,CH1=.6 |
| Perceptual | Selected observation | CH0=.47,CH1=.18,CH2=.15 |

Command ordering is the SDK mapper's ordering and is preserved in the artifact;
the table compares channel values, not an imposed sort order. The illustrative
profile defines channel meaning and declared capability bounds. RDKit's formula,
mass or other computed properties never supply mapping intensities.

## Preconditions and output

The source is a strict Generic ResourceGraph, up to8MiB; the explicit profile is
strict JSON, up to1MiB. Both are retained at the byte level. The selected resource
must be a known Observation whose stimulus resolves to a known Stimulus with an
explicit source reference equal to the chosen molecule ID. The selected mapping
resource must be that molecule or observation; the SDK still checks whether the
profile/mapper supports it. Missing/inconsistent links, unmapped data, invalid
molecular parsing or out-of-capability plans refuse before directory creation.

The source/profile are never rewritten. The selected observation's dilution,
ratings, scale/unit, target and supplied provenance remain in the exact source;
this example does not join, aggregate or impute measurements. A structural link
asserted in the graph is not independent chemical authentication.

A new output directory contains the molecular consumer's `source.osmell`,
`molecule.sdf` and `report.json`, plus:

| File | Meaning |
|---|---|
| profile.json | Exact profile bytes provided by the caller |
| plan.json | Standard experimental offline-plan0.1 artifact with source/profile/request snapshots and supplied-capability basis |
| experiment.json | Explicit selection/link basis, hashes, separate-chemistry declaration and passive plan |

Only `experiment.json` with `status: prepared` marks the full experiment package
complete; a missing/incomplete marker is not success. `report.json` describes only
the chemistry stage. A successful package has `execution: not_attempted`; it is
not a device command, acceptance, observed execution or measured odor result.
No transport is opened. Existing directories refuse replacement. Exit codes:
0 prepared,1 refused/invalid,2 file/dependency/collision error.

The passive plan can be inspected or passed explicitly to the installed
`opensmell encode-frame` command with separately selected supplied capabilities.
The installed proof uses this normal entry to check artifact reuse, but does not
send the frame. Reading either report is passive.

## Proof and limits

The optional-science CI job runs17 focused tests and the fresh wheel proof. It
tries both mapping paths, validates the installed normal frame-export entry,
retains exact source/profile files and refuses mismatched molecule links and
output collisions. The SDK itself remains unchanged. Same-version SDF re-read
checks do not establish universal chemical equivalence; the RDKit policy and
limits remain documented in the molecular guide.

The scripts are included in the kit, while RDKit and its dependencies are not
added to the SDK default or offline dependency closure. This is a project-run
scientific interoperability walkthrough, not outside adoption, a stable release
or experimental evidence of odor reproduction. No hardware or media is generated.
