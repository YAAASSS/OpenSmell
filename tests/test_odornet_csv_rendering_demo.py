"""Tests for the enriched OdorNet CSV rendering demo helpers."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from opensmell.adapters.odornet import (
    ODORNET_LABELS,
)
from opensmell.experimental.annotation import (
    Annotation,
)
from opensmell.experimental.molecule import (
    Molecule,
)
from opensmell.experimental.odornet_enriched_adapter import (
    PUBCHEM_INCHIKEY_SCHEME,
    enriched_odornet_record_to_graph,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEMO_PATH = (
    PROJECT_ROOT
    / "examples"
    / "odornet_csv_rendering_demo.py"
)


def _load_demo_module() -> ModuleType:
    """Load the example script directly from its file path."""

    spec = importlib.util.spec_from_file_location(
        "odornet_csv_rendering_demo",
        DEMO_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "could not load OdorNet CSV rendering demo"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


demo = _load_demo_module()

parse_odornet_value = (
    demo.parse_odornet_value
)

load_row = demo.load_row

display_value = demo.display_value


def _write_csv(
    path: Path,
    *,
    fieldnames: list[str] | None = None,
    rows: list[dict[str, object]] | None = None,
) -> None:
    if fieldnames is None:
        fieldnames = [
            "SMILES",
            *ODORNET_LABELS,
            "PubChem_Status",
            "PubChem_Title",
            "PubChem_IUPACName",
            "PubChem_CanonicalSMILES",
            "PubChem_InChIKey",
        ]

    if rows is None:
        rows = []

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
        writer.writerows(
            rows
        )


def _complete_row(
    **overrides: object,
) -> dict[str, object]:
    row: dict[str, object] = {
        "SMILES": "CCO",
        **{
            label: "0.0"
            for label in ODORNET_LABELS
        },
        "PubChem_Status": "resolved",
        "PubChem_Title": "Example molecule",
        "PubChem_IUPACName": "example",
        "PubChem_CanonicalSMILES": "CCO",
        "PubChem_InChIKey": (
            "EXAMPLE-INCHIKEY"
        ),
    }

    row.update(
        overrides
    )

    return row


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", 1),
        ("1.0", 1),
        (" 1.0 ", 1),
        ("0", 0),
        ("0.0", 0),
        (" 0.0 ", 0),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_parse_odornet_value(
    raw: str | None,
    expected: int | None,
) -> None:
    assert (
        parse_odornet_value(
            raw
        )
        == expected
    )


def test_parse_odornet_value_rejects_unexpected_value() -> None:
    with pytest.raises(
        ValueError,
        match="unexpected OdorNet label value",
    ):
        parse_odornet_value(
            "0.5"
        )


def test_load_row_converts_real_odornet_cell_semantics(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    row = _complete_row(
        **{
            "sweety&gourmand": "1.0",
            "floral": "0.0",
            "fruity&vegetable": "",
        }
    )

    _write_csv(
        path,
        rows=[row],
    )

    record, raw_row = load_row(
        path,
        0,
    )

    assert (
        record["SMILES"]
        == "CCO"
    )

    assert (
        record["sweety&gourmand"]
        == 1
    )

    assert (
        record["floral"]
        == 0
    )

    assert (
        record["fruity&vegetable"]
        is None
    )

    assert (
        raw_row["PubChem_Status"]
        == "resolved"
    )

    assert (
        raw_row["PubChem_Title"]
        == "Example molecule"
    )


def test_load_row_includes_pubchem_enrichment_in_adapter_record(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    _write_csv(
        path,
        rows=[
            _complete_row(
                PubChem_Status="resolved",
                PubChem_Title="Ethanol",
                PubChem_IUPACName="ethanol",
                PubChem_CanonicalSMILES="CCO",
                PubChem_InChIKey=(
                    "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"
                ),
            )
        ],
    )

    record, _ = load_row(
        path,
        0,
    )

    assert (
        record["PubChem_Status"]
        == "resolved"
    )

    assert (
        record["PubChem_Title"]
        == "Ethanol"
    )

    assert (
        record["PubChem_IUPACName"]
        == "ethanol"
    )

    assert (
        record["PubChem_CanonicalSMILES"]
        == "CCO"
    )

    assert (
        record["PubChem_InChIKey"]
        == "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"
    )


def test_loaded_row_produces_structured_pubchem_identifier(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    _write_csv(
        path,
        rows=[
            _complete_row(
                PubChem_Status="resolved",
                PubChem_InChIKey=(
                    "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"
                ),
            )
        ],
    )

    record, _ = load_row(
        path,
        0,
    )

    result = (
        enriched_odornet_record_to_graph(
            record
        )
    )

    molecule = result.graph.require(
        result.molecule_id
    )

    assert isinstance(
        molecule,
        Molecule,
    )

    identifiers = [
        identifier
        for identifier
        in molecule.identifiers
        if (
            identifier.scheme
            == PUBCHEM_INCHIKEY_SCHEME
        )
    ]

    assert len(
        identifiers
    ) == 1

    assert (
        identifiers[0].value
        == "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"
    )


def test_loaded_row_produces_annotation_referencing_molecule(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    _write_csv(
        path,
        rows=[
            _complete_row(
                **{
                    "sweety&gourmand": "1.0",
                    "floral": "0.0",
                    "fruity&vegetable": "",
                }
            )
        ],
    )

    record, _ = load_row(
        path,
        0,
    )

    result = (
        enriched_odornet_record_to_graph(
            record
        )
    )

    annotation = result.graph.require(
        result.annotation_id
    )

    assert isinstance(
        annotation,
        Annotation,
    )

    assert (
        annotation.subject.resource_id
        == result.molecule_id
    )

    states = {
        item["value"]: item["state"]
        for item
        in annotation.data[
            "annotations"
        ]
    }

    assert (
        states["sweety&gourmand"]
        == "present"
    )

    assert (
        states["floral"]
        == "absent"
    )

    assert (
        states["fruity&vegetable"]
        == "unknown"
    )


def test_loaded_row_without_inchikey_remains_valid(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    _write_csv(
        path,
        rows=[
            _complete_row(
                PubChem_Status="resolved",
                PubChem_InChIKey="",
            )
        ],
    )

    record, _ = load_row(
        path,
        0,
    )

    result = (
        enriched_odornet_record_to_graph(
            record
        )
    )

    molecule = result.graph.require(
        result.molecule_id
    )

    assert isinstance(
        molecule,
        Molecule,
    )

    assert molecule.smiles == "CCO"
    assert molecule.identifiers == []


def test_load_row_selects_requested_zero_based_row(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    _write_csv(
        path,
        rows=[
            _complete_row(
                SMILES="CCO",
            ),
            _complete_row(
                SMILES="CCN",
            ),
        ],
    )

    record, _ = load_row(
        path,
        1,
    )

    assert (
        record["SMILES"]
        == "CCN"
    )


def test_load_row_strips_smiles(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    _write_csv(
        path,
        rows=[
            _complete_row(
                SMILES="  CCO  ",
            ),
        ],
    )

    record, _ = load_row(
        path,
        0,
    )

    assert (
        record["SMILES"]
        == "CCO"
    )


def test_load_row_rejects_negative_row_index(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    _write_csv(
        path,
        rows=[
            _complete_row(),
        ],
    )

    with pytest.raises(
        ValueError,
        match="--row must be zero or greater",
    ):
        load_row(
            path,
            -1,
        )


def test_load_row_rejects_missing_file(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "missing.csv"
    )

    with pytest.raises(
        FileNotFoundError,
        match="OdorNet CSV not found",
    ):
        load_row(
            path,
            0,
        )


def test_load_row_rejects_missing_required_column(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    fieldnames = [
        "SMILES",
        *[
            label
            for label in ODORNET_LABELS
            if label != "floral"
        ],
    ]

    _write_csv(
        path,
        fieldnames=fieldnames,
        rows=[],
    )

    with pytest.raises(
        ValueError,
        match="missing required column",
    ):
        load_row(
            path,
            0,
        )


def test_load_row_rejects_out_of_range_row(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    _write_csv(
        path,
        rows=[
            _complete_row(),
        ],
    )

    with pytest.raises(
        IndexError,
        match="does not exist",
    ):
        load_row(
            path,
            1,
        )


def test_load_row_rejects_empty_smiles(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    _write_csv(
        path,
        rows=[
            _complete_row(
                SMILES="",
            ),
        ],
    )

    with pytest.raises(
        ValueError,
        match="empty SMILES",
    ):
        load_row(
            path,
            0,
        )


def test_load_row_rejects_invalid_label_value(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "odornet.csv"
    )

    _write_csv(
        path,
        rows=[
            _complete_row(
                floral="0.5",
            ),
        ],
    )

    with pytest.raises(
        ValueError,
        match="unexpected OdorNet label value",
    ):
        load_row(
            path,
            0,
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "resolved",
            "resolved",
        ),
        (
            "  resolved  ",
            "resolved",
        ),
        (
            "",
            "<blank>",
        ),
        (
            "   ",
            "<blank>",
        ),
    ],
)
def test_display_value(
    value: str,
    expected: str,
) -> None:
    row = {
        "PubChem_Status": value,
    }

    assert (
        display_value(
            row,
            "PubChem_Status",
        )
        == expected
    )


def test_display_value_reports_missing_field() -> None:
    assert (
        display_value(
            {},
            "PubChem_Status",
        )
        == "<blank>"
    )