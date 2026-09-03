"""Experimental OpenSmell resource graph model.

This module provides an experimental container for OpenSmell resources defined
by RFC-0007.

It is intentionally separate from the OpenSmell 0.1 Core document model.

The resource graph provides:

- a flat collection of resources;
- uniqueness checks for Resource IDs;
- resource lookup;
- reference resolution;
- unresolved-reference discovery.

Unresolved references are permitted. A reference that cannot be resolved
within a graph does not, by itself, make the graph invalid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias

from .resources import (
    Observation,
    ObservationTarget,
    Reference,
    Stimulus,
)


Resource: TypeAlias = Stimulus | ObservationTarget | Observation


def _require_dict(value: Any, name: str) -> None:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a dict")


def _require_resource(value: Any) -> None:
    if not isinstance(value, (Stimulus, ObservationTarget, Observation)):
        raise TypeError(
            "resources must contain only Stimulus, "
            "ObservationTarget, or Observation instances"
        )


@dataclass
class ResourceGraph:
    """Experimental flat resource graph.

    Resources are stored in a single flat collection.

    Relationships between resources are represented using RFC-0007
    ``Reference`` objects rather than nested resource objects.

    Resource IDs MUST be unique within one graph.

    References are allowed to remain unresolved. This is important for
    partial datasets, external references, incomplete source archives,
    and lossless preservation of imported scientific data.
    """

    resources: list[Resource] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.resources, list):
            raise TypeError("resources must be a list")

        _require_dict(self.extra, "extra")

        seen_ids: set[str] = set()

        for resource in self.resources:
            _require_resource(resource)

            if resource.id in seen_ids:
                raise ValueError(
                    f"duplicate Resource ID in graph: {resource.id!r}"
                )

            seen_ids.add(resource.id)

    def __len__(self) -> int:
        """Return the number of resources in the graph."""

        return len(self.resources)

    def __iter__(self):
        """Iterate over resources in graph order."""

        return iter(self.resources)

    def ids(self) -> set[str]:
        """Return all Resource IDs present in the graph."""

        return {resource.id for resource in self.resources}

    def get(self, resource_id: str) -> Resource | None:
        """Return a resource by ID, or None when it is not present."""

        if not isinstance(resource_id, str):
            raise TypeError("resource_id must be a string")

        for resource in self.resources:
            if resource.id == resource_id:
                return resource

        return None

    def require(self, resource_id: str) -> Resource:
        """Return a resource by ID.

        Raises
        ------
        KeyError
            If the Resource ID is not present in the graph.
        """

        resource = self.get(resource_id)

        if resource is None:
            raise KeyError(resource_id)

        return resource

    def resolve(self, reference: Reference) -> Resource | None:
        """Resolve a Reference inside this graph.

        Resolution is deliberately separate from structural validity.

        An unresolved reference therefore returns None instead of raising
        an exception.
        """

        if not isinstance(reference, Reference):
            raise TypeError("reference must be a Reference")

        return self.get(reference.resource_id)

    def references(self) -> list[Reference]:
        """Return all resource references contained in the graph.

        Current RFC-0007 reference-bearing fields are:

        - Stimulus.source
        - Observation.stimulus
        - Observation.target

        Result payloads are scheme-defined and are intentionally not scanned
        for generic references by this experimental graph layer.
        """

        result: list[Reference] = []

        for resource in self.resources:
            if isinstance(resource, Stimulus):
                if resource.source is not None:
                    result.append(resource.source)

                continue

            if isinstance(resource, Observation):
                result.append(resource.stimulus)

                if resource.target is not None:
                    result.append(resource.target)

        return result

    def unresolved_references(self) -> list[Reference]:
        """Return references that cannot be resolved inside this graph.

        Duplicate unresolved references are preserved because this method
        reports reference occurrences rather than only unique target IDs.
        """

        return [
            reference
            for reference in self.references()
            if self.resolve(reference) is None
        ]

    def unresolved_reference_ids(self) -> set[str]:
        """Return unique unresolved Resource IDs."""

        return {
            reference.resource_id
            for reference in self.unresolved_references()
        }

    def is_fully_resolved(self) -> bool:
        """Return True when every graph-level reference resolves locally."""

        return not self.unresolved_references()

    def resources_of_type(
        self,
        resource_type: type[Resource],
    ) -> list[Resource]:
        """Return resources matching a requested resource class."""

        if resource_type not in (
            Stimulus,
            ObservationTarget,
            Observation,
        ):
            raise TypeError(
                "resource_type must be Stimulus, "
                "ObservationTarget, or Observation"
            )

        return [
            resource
            for resource in self.resources
            if isinstance(resource, resource_type)
        ]