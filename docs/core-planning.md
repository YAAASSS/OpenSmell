# Explicit Core semantic planning (experimental)

`opensmell plan-core` plans **one explicitly selected semantic representation**
from a Core0.1 `.osmell` file with an application-owned mapping/capability profile.
It also works when the file contains no SMILES/chemical representation. The
existing `bridge-core` chemical projection and graph `plan` command are unchanged.

This is a bounded experimental application path, not a change to Core0.1,
Generic ResourceGraph, Device Protocol0.1 or RFC maturity. Channel intensities
come from explicit profile bindings, not from inferred chemistry or universal
odor primaries. Preparation is passive; no adapter or transport is opened.

## Install and try the normal entry

Install this source revision (`python -m pip install .`) or its locally built
wheel. From the checkout:

```sh
opensmell plan-core examples/core_semantic_only.osmell \
  --representation-index 0 --profile examples/offline_semantic_profile.json \
  --duration 0.1 --output core-plan.json
opensmell encode-frame core-plan.json --capabilities hardware/esp32/led_capabilities.json \
  --output core-frame.json
```

Expected: a normal `offline-plan`0.1 artifact, `status:planned`,
`execution:not_attempted`, command CH0=.25 under the supplied demonstration
profile. Frame export is data, not sending. The example derives its semantic
annotations from the repository geraniol example; the additional opaque
representation is declared synthetic and remains uninterpreted.

For the existing complete Core `examples/geraniol.osmell`, select index **1**
(the chemical representation is index0). No default index or best-match/fallback
selection is supplied. Use your own Core/profile paths outside the checkout;
stdin `-` is supported for Core input. `--output` exclusively creates a new file;
stdout is available when it is omitted. Exit0 planned,1 invalid/refused,2 file error.

The first slice accepts only `type:semantic`,
`org.opensmell.semantic.annotations` version0.1, with an explicit `mapper:semantic`
profile. Known scheme data must validate. A selected unknown scheme/type/version,
invalid index, unmapped annotation set, incompatible supplied capabilities or
unsupported duration refuses. A known alternative is never silently selected.
Multiple supported representations are allowed only because the caller selects
one exact zero-based array position; only that one contributes annotations.
Other representations/unknown extensions remain retained, not merged or interpreted.
The entire Core envelope and known schemes still undergo their normal validation.

## Exact source, projection and downstream validation

The SDK API is:

```python
from opensmell.experimental.core_planning import plan_core_bytes
artifact = plan_core_bytes(core_bytes, profile_bytes,
                           representation_index=0, duration=0.1)
```

It returns the same passive offline-plan envelope consumed by installed frame
export and software sequencing. Its `source.document` is an explicit temporary
Generic ResourceGraph projection: an **opaque application subject**, plus one
known Annotation with the selected scheme/data and representation context. No
Molecule, chemical identity, Stimulus or measured Observation is invented.
The opaque subject type is an application convention, not a newly standardized
resource; generic graph readers may report partial coverage.

The reserved graph extension
`org.opensmell.experimental.core-semantic-selection` contains the explicit index
and complete original Core bytes in Base64, with SHA-256 and length. Decode its
`source.data` to recover the exact original, including unknown representations,
provenance, valid JSON whitespace and line endings. UTF-8 BOM remains refused
by the existing strict JSON boundary. The old `extract-core` command remains
specific to the old chemical bridge; it does not interpret this different convention.
The offline-plan `source.sha256` identifies the canonical projected graph;
the embedded selection's `source.sha256` identifies the original Core bytes.
Profile values/unknown fields and its declared input hash are retained, without
claiming retention of original profile whitespace bytes.

Before frame export or the sequence preflight, the existing normal boundary
recognizes this reserved convention and **rebuilds the projection from exact Core
bytes and index**. Changing projected annotations/index/snapshot/hash/resources
is refused even if the edited plan matches the edited graph. Reprepare from
changed Core input rather than editing generated projection/plan fields. A
profile change still requires a plan consistent with that explicit profile.
Other generic graphs are unchanged. This integrity/recomputation check does not
authenticate the source, and removing/replacing provenance is not prevented by
a signature. Unknown input context is preserved; its truth is not established.

Bounds: Core4MiB, profile1MiB, resulting serialized offline plan8MiB. Only finite
supported duration/intensities and nonempty mapped commands are permitted. The
normal downstream entry applies its own frame/message/live capability bounds.

## Independently choose software execution

After inspecting the artifact, explicitly select a trusted software endpoint:

```sh
opensmell run-sequence core-plan.json \
  --software-command-json '["node","examples/lifecycle_adapter/device.cjs"]' \
  --expected-device-id opensmell-node-simulator-001 --output core-receipts.json
```

No input data chooses an executable. See the [software sequence guide](https://github.com/YAAASSS/OpenSmell/blob/main/docs/software-sequence.md)
for live capability/identity checks, cooperative Stop, no retry/reconnect and
uncertain replies. A plan is not a command, acceptance, observed completion or a
measured olfactory result. No physical execution is authorized by this example.

In the extracted kit: `data/core_semantic_only.osmell`, `profiles/semantic.json`,
`profiles/esp32-led-capabilities.json` and `["node","software/device.cjs"]` are the
equivalent paths. The guide is included as `CORE_PLANNING.md`.

## Reproduce installed evidence

```sh
python -m build --wheel
python -m tools.verify_installed_core_plan dist/opensmell-0.1.0-py3-none-any.whl \
  --evidence-directory dist/core-plan-proof
```

The fresh wheel is installed outside the checkout. An existing chemical+semantic
Core and a declared synthetic caller semantic-only Core produce two distinct
plans. Original Core/profile files are deleted before normal frame export and
software receipts on Python/independent Node. Exact Core bytes are checked;
unknown selection, output collision and stale-but-plan-consistent edited
projection fail before execution. Proof retains original Core, plans, frame data
and receipts. Add `--host /absolute/path/to/lifecycle-host` to include the actual
sketch compiled natively according to the firmware guide; no port/flash action.
Host build dependencies are inherited; this is not a clean/offline installation
proof, source authentication, hardware validation or outside adoption.

Exit: installed Core selection -> normal offline plan/frame/explicit software
receipt, semantic-only data, exact preservation and refusal guards. Close this
first slice after CI; do not automatically add chemical/perceptual fallbacks,
new projection modes or graph diagnostics. Other Core representations can remain
valid and opaque without being renderable by this experimental mapping path.
