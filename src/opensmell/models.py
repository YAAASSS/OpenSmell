"""Core data models for OpenSmell."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Scheme:
    """Identifies the scheme used to interpret a representation."""

    id: str
    version: str


@dataclass
class Representation:
    """A digital representation of an odor."""

    type: str
    scheme: Scheme
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Metadata:
    """Optional human-readable information about an odor."""

    labels: dict[str, str] = field(default_factory=dict)
    description: str | None = None


@dataclass
class Odor:
    """A conceptual odor containing one or more representations."""

    id: str
    representations: list[Representation]
    metadata: Metadata | None = None