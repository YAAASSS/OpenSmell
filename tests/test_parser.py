from pathlib import Path
import json

import pytest

import opensmell


ROOT = Path(__file__).parent.parent


def test_load_valid_coffee():
    odor = opensmell.load(ROOT / "examples" / "coffee.osmell")

    assert odor.metadata is not None
    assert odor.metadata.labels["en"] == "Coffee"
    assert odor.metadata.labels["fr"] == "Café"

    assert len(odor.representations) == 1

    representation = odor.representations[0]

    assert representation.type == "semantic"
    assert (
        representation.scheme.id
        == "org.opensmell.semantic.descriptors"
    )
    assert representation.scheme.version == "0.1"


def test_invalid_document_is_rejected():
    with pytest.raises(opensmell.OpenSmellValidationError):
        opensmell.load(ROOT / "examples" / "invalid.osmell")


def test_invalid_known_scheme_is_rejected(tmp_path):
    document = {
        "opensmell": "0.1",
        "odor": {
            "id": "test-invalid-scheme",
            "representations": [
                {
                    "type": "semantic",
                    "scheme": {
                        "id": "org.opensmell.semantic.descriptors",
                        "version": "0.1",
                    },
                    "data": {
                        "descriptors": [],
                    },
                }
            ],
        },
    }

    path = tmp_path / "invalid-scheme.osmell"

    path.write_text(
        json.dumps(document),
        encoding="utf-8",
    )

    with pytest.raises(opensmell.SchemeValidationError):
        opensmell.load(path)


def test_unknown_scheme_is_preserved(tmp_path):
    document = {
        "opensmell": "0.1",
        "odor": {
            "id": "future-odor",
            "representations": [
                {
                    "type": "experimental",
                    "scheme": {
                        "id": "org.example.future",
                        "version": "42.0",
                    },
                    "data": {
                        "something": "OpenSmell does not understand this",
                        "value": 123,
                    },
                }
            ],
        },
    }

    path = tmp_path / "future.osmell"

    path.write_text(
        json.dumps(document),
        encoding="utf-8",
    )

    odor = opensmell.load(path)

    representation = odor.representations[0]

    assert representation.scheme.id == "org.example.future"
    assert representation.scheme.version == "42.0"

    assert representation.data == {
        "something": "OpenSmell does not understand this",
        "value": 123,
    }