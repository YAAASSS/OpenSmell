"""Built-in OpenSmell representation schemes."""

from . import semantic_descriptors
from .registry import get_validator, register


register(
    semantic_descriptors.SCHEME_ID,
    semantic_descriptors.SCHEME_VERSION,
    semantic_descriptors.validate,
)


__all__ = [
    "get_validator",
    "register",
]