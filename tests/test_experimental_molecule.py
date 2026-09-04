"""Tests for the experimental OpenSmell Molecule resource.

These tests exercise the first namespaced, versioned OpenSmell resource type
built on the RFC-0008 Generic ResourceGraph experiment.

The Molecule resource identifies a chemical molecule. It does not represent
an odor perception, a stimulus presentation, an observation, or a rendering
recipe.
"""

from __future__ import annotations

from typing import Any

import pytest

from opensmell.experimental.generic_graph import (
    GenericResource,
    GenericResourceGraph,
    create_default_resource_type_registry,
    generic_graph_from_dict,
    generic_graph_to_dict,
    resource_from_dict,
    resource_to_dict,
)
from opensmell.experimental.molecule import (
    MOLECULE_RESOURCE_TYPE,
    MOLECULE_RESOURCE_TYPE_VERSION,
    Molecule,
    molecule_from_dict,
    molecule_to_dict,
    register_molecule_resource_type,
)
from opensmell.experimental.resources import (
    ExternalIdentifier,
    Stimulus,
)


def create_molecule_registry():
    registry = (
        create_default_resource_type_registry()
    )

    register_molecule_resource_type(
        registry
    )

    return registry


def test_molecule_contract_constants() -> None:
    assert (
        MOLECULE_RESOURCE_TYPE
        == "org.opensmell.molecule"
    )
    assert (
        MOLECULE_RESOURCE_TYPE_VERSION
        == "0.1"
    )


def test_molecule_with_smiles() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    assert molecule.id == "molecule-1"
    assert molecule.smiles == "CCO"
    assert molecule.identifiers == []
    assert molecule.extra == {}


def test_molecule_with_external_identifier() -> None:
    molecule = Molecule(
        id="molecule-1",
        identifiers=[
            ExternalIdentifier(
                scheme="pubchem.cid",
                value="702",
            )
        ],
    )

    assert molecule.smiles is None
    assert molecule.identifiers == [
        ExternalIdentifier(
            scheme="pubchem.cid",
            value="702",
        )
    ]


def test_molecule_with_smiles_and_pubchem_cid() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
        identifiers=[
            ExternalIdentifier(
                scheme="pubchem.cid",
                value="702",
            )
        ],
    )

    assert molecule.smiles == "CCO"
    assert (
        molecule.identifiers[0].scheme
        == "pubchem.cid"
    )
    assert (
        molecule.identifiers[0].value
        == "702"
    )


def test_molecule_requires_chemical_identity() -> None:
    with pytest.raises(ValueError):
        Molecule(
            id="molecule-1",
        )


@pytest.mark.parametrize(
    "resource_id",
    [
        "",
        None,
        1,
        False,
    ],
)
def test_molecule_rejects_invalid_resource_id(
    resource_id: Any,
) -> None:
    with pytest.raises(
        (TypeError, ValueError)
    ):
        Molecule(
            id=resource_id,
            smiles="CCO",
        )


@pytest.mark.parametrize(
    "smiles",
    [
        "",
        1,
        False,
        [],
        {},
    ],
)
def test_molecule_rejects_invalid_smiles(
    smiles: Any,
) -> None:
    with pytest.raises(
        (TypeError, ValueError)
    ):
        Molecule(
            id="molecule-1",
            smiles=smiles,
        )


def test_molecule_rejects_non_list_identifiers() -> None:
    with pytest.raises(TypeError):
        Molecule(
            id="molecule-1",
            identifiers="702",
        )


def test_molecule_rejects_invalid_identifier_item() -> None:
    with pytest.raises(TypeError):
        Molecule(
            id="molecule-1",
            identifiers=[
                {
                    "scheme": "pubchem.cid",
                    "value": "702",
                }
            ],
        )


def test_molecule_rejects_non_dict_extra() -> None:
    with pytest.raises(TypeError):
        Molecule(
            id="molecule-1",
            smiles="CCO",
            extra=[],
        )


