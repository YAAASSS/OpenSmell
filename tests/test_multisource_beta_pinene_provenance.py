"""Provenance tests for the multi-source (-)-beta-pinene example."""

from __future__ import annotations

import json
from pathlib import Path

from opensmell.experimental.provenance import (
    provenance_from_dict,
    provenance_to_dict,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    PROJECT_ROOT
    / "examples"
    / "multisource_beta_pinene.osmell"
)


def _load_fixture() -> dict:
    return json.loads(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )


def _resources_by_type(document: dict) -> dict[str, list[dict]]:
    resources: dict[str, list[dict]] = {}
    for resource in document["resources"]:
        resources.setdefault(resource["type"], []).append(resource)
    return resources


def test_multisource_fixture_has_separate_source_provenance() -> None:
    document = _load_fixture()
    resources = _resources_by_type(document)

    molecule = resources["org.opensmell.molecule"][0]
    annotation = resources["org.opensmell.annotation"][0]
    observation = resources["observation"][0]

    molecule_provenance = molecule["provenance"]
    annotation_provenance = annotation["provenance"]
    observation_provenance = observation["provenance"]

    assert molecule_provenance["source"] == {"name": "OdorNet"}
    assert annotation_provenance["source"] == {"name": "OdorNet"}
    assert observation_provenance["source"] == {
        "name": "Keller/Vosshall"
    }


def test_multisource_keller_record_identity_is_only_source_row() -> None:
    document = _load_fixture()
    resources = _resources_by_type(document)
    observation = resources["observation"][0]

    provenance = observation["provenance"]

    assert provenance["record"]["identity"] == {
        "source_row": 46426
    }
    assert "subject" not in provenance["record"]["identity"]
    assert "cid" not in provenance["record"]["identity"]
    assert "dilution" not in provenance["record"]["identity"]


def test_multisource_keller_provenance_round_trips_model() -> None:
    document = _load_fixture()
    resources = _resources_by_type(document)
    observation = resources["observation"][0]

    raw = observation["provenance"]
    parsed = provenance_from_dict(raw)

    assert provenance_to_dict(parsed) == raw


def test_multisource_identity_match_remains_integration_metadata() -> None:
    document = _load_fixture()
    resources = _resources_by_type(document)

    stimulus = resources["stimulus"][0]
    observation = resources["observation"][0]

    assert stimulus["identity_match"] == {
        "method": "exact_pubchem_inchikey",
        "inchikey": "WTARULDDTDQWMU-IUCAKERBSA-N",
    }

    provenance_identity = (
        observation["provenance"]["record"]["identity"]
    )
    assert "inchikey" not in provenance_identity
    assert stimulus["identity_match"]["inchikey"] not in (
        str(provenance_identity)
    )


def test_multisource_does_not_duplicate_keller_provenance() -> None:
    document = _load_fixture()
    resources = _resources_by_type(document)

    stimulus = resources["stimulus"][0]
    target = resources["observation_target"][0]
    observation = resources["observation"][0]

    assert "provenance" not in stimulus
    assert "provenance" not in target
    assert "provenance" in observation

    result = observation["results"][0]
    assert "provenance" not in result
