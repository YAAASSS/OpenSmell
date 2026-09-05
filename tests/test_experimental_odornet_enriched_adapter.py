"""Tests for the experimental enriched OdorNet graph adapter."""

from __future__ import annotations

import pytest

from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    ANNOTATION_SCHEME_VERSION,
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


def _record(
    **overrides: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "SMILES": "CCO",
        **{
            label: 0
            for label in ODORNET_LABELS
        },
        "PubChem_Status": "resolved",
        "PubChem_Title": "Ethanol",
        "PubChem_IUPACName": "ethanol",
        "PubChem_CanonicalSMILES": "CCO",
        "PubChem_InChIKey": (
            "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"
        ),
    }

    record.update(
        overrides
    )

    return record


def test_adapter_creates_molecule_and_annotation() -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record()
        )
    )

    assert len(
        result.graph.resources
    ) == 2

    molecule = result.graph.require(
        result.molecule_id
    )

    annotation = result.graph.require(
        result.annotation_id
    )

    assert isinstance(
        molecule,
        Molecule,
    )

    assert isinstance(
        annotation,
        Annotation,
    )


def test_molecule_preserves_original_smiles() -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record(
                SMILES="  CCO  ",
            )
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


def test_resolved_pubchem_inchikey_becomes_external_identifier() -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record()
        )
    )

    molecule = result.graph.require(
        result.molecule_id
    )

    assert isinstance(
        molecule,
        Molecule,
    )

    assert len(
        molecule.identifiers
    ) == 1

    identifier = (
        molecule.identifiers[0]
    )

    assert (
        identifier.scheme
        == PUBCHEM_INCHIKEY_SCHEME
    )

    assert (
        identifier.value
        == "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"
    )


@pytest.mark.parametrize(
    (
        "status",
        "inchikey",
    ),
    [
        (
            "not_found",
            "",
        ),
        (
            "http_400",
            "",
        ),
        (
            "resolved",
            "",
        ),
        (
            "",
            "",
        ),
        (
            None,
            None,
        ),
    ],
)
def test_missing_or_unusable_pubchem_enrichment_does_not_reject_molecule(
    status: str | None,
    inchikey: str | None,
) -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record(
                PubChem_Status=status,
                PubChem_InChIKey=inchikey,
            )
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


def test_nonresolved_status_does_not_use_inchikey() -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record(
                PubChem_Status="not_found",
                PubChem_InChIKey=(
                    "SHOULD-NOT-BE-USED"
                ),
            )
        )
    )

    molecule = result.graph.require(
        result.molecule_id
    )

    assert isinstance(
        molecule,
        Molecule,
    )

    assert molecule.identifiers == []


def test_pubchem_metadata_is_preserved_in_molecule_extra() -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record()
        )
    )

    molecule = result.graph.require(
        result.molecule_id
    )

    assert isinstance(
        molecule,
        Molecule,
    )

    assert molecule.extra[
        "provenance"
    ] == {
        "source": "OdorNet",
    }

    assert molecule.extra[
        "pubchem"
    ] == {
        "status": "resolved",
        "title": "Ethanol",
        "iupac_name": "ethanol",
        "canonical_smiles": "CCO",
    }


def test_annotation_references_molecule() -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record()
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


def test_annotation_uses_odornet_semantic_scheme() -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record()
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
        annotation.scheme.id
        == ANNOTATION_SCHEME_ID
    )

    assert (
        annotation.scheme.version
        == ANNOTATION_SCHEME_VERSION
    )


def test_annotation_contains_all_odornet_labels() -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record()
        )
    )

    annotation = result.graph.require(
        result.annotation_id
    )

    assert isinstance(
        annotation,
        Annotation,
    )

    annotations = (
        annotation.data[
            "annotations"
        ]
    )

    assert len(
        annotations
    ) == len(
        ODORNET_LABELS
    )

    assert [
        item["value"]
        for item in annotations
    ] == list(
        ODORNET_LABELS
    )


def test_semantic_states_are_preserved() -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record(
                **{
                    "sweety&gourmand": 1,
                    "floral": 0,
                    "fruity&vegetable": None,
                }
            )
        )
    )

    annotation = result.graph.require(
        result.annotation_id
    )

    assert isinstance(
        annotation,
        Annotation,
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


@pytest.mark.parametrize(
    (
        "raw",
        "expected",
    ),
    [
        (
            "1.0",
            "present",
        ),
        (
            "0.0",
            "absent",
        ),
        (
            "",
            "unknown",
        ),
        (
            "   ",
            "unknown",
        ),
    ],
)
def test_adapter_accepts_raw_csv_style_semantic_values(
    raw: str,
    expected: str,
) -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record(
                floral=raw,
            )
        )
    )

    annotation = result.graph.require(
        result.annotation_id
    )

    assert isinstance(
        annotation,
        Annotation,
    )

    states = {
        item["value"]: item["state"]
        for item
        in annotation.data[
            "annotations"
        ]
    }

    assert (
        states["floral"]
        == expected
    )


def test_resource_ids_are_deterministic() -> None:
    first = (
        enriched_odornet_record_to_graph(
            _record()
        )
    )

    second = (
        enriched_odornet_record_to_graph(
            _record()
        )
    )

    assert (
        first.molecule_id
        == second.molecule_id
    )

    assert (
        first.annotation_id
        == second.annotation_id
    )


def test_pubchem_changes_do_not_change_resource_identity() -> None:
    first = (
        enriched_odornet_record_to_graph(
            _record()
        )
    )

    second = (
        enriched_odornet_record_to_graph(
            _record(
                PubChem_Status="not_found",
                PubChem_Title="Different",
                PubChem_IUPACName="Different",
                PubChem_CanonicalSMILES="Different",
                PubChem_InChIKey="",
            )
        )
    )

    assert (
        first.molecule_id
        == second.molecule_id
    )

    assert (
        first.annotation_id
        == second.annotation_id
    )


def test_different_smiles_produces_different_resource_ids() -> None:
    first = (
        enriched_odornet_record_to_graph(
            _record(
                SMILES="CCO",
            )
        )
    )

    second = (
        enriched_odornet_record_to_graph(
            _record(
                SMILES="CCN",
            )
        )
    )

    assert (
        first.molecule_id
        != second.molecule_id
    )

    assert (
        first.annotation_id
        != second.annotation_id
    )


@pytest.mark.parametrize(
    "smiles",
    [
        "",
        "   ",
    ],
)
def test_empty_smiles_is_rejected(
    smiles: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="SMILES must be non-empty",
    ):
        enriched_odornet_record_to_graph(
            _record(
                SMILES=smiles,
            )
        )


def test_non_string_smiles_is_rejected() -> None:
    with pytest.raises(
        TypeError,
        match="SMILES must be a string",
    ):
        enriched_odornet_record_to_graph(
            _record(
                SMILES=123,
            )
        )


def test_invalid_semantic_value_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "unexpected OdorNet "
            "semantic value"
        ),
    ):
        enriched_odornet_record_to_graph(
            _record(
                floral="0.5",
            )
        )


def test_annotation_provenance_is_preserved() -> None:
    result = (
        enriched_odornet_record_to_graph(
            _record()
        )
    )

    annotation = result.graph.require(
        result.annotation_id
    )

    assert isinstance(
        annotation,
        Annotation,
    )

    assert annotation.extra[
        "provenance"
    ] == {
        "source": "OdorNet",
    }