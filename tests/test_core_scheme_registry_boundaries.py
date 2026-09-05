"""Architecture guardrails for built-in OpenSmell Core schemes.

These tests intentionally protect the boundary between the frozen OpenSmell
Core 0.1 scheme registry and experimental scheme implementations.

An experimental validator may exist in the source tree without becoming a
built-in Core scheme. Promotion into the Core registry must therefore be an
explicit architectural decision rather than an incidental import.
"""

from __future__ import annotations

from opensmell.schemes import get_definition
from opensmell.schemes import chemical_smiles, semantic_descriptors
from opensmell.schemes import perceptual_measurements


def test_core_semantic_descriptors_scheme_is_registered() -> None:
    definition = get_definition(
        semantic_descriptors.SCHEME_ID,
        semantic_descriptors.SCHEME_VERSION,
    )

    assert definition is not None
    assert definition.representation_type == "semantic"
    assert definition.validator is semantic_descriptors.validate


def test_core_chemical_smiles_scheme_is_registered() -> None:
    definition = get_definition(
        chemical_smiles.SCHEME_ID,
        chemical_smiles.SCHEME_VERSION,
    )

    assert definition is not None
    assert definition.representation_type == "chemical"
    assert definition.validator is chemical_smiles.validate


def test_experimental_perceptual_measurements_is_not_core_registered() -> None:
    """RFC-0005 must not become a Core 0.1 built-in by incidental import."""

    definition = get_definition(
        perceptual_measurements.SCHEME_ID,
        perceptual_measurements.SCHEME_VERSION,
    )

    assert definition is None
