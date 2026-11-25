# Explicit Core perceptual planning (experimental)

`plan-core` can now select one quantitative perceptual representation without a
chemical structure. Existing semantic selection remains compatible. This opt-in
application path interprets provisional `org.opensmell.perceptual.measurements`
0.1 from Draft RFC-0005; it does not promote the scheme or change Core0.1,
Generic ResourceGraph, Device Protocol or RFC maturity. No transport opens.

## Installed normal entry

With this revision installed, or its locally built wheel:

```sh
opensmell plan-core examples/core_perceptual_only.osmell --representation-index 0 \
  --profile examples/offline_core_perceptual_profile.json --duration 0.1 --output first.json
opensmell plan-core examples/core_perceptual_only.osmell --representation-index 1 \
  --profile examples/offline_core_perceptual_profile.json --duration 0.1 --output second.json
opensmell encode-frame first.json --capabilities hardware/esp32/led_capabilities.json \
  --output first-frame.json
```

Use your own file/profile paths outside the checkout; Core stdin `-` works.
The included source is **declared synthetic** and has no chemical representation.
Index0 produces CH0=.25,CH1=.5,CH2=1 under the explicit profile; index1 changes
CH0 to .75. The third opaque representation cannot be selected as a fallback.
All output files are new/exclusive. Exit0 planned,1 refused/invalid,2 filesystem
error. An offline plan/frame is data, not acceptance, execution or measured odor.

## Explicit policy, not inferred units or calibration

The profile still has `mapper:perceptual`, ordinary property/channel `bindings`
and supplied `capabilities`. This Core path additionally requires the recognized
application extension `org.opensmell.experimental.core-perceptual-policy`:

```json
{
  "version": "0.1",
  "normalization": "value-minus-min-over-range",
  "measurements": [
    {"property": "flower", "scale": {"min": 0, "max": 10}, "unit": "rating"},
    {"property": "grass", "scale": {"min": -1, "max": 1}, "unit": null},
    {"property": "wood", "scale": {"min": 0, "max": 100}}
  ]
}
```

This is the application author's explicit choice of the existing demonstration
formula `(value-min)/(max-min)`, not an automatic normalization or a universal
odor mapping. There is no unit conversion, calibration or efficacy claim. Source
units/scale stay untouched in snapshots; command intensities are floating-point
software mapping results. Ranges unusable by that mapper refuse.

Policy properties must exactly match bindings; each bound property must occur
exactly once in the selected representation. Missing or repeated bound properties
refuse, rather than silently ignoring data or choosing the first occurrence.
The policy's numeric min/max must equal the source scale. Unit spelling and
presence must match exactly: missing, `null` and a nonblank string are distinct.
No percent/rating/score conversion or assumed 0..100 range. Unknown policy
extensions are passive context; only documented fields affect this path.

The selected known scheme data is validated explicitly; registered Core schemes
still undergo normal whole-envelope validation. Other unselected representations
remain retained and uninterpreted. Ordinary graph perceptual mapping and existing
semantic Core mapping do not acquire this new policy requirement.

## Projection, SDK and provenance

The SDK entry stays the same:

```python
from opensmell.experimental.core_planning import plan_core_bytes
artifact = plan_core_bytes(core_bytes, profile_bytes, representation_index=0, duration=0.1)
```

The plan uses the existing offline-plan0.1 envelope. `source.document` contains
one opaque `org.opensmell.experimental.core-perceptual-representation` resource,
with selected scheme/data/context and Core odor ID. It is **not** a Molecule,
Stimulus, participant or measured Observation. An application representation does
not establish a presentation or experimental measurement event.

The reserved root extension `org.opensmell.experimental.core-perceptual-selection`
retains the explicit index and exact Core bytes/Base64/SHA-256/length. Unknown
source fields, provenance, other representations and JSON whitespace/line endings
are preserved. Parsed profile data and its declared hash are retained; profile
whitespace is not reconstructed. Hashes identify bytes, not authenticity.

Normal `plan` on the projection, frame export and sequence preflight recompute it
from retained Core bytes/index. A changed projection is refused even if an edited
plan agrees with it. Both semantic and perceptual selection markers in one graph
refuse. Reprepare changed source instead of editing generated projection fields.
The old semantic namespace/output and chemical bridge remain unchanged. Removing
source metadata does not authenticate a graph; the new opaque subject alone is
not a regular Observation accepted by the ordinary perceptual mapper.

Bounds stay Core4MiB/profile1MiB/offline plan8MiB, finite durations/intensities,
nonempty unique commands and all supplied/live target capabilities. No default
representation, profile, command, retry, discovery or automatic sending is added.

## Reproduce software interoperability

```sh
python -m build --wheel
python -m tools.verify_installed_core_perceptual dist/opensmell-0.1.0-py3-none-any.whl \
  --output /tmp/new-core-perceptual-proof
```

The fresh-wheel proof runs outside checkout with inherited build dependencies,
prepares both selections, deletes original Core/profile paths, exports frames and
uses explicit Python and independent Node software endpoints. Unit/scale/policy/
index and stale-projection refusals and output collisions are checked. Optional
`--host /explicit/native-lifecycle-host` adds the actual compiled lifecycle sketch
in native `--realtime` software mode. Existing CI runs that case without flashing.
No physical delivery, participant observation, odor reproduction or independent
third-party adoption follows from these repository-owned software checks.
