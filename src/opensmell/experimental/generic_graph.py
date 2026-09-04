"""Experimental generic OpenSmell resource graph prototype.

This module explores a possible RFC-0008 direction without changing the
RFC-0007 ResourceGraph model or the OpenSmell 0.1 Core model.

The prototype adds three concepts:

- ``GenericResource`` for structurally valid but otherwise unknown resource
  types;
- ``ResourceTypeRegistry`` for mapping resource type names to typed parsers and
  serializers;
- ``GenericResourceGraph`` for storing known typed resources and unknown
  generic resources in one flat graph.

Design goals
------------

1. Known RFC-0007 resource types remain represented by their existing Python
   classes.
2. Unknown resource types remain representable instead of causing rejection.
3. Unknown resource data is preserved through dict round-trips.
4. Resource IDs remain unique within one graph.
5. Unresolved references remain permitted.
6. The existing RFC-0007 ``ResourceGraph`` and serialization API are not
   modified by this experiment.

This module is non-normative and experimental.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, TypeAlias

from .graph_serialization import (
    observation_from_dict,
    observation_target_from_dict,
    observation_target_to_dict,
    observation_to_dict,
    stimulus_from_dict,
    stimulus_to_dict,
)
from .resources import (
    Observation,
    ObservationTarget,
    Reference,
    Stimulus,
)


class ResourceLike(Protocol):
    """Structural typing contract for resources stored in a generic graph."""

    id: str


ResourceParser: TypeAlias = Callable[[Any], Any]
ResourceSerializer: TypeAlias = Callable[[Any], dict[str, Any]]


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")

    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a list")

    return value


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")

    if not value:
        raise ValueError(f"{name} must not be empty")

    return value


def _require_namespaced_resource_type(
    value: Any,
    name: str,
) -> str:
    resource_type = _require_string(value, name)
    segments = resource_type.split(".")

    if (
        len(segments) < 2
        or any(
            not segment
            or segment != segment.strip()
            or any(character.isspace() for character in segment)
            for segment in segments
        )
    ):
        raise ValueError(
            f"{name} must be a namespaced resource type identifier"
        )

    return resource_type


def _copy_json_value(value: Any) -> Any:
    """Recursively copy JSON-compatible data."""

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return value

    if isinstance(value, list):
        return [
            _copy_json_value(item)
            for item in value
        ]

    if isinstance(value, dict):
        result: dict[str, Any] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "JSON object keys must be strings"
                )

            result[key] = _copy_json_value(item)

        return result

    raise TypeError(
        "generic resource data must contain only "
        "JSON-compatible values"
    )


@dataclass
class GenericResource:
    """Preserved representation of an unknown resource type."""

    id: str
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    type_version: str | None = None

    def __post_init__(self) -> None:
        _require_string(self.id, "generic resource.id")
        _require_string(self.type, "generic resource.type")

        if self.type_version is not None:
            _require_string(
                self.type_version,
                "generic resource.type_version",
            )

        _require_dict(self.data, "generic resource.data")

        self.data = _copy_json_value(self.data)

        if "id" in self.data:
            raise ValueError(
                "generic resource.data must not contain reserved field 'id'"
            )

        if "type" in self.data:
            raise ValueError(
                "generic resource.data must not contain reserved field 'type'"
            )

        if "type_version" in self.data:
            raise ValueError(
                "generic resource.data must not contain reserved field "
                "'type_version'"
            )


GenericGraphResource: TypeAlias = ResourceLike


@dataclass(frozen=True)
class ResourceTypeHandler:
    """Parser/serializer pair for one registered resource type."""

    resource_type: str
    python_type: type[Any]
    parser: ResourceParser
    serializer: ResourceSerializer
    resource_type_version: str | None = None

    def __post_init__(self) -> None:
        _require_string(
            self.resource_type,
            "resource type handler.resource_type",
        )

        if self.resource_type_version is not None:
            _require_string(
                self.resource_type_version,
                "resource type handler.resource_type_version",
            )
            _require_namespaced_resource_type(
                self.resource_type,
                "resource type handler.resource_type",
            )

        if not isinstance(self.python_type, type):
            raise TypeError(
                "resource type handler.python_type must be a type"
            )

        if not callable(self.parser):
            raise TypeError(
                "resource type handler.parser must be callable"
            )

        if not callable(self.serializer):
            raise TypeError(
                "resource type handler.serializer must be callable"
            )


class ResourceTypeRegistry:
    """Registry of typed resource parsers and serializers."""

    def __init__(self) -> None:
        self._by_resource_contract: dict[
            tuple[str, str | None],
            ResourceTypeHandler,
        ] = {}
        self._by_python_type: dict[type[Any], ResourceTypeHandler] = {}

    def register(
        self,
        resource_type: str,
        python_type: type[Any],
        parser: ResourceParser,
        serializer: ResourceSerializer,
        *,
        resource_type_version: str | None = None,
    ) -> None:
        handler = ResourceTypeHandler(
            resource_type=resource_type,
            python_type=python_type,
            parser=parser,
            serializer=serializer,
            resource_type_version=resource_type_version,
        )

        contract = (
            handler.resource_type,
            handler.resource_type_version,
        )

        if contract in self._by_resource_contract:
            raise ValueError(
                "resource type already registered for contract: "
                f"{contract!r}"
            )

        if python_type in self._by_python_type:
            raise ValueError(
                "Python resource type already registered: "
                f"{python_type.__name__}"
            )

        self._by_resource_contract[contract] = handler
        self._by_python_type[python_type] = handler

    def handler_for_resource_type(
        self,
        resource_type: str,
        resource_type_version: str | None = None,
    ) -> ResourceTypeHandler | None:
        _require_string(resource_type, "resource_type")

        if resource_type_version is not None:
            _require_string(
                resource_type_version,
                "resource_type_version",
            )

        return self._by_resource_contract.get(
            (resource_type, resource_type_version)
        )

    def handler_for_resource(
        self,
        resource: Any,
    ) -> ResourceTypeHandler | None:
        return self._by_python_type.get(type(resource))

    def resource_types(self) -> set[str]:
        return {
            resource_type
            for resource_type, _ in self._by_resource_contract
        }

    def resource_contracts(
        self,
    ) -> set[tuple[str, str | None]]:
        return set(self._by_resource_contract)

    def __contains__(self, resource_type: object) -> bool:
        if not isinstance(resource_type, str):
            return False

        return any(
            registered_type == resource_type
            for registered_type, _ in self._by_resource_contract
        )


def create_default_resource_type_registry() -> ResourceTypeRegistry:
    """Create a registry containing the RFC-0007 resource types."""

    registry = ResourceTypeRegistry()

    registry.register(
        "stimulus",
        Stimulus,
        stimulus_from_dict,
        stimulus_to_dict,
    )

    registry.register(
        "observation_target",
        ObservationTarget,
        observation_target_from_dict,
        observation_target_to_dict,
    )

    registry.register(
        "observation",
        Observation,
        observation_from_dict,
        observation_to_dict,
    )

    return registry


DEFAULT_RESOURCE_TYPE_REGISTRY = create_default_resource_type_registry()


def generic_resource_from_dict(value: Any) -> GenericResource:
    """Parse an unknown resource without interpreting its type-specific data."""

    obj = _require_dict(value, "generic resource")

    resource_id = _require_string(
        obj.get("id"),
        "generic resource.id",
    )

    resource_type = _require_string(
        obj.get("type"),
        "generic resource.type",
    )

    if "type_version" in obj:
        resource_type_version = _require_string(
            obj["type_version"],
            "generic resource.type_version",
        )
    else:
        resource_type_version = None

    data = {
        key: _copy_json_value(item)
        for key, item in obj.items()
        if key not in {"id", "type", "type_version"}
    }

    return GenericResource(
        id=resource_id,
        type=resource_type,
        type_version=resource_type_version,
        data=data,
    )


def generic_resource_to_dict(
    resource: GenericResource,
) -> dict[str, Any]:
    """Serialize an unknown resource without losing preserved members."""

    if not isinstance(resource, GenericResource):
        raise TypeError(
            "resource must be a GenericResource"
        )

    result = _copy_json_value(resource.data)
    result["type"] = resource.type

    if resource.type_version is not None:
        result["type_version"] = resource.type_version

    result["id"] = resource.id

    return result


def resource_from_dict(
    value: Any,
    *,
    registry: ResourceTypeRegistry = DEFAULT_RESOURCE_TYPE_REGISTRY,
) -> GenericGraphResource:
    """Parse a known typed resource or preserve an unknown resource."""

    if not isinstance(registry, ResourceTypeRegistry):
        raise TypeError(
            "registry must be a ResourceTypeRegistry"
        )

    obj = _require_dict(value, "resource")

    resource_type = _require_string(
        obj.get("type"),
        "resource.type",
    )

    if "type_version" in obj:
        resource_type_version = _require_string(
            obj["type_version"],
            "resource.type_version",
        )
    else:
        resource_type_version = None

    handler = registry.handler_for_resource_type(
        resource_type,
        resource_type_version,
    )

    if handler is None:
        return generic_resource_from_dict(obj)

    resource = handler.parser(obj)

    if not isinstance(resource, handler.python_type):
        raise TypeError(
            f"parser for resource type {resource_type!r} "
            "returned an unexpected Python type"
        )

    return resource


def resource_to_dict(
    resource: GenericGraphResource,
    *,
    registry: ResourceTypeRegistry = DEFAULT_RESOURCE_TYPE_REGISTRY,
) -> dict[str, Any]:
    """Serialize a known typed resource or a preserved unknown resource."""

    if not isinstance(registry, ResourceTypeRegistry):
        raise TypeError(
            "registry must be a ResourceTypeRegistry"
        )

    if isinstance(resource, GenericResource):
        return generic_resource_to_dict(resource)

    handler = registry.handler_for_resource(resource)

    if handler is None:
        raise TypeError(
            "no resource type handler is registered for "
            f"{type(resource).__name__}"
        )

    document = handler.serializer(resource)

    if not isinstance(document, dict):
        raise TypeError(
            f"serializer for resource type {handler.resource_type!r} "
            "must return a dict"
        )

    if document.get("type") != handler.resource_type:
        raise ValueError(
            f"serializer for resource type {handler.resource_type!r} "
            "returned a mismatched type field"
        )

    if handler.resource_type_version is None:
        if "type_version" in document:
            raise ValueError(
                f"serializer for legacy resource type "
                f"{handler.resource_type!r} returned an unexpected "
                "type_version field"
            )
    elif document.get("type_version") != handler.resource_type_version:
        raise ValueError(
            f"serializer for resource type {handler.resource_type!r} "
            "returned a mismatched type_version field"
        )

    if document.get("id") != resource.id:
        raise ValueError(
            f"serializer for resource type {handler.resource_type!r} "
            "returned a mismatched id field"
        )

    return document


@dataclass
class GenericResourceGraph:
    """Flat graph containing typed and unknown resources.

    The graph itself only requires every resource to expose a non-empty
    string ``id``. It deliberately does not maintain a closed list of Python
    resource classes.

    Type-specific parsing and serialization belong to ``ResourceTypeRegistry``.
    A custom typed resource can therefore participate in the graph when a
    registry handler exists for it.

    Unknown serialized resource types are represented by ``GenericResource``
    and remain available for lookup and round-trip preservation.
    """

    resources: list[GenericGraphResource] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.resources, list):
            raise TypeError("resources must be a list")

        _require_dict(self.extra, "extra")
        self.extra = _copy_json_value(self.extra)

        seen_ids: set[str] = set()

        for resource in self.resources:
            if not hasattr(resource, "id"):
                raise TypeError(
                    "resources must expose an id attribute"
                )

            resource_id = _require_string(
                resource.id,
                "resource.id",
            )

            if resource_id in seen_ids:
                raise ValueError(
                    f"duplicate Resource ID in graph: {resource_id!r}"
                )

            seen_ids.add(resource_id)

    def __len__(self) -> int:
        return len(self.resources)

    def __iter__(self):
        return iter(self.resources)

    def ids(self) -> set[str]:
        return {
            resource.id
            for resource in self.resources
        }

    def get(
        self,
        resource_id: str,
    ) -> GenericGraphResource | None:
        _require_string(resource_id, "resource_id")

        for resource in self.resources:
            if resource.id == resource_id:
                return resource

        return None

    def require(
        self,
        resource_id: str,
    ) -> GenericGraphResource:
        resource = self.get(resource_id)

        if resource is None:
            raise KeyError(resource_id)

        return resource

    def resolve(
        self,
        reference: Reference,
    ) -> GenericGraphResource | None:
        if not isinstance(reference, Reference):
            raise TypeError(
                "reference must be a Reference"
            )

        return self.get(reference.resource_id)

    def known_resources(
        self,
        *,
        registry: ResourceTypeRegistry = DEFAULT_RESOURCE_TYPE_REGISTRY,
    ) -> list[GenericGraphResource]:
        """Return typed resources understood by the supplied registry."""

        if not isinstance(registry, ResourceTypeRegistry):
            raise TypeError(
                "registry must be a ResourceTypeRegistry"
            )

        return [
            resource
            for resource in self.resources
            if (
                not isinstance(resource, GenericResource)
                and registry.handler_for_resource(resource) is not None
            )
        ]

    def unknown_resources(
        self,
        *,
        registry: ResourceTypeRegistry = DEFAULT_RESOURCE_TYPE_REGISTRY,
    ) -> list[GenericGraphResource]:
        """Return resources not understood as typed by the supplied registry."""

        if not isinstance(registry, ResourceTypeRegistry):
            raise TypeError(
                "registry must be a ResourceTypeRegistry"
            )

        return [
            resource
            for resource in self.resources
            if (
                isinstance(resource, GenericResource)
                or registry.handler_for_resource(resource) is None
            )
        ]

    def resources_with_type(
        self,
        resource_type: str,
        *,
        registry: ResourceTypeRegistry = DEFAULT_RESOURCE_TYPE_REGISTRY,
    ) -> list[GenericGraphResource]:
        """Return resources whose serialized type matches resource_type."""

        _require_string(resource_type, "resource_type")

        if not isinstance(registry, ResourceTypeRegistry):
            raise TypeError(
                "registry must be a ResourceTypeRegistry"
            )

        result: list[GenericGraphResource] = []

        for resource in self.resources:
            if isinstance(resource, GenericResource):
                if resource.type == resource_type:
                    result.append(resource)

                continue

            handler = registry.handler_for_resource(resource)

            if (
                handler is not None
                and handler.resource_type == resource_type
            ):
                result.append(resource)

        return result


GENERIC_RESOURCE_GRAPH_FORMAT = (
    "org.opensmell.experimental.generic-resource-graph"
)
GENERIC_RESOURCE_GRAPH_VERSION = "0.1"


def generic_graph_to_dict(
    graph: GenericResourceGraph,
    *,
    registry: ResourceTypeRegistry = DEFAULT_RESOURCE_TYPE_REGISTRY,
) -> dict[str, Any]:
    """Serialize a GenericResourceGraph to its experimental document envelope."""

    if not isinstance(graph, GenericResourceGraph):
        raise TypeError(
            "graph must be a GenericResourceGraph"
        )

    if not isinstance(registry, ResourceTypeRegistry):
        raise TypeError(
            "registry must be a ResourceTypeRegistry"
        )

    official: dict[str, Any] = {
        "format": GENERIC_RESOURCE_GRAPH_FORMAT,
        "version": GENERIC_RESOURCE_GRAPH_VERSION,
        "resources": [
            resource_to_dict(
                resource,
                registry=registry,
            )
            for resource in graph.resources
        ],
    }

    result = _copy_json_value(graph.extra)
    result.update(official)
    return result


def generic_graph_from_dict(
    value: Any,
    *,
    registry: ResourceTypeRegistry = DEFAULT_RESOURCE_TYPE_REGISTRY,
) -> GenericResourceGraph:
    """Parse the experimental generic ResourceGraph document envelope."""

    if not isinstance(registry, ResourceTypeRegistry):
        raise TypeError(
            "registry must be a ResourceTypeRegistry"
        )

    obj = _require_dict(
        value,
        "generic resource graph document",
    )

    document_format = _require_string(
        obj.get("format"),
        "generic resource graph format",
    )

    if document_format != GENERIC_RESOURCE_GRAPH_FORMAT:
        raise ValueError(
            "unsupported generic resource graph format: "
            f"{document_format!r}"
        )

    version = _require_string(
        obj.get("version"),
        "generic resource graph version",
    )

    if version != GENERIC_RESOURCE_GRAPH_VERSION:
        raise ValueError(
            "unsupported generic resource graph version: "
            f"{version!r}"
        )

    if "resources" not in obj:
        raise ValueError(
            "generic resource graph resources are required"
        )

    resources = [
        resource_from_dict(
            item,
            registry=registry,
        )
        for item in _require_list(
            obj["resources"],
            "generic resource graph resources",
        )
    ]

    extra = {
        key: _copy_json_value(item)
        for key, item in obj.items()
        if key not in {
            "format",
            "version",
            "resources",
        }
    }

    return GenericResourceGraph(
        resources=resources,
        extra=extra,
    )


def generic_graph_dumps(
    graph: GenericResourceGraph,
    *,
    registry: ResourceTypeRegistry = DEFAULT_RESOURCE_TYPE_REGISTRY,
    indent: int | None = 2,
) -> str:
    """Serialize a GenericResourceGraph to strict JSON text."""

    import json

    return json.dumps(
        generic_graph_to_dict(
            graph,
            registry=registry,
        ),
        ensure_ascii=False,
        indent=indent,
        allow_nan=False,
    )


def _reject_nonstandard_json_constant(value: str) -> Any:
    raise ValueError(
        f"non-standard JSON numeric constant is not allowed: {value}"
    )


def generic_graph_loads(
    value: str,
    *,
    registry: ResourceTypeRegistry = DEFAULT_RESOURCE_TYPE_REGISTRY,
) -> GenericResourceGraph:
    """Parse a GenericResourceGraph from strict JSON text."""

    import json

    if not isinstance(value, str):
        raise TypeError(
            "value must be a string"
        )

    parsed = json.loads(
        value,
        parse_constant=_reject_nonstandard_json_constant,
    )

    return generic_graph_from_dict(
        parsed,
        registry=registry,
    )
