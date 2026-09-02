"""Tests for the OdorNet adapter."""

import pytest

from opensmell.adapters import odornet


def test_odornet_record_with_descriptors():
    record = {
        "SMILES": "CCO",
        "floral": 1,
        "fruity&vegetable": 1,
        "spice": 0,
    }

    odor = odornet.from_record(record)

    assert len(odor.representations) == 2

    chemical = odor.representations[0]
    semantic = odor.representations[1]

    assert chemical.type == "chemical"
    assert chemical.data["smiles"] == "CCO"

    assert semantic.type == "semantic"

    values = [
        descriptor["value"]
        for descriptor in semantic.data["descriptors"]
    ]

    assert values == [
        "floral",
        "fruity&vegetable",
    ]


def test_odornet_zero_labels_are_ignored():
    record = {
        "SMILES": "CCO",
        "floral": 0,
        "spice": 0,
    }

    odor = odornet.from_record(record)

    assert len(odor.representations) == 1
    assert odor.representations[0].type == "chemical"


def test_odornet_unresolved_labels_are_ignored():
    record = {
        "SMILES": "CCO",
        "floral": None,
        "spice": "",
    }

    odor = odornet.from_record(record)

    assert len(odor.representations) == 1


def test_odornet_missing_smiles_is_rejected():
    record = {
        "floral": 1,
    }

    with pytest.raises(ValueError):
        odornet.from_record(record)


def test_odornet_empty_smiles_is_rejected():
    record = {
        "SMILES": "",
        "floral": 1,
    }

    with pytest.raises(ValueError):
        odornet.from_record(record)


def test_odornet_custom_odor_id():
    record = {
        "SMILES": "CCO",
        "floral": 1,
    }

    odor = odornet.from_record(
        record,
        odor_id="urn:example:test",
    )

    assert odor.id == "urn:example:test"