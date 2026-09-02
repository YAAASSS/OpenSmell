import pytest

import opensmell


def test_semantic_descriptors_builder():
    representation = opensmell.builders.semantic_descriptors(
        "vanilla",
        "sweet",
        language="en",
    )

    assert representation.type == "semantic"

    assert (
        representation.scheme.id
        == "org.opensmell.semantic.descriptors"
    )

    assert representation.scheme.version == "0.1"

    assert representation.data == {
        "descriptors": [
            {
                "value": "vanilla",
                "language": "en",
            },
            {
                "value": "sweet",
                "language": "en",
            },
        ]
    }


def test_semantic_descriptors_requires_descriptor():
    with pytest.raises(ValueError):
        opensmell.builders.semantic_descriptors()


def test_odor_builder_generates_uuid():
    representation = opensmell.builders.semantic_descriptors(
        "vanilla",
        language="en",
    )

    odor = opensmell.builders.odor(
        representations=[representation],
        labels={
            "en": "Vanilla",
            "fr": "Vanille",
        },
    )

    assert odor.id.startswith("urn:uuid:")
    assert odor.metadata is not None
    assert odor.metadata.labels["en"] == "Vanilla"
    assert odor.metadata.labels["fr"] == "Vanille"
    assert odor.representations == [representation]


def test_odor_builder_requires_representation():
    with pytest.raises(ValueError):
        opensmell.builders.odor(
            representations=[]
        )

def test_chemical_smiles_builder():
    representation = opensmell.builders.chemical_smiles(
        "C1=CC=C2C(=C1)C=CC(=O)O2"
    )

    assert representation.type == "chemical"

    assert (
        representation.scheme.id
        == "org.opensmell.chemical.smiles"
    )

    assert representation.scheme.version == "0.1"

    assert representation.data == {
        "smiles": "C1=CC=C2C(=C1)C=CC(=O)O2"
    }


def test_chemical_smiles_requires_value():
    with pytest.raises(ValueError):
        opensmell.builders.chemical_smiles("")