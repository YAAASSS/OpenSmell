from pathlib import Path

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
    assert representation.scheme.id == "org.opensmell.semantic.free"
    assert representation.scheme.version == "0.1"


def test_invalid_document_is_rejected():
    with pytest.raises(opensmell.OpenSmellValidationError):
        opensmell.load(ROOT / "examples" / "invalid.osmell")