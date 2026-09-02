"""OpenSmell exceptions."""


class OpenSmellError(Exception):
    """Base exception for OpenSmell."""


class OpenSmellValidationError(OpenSmellError):
    """Raised when an OpenSmell document is structurally invalid."""


class SchemeValidationError(OpenSmellValidationError):
    """Raised when data does not conform to a known representation scheme."""