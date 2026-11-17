# Clean offline installation target

The optional experimental offline kit includes a pinned Python runtime dependency
wheelhouse, hashes, source URLs and license texts. First target: **CPython 3.12,
Linux x86_64, glibc >=2.28**. Python with venv/ensurepip and Node.js 22+/npm must
already exist on the consumer machine; their installers are not bundled. No
Windows, macOS, ARM or other Python version compatibility is implied.

## Prepare explicitly while connected

From the development checkout with its normal build dependencies installed:

```sh
python -m tools.offline_dependencies --output /new/path/dependencies
python -m tools.build_developer_kit --wheelhouse /new/path/dependencies \
  --output dist/opensmell-offline-linux-cp312.zip
```

Acquisition explicitly downloads six pinned binary wheels from public PyPI,
compares each downloaded SHA-256 to the release JSON metadata and retains the
release/download URLs, metadata, dependency requirements and license texts.
The inventory and every wheel enter the kit byte manifest. No source build,
registry upload, tag or release occurs. Failed acquisitions leave their directory
for inspection; they are not silently resumed or overwritten. The builder itself
does not acquire dependencies. Its original no-wheelhouse path remains available.

Pins: jsonschema4.26.0, attrs26.1.0, jsonschema-specifications2025.9.1,
referencing0.37.0, rpds-py2026.9.1, typing-extensions4.16.0. Five dependency
license expressions are MIT, typing-extensions is PSF-2.0; actual wheel license
texts and metadata are retained in `wheelhouse/inventory.json` and inside wheels.
Hashes provide byte identity, not signatures or a security/chemical authenticity
audit. Source/license declarations remain inspectable rather than inferred.

## Install and try without a package index

Extract into a new directory on the declared target:

```sh
python install_offline.py --venv .venv
. .venv/bin/activate
npm install --offline --ignore-scripts --no-save --no-audit --no-fund --package-lock=false ./packages/opensmell-graph-reader-0.1.0-experimental.0.tgz ./packages/opensmell-lifecycle-client-0.1.0-experimental.0.tgz
python try_kit.py --report first-trial.json
```

The installer checks target, kit manifest and wheel inventory before creating
a **new** venv with `system_site_packages=False`. pip uses `--isolated`,
`--no-index`, `--no-cache-dir`, local find-links, binary wheels and
`--require-hashes`; all seven packages including OpenSmell have exact versions
and hashes in `offline-requirements.txt`. `pip check` verifies dependency closure.
There is no automatic online fallback. Existing environments refuse replacement;
failed partial environments require an explicitly chosen new path.

`START_HERE.md`, `PERCEPTUAL_IMPORT.md` and `CALLER_GRAPH.md` describe the normal
categorical/perceptual import, explicit-profile plan, caller graph and opt-in
software trials. Default kit self-test uses synthetic data and fixed software
endpoints. Caller graphs are passive unless `--simulate` is explicit. Original
bytes, unknown fields, partial inspection, plan refusals and unknown execution
outcomes retain their previous meanings. No physical hardware or odor proof.

## Executable installation proof

```sh
python -m tools.verify_developer_kit dist/opensmell-offline-linux-cp312.zip --offline
```

The verifier extracts outside the checkout, uses a clean environment, checks the
installed module location and disabled user site, and exercises the full original
kit plus categorical/perceptual caller graphs, changed profiles, both clients and
both Python/Node endpoints. Report collisions and altered kit data still refuse.
The offline CI job executes this verifier inside a Linux network namespace with
no external network interfaces, **after** connected acquisition/build. This
separates acquisition from demonstrated offline installation and software use.
It is not an independent third-party adoption trial. The artifact is retained for
14 days, not published as a stable release.

This closes the first clean/offline target slice; expanding platform coverage or
adding dependencies needs its own clean trial. SDK/format experiments and manual
hardware/olfactory validation remain separate work.