@pytest.mark.parametrize(
    "reserved_field",
    [
        "type",
        "type_version",
        "id",
        "smiles",
        "identifiers",
    ],
)
def test_molecule_extra_rejects_reserved_fields(
    reserved_field: str,
) -> None:
    with pytest.raises(ValueError):
        Molecule(
            id="molecule-1",
            smiles="CCO",
            extra={
                reserved_field: "conflict",
            },
        )


def test_molecule_serialization_with_smiles() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    assert molecule_to_dict(
        molecule
    ) == {
        "type": "org.opensmell.molecule",
        "type_version": "0.1",
        "id": "molecule-1",
        "smiles": "CCO",
    }


def test_molecule_serialization_with_identifier() -> None:
    molecule = Molecule(
        id="molecule-1",
        identifiers=[
            ExternalIdentifier(
                scheme="pubchem.cid",
                value="702",
            )
        ],
    )

    assert molecule_to_dict(
        molecule
    ) == {
        "type": "org.opensmell.molecule",
        "type_version": "0.1",
        "id": "molecule-1",
        "identifiers": [
            {
                "scheme": "pubchem.cid",
                "value": "702",
            }
        ],
    }


def test_molecule_round_trip_preserves_extensions() -> None:
    document = {
        "type": "org.opensmell.molecule",
        "type_version": "0.1",
        "id": "molecule-1",
        "smiles": "CCO",
        "identifiers": [
            {
                "scheme": "pubchem.cid",
                "value": "702",
                "future.identifier": {
                    "source": "example",
                },
            }
        ],
        "future.resource": {
            "value": 42,
            "nested": [
                1,
                2,
                {
                    "preserve": True,
                },
            ],
        },
    }

    molecule = molecule_from_dict(
        document
    )

    assert molecule_to_dict(
        molecule
    ) == document


def test_molecule_round_trip_preserves_unicode() -> None:
    document = {
        "type": "org.opensmell.molecule",
        "type_version": "0.1",
        "id": "molécule-日本語-🚀",
        "smiles": "CCO",
        "future.label": "éthanol-香り-запах-🌹",
    }

    molecule = molecule_from_dict(
        document
    )

    assert molecule_to_dict(
        molecule
    ) == document


def test_molecule_parser_rejects_wrong_type() -> None:
    with pytest.raises(ValueError):
        molecule_from_dict(
            {
                "type": "org.example.molecule",
                "type_version": "0.1",
                "id": "molecule-1",
                "smiles": "CCO",
            }
        )


@pytest.mark.parametrize(
    "type_version",
    [
        "0.2",
        "1.0",
        "future",
    ],
)
def test_molecule_parser_rejects_unsupported_version(
    type_version: str,
) -> None:
    with pytest.raises(ValueError):
        molecule_from_dict(
            {
                "type": "org.opensmell.molecule",
                "type_version": type_version,
                "id": "molecule-1",
                "smiles": "CCO",
            }
        )


@pytest.mark.parametrize(
    "type_version",
    [
        None,
        "",
        1,
        False,
        [],
        {},
    ],
)
def test_molecule_parser_rejects_invalid_type_version(
    type_version: Any,
) -> None:
    with pytest.raises(
        (TypeError, ValueError)
    ):
        molecule_from_dict(
            {
                "type": "org.opensmell.molecule",
                "type_version": type_version,
                "id": "molecule-1",
                "smiles": "CCO",
            }
        )


def test_molecule_parser_requires_identity() -> None:
    with pytest.raises(ValueError):
        molecule_from_dict(
            {
                "type": "org.opensmell.molecule",
                "type_version": "0.1",
                "id": "molecule-1",
            }
        )


def test_molecule_registry_registration() -> None:
    registry = create_molecule_registry()

    assert (
        (
            "org.opensmell.molecule",
            "0.1",
        )
        in registry.resource_contracts()
    )


def test_registered_molecule_parses_to_typed_resource() -> None:
    registry = create_molecule_registry()

    resource = resource_from_dict(
        {
            "type": "org.opensmell.molecule",
            "type_version": "0.1",
            "id": "molecule-1",
            "smiles": "CCO",
        },
        registry=registry,
    )

    assert isinstance(
        resource,
        Molecule,
    )
    assert resource.id == "molecule-1"
    assert resource.smiles == "CCO"


