"""Tests for the experimental Keller/Vosshall adapter."""

import pytest

from opensmell.adapters.keller_vosshall import (
    SCHEME_ID,
    measurements_from_record,
    representation_from_record,
)
from opensmell.schemes.perceptual_measurements import validate


def test_global_measurements_are_preserved() -> None:
    record = {
        "HOW STRONG IS THE SMELL?": 61,
        "HOW PLEASANT IS THE SMELL?": 45,
        "HOW FAMILIAR IS THE SMELL?": 73,
    }

    representation = representation_from_record(record)

    assert representation is not None
    assert representation.type == "perceptual"
    assert representation.scheme.id == SCHEME_ID

    measurements = {
        measurement["property"]: measurement
        for measurement in representation.data["measurements"]
    }

    assert measurements["intensity"]["value"] == 61
    assert measurements["pleasantness"]["value"] == 45
    assert measurements["familiarity"]["value"] == 73

    assert measurements["intensity"]["scale"] == {
        "min": 0,
        "max": 100,
    }


def test_quantitative_descriptor_is_preserved() -> None:
    record = {
        "FLOWER": 73,
        "SWEET": 21,
    }

    measurements = measurements_from_record(record)

    values = {
        measurement["property"]: measurement["value"]
        for measurement in measurements
    }

    assert values["flower"] == 73
    assert values["sweet"] == 21


def test_missing_descriptor_is_not_converted_to_zero() -> None:
    record = {
        "FLOWER": None,
        "SWEET": 0,
    }

    measurements = measurements_from_record(record)

    values = {
        measurement["property"]: measurement["value"]
        for measurement in measurements
    }

    assert "flower" not in values
    assert values["sweet"] == 0


def test_row_without_measurements_returns_none() -> None:
    representation = representation_from_record({})

    assert representation is None


def test_scheme_validator_accepts_measurements() -> None:
    data = {
        "measurements": [
            {
                "property": "intensity",
                "value": 61,
                "scale": {
                    "min": 0,
                    "max": 100,
                },
            }
        ]
    }

    validate(data)


def test_scheme_validator_rejects_out_of_range_value() -> None:
    data = {
        "measurements": [
            {
                "property": "intensity",
                "value": 101,
                "scale": {
                    "min": 0,
                    "max": 100,
                },
            }
        ]
    }

    with pytest.raises(Exception):
        validate(data)