# Developer quickstart

Use Python 3.10 or newer. From a source checkout:

```sh
python -m venv .venv
# Activate .venv using your platform's normal command.
python -m pip install .
opensmell --help
```

This installs development main, not a newly published PyPI release.
The installed commands also work outside the checkout on your own files.

For a complete portable trial, use the [local developer kit](developer-kit.md):
extract the verified ZIP, install its two local packages and run `python try_kit.py`.
The synthetic cohort becomes two distinct plans and Python/Node software observations.

Choose a starting point:

| You have | First useful path | Proof to expect |
| --- | --- | --- |
| An OpenSmell file | `opensmell validate file.osmell`, then `inspect --json` | Structural acceptance and disclosed unknown content |
| A Node.js project and graph file | [Local JavaScript package](javascript-sdk.md) | CJS/ESM inspection and original-byte exchange into Python planning |
| A prepared CSV record | [CSV import](csv-import.md) | Core document with explicit source and raw selected cells |
| A Core file with one supported SMILES representation | [Core bridge](core-interchange.md) | Graph, explicit plan and exact original Core recovery |
| A software device implementation | [Lifecycle SDK](lifecycle-sdk.md) | Correlated completion/Stop/unknown on Python or Node |
| A classic ESP32 LED board | [Build and bench](../hardware/esp32/BENCH.md) | Compile/software checks first; physical observations recorded manually |

For a complete runnable data path, start with the synthetic CSV in the import
guide. It imports one explicit record, validates it, projects it to a graph,
maps it to a supplied device profile and exercises a software endpoint.
The synthetic labels are test data, not observations from an upstream corpus.

Source declarations, representation, mapping policy, plan, device acceptance,
observed software execution and measured physical output are separate evidence.
Do not infer a later stage from an earlier one. The SDK remains experimental;
unknown fields are retained rather than interpreted automatically.

To contribute, make one reproducible example or change with its normal entry
point, an observable result, relevant tests and accurate limitations. Run
`python -m pip install -e ".[dev]"`, then `python -m pytest`. The installed-wheel
workflow is `python -m build --wheel` followed by
`python -m tools.verify_installed_cli dist/opensmell-0.1.0-py3-none-any.whl`.
Node is needed for the full independent software proof. For firmware work, also
run the dedicated build/host bench commands. See the existing RFC maturity and
avoid claiming third-party adoption or physical compatibility from simulations.
