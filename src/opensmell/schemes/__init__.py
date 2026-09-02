"""Built-in OpenSmell representation schemes."""

from . import chemical_smiles, semantic_descriptors
from .registry import (
    get_definition,
    get_validator,
    register,
)


register(
    semantic_descriptors.SCHEME_ID,
    semantic_descriptors.SCHEME_VERSION,
    "semantic",
    semantic_descriptors.validate,
)

register(
    chemical_smiles.SCHEME_ID,
    chemical_smiles.SCHEME_VERSION,
    "chemical",
    chemical_smiles.validate,
)


__all__ = [
    "get_definition",
    "get_validator",
    "register",
]