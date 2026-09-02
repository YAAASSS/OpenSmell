"""OpenSmell chemical SMILES scheme."""

from typing import Any


SCHEME_ID = "org.opensmell.chemical.smiles"
SCHEME_VERSION = "0.1"


def validate(data: dict[str, Any]) -> None:
    """Validate chemical SMILES data."""

    smiles = data.get("smiles")

    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError(
            "'smiles' must be a non-empty string"
        )