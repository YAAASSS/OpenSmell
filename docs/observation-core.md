# Select an observation result into Core (experimental)

`export-observation-core` bridges one explicitly selected Generic ResourceGraph
Observation/result to a quantitative Core0.1 representation. It requires a
**caller-owned odor ID** and retains the complete original graph for recovery.
It never infers chemical identity, equivalent stimuli, averaging across subjects
or a new experimental presentation. All operations here are passive.

## Try the installed normal entry

With this revision installed and the repository examples available:

```sh
opensmell export-observation-core examples/multisource_diphenyl_ether.osmell \
  --observation-id 219ef28c-9b58-52f2-93a7-0807f5897857 --result-index 0 \
  --odor-id urn:caller:selected-odor --output selected-core.osmell
opensmell extract-observation-source selected-core.osmell --output recovered.osmell
opensmell plan-core selected-core.osmell --representation-index 0 \
  --profile examples/offline_observation_core_profile.json --duration 0.1 --output selected-plan.json
```

Expected plan intensities: CH0=.47,CH1=.18,CH2=.15. These are illustrative profile
outputs, not a reproduction of the source odor. In the extracted kit, use
`data/multisource_diphenyl_ether.osmell` and `data/observation_core_profile.json`.
Use your own paths outside checkout; graph/Core stdin `-` and stdout are supported.
Outputs exclusively create files; no overwrite. Exit0 exported/recovered,1
invalid/refused,2 filesystem error/collision. Preparation does not select a device.

For imported caller data, use `import-keller` or an existing graph producer first,
then inspect IDs and result positions, for example with `inspect --json` and
`observation-table`. Result indices are zero-based **within the chosen observation**.
The synthetic CSV importer puts categorical context before quantitative results;
select its quantitative result index explicitly (normally1), not the first result
by assumption. An unknown/categorical/unmeasured selection refuses without trying
a different result. No resource, result, subject, chemical ID or profile is picked
as a default. `--odor-id` belongs to the caller and asserts no identity equivalence.

The example mapping profile is specific to the supplied example's unit/scale
expectations. Imported data may require a different explicitly authored profile;
[Core perceptual planning](core-perceptual-planning.md) compares units and scale
presence/value rather than converting them. An export never invents a profile or
fills absent ratings. An incomplete measurement set can export faithfully but a
profile binding absent data will refuse to plan.

## Data and context

The Core contains exactly one `type:perceptual` representation with the selected
provisional `org.opensmell.perceptual.measurements`0.1 scheme/data. Numeric values,
units, scales, unknown result data and result extensions are copied without
normalization. The scheme must validate and optional unit fields must be a
nonblank string, null or absent. Duplicate measurements are retained without
aggregation; a downstream Core policy refuses duplicate bound properties.

The reserved `org.opensmell.experimental.observation-core-export` root extension
retains the explicit observation/result/odor selection and exact entire graph as
Base64/SHA-256/byte count. Stimulus conditions, targets/participants, provenance,
other results/resources, unknown schemes and lexical JSON bytes are recoverable.
Parsed selected data is not a byte-for-byte slice of its JSON spelling; recovering
the embedded graph returns the original bytes exactly. Unresolved references in
source context stay unresolved; no replacement identity is inferred.

The representation's provenance identifies source digest/observation/result, and
`org.opensmell.experimental.observation-result-context` retains extra selected
result fields. This is source tracking, not authentication or scientific truth.
Extraction returns the original graph, not a graph updated from edits to Core.

Before extraction and the normal Core planning/frame/sequence path, this reserved
convention is recomputed from the retained graph and explicit selection. Editing
Core data/identity/metadata while retaining an inconsistent source refuses, even
if a caller updates an outer Core snapshot and plan. Re-export changed graph data
through the normal entry. Other Core files and the existing chemical bridge are
unchanged. Removing an unsigned convention does not authenticate the resulting
independent document; hashes are not signatures.

## SDK

```python
from opensmell.experimental.observation_core import export_observation_core, extract_observation_source
core_bytes = export_observation_core(graph_bytes, observation_id=selected_id,
                                    result_index=selected_index, odor_id=caller_odor_id)
assert extract_observation_source(core_bytes) == graph_bytes
```

Graph input is bounded at2MiB for this embedded-source export, Core output/input
at4MiB, IDs at128 characters. The final serialized Core must fit4MiB even when
selected data/Unicode/context increase its size; no truncation occurs. These
export bounds are narrower than the general graph reader's8MiB bound. Existing
Core planning/profile/plan/live-capability bounds apply separately.

## Reproduce the complete software proof

```sh
python -m build --wheel
python -m tools.verify_installed_observation_core dist/opensmell-0.1.0-py3-none-any.whl \
  --output /tmp/new-observation-core-proof
```

The proof installs a fresh wheel outside checkout, imports explicitly synthetic
CSV rows, selects a known quantitative result, exports/retrieves exact graph bytes,
then plans under separately supplied unit/scale policy. One source has an absent
wood rating: it stays absent, and the caller explicitly chooses fewer bindings.
Original CSV/source/graph/Core/profile paths are removed before frame export and
explicit Python/independent Node software trials. Optional
`--host /explicit/native-lifecycle-host` adds the real compiled sketch in software
`--realtime` mode. Unknown/unmeasured selections, source inconsistency, stale plan
before process launch and collisions are checked. Build dependencies are inherited,
not a new clean offline closure proof. No third-party adoption is established.

This is an opt-in application projection, not a Core wire change or promotion of
RFC-0005/0015 beyond Draft. Export/planning/receipts do not establish physical
execution, calibrated diffusion or measured odor reproduction. The module opens
no transport; hardware, human observations and their provenance remain independent.
