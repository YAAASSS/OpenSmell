"""Tests for the experimental scientific provenance model."""

from __future__ import annotations

import pytest

from opensmell.experimental.provenance import (
    Provenance,
    ProvenanceDerivation,
    ProvenanceRecord,
    ProvenanceSource,
    SourceIdentifier,
    provenance_from_dict,
    provenance_to_dict,
)


def test_minimal_provenance() -> None:
    provenance = Provenance(
        source=ProvenanceSource(
            name="Example Dataset",
        )
    )

    assert provenance_to_dict(
        provenance
    ) == {
        "source": {
            "name": "Example Dataset",
        }
    }


def test_odornet_style_provenance() -> None:
    provenance = Provenance(
        source=ProvenanceSource(
            name="OdorNet",
            version="1.0.0",
            identifier=SourceIdentifier(
                scheme="doi",
                value="10.example/odornet",
            ),
        ),
        record=ProvenanceRecord(
            identity={
                "smiles": "CCO",
            }
        ),
        derivation=ProvenanceDerivation(
            method="opensmell.adapter.odornet",
        ),
    )

    document = provenance_to_dict(
        provenance
    )

    assert document["source"]["name"] == "OdorNet"
    assert document["source"]["version"] == "1.0.0"
    assert document["record"]["identity"] == {
        "smiles": "CCO",
    }
    assert document["derivation"]["method"] == (
        "opensmell.adapter.odornet"
    )


def test_keller_style_record_identity_accepts_row_number() -> None:
    provenance = Provenance(
        source=ProvenanceSource(
            name="Keller/Vosshall",
        ),
        record=ProvenanceRecord(
            identity={
                "row": 46426,
                "subject": "47",
                "dilution": "1/10",
            }
        ),
    )

    assert provenance_to_dict(
        provenance
    )["record"]["identity"]["row"] == 46426


def test_round_trip_preserves_extensions() -> None:
    document = {
        "source": {
            "name": "Example Dataset",
            "version": "2026.1",
            "identifier": {
                "scheme": "doi",
                "value": "10.example/dataset",
                "resolver": "example",
            },
            "archive": {
                "checksum": "abc",
            },
        },
        "record": {
            "identity": {
                "row": 12,
            },
            "source_file": "data.csv",
        },
        "derivation": {
            "method": "example.importer",
            "mapping": {
                "mode": "exact",
            },
        },
        "extension": {
            "value": True,
        },
    }

    provenance = provenance_from_dict(
        document
    )

    assert provenance_to_dict(
        provenance
    ) == document


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_provenance_rejects_non_finite_numbers(
    value: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="JSON numeric values must be finite",
    ):
        ProvenanceRecord(
            identity={
                "value": value,
            }
        )


def test_provenance_record_identity_must_be_non_empty() -> None:
    with pytest.raises(
        ValueError,
        match="must be non-empty",
    ):
        ProvenanceRecord(
            identity={}
        )


def test_source_name_must_be_non_empty() -> None:
    with pytest.raises(ValueError):
        ProvenanceSource(
            name="",
        )


def test_source_identifier_requires_non_empty_fields() -> None:
    with pytest.raises(ValueError):
        SourceIdentifier(
            scheme="",
            value="identifier",
        )

    with pytest.raises(ValueError):
        SourceIdentifier(
            scheme="doi",
            value="",
        )


def test_derivation_method_must_be_non_empty() -> None:
    with pytest.raises(ValueError):
        ProvenanceDerivation(
            method="",
        )


def test_serialization_returns_independent_data() -> None:
    provenance = Provenance(
        source=ProvenanceSource(
            name="Example Dataset",
        ),
        record=ProvenanceRecord(
            identity={
                "row": 1,
            }
        ),
    )

    document = provenance_to_dict(
        provenance
    )
    document["record"]["identity"]["row"] = 999

    assert provenance.record is not None
    assert provenance.record.identity["row"] == 1
