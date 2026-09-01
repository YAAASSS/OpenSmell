"""OpenSmell exceptions."""


class OpenSmellError(Exception):
    """Base exception for OpenSmell."""


class OpenSmellValidationError(OpenSmellError):
    """Raised when an OpenSmell document is structurally invalid."""