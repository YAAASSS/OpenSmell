"""Conformance tests for the OpenSmell 0.1 specification."""

import copy

import pytest

from opensmell.exceptions import (
    OpenSmellValidationError,
    SchemeValidationError,
)
from opensmell.validation import validate_document


def valid_document():
    """Return a minimal structurally valid OpenSmell 0.1 document."""

    return {
        "opensmell": "0.1",
        "odor": {
            "id": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
            "representations": [
                {
                    "type": "experimental",
                    "scheme": {
                        "id": "org.example.test",
                        "version": "1.0",
                    },
                    "data": {},
                }
            ],
        },
    }


def test_minimal_document_is_valid():
    document = valid_document()

    validate_document(document)


def test_empty_odor_id_is_rejected():
    document = valid_document()
    document["odor"]["id"] = ""

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_empty_representations_are_rejected():
    document = valid_document()
    document["odor"]["representations"] = []

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_empty_representation_type_is_rejected():
    document = valid_document()
    document["odor"]["representations"][0]["type"] = ""

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_empty_scheme_id_is_rejected():
    document = valid_document()
    document["odor"]["representations"][0]["scheme"]["id"] = ""

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_empty_scheme_version_is_rejected():
    document = valid_document()
    document["odor"]["representations"][0]["scheme"]["version"] = ""

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_representation_data_must_be_object():
    document = valid_document()
    document["odor"]["representations"][0]["data"] = []

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_unknown_scheme_is_accepted():
    document = valid_document()

    document["odor"]["representations"][0]["scheme"] = {
        "id": "org.example.unknown",
        "version": "99.0",
    }

    validate_document(document)


def test_unknown_representation_type_is_accepted():
    document = valid_document()

    document["odor"]["representations"][0]["type"] = (
        "future-representation-type"
    )

    validate_document(document)


def test_multiple_representations_are_accepted():
    document = valid_document()

    second_representation = copy.deepcopy(
        document["odor"]["representations"][0]
    )

    second_representation["type"] = "another-type"
    second_representation["scheme"] = {
        "id": "org.example.another",
        "version": "1.0",
    }

    document["odor"]["representations"].append(
        second_representation
    )

    validate_document(document)


def test_empty_label_is_rejected():
    document = valid_document()

    document["odor"]["metadata"] = {
        "labels": {
            "en": "",
        }
    }

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_empty_description_is_rejected():
    document = valid_document()

    document["odor"]["metadata"] = {
        "description": "",
    }

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_missing_opensmell_is_rejected():
    document = valid_document()
    del document["opensmell"]

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_missing_odor_is_rejected():
    document = valid_document()
    del document["odor"]

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_missing_odor_id_is_rejected():
    document = valid_document()
    del document["odor"]["id"]

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_missing_representations_is_rejected():
    document = valid_document()
    del document["odor"]["representations"]

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_missing_representation_type_is_rejected():
    document = valid_document()
    del document["odor"]["representations"][0]["type"]

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_missing_scheme_is_rejected():
    document = valid_document()
    del document["odor"]["representations"][0]["scheme"]

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_missing_scheme_id_is_rejected():
    document = valid_document()
    del document["odor"]["representations"][0]["scheme"]["id"]

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_missing_scheme_version_is_rejected():
    document = valid_document()
    del document["odor"]["representations"][0]["scheme"]["version"]

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_missing_representation_data_is_rejected():
    document = valid_document()
    del document["odor"]["representations"][0]["data"]

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_semantic_scheme_with_wrong_type_is_rejected():
    document = valid_document()

    document["odor"]["representations"][0] = {
        "type": "chemical",
        "scheme": {
            "id": "org.opensmell.semantic.descriptors",
            "version": "0.1",
        },
        "data": {
            "descriptors": [
                {
                    "value": "coffee",
                    "language": "en",
                }
            ]
        },
    }

    with pytest.raises(SchemeValidationError):
        validate_document(document)


def test_chemical_smiles_scheme_with_wrong_type_is_rejected():
    document = valid_document()

    document["odor"]["representations"][0] = {
        "type": "semantic",
        "scheme": {
            "id": "org.opensmell.chemical.smiles",
            "version": "0.1",
        },
        "data": {
            "smiles": "O=C1OC2=CC=CC=C2C=C1",
        },
    }

    with pytest.raises(SchemeValidationError):
        validate_document(document)

def test_semantic_scheme_with_empty_descriptors_is_rejected():
    document = valid_document()

    document["odor"]["representations"][0] = {
        "type": "semantic",
        "scheme": {
            "id": "org.opensmell.semantic.descriptors",
            "version": "0.1",
        },
        "data": {
            "descriptors": [],
        },
    }

    with pytest.raises(SchemeValidationError):
        validate_document(document)


def test_semantic_scheme_with_empty_descriptor_value_is_rejected():
    document = valid_document()

    document["odor"]["representations"][0] = {
        "type": "semantic",
        "scheme": {
            "id": "org.opensmell.semantic.descriptors",
            "version": "0.1",
        },
        "data": {
            "descriptors": [
                {
                    "value": "",
                    "language": "en",
                }
            ],
        },
    }

    with pytest.raises(SchemeValidationError):
        validate_document(document)


def test_smiles_scheme_with_empty_value_is_rejected():
    document = valid_document()

    document["odor"]["representations"][0] = {
        "type": "chemical",
        "scheme": {
            "id": "org.opensmell.chemical.smiles",
            "version": "0.1",
        },
        "data": {
            "smiles": "",
        },
    }

    with pytest.raises(SchemeValidationError):
        validate_document(document)


def test_unknown_scheme_data_is_preserved():
    document = valid_document()

    representation = document["odor"]["representations"][0]

    representation["type"] = "future-type"
    representation["scheme"] = {
        "id": "org.example.future",
        "version": "42.0",
    }
    representation["data"] = {
        "custom": {
            "values": [1, 2, 3],
        },
        "experimental": True,
    }

    validate_document(document)

    assert representation["data"] == {
        "custom": {
            "values": [1, 2, 3],
        },
        "experimental": True,
    }