# Core import, graph projection and original-source recovery

With the development checkout installed (`python -m pip install .`), the
following commands run outside the checkout on your own files:

```sh
opensmell bridge-core examples/geraniol.osmell --output geraniol-graph.osmell
opensmell inspect geraniol-graph.osmell --json
opensmell extract-core geraniol-graph.osmell --output geraniol-original.osmell
```

The output graph is a normal experimental ResourceGraph accepted by the existing
reader/planner. Find its main molecule ID in the top-level
`org.opensmell.experimental.core-import.primary_resource_id` field. Use that
explicit ID with `opensmell plan`:

```sh
opensmell plan geraniol-graph.osmell \
  --profile examples/offline_semantic_profile.json \
  --resource-id PRIMARY_RESOURCE_ID --duration 5
```

For the geraniol fixture, this produces channel 0 at 0.25 for five seconds.
These illustrative channel bindings do not establish physical odor reproduction.
The existing [geraniol generation example](../examples/generate_geraniol_osmell.py) and source fixture carry
the data context; this conversion adds no new experimental measurements or
license grants for upstream data.

## Installed SDK

```python
from pathlib import Path
from opensmell.experimental.core_interchange import (
    bridge_core_bytes, extract_core_bytes, interchange_registry,
)
from opensmell.experimental.generic_graph import generic_graph_dumps
from opensmell.experimental.planning import plan_with_profile
from opensmell.experimental.rendering import RenderRequest
import json

original = Path("examples/geraniol.osmell").read_bytes()
imported = bridge_core_bytes(original)
graph_text = generic_graph_dumps(imported.graph, registry=interchange_registry())
assert extract_core_bytes(graph_text.encode("utf-8")) == original
profile = json.loads(Path("examples/offline_semantic_profile.json").read_bytes())
plan = plan_with_profile(imported.graph, RenderRequest(imported.primary_resource_id, 5), profile)
```

Pass this plan explicitly to an experimental software LifecycleAdapter if desired.
The installed-wheel proof exercises the recovered graph through both Python and
Node software endpoints, including completion, Stop and unknown-on-disconnect.
The wheel proof also inspects the graph with the independent JavaScript reader,
returns its original graph bytes and recovers the same Core source in Python.
This is repository-maintained cross-language evidence, not third-party adoption.
Neither CLI conversion nor planning opens a transport.

## Boundaries and preservation

The existing Odor bridge requires **exactly one** chemical representation with
type `chemical`, scheme `org.opensmell.chemical.smiles`, version `0.1`.
There is no implicit chemical inference or automatic choice between multiple
chemical representations. Files without that representation fail explicitly.

The bridge projects SMILES into a Molecule and other representations into
Annotations using the existing deterministic IDs. This is a partial projection:
some Core metadata, chemical payload extensions and reserved-field collisions
are not represented as native graph fields. All original bytes are retained in
an explicit base64 snapshot, including whitespace, document/odor/metadata
extensions, unknown representations, scheme fields and supplied provenance.
Base64 increases file size; whole files are held in memory.

`extract-core` validates the graph, checks the snapshot encoding/count/hash,
validates its Core document and returns the exact embedded original. It does not
translate graph edits back into Core. Removing the snapshot prevents recovery;
tampering without updating its hash fails. A hash can be replaced by an attacker:
this is integrity bookkeeping, not authenticated provenance or proof that a graph
was derived from that source. The data may be private; exporting the graph also
exports the complete source snapshot.

Both commands accept stdin as `-` and default to raw stdout. With `--output`,
they exclusively create a new path and refuse any existing path, including the
input. Invalid input is fully rejected before output creation. Errors are JSON on
stderr; exit statuses are 0 success, 1 invalid/unsupported input and 2 I/O/usage
error. Shell redirection is controlled by the caller and can overwrite files.
Duplicate JSON keys, non-finite numeric values and ambiguous envelopes fail.

No stable Core format change is introduced. The snapshot extension is documented
in [Draft RFC-0016](../rfcs/RFC-0016.md); the projection remains experimental.