def test_registered_molecule_serializes_as_versioned_resource() -> None:
    registry = create_molecule_registry()

    resource = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    assert resource_to_dict(
        resource,
        registry=registry,
    ) == {
        "type": "org.opensmell.molecule",
        "type_version": "0.1",
        "id": "molecule-1",
        "smiles": "CCO",
    }


def test_unknown_future_molecule_version_falls_back_to_generic() -> None:
    registry = create_molecule_registry()

    document = {
        "type": "org.opensmell.molecule",
        "type_version": "0.2",
        "id": "molecule-1",
        "smiles": "CCO",
        "future": {
            "preserve": True,
        },
    }

    resource = resource_from_dict(
        document,
        registry=registry,
    )

    assert isinstance(
        resource,
        GenericResource,
    )
    assert resource.type == (
        "org.opensmell.molecule"
    )
    assert resource.type_version == "0.2"

    assert resource_to_dict(
        resource,
        registry=registry,
    ) == document


def test_molecule_participates_in_generic_graph() -> None:
    registry = create_molecule_registry()

    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
                identifiers=[
                    ExternalIdentifier(
                        scheme="pubchem.cid",
                        value="702",
                    )
                ],
            ),
        ]
    )

    document = generic_graph_to_dict(
        graph,
        registry=registry,
    )

    parsed = generic_graph_from_dict(
        document,
        registry=registry,
    )

    assert len(parsed.resources) == 1
    assert isinstance(
        parsed.resources[0],
        Molecule,
    )

    assert generic_graph_to_dict(
        parsed,
        registry=registry,
    ) == document


def test_molecule_can_be_referenced_by_legacy_stimulus() -> None:
    registry = create_molecule_registry()

    document = {
        "format": (
            "org.opensmell.experimental."
            "generic-resource-graph"
        ),
        "version": "0.1",
        "resources": [
            {
                "type": "org.opensmell.molecule",
                "type_version": "0.1",
                "id": "molecule-1",
                "smiles": "CCO",
            },
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "source": {
                    "resource_id": "molecule-1",
                },
            },
        ],
    }

    graph = generic_graph_from_dict(
        document,
        registry=registry,
    )

    assert isinstance(
        graph.resources[0],
        Molecule,
    )
    assert isinstance(
        graph.resources[1],
        Stimulus,
    )

    assert (
        graph.resources[1].source
        is not None
    )
    assert (
        graph.resources[1].source.resource_id
        == "molecule-1"
    )

    assert graph.resolve(
        graph.resources[1].source
    ) is graph.resources[0]

    assert generic_graph_to_dict(
        graph,
        registry=registry,
    ) == document


def test_molecule_coexists_with_unknown_resource() -> None:
    registry = create_molecule_registry()

    document = {
        "format": (
            "org.opensmell.experimental."
            "generic-resource-graph"
        ),
        "version": "0.1",
        "resources": [
            {
                "type": "org.opensmell.molecule",
                "type_version": "0.1",
                "id": "molecule-1",
                "smiles": "CCO",
            },
            {
                "type": "org.example.future-resource",
                "type_version": "9.9",
                "id": "future-1",
                "payload": {
                    "value": 42,
                },
            },
        ],
    }

    graph = generic_graph_from_dict(
        document,
        registry=registry,
    )

    assert isinstance(
        graph.resources[0],
        Molecule,
    )
    assert isinstance(
        graph.resources[1],
        GenericResource,
    )

    assert generic_graph_to_dict(
        graph,
        registry=registry,
    ) == document


def test_default_registry_does_not_implicitly_register_molecule() -> None:
    document = {
        "type": "org.opensmell.molecule",
        "type_version": "0.1",
        "id": "molecule-1",
        "smiles": "CCO",
    }

    resource = resource_from_dict(
        document
    )

    assert isinstance(
        resource,
        GenericResource,
    )