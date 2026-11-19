# Structural-reference GraphML and NetworkX interoperability

The installed `opensmell reference-graph` command exports a passive graph view for
scientific graph tools. Use it to inspect which resources an observation refers
to, follow its known structural dependencies, and distinguish missing targets
from resources present in the file. It uses existing SDK reference discovery;
no resource model, schema, protocol or RFC maturity changes.

## Normal entry outside the checkout

Install the current locally built wheel with its normal dependencies, then use
an explicitly selected Generic ResourceGraph `.osmell` file:

```sh
opensmell reference-graph caller.osmell --output-directory new-reference-bundle
```

`python -m opensmell` is equivalent. `-` reads stdin. The input boundary is8MiB,
strict UTF-8/JSON with duplicate keys and nonfinite numbers refused. Input is
validated before output creation. The directory must be new; an existing path
never gets overwritten. An interrupted directory is retained for inspection and
must not be treated as a successful export.

The bundle contains:

| File | Meaning |
|---|---|
| `source.osmell` | Exact original input bytes, including unknown content and supplied provenance |
| `references.graphml` | Directed structural view, one edge per discovered reference occurrence |
| `manifest.json` | Completion marker, byte counts/hashes, node mapping, coverage and limits |

This is an experimental projection, not an alternative lossless serialization
of the full OpenSmell model. Only the original file is authoritative for recovery.
GraphML edits do not update it; no GraphML-to-OpenSmell importer is supplied.
Manifest hashes identify bytes, not signatures or source authentication.

## Read with an actual external library

Install optional `networkx==3.4.2` in your analysis environment; it is not a default
SDK runtime dependency and is not bundled into the offline kit's closure. Copy
`examples/networkx_graph/inspect_bundle.py` to your working directory as `inspect_reference_graph.py` (already included
in the kit under that name), then:

```sh
python inspect_reference_graph.py new-reference-bundle --resource-id YOUR_OBSERVATION_ID
```

For the real multisource diphenyl ether fixture, select observation
`219ef28c-9b58-52f2-93a7-0807f5897857`. It has two direct reference occurrences
and three distinct reachable target resources. The reader verifies the bundle's
byte hashes, loads GraphML with NetworkX and prints direct/reachable target IDs,
missing targets and uninterpreted resource IDs. It imports no OpenSmell code,
changes no files and never contacts a device or fetches a dataset.

In your own application:

```python
import json
import networkx as nx

graph = nx.read_graphml("new-reference-bundle/references.graphml",
                       force_multigraph=True, edge_key_type=str)
resource_ids = {node: json.loads(data["resource_id_json"])
                for node, data in graph.nodes(data=True)}
```

`force_multigraph=True` preserves the same graph class even when no parallel
edges occur. The pinned proof uses NetworkX3.4.2; the reader API and directed/
multigraph behavior are documented in the
[official NetworkX reference](https://networkx.org/documentation/stable/reference/readwrite/generated/networkx.readwrite.graphml.read_graphml.html).
This is project-maintained external-library interoperability, not independent
third-party adoption or universal tool compatibility.

## Projection rules

Node IDs (`n0` etc.) and edge IDs (`e0` etc.) belong only to this export. Original
resource IDs are opaque graph-local values in `resource_id_json`; they do not
assert chemical or cross-file equivalence. JSON string attributes preserve Unicode,
control characters and large integers without XML numeric coercion. Decode these
attributes with JSON, not heuristics or case normalization.

Every input resource is a node, including isolated/unknown resources. `present`
is true only for actual input resources. Known absent targets get explicit nodes
with `present=false`, `source_index=-1` and `resource_json=null`. Their IDs also
appear in manifest coverage. No resource is invented for fields merely named
`resource_id` inside unknown payloads, schemes or extensions.

`understood` denotes a registered resource class, not full scientific validation
of all its schemes or content. Unknown resource payloads remain opaque JSON in
`resource_json`, and their IDs are listed as uninterpreted. Coverage is always
partial because arbitrary payload references are deliberately not inferred.

Each directed edge goes from the resource containing a known structural reference
to its target. Parallel occurrences and self-references survive. Edge attributes
retain discovery order and unknown reference extension fields as JSON. The
existing discovery API does not supply an edge role or JSON path: the projection
never invents those distinctions. Nor does it infer chemical joins, causal links,
means, similarities, mapping channels or odor outcomes from reachability.

## SDK and reproducible proof

`opensmell.experimental.reference_graph.project_reference_graph(raw_bytes)`
returns GraphML bytes and coverage without filesystem mutation.
`export_reference_graph(raw_bytes, new_directory)` writes the exclusive bundle.
NetworkX is unnecessary for either SDK/CLI export entry.

```sh
python -m build --wheel
python -m tools.verify_installed_reference_graph dist/opensmell-0.1.0-py3-none-any.whl \
  --evidence-directory /tmp/new-reference-proof
```

The verifier installs the wheel outside the checkout and runs the independent
consumer on both real multisource fixtures and a declared variant with opaque
content, two references to one missing target and XML-sensitive IDs. It checks
exact source bytes, no overwrite and modified-bundle refusal. Host dependencies
are inherited; an optional explicit local NetworkX wheel can be passed using
`--networkx-wheel`. This is separate from the clean offline kit proof. CI retains
the bundles/consumer reports as `reference-graph-networkx-proof` for14 days.
No hardware access, plan execution or measured olfactory result is established.
