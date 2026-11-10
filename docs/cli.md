# Installed OpenSmell CLI

Validate and inspect files, or produce an offline plan with explicit mapping and
capability profiles, without starting Local Explorer, a server or a device. This is the first
installed entry point in the broader [developer-kit milestone](development-status.md).

## Install and try

Use Python 3.10 or newer. From a current checkout:

```sh
python -m pip install .
opensmell validate examples/geraniol.osmell examples/multisource_beta_pinene.osmell
opensmell inspect examples/multisource_beta_pinene.osmell
```

After installation, the `opensmell` command works from any directory on your own
files. `python -m opensmell` works equivalently if the command's scripts directory
is not on PATH. The example files above belong to the checkout; they are not
installed with the package. No `apps` or `tools` import is required. This feature
is in development main; the previously published release does not contain it.

For a built wheel, install that wheel instead of the checkout:

```sh
python -m build
python -m pip install --force-reinstall dist/opensmell-0.1.0-py3-none-any.whl
```

Building requires the development dependencies (`python -m pip install '.[dev]'`).
The version number remains the existing experimental 0.1.0; this is not a release.

## Batch processing and scripts

```sh
opensmell validate first.osmell second.osmell --json
opensmell inspect input.osmell --json > inspection.json
python -m opensmell validate - --json < input.osmell
```

Use `-` once to read UTF-8 bytes from standard input. Every input is processed,
even when an earlier file is invalid or unavailable. JSON output is one object
with `report_version`, `command` and an ordered `results` array. Each item has
`input` and `status` (`valid`, `invalid`, or `error`). Valid items include the
SHA-256 of the original bytes, byte count, format/version, summaries and warnings.
Invalid/unreadable items contain an error code and message. Human-readable output
escapes terminal control characters in file-controlled text.

| Exit code | Meaning |
| --- | --- |
| 0 | Every input passed the supported structural checks; warnings may remain. |
| 1 | At least one invalid document and no input/usage error. |
| 2 | At least one unreadable input, or invalid command-line usage. |

Usage errors are argparse messages on stderr; input/document results go to stdout,
including errors in JSON mode. Consumers should inspect warning codes as well as
the exit status. Treat report version 0.1 as experimental.

## What is checked

- Core OpenSmell 0.1: packaged JSON Schema and registered built-in representation
  validators. Unknown schemes remain accepted with `unknown_scheme`; their payload
  semantics are not validated. For example, the Geraniol semantic annotation
  extension is disclosed as unknown to the Core scheme registry.
- Experimental generic ResourceGraph 0.1: existing SDK envelope/resource parsers,
  unique IDs and registered Stimulus, ObservationTarget, Observation, Molecule and
  Annotation structures. Unknown resource contracts produce `unknown_resource_type`.
  Registered resource structure does not imply validation of every embedded scheme
  payload or provenance extension.
- Known structural graph references are counted. Targets absent from the file
  produce `unresolved_references`, which is allowed by the graph model. Unknown
  resources and arbitrary extension data are not scanned for invented references.
- The CLI rejects duplicate JSON members at every depth, non-finite values,
  invalid UTF-8, unsupported envelopes/versions and ambiguous envelopes containing
  both Core and graph discriminators. The existing Core loader API is unchanged.

## Produce an offline plan

Use a generic ResourceGraph, an explicit target resource ID, a mapping profile
and duration. The committed profiles reuse the existing demonstration bindings;
they do not establish any physical relationship between a channel and an odor.

```sh
opensmell plan examples/multisource_diphenyl_ether.osmell --profile examples/offline_semantic_profile.json --resource-id e6ad8ce3-dc6e-5d94-9287-57665d48fc0b --duration 5 > semantic-plan.json
opensmell plan examples/multisource_diphenyl_ether.osmell --profile examples/offline_perceptual_profile.json --resource-id 219ef28c-9b58-52f2-93a7-0807f5897857 --duration 5 > perceptual-plan.json
```

The semantic example produces CH0=0.25 and CH1=0.60. The perceptual example
produces CH0=0.47, CH1=0.18 and CH2=0.15 from the explicit measurement scales.
Both last five seconds. These are illustrative plans for the same source graph,
not equivalent perceptual or chemical results.

`plan` always outputs JSON. Its artifact includes the original parsed source
and profile (including provenance and unknown extensions), hashes of their exact
input bytes, the selected request and computed commands. `execution` is always
`not_attempted`; `capability_basis` is `supplied_profile_not_live_device`.
It is deliberately not a wire-level render message. Nothing sends it to a device.
Use `inspect --json` to find resource IDs; the planner never guesses a resource.
Core bridging is not automatic: `plan` requires a generic ResourceGraph.

The target capabilities use the existing Device Protocol 0.1 capability response
shape embedded in the profile. Duplicate bindings, unsupported channels/intensities,
invalid durations (including 31 seconds against a 30-second profile), missing
resources and mappings that produce no commands are rejected. Profile extensions
are carried through, not executed. Unknown fields in a binding are rejected to
catch misspelled configuration. Codes 0/1/2 mean planned/rejected/input-or-usage
error. Failure output has `status` and `error`, and contains no partial plan.

For Python clients, `opensmell.experimental.planning.plan_with_profile(graph,
request, profile)` returns a `RenderingPlan` after the same mapping/capability
checks. It uses existing SDK mappers and requires no app or transport. The
profile/artifact envelopes are experimental [Draft RFC-0015](../rfcs/RFC-0015.md).

## Limits

The commands are passive and leave input bytes untouched. SHA-256 identifies
bytes, not an authenticated author. Provenance is reported as supplied, not
verified against external sources. Structural acceptance does not prove chemical
identity, perceptual equivalence, hardware compatibility, safety or reproduction
of an odor. RFC-0007 legacy envelopes are not auto-converted. Whole files are read
into memory; this is not streaming support or a service for unbounded inputs.

Data import/Core bridging and reusable lifecycle adapters are subsequent
developer-kit work. An inspection report is not a rendering plan; an offline
plan is not device acceptance or execution.
