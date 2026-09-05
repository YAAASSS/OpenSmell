"""Cross-language enriched OdorNet interoperability tests.

These tests exercise the complete experimental interoperability path:

    OdorNet-shaped CSV
        -> OpenSmell Python producer
        -> GenericResourceGraph JSON
        -> independent JavaScript consumer

The fixture is intentionally small and controlled. It does not depend on the
full enriched OdorNet dataset, while still exercising the same production
adapter and serialization path used by the real-data demonstration.

This is experimental and non-normative.
"""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType

import pytest

from opensmell.adapters.odornet import (
    ODORNET_LABELS,
)


ROOT = Path(__file__).resolve().parents[1]

GENERATOR_PATH = (
    ROOT
    / "tools"
    / "generate_odornet_enriched_interop.py"
)

VERIFIER_PATH = (
    ROOT
    / "tools"
    / "verify_odornet_enriched_interop.js"
)

PUBCHEM_FIELDS = (
    "PubChem_Status",
    "PubChem_Title",
    "PubChem_IUPACName",
    "PubChem_CanonicalSMILES",
    "PubChem_InChIKey",
)

EXPECTED_SMILES = "CCO"

EXPECTED_INCHIKEY = (
    "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"
)

EXPECTED_STATES = {
    "animalic&ambery": "absent",
    "sweety&gourmand": "present",
    "floral": "absent",
    "fruity&vegetable": "unknown",
    "pungent&disagreeable": "absent",
    "green&herbal": "present",
    "nutty": "absent",
    "woody&mossy": "absent",
    "resinous&balsamic": "absent",
    "cooked": "unknown",
    "odorless": "absent",
    "spice": "present",
}


def _load_generator_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "generate_odornet_enriched_interop",
        GENERATOR_PATH,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "could not load enriched OdorNet "
            "interop generator"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


generator = _load_generator_module()


def _write_fixture_csv(
    path: Path,
) -> None:
    row: dict[str, str] = {
        "SMILES": EXPECTED_SMILES,
        **{
            label: "0.0"
            for label in ODORNET_LABELS
        },
        "PubChem_Status": "resolved",
        "PubChem_Title": "Ethanol",
        "PubChem_IUPACName": "ethanol",
        "PubChem_CanonicalSMILES": "CCO",
        "PubChem_InChIKey": EXPECTED_INCHIKEY,
    }

    row["sweety&gourmand"] = "1.0"
    row["green&herbal"] = "1.0"
    row["spice"] = "1.0"

    row["fruity&vegetable"] = ""
    row["cooked"] = ""

    fieldnames = [
        "SMILES",
        *ODORNET_LABELS,
        *PUBCHEM_FIELDS,
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerow(
            row
        )


@pytest.fixture
def interop_paths(
    tmp_path: Path,
) -> tuple[Path, Path]:
    csv_path = (
        tmp_path
        / "odornet_fixture.csv"
    )

    output_path = (
        tmp_path
        / "interop.json"
    )

    _write_fixture_csv(
        csv_path
    )

    return (
        csv_path,
        output_path,
    )


def test_generator_builds_expected_independent_fixture(
    interop_paths: tuple[Path, Path],
) -> None:
    csv_path, _ = interop_paths

    document = generator.build_document(
        csv_path,
        0,
    )

    assert (
        document["interop_test"]
        == (
            "org.opensmell.experimental."
            "odornet-enriched.interop"
        )
    )

    assert (
        document["version"]
        == "0.1"
    )

    assert (
        document["source"]["dataset"]
        == "OdorNet"
    )

    assert (
        document["source"]["row"]
        == 0
    )

    expected = document[
        "expected"
    ]

    assert (
        expected["smiles"]
        == EXPECTED_SMILES
    )

    assert (
        expected["pubchem_inchikey"]
        == EXPECTED_INCHIKEY
    )

    assert (
        expected["semantic_states"]
        == EXPECTED_STATES
    )

    graph = document[
        "graph"
    ]

    assert (
        graph["format"]
        == (
            "org.opensmell.experimental."
            "generic-resource-graph"
        )
    )

    assert (
        graph["version"]
        == "0.1"
    )

    assert (
        len(
            graph["resources"]
        )
        == 2
    )


def test_generator_command_writes_interop_document(
    interop_paths: tuple[Path, Path],
) -> None:
    csv_path, output_path = (
        interop_paths
    )

    result = subprocess.run(
        [
            sys.executable,
            str(
                GENERATOR_PATH
            ),
            "--csv",
            str(
                csv_path
            ),
            "--row",
            "0",
            "--output",
            str(
                output_path
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert (
        result.returncode
        == 0
    ), (
        "generator failed\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    assert output_path.is_file()

    document = json.loads(
        output_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        document["expected"]["smiles"]
        == EXPECTED_SMILES
    )

    assert (
        document[
            "expected"
        ][
            "pubchem_inchikey"
        ]
        == EXPECTED_INCHIKEY
    )

    assert (
        document[
            "expected"
        ][
            "semantic_states"
        ]
        == EXPECTED_STATES
    )

    assert (
        "Resources: 2"
        in result.stdout
    )


def test_independent_javascript_consumer_understands_python_output(
    interop_paths: tuple[Path, Path],
) -> None:
    node = shutil.which(
        "node"
    )

    if node is None:
        pytest.skip(
            "Node.js is required for "
            "cross-language interoperability test"
        )

    csv_path, output_path = (
        interop_paths
    )

    document = generator.build_document(
        csv_path,
        0,
    )

    output_path.write_text(
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            node,
            str(
                VERIFIER_PATH
            ),
            "--input",
            str(
                output_path
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert (
        result.returncode
        == 0
    ), (
        "JavaScript verifier failed\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    expected_output = (
        "PASS GenericResourceGraph format/version",
        "PASS Molecule 0.1 recognition",
        "PASS SMILES preservation",
        "PASS PubChem InChIKey preservation",
        "PASS Annotation 0.1 recognition",
        "PASS Annotation subject resolution",
        "PASS 12 OdorNet semantic states",
        "PASS JavaScript graph round-trip preservation",
    )

    for message in expected_output:
        assert (
            message
            in result.stdout
        )

    assert (
        EXPECTED_SMILES
        in result.stdout
    )

    assert (
        EXPECTED_INCHIKEY
        in result.stdout
    )

    assert (
        "SUCCESS: independent JavaScript consumer "
        "understood the real OpenSmell ResourceGraph "
        "generated from enriched OdorNet."
        in result.stdout
    )


def test_javascript_consumer_detects_semantic_corruption(
    interop_paths: tuple[Path, Path],
) -> None:
    node = shutil.which(
        "node"
    )

    if node is None:
        pytest.skip(
            "Node.js is required for "
            "cross-language interoperability test"
        )

    csv_path, output_path = (
        interop_paths
    )

    document = generator.build_document(
        csv_path,
        0,
    )

    annotation = next(
        resource
        for resource
        in document["graph"]["resources"]
        if (
            resource["type"]
            == "org.opensmell.annotation"
        )
    )

    annotation[
        "data"
    ][
        "annotations"
    ][1][
        "state"
    ] = "absent"

    output_path.write_text(
        json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            node,
            str(
                VERIFIER_PATH
            ),
            "--input",
            str(
                output_path
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert (
        result.returncode
        != 0
    )

    combined_output = (
        result.stdout
        + result.stderr
    )

    assert (
        "sweety&gourmand"
        in combined_output
    )

    assert (
        "expected state present"
        in combined_output
    )