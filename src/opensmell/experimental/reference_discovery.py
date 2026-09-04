"""Experimental structural reference discovery for OpenSmell resources.

This module explores generic discovery of structural Resource references
without modifying the RFC-0008 ResourceTypeRegistry or GenericResourceGraph.

A reference discoverer knows how to extract structural ``Reference`` objects
from one understood Python resource type.

The mechanism deliberately does not inspect arbitrary serialized JSON and does
not scan scheme-defined payloads for fields that merely look like references.

Unknown resources remain transportable but uninterpreted.

This module also explores graph-level reference discovery and an indexed view
of discovered structural relationships. These helpers do not modify
GenericResourceGraph itself.

This module is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypeAlias

from .annotation import Annotation
from .generic_graph import (
    GenericResource,
    GenericResourceGraph,
)
from .molecule import Molecule
from .resources import (
    Observation,
    ObservationTarget,
    Reference,
    Stimulus,
)


ReferenceDiscoverer: TypeAlias = Callable[[Any], list[Reference]]


def _require_nonempty_string(
    value: Any,
    name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be a string"
        )

    if not value:
        raise ValueError(
            f"{name} must not be empty"
        )

    return value


def _require_reference_list(
    value: Any,
    name: str,
) -> list[Reference]:
    if not isinstance(value, list):
        raise TypeError(
            f"{name} must return a list"
        )

    for item in value:
        if not isinstance(item, Reference):
            raise TypeError(
                f"{name} must return only Reference objects"
            )

    return list(value)


@dataclass(frozen=True)
class ReferenceDiscoveryHandler:
    """Reference discoverer for one exact Python resource type."""

    python_type: type[Any]
    discoverer: ReferenceDiscoverer

    def __post_init__(self) -> None:
        if not isinstance(self.python_type, type):
            raise TypeError(
                "reference discovery handler.python_type must be a type"
            )

        if not callable(self.discoverer):
            raise TypeError(
                "reference discovery handler.discoverer must be callable"
            )


class ReferenceDiscoveryRegistry:
    """Registry mapping exact Python resource types to reference discoverers."""

    def __init__(self) -> None:
        self._by_python_type: dict[
            type[Any],
            ReferenceDiscoveryHandler,
        ] = {}

    def register(
        self,
        python_type: type[Any],
        discoverer: ReferenceDiscoverer,
    ) -> None:
        handler = ReferenceDiscoveryHandler(
            python_type=python_type,
            discoverer=discoverer,
        )

        if python_type in self._by_python_type:
            raise ValueError(
                "reference discoverer already registered for Python type: "
                f"{python_type.__name__}"
            )

        self._by_python_type[python_type] = handler

    def handler_for_resource(
        self,
        resource: Any,
    ) -> ReferenceDiscoveryHandler | None:
        return self._by_python_type.get(
            type(resource)
        )

    def python_types(self) -> set[type[Any]]:
        return set(self._by_python_type)

    def __contains__(
        self,
        python_type: object,
    ) -> bool:
        if not isinstance(python_type, type):
            return False

        return python_type in self._by_python_type


@dataclass(frozen=True)
class DiscoveredReference:
    """One structural reference discovered from a graph resource.

    ``source_id`` identifies the resource containing the structural reference.

    ``reference`` is the original Reference object declared by that resource.

    The target does not need to exist in the graph.
    """

    source_id: str
    reference: Reference

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.source_id,
            "discovered reference.source_id",
        )

        if not isinstance(
            self.reference,
            Reference,
        ):
            raise TypeError(
                "discovered reference.reference must be a Reference"
            )

    @property
    def target_id(self) -> str:
        """Return the Resource ID named by the reference."""

        return self.reference.resource_id


class ReferenceIndex:
    """Indexed view of discovered structural graph references.

    The index is a snapshot built from one GenericResourceGraph.

    Structural references are discovered once during construction. Incoming
    and outgoing queries then use dictionaries instead of rescanning the graph.

    The index deliberately does not interpret GenericResource payloads and
    does not automatically update if the original graph is later mutated.
    """

    def __init__(
        self,
        graph: GenericResourceGraph,
        *,
        registry: ReferenceDiscoveryRegistry = None,
    ) -> None:
        if not isinstance(
            graph,
            GenericResourceGraph,
        ):
            raise TypeError(
                "graph must be a GenericResourceGraph"
            )

        if registry is None:
            registry = DEFAULT_REFERENCE_DISCOVERY_REGISTRY

        if not isinstance(
            registry,
            ReferenceDiscoveryRegistry,
        ):
            raise TypeError(
                "registry must be a ReferenceDiscoveryRegistry"
            )

        self._graph = graph
        self._registry = registry

        discovered = discover_graph_references(
            graph,
            registry=registry,
        )

        self._references: tuple[
            DiscoveredReference,
            ...
        ] = tuple(discovered)

        outgoing: dict[
            str,
            list[DiscoveredReference],
        ] = {}

        incoming: dict[
            str,
            list[DiscoveredReference],
        ] = {}

        resolved: list[
            DiscoveredReference
        ] = []

        unresolved: list[
            DiscoveredReference
        ] = []

        for edge in self._references:
            outgoing.setdefault(
                edge.source_id,
                [],
            ).append(edge)

            incoming.setdefault(
                edge.target_id,
                [],
            ).append(edge)

            if graph.resolve(
                edge.reference
            ) is None:
                unresolved.append(
                    edge
                )
            else:
                resolved.append(
                    edge
                )

        self._outgoing: dict[
            str,
            tuple[DiscoveredReference, ...],
        ] = {
            resource_id: tuple(edges)
            for resource_id, edges
            in outgoing.items()
        }

        self._incoming: dict[
            str,
            tuple[DiscoveredReference, ...],
        ] = {
            resource_id: tuple(edges)
            for resource_id, edges
            in incoming.items()
        }

        self._resolved: tuple[
            DiscoveredReference,
            ...
        ] = tuple(resolved)

        self._unresolved: tuple[
            DiscoveredReference,
            ...
        ] = tuple(unresolved)

    @property
    def graph(
        self,
    ) -> GenericResourceGraph:
        """Return the graph from which this snapshot was built."""

        return self._graph

    def references(
        self,
    ) -> list[DiscoveredReference]:
        """Return all discovered references in graph/discovery order."""

        return list(
            self._references
        )

    def references_from(
        self,
        source_id: str,
    ) -> list[DiscoveredReference]:
        """Return indexed outgoing references for one Resource ID."""

        _require_nonempty_string(
            source_id,
            "source_id",
        )

        return list(
            self._outgoing.get(
                source_id,
                (),
            )
        )

    def references_to(
        self,
        target_id: str,
    ) -> list[DiscoveredReference]:
        """Return indexed incoming references for one target Resource ID.

        The target does not need to exist in the graph.
        """

        _require_nonempty_string(
            target_id,
            "target_id",
        )

        return list(
            self._incoming.get(
                target_id,
                (),
            )
        )

    def resolved(
        self,
    ) -> list[DiscoveredReference]:
        """Return references whose targets existed at index construction."""

        return list(
            self._resolved
        )

    def unresolved(
        self,
    ) -> list[DiscoveredReference]:
        """Return references whose targets were absent at index construction."""

        return list(
            self._unresolved
        )

    def resolve(
        self,
        discovered: DiscoveredReference,
    ) -> Any | None:
        """Resolve one discovered reference through the indexed graph."""

        if not isinstance(
            discovered,
            DiscoveredReference,
        ):
            raise TypeError(
                "discovered must be a DiscoveredReference"
            )

        return self._graph.resolve(
            discovered.reference
        )

    def __len__(
        self,
    ) -> int:
        return len(
            self._references
        )


def discover_references(
    resource: Any,
    *,
    registry: ReferenceDiscoveryRegistry,
) -> list[Reference]:
    """Return structural references declared by an understood resource.

    Unknown or unregistered resource types return an empty list.

    The function deliberately does not inspect arbitrary attributes or JSON
    payloads in an attempt to infer references.
    """

    if not isinstance(
        registry,
        ReferenceDiscoveryRegistry,
    ):
        raise TypeError(
            "registry must be a ReferenceDiscoveryRegistry"
        )

    handler = registry.handler_for_resource(
        resource
    )

    if handler is None:
        return []

    references = handler.discoverer(
        resource
    )

    return _require_reference_list(
        references,
        (
            "reference discoverer for "
            f"{handler.python_type.__name__}"
        ),
    )


def _discover_stimulus_references(
    resource: Stimulus,
) -> list[Reference]:
    if resource.source is None:
        return []

    return [resource.source]


def _discover_observation_target_references(
    resource: ObservationTarget,
) -> list[Reference]:
    return []


def _discover_observation_references(
    resource: Observation,
) -> list[Reference]:
    references = [
        resource.stimulus,
    ]

    if resource.target is not None:
        references.append(
            resource.target
        )

    return references


def _discover_molecule_references(
    resource: Molecule,
) -> list[Reference]:
    return []


def _discover_annotation_references(
    resource: Annotation,
) -> list[Reference]:
    return [
        resource.subject,
    ]


def create_default_reference_discovery_registry(
) -> ReferenceDiscoveryRegistry:
    """Create the current experimental reference discovery registry.

    The registry understands structural references declared by the currently
    known experimental resource classes.

    GenericResource is intentionally not registered because its type-specific
    contents are unknown and must not be interpreted heuristically.
    """

    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Stimulus,
        _discover_stimulus_references,
    )

    registry.register(
        ObservationTarget,
        _discover_observation_target_references,
    )

    registry.register(
        Observation,
        _discover_observation_references,
    )

    registry.register(
        Molecule,
        _discover_molecule_references,
    )

    registry.register(
        Annotation,
        _discover_annotation_references,
    )

    return registry


DEFAULT_REFERENCE_DISCOVERY_REGISTRY = (
    create_default_reference_discovery_registry()
)


def discover_known_references(
    resource: Any,
    *,
    registry: ReferenceDiscoveryRegistry = (
        DEFAULT_REFERENCE_DISCOVERY_REGISTRY
    ),
) -> list[Reference]:
    """Convenience wrapper using the default experimental registry."""

    return discover_references(
        resource,
        registry=registry,
    )


def discover_graph_references(
    graph: GenericResourceGraph,
    *,
    registry: ReferenceDiscoveryRegistry = (
        DEFAULT_REFERENCE_DISCOVERY_REGISTRY
    ),
) -> list[DiscoveredReference]:
    """Discover all known structural references in a generic graph.

    Resources are visited in graph order. References emitted by each resource
    retain the order returned by that resource's registered discoverer.

    Unknown and unregistered resource types contribute no discovered
    references.
    """

    if not isinstance(
        graph,
        GenericResourceGraph,
    ):
        raise TypeError(
            "graph must be a GenericResourceGraph"
        )

    if not isinstance(
        registry,
        ReferenceDiscoveryRegistry,
    ):
        raise TypeError(
            "registry must be a ReferenceDiscoveryRegistry"
        )

    result: list[DiscoveredReference] = []

    for resource in graph.resources:
        references = discover_references(
            resource,
            registry=registry,
        )

        for reference in references:
            result.append(
                DiscoveredReference(
                    source_id=resource.id,
                    reference=reference,
                )
            )

    return result


def references_from(
    graph: GenericResourceGraph,
    source_id: str,
    *,
    registry: ReferenceDiscoveryRegistry = (
        DEFAULT_REFERENCE_DISCOVERY_REGISTRY
    ),
) -> list[DiscoveredReference]:
    """Return known structural references originating from one Resource ID.

    This unindexed helper is convenient for small graphs. Repeated graph
    queries should use ReferenceIndex instead.
    """

    if not isinstance(
        graph,
        GenericResourceGraph,
    ):
        raise TypeError(
            "graph must be a GenericResourceGraph"
        )

    _require_nonempty_string(
        source_id,
        "source_id",
    )

    if not isinstance(
        registry,
        ReferenceDiscoveryRegistry,
    ):
        raise TypeError(
            "registry must be a ReferenceDiscoveryRegistry"
        )

    resource = graph.get(
        source_id
    )

    if resource is None:
        return []

    return [
        DiscoveredReference(
            source_id=resource.id,
            reference=reference,
        )
        for reference in discover_references(
            resource,
            registry=registry,
        )
    ]


def references_to(
    graph: GenericResourceGraph,
    target_id: str,
    *,
    registry: ReferenceDiscoveryRegistry = (
        DEFAULT_REFERENCE_DISCOVERY_REGISTRY
    ),
) -> list[DiscoveredReference]:
    """Return known structural references targeting one Resource ID.

    This unindexed helper scans known graph references. Repeated incoming
    queries should use ReferenceIndex instead.
    """

    if not isinstance(
        graph,
        GenericResourceGraph,
    ):
        raise TypeError(
            "graph must be a GenericResourceGraph"
        )

    _require_nonempty_string(
        target_id,
        "target_id",
    )

    if not isinstance(
        registry,
        ReferenceDiscoveryRegistry,
    ):
        raise TypeError(
            "registry must be a ReferenceDiscoveryRegistry"
        )

    return [
        discovered
        for discovered in discover_graph_references(
            graph,
            registry=registry,
        )
        if discovered.target_id == target_id
    ]


def resolved_graph_references(
    graph: GenericResourceGraph,
    *,
    registry: ReferenceDiscoveryRegistry = (
        DEFAULT_REFERENCE_DISCOVERY_REGISTRY
    ),
) -> list[DiscoveredReference]:
    """Return discovered references whose targets exist in the graph."""

    if not isinstance(
        graph,
        GenericResourceGraph,
    ):
        raise TypeError(
            "graph must be a GenericResourceGraph"
        )

    if not isinstance(
        registry,
        ReferenceDiscoveryRegistry,
    ):
        raise TypeError(
            "registry must be a ReferenceDiscoveryRegistry"
        )

    return [
        discovered
        for discovered in discover_graph_references(
            graph,
            registry=registry,
        )
        if graph.resolve(
            discovered.reference
        ) is not None
    ]


def unresolved_graph_references(
    graph: GenericResourceGraph,
    *,
    registry: ReferenceDiscoveryRegistry = (
        DEFAULT_REFERENCE_DISCOVERY_REGISTRY
    ),
) -> list[DiscoveredReference]:
    """Return discovered references whose targets are absent from the graph."""

    if not isinstance(
        graph,
        GenericResourceGraph,
    ):
        raise TypeError(
            "graph must be a GenericResourceGraph"
        )

    if not isinstance(
        registry,
        ReferenceDiscoveryRegistry,
    ):
        raise TypeError(
            "registry must be a ReferenceDiscoveryRegistry"
        )

    return [
        discovered
        for discovered in discover_graph_references(
            graph,
            registry=registry,
        )
        if graph.resolve(
            discovered.reference
        ) is None
    ]


def build_reference_index(
    graph: GenericResourceGraph,
    *,
    registry: ReferenceDiscoveryRegistry = (
        DEFAULT_REFERENCE_DISCOVERY_REGISTRY
    ),
) -> ReferenceIndex:
    """Build an indexed snapshot of known structural graph references."""

    return ReferenceIndex(
        graph,
        registry=registry,
    )