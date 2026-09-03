"""Tests for experimental RFC-0004 OdorNet annotations."""

from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    ODORNET_LABELS,
    from_record_with_annotations,
)


def test_odornet_annotation_states() -> None:
    """OdorNet values preserve present, absent, and unknown states."""

    record = {
        "SMILES": "CCO",
        "floral": 1,
        "spice": 0,
        "woody&mossy": "",
    }

    odor = from_record_with_annotations(
        record,
        odor_id="test-odor",
    )

    representation = odor.representations[1]

    assert representation.type == "semantic"

    assert (
        representation.scheme.id
        == ANNOTATION_SCHEME_ID
    )

    annotations = {
        annotation["value"]: annotation["state"]
        for annotation
        in representation.data["annotations"]
    }

    assert annotations["floral"] == "present"
    assert annotations["spice"] == "absent"
    assert annotations["woody&mossy"] == "unknown"


def test_all_odornet_labels_are_preserved() -> None:
    """Every OdorNet category must produce one annotation."""

    record = {
        "SMILES": "CCO",
    }

    odor = from_record_with_annotations(
        record
    )

    representation = odor.representations[1]

    annotations = representation.data[
        "annotations"
    ]

    assert len(annotations) == len(
        ODORNET_LABELS
    )

    assert {
        annotation["value"]
        for annotation in annotations
    } == set(
        ODORNET_LABELS
    )


def test_annotation_provenance() -> None:
    """Experimental annotations retain OdorNet provenance."""

    record = {
        "SMILES": "CCO",
        "floral": 1,
    }

    odor = from_record_with_annotations(
        record
    )

    representation = odor.representations[1]

    assert representation.extra[
        "provenance"
    ] == {
        "source": "OdorNet",
    }