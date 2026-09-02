"""OpenSmell reference implementation."""

from . import builders
from .exceptions import (
    OpenSmellError,
    OpenSmellValidationError,
    SchemeValidationError,
)
from .models import (
    Document,
    Metadata,
    Odor,
    Representation,
    Scheme,
)
from .parser import (
    load,
    load_document,
)
from .serializer import dump

__version__ = "0.1.0"

__all__ = [
    "Document",
    "Metadata",
    "Odor",
    "OpenSmellError",
    "OpenSmellValidationError",
    "Representation",
    "Scheme",
    "SchemeValidationError",
    "builders",
    "dump",
    "load",
    "load_document",
]