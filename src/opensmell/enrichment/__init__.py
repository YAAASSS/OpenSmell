"""External enrichment utilities for OpenSmell."""

from .pubchem import (
    ChemicalIdentity,
    PubChemResolutionError,
    resolve_smiles,
)


__all__ = [
    "ChemicalIdentity",
    "PubChemResolutionError",
    "resolve_smiles",
]