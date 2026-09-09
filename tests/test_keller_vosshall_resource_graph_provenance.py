"""Tests for Keller/Vosshall ResourceGraph provenance."""

from __future__ import annotations

import pandas as pd

from opensmell.experimental.provenance import (
    provenance_from_dict,
    provenance_to_dict,
)
from opensmell.experimental.resources import (
    ObservationTarget,
    Stimulus,
)
from tools.analyze_keller_vosshall_resource_graph import (
    build_observations,
)


def _build_one_observation(*, source_row: int = 2500):
    dataframe = pd.DataFrame(
        [
            {
                "subject": 3,
                "cid": 61918,
                "dilution": "1/1,000",
                "detection": "I can smell something",
                "recognition": None,
                "intensity": 50,
                "pleasantness": 60,
                "familiarity": 70,
                "FLOWER": 26,
                "GRASS": 38,
                "WOOD": 89,
            }
        ],
        index=[source_row],
    )

    stimulus = Stimulus(
        id="stimulus-1",
    )
    target = ObservationTarget(
        id="target-1",
    )

    observations = build_observations(
        dataframe,
        subject_column="subject",
        cid_column="cid",
        dilution_column="dilution",
        detection_column="detection",
        recognition_column="recognition",
        intensity_column="intensity",
        pleasantness_column="pleasantness",
        familiarity_column="familiarity",
        descriptor_columns={
            "FLOWER": "FLOWER",
            "GRASS": "GRASS",
            "WOOD": "WOOD",
        },
        stimuli={
            ("61918", "1/1,000"): stimulus,
        },
        targets={
            "3": target,
        },
    )

    assert len(observations) == 1
    return observations[0]


def test_observation_has_structured_source_provenance() -> None:
    observation = _build_one_observation()

    assert observation.extra["provenance"] == {
        "source": {
            "name": "Keller/Vosshall",
        },
        "record": {
            "identity": {
                "source_row": 2500,
            }
        },
        "derivation": {
            "method": (
                "tools."
                "analyze_keller_vosshall_"
                "resource_graph."
                "build_observations"
            )
        },
    }


def test_provenance_does_not_duplicate_observation_semantics() -> None:
    observation = _build_one_observation()
    identity = observation.extra[
        "provenance"
    ]["record"]["identity"]

    assert set(identity) == {"source_row"}
    assert "subject" not in identity
    assert "cid" not in identity
    assert "dilution" not in identity


def test_keller_provenance_round_trips_through_model() -> None:
    observation = _build_one_observation()
    document = observation.extra["provenance"]

    assert provenance_to_dict(
        provenance_from_dict(document)
    ) == document


def test_source_row_changes_provenance_without_changing_source() -> None:
    first = _build_one_observation(
        source_row=2500,
    )
    second = _build_one_observation(
        source_row=2501,
    )

    first_provenance = first.extra["provenance"]
    second_provenance = second.extra["provenance"]

    assert (
        first_provenance["source"]
        == second_provenance["source"]
    )
    assert (
        first_provenance["record"]["identity"]["source_row"]
        == 2500
    )
    assert (
        second_provenance["record"]["identity"]["source_row"]
        == 2501
    )


def test_source_release_is_not_invented() -> None:
    observation = _build_one_observation()
    source = observation.extra["provenance"]["source"]

    assert source == {
        "name": "Keller/Vosshall",
    }
    assert "version" not in source
    assert "identifier" not in source
