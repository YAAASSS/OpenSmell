# Portable local developer-kit trial

This experimental ZIP lets another developer try the installed data/SDK/adapter
path without keeping an OpenSmell checkout. It contains local Python/JavaScript
packages, an explicitly synthetic CSV cohort and source/license declaration,
one illustrative profile, the Node software endpoint and trial scripts.
It is not a stable release or a complete offline dependency distribution.

## Obtain a kit

A successful Tests → interoperability job retains `opensmell-local-developer-kit`
for 14 days as a workflow artifact. Download that artifact from the relevant
commit's Actions run, then extract the contained `opensmell-developer-kit.zip`
into a new directory. Artifact availability depends on GitHub retention/access;
no public package registry or release is used.

Alternatively, with Node.js 22+/npm and the normal Python development dependencies
installed (`python -m pip install -e ".[dev]"` includes `setuptools` and `wheel`),
build from a checkout:

```sh
python -m tools.build_developer_kit --output dist/opensmell-developer-kit.zip
```

The builder runs the wheel build without build isolation (dependencies must
already be installed), locally packs the JS SDK with scripts disabled, and uses
an explicit file allowlist. It refuses existing output paths. The manifest records
included byte lengths/hashes, source checkout revision and whether it was dirty.
These identify the actual included artifacts; they are not signed attestations.
ZIP metadata is stable for fixed payload bytes; wheel bytes may vary across builds.
No external data download or software endpoint runs during the build.

## Try outside the checkout

Follow the extracted `START_HERE.md`: create/activate a Python environment,
install its wheel, install the local JS tarball offline with `--no-save` (preserving the included package manifest), and run:

```sh
python try_kit.py --report first-trial.json
```

Python's `jsonschema` dependencies may need your normal package index or an
independently prepared wheelhouse. They are not included; JavaScript has no runtime
dependencies. Use a new output name for every retained trial.

Expected: two accepted CSV records plus an invalid-label and absent-record refusal.
Row 1 plans channel 0 at 0.25; row 3 plans channel 1 at 0.6 for five seconds.
Both graphs pass installed JS inspection/original-byte transfer and installed
Python validation/planning; their original Core bytes are recovered intact.
The report includes correlated completed/stopped/unknown observations from both
Python and Node software endpoints. Inspecting or planning alone sends no command.
The trial explicitly launches the trusted included software endpoint; it is not
sandboxed and never addresses hardware. It verifies kit hashes before that path.

The report retains source/raw-cell context and all software observations. Temporary
intermediate files are removed. Hashes/source/license fields are declarations or
byte identities, not proof of authenticity, chemical identity or measured output.
Synthetic annotations are pipeline data; channel bindings are illustrative.
Read [CSV cohort limits](csv-batch.md), [JS limits](javascript-sdk.md),
[Core recovery limits](core-interchange.md) and [software lifecycle limits](lifecycle-sdk.md).

## Verify and readiness gates

From the development checkout:

```sh
python -m pytest tests/test_developer_kit.py -q
python -m tools.verify_developer_kit dist/opensmell-developer-kit.zip
```

The verifier extracts into a fresh directory, installs the archive's wheel into a
fresh environment and its JS package offline, then runs the normal `try_kit.py`
entry. It verifies installed import location, both records/plans/endpoints, a full
retained report, no overwrite and failure after changing included data. Test
Python dependencies are inherited from the development environment, not downloaded.

| Gate | Status / required evidence |
| --- | --- |
| Local installed Python + JS data-to-software path | Executable builder/verifier and exact-head interoperability CI |
| Experimental boundaries and source/license context | Included source manifest, original-byte hashes, explicit partial/refusal/software labels |
| Complete offline installation | Not supplied; prepare and verify a third-party dependency wheelhouse separately |
| Supported OS/runtime matrix | CI reference: Ubuntu, Python 3.10–3.13, Node 22; other hosts require observed trials |
| TypeScript consumer and browser user trial | Declarations/classic-script engine included; no separate compiler or visual trial claimed by this slice |
| Third-party adoption | Not observed; requires a developer outside this repository to record their own trial |
| Stable API/version and publication | Not declared; Draft contracts remain Draft. No tags, releases, PyPI or npm publication performed |
| Physical prototype / odor | Compilation/native bench is separate. Manual board observations remain NOT RUN; a LED cannot establish odor reproduction |

The next SDK capability is a standalone installed JavaScript lifecycle client
against the existing Python/Node software adapters. Broader reader/UI polish or a
stable release should not be inferred from this kit's successful software trial.

The kit also runs the installed JavaScript lifecycle client for both accepted
records against Python and Node endpoints, retaining full observations in
`javascript_client_observations`. Install both local npm tarballs together as
shown in START_HERE.md. The byte manifest includes both client packages and the
standalone software consumer.
