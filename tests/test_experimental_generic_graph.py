"""Tests for the experimental generic ResourceGraph prototype.

These tests explore a possible RFC-0008 direction without changing the
RFC-0007 ResourceGraph model or OpenSmell 0.1 Core.

The prototype must demonstrate that:

- known RFC-0007 resources remain typed;
- unknown resource types remain representable;
- unknown resource payloads survive dict round-trips;
- known and unknown resources can coexist in one graph;
- Resource IDs remain unique across both categories;
- references from known resources can resolve to unknown resources;
- resource type registration is extensible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from opensmell.experimental.generic_graph import (
    DEFAULT_RESOURCE_TYPE_REGISTRY,
    GENERIC_RESOURCE_GRAPH_FORMAT,
    GENERIC_RESOURCE_GRAPH_VERSION,
    GenericResource,
    GenericResourceGraph,
    ResourceTypeRegistry,
    create_default_resource_type_registry,
    generic_graph_dumps,
    generic_graph_from_dict,
    generic_graph_loads,
    generic_graph_to_dict,
    generic_resource_from_dict,
    generic_resource_to_dict,
    resource_from_dict,
    resource_to_dict,
)
from opensmell.experimental.resources import (
    Observation,
    ObservationTarget,
    Reference,
    Stimulus,
)


def test_default_registry_contains_rfc0007_resource_types() -> None:
    assert DEFAULT_RESOURCE_TYPE_REGISTRY.resource_types() == {
        "stimulus",
        "observation_target",
        "observation",
    }


@pytest.mark.parametrize(
    ("resource_type", "python_type"),
    [
        ("stimulus", Stimulus),
        ("observation_target", ObservationTarget),
        ("observation", Observation),
    ],
)
def test_known_resource_types_parse_to_existing_models(
    resource_type: str,
    python_type: type[Any],
) -> None:
    documents: dict[str, dict[str, Any]] = {
        "stimulus": {
            "type": "stimulus",
            "id": "stimulus-1",
        },
        "observation_target": {
            "type": "observation_target",
            "id": "target-1",
        },
        "observation": {
            "type": "observation",
            "id": "observation-1",
            "stimulus": {
                "resource_id": "stimulus-1",
            },
        },
    }

    resource = resource_from_dict(
        documents[resource_type]
    )

    assert isinstance(resource, python_type)


def test_unknown_resource_type_parses_to_generic_resource() -> None:
    document = {
        "type": "molecule",
        "id": "molecule-1",
        "smiles": "CCO",
        "future": {
            "value": 42,
        },
    }

    resource = resource_from_dict(document)

    assert isinstance(resource, GenericResource)
    assert resource.id == "molecule-1"
    assert resource.type == "molecule"
    assert resource.data == {
        "smiles": "CCO",
        "future": {
            "value": 42,
        },
    }


def test_unknown_resource_round_trip_preserves_complete_document() -> None:
    document = {
        "type": "future.resource",
        "id": "future-1",
        "name": "Future resource",
        "nested": {
            "boolean": True,
            "number": 12.5,
            "nothing": None,
            "list": [
                1,
                "two",
                {
                    "three": 3,
                },
            ],
        },
    }

    resource = generic_resource_from_dict(document)

    assert generic_resource_to_dict(resource) == document
    assert resource_to_dict(resource) == document


def test_unknown_resource_parser_owns_preserved_payload() -> None:
    document = {
        "type": "future.resource",
        "id": "future-1",
        "nested": {
            "value": [
                1,
                2,
                3,
            ],
        },
    }

    resource = generic_resource_from_dict(document)

    document["nested"]["value"].append(4)

    assert resource.data == {
        "nested": {
            "value": [
                1,
                2,
                3,
            ],
        },
    }


def test_unknown_resource_serializer_returns_independent_payload() -> None:
    resource = GenericResource(
        id="future-1",
        type="future.resource",
        data={
            "nested": {
                "value": [
                    1,
                    2,
                    3,
                ],
            },
        },
    )

    document = generic_resource_to_dict(resource)

    document["nested"]["value"].append(4)

    assert resource.data == {
        "nested": {
            "value": [
                1,
                2,
                3,
            ],
        },
    }


@pytest.mark.parametrize(
    ("resource_id", "resource_type", "exception_type"),
    [
        (
            "",
            "future.resource",
            ValueError,
        ),
        (
            123,
            "future.resource",
            TypeError,
        ),
        (
            "future-1",
            "",
            ValueError,
        ),
        (
            "future-1",
            123,
            TypeError,
        ),
    ],
)
def test_generic_resource_requires_nonempty_string_type_and_id(
    resource_id: Any,
    resource_type: Any,
    exception_type: type[Exception],
) -> None:
    with pytest.raises(exception_type):
        GenericResource(
            id=resource_id,
            type=resource_type,
        )


def test_generic_resource_rejects_reserved_id_in_data() -> None:
    with pytest.raises(
        ValueError,
        match="reserved field 'id'",
    ):
        GenericResource(
            id="future-1",
            type="future.resource",
            data={
                "id": "other-id",
            },
        )


def test_generic_resource_rejects_reserved_type_in_data() -> None:
    with pytest.raises(
        ValueError,
        match="reserved field 'type'",
    ):
        GenericResource(
            id="future-1",
            type="future.resource",
            data={
                "type": "other.resource",
            },
        )


def test_generic_resource_rejects_non_json_payload_value() -> None:
    with pytest.raises(
        TypeError,
        match="JSON-compatible",
    ):
        GenericResource(
            id="future-1",
            type="future.resource",
            data={
                "invalid": object(),
            },
        )


def test_known_resource_round_trip_uses_existing_serializer() -> None:
    document = {
        "type": "stimulus",
        "id": "stimulus-1",
        "source": {
            "resource_id": "molecule-1",
            "future.reference": {
                "preserve": True,
            },
        },
        "future.stimulus": {
            "preserve": True,
        },
    }

    resource = resource_from_dict(document)

    assert isinstance(resource, Stimulus)
    assert resource.source is not None

    assert resource.source.extra == {
        "future.reference": {
            "preserve": True,
        },
    }

    assert resource_to_dict(resource) == document


def test_known_and_unknown_resources_can_coexist() -> None:
    unknown = GenericResource(
        id="molecule-1",
        type="molecule",
        data={
            "smiles": "CCO",
        },
    )

    stimulus = Stimulus(
        id="stimulus-1",
        source=Reference(
            resource_id="molecule-1",
        ),
    )

    target = ObservationTarget(
        id="target-1",
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1",
        ),
        target=Reference(
            resource_id="target-1",
        ),
    )

    graph = GenericResourceGraph(
        resources=[
            unknown,
            stimulus,
            target,
            observation,
        ],
    )

    assert len(graph) == 4

    assert graph.ids() == {
        "molecule-1",
        "stimulus-1",
        "target-1",
        "observation-1",
    }

    assert graph.get("molecule-1") is unknown
    assert graph.get("stimulus-1") is stimulus
    assert graph.get("target-1") is target
    assert graph.get("observation-1") is observation


def test_duplicate_ids_are_rejected_across_known_and_unknown_resources() -> None:
    known = Stimulus(
        id="shared-id",
    )

    unknown = GenericResource(
        id="shared-id",
        type="future.resource",
    )

    with pytest.raises(
        ValueError,
        match="duplicate Resource ID",
    ):
        GenericResourceGraph(
            resources=[
                known,
                unknown,
            ],
        )


def test_reference_from_known_resource_can_resolve_to_unknown_resource() -> None:
    molecule = GenericResource(
        id="molecule-1",
        type="molecule",
        data={
            "smiles": "CCO",
        },
    )

    stimulus = Stimulus(
        id="stimulus-1",
        source=Reference(
            resource_id="molecule-1",
        ),
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            stimulus,
        ],
    )

    assert stimulus.source is not None
    assert graph.resolve(stimulus.source) is molecule


def test_unresolved_reference_remains_permitted() -> None:
    stimulus = Stimulus(
        id="stimulus-1",
        source=Reference(
            resource_id="missing-resource",
        ),
    )

    graph = GenericResourceGraph(
        resources=[
            stimulus,
        ],
    )

    assert stimulus.source is not None
    assert graph.resolve(stimulus.source) is None


def test_graph_lookup_includes_unknown_resources() -> None:
    unknown = GenericResource(
        id="future-1",
        type="future.resource",
    )

    graph = GenericResourceGraph(
        resources=[
            unknown,
        ],
    )

    assert graph.get("future-1") is unknown
    assert graph.require("future-1") is unknown

    with pytest.raises(KeyError):
        graph.require("missing")


def test_resources_with_type_handles_known_and_unknown_types() -> None:
    stimulus = Stimulus(
        id="stimulus-1",
    )

    unknown_a = GenericResource(
        id="future-1",
        type="future.resource",
    )

    unknown_b = GenericResource(
        id="future-2",
        type="future.resource",
    )

    other = GenericResource(
        id="other-1",
        type="other.resource",
    )

    graph = GenericResourceGraph(
        resources=[
            stimulus,
            unknown_a,
            unknown_b,
            other,
        ],
    )

    assert graph.resources_with_type(
        "stimulus"
    ) == [
        stimulus,
    ]

    assert graph.resources_with_type(
        "future.resource"
    ) == [
        unknown_a,
        unknown_b,
    ]


def test_default_registry_factory_returns_independent_registries() -> None:
    registry_a = create_default_resource_type_registry()
    registry_b = create_default_resource_type_registry()

    assert registry_a is not registry_b

    assert registry_a.resource_types() == {
        "stimulus",
        "observation_target",
        "observation",
    }

    assert registry_b.resource_types() == {
        "stimulus",
        "observation_target",
        "observation",
    }


@dataclass
class ExampleResource:
    id: str
    value: str


def _example_resource_from_dict(
    value: Any,
) -> ExampleResource:
    if not isinstance(value, dict):
        raise TypeError(
            "example resource must be an object"
        )

    resource_id = value.get("id")
    resource_value = value.get("value")

    if not isinstance(resource_id, str):
        raise TypeError(
            "example resource.id must be a string"
        )

    if not resource_id:
        raise ValueError(
            "example resource.id must not be empty"
        )

    if not isinstance(resource_value, str):
        raise TypeError(
            "example resource.value must be a string"
        )

    return ExampleResource(
        id=resource_id,
        value=resource_value,
    )


def _example_resource_to_dict(
    resource: ExampleResource,
) -> dict[str, Any]:
    return {
        "type": "example.resource",
        "id": resource.id,
        "value": resource.value,
    }


def test_registry_can_add_future_resource_type() -> None:
    registry = create_default_resource_type_registry()

    registry.register(
        "example.resource",
        ExampleResource,
        _example_resource_from_dict,
        _example_resource_to_dict,
    )

    document = {
        "type": "example.resource",
        "id": "example-1",
        "value": "hello",
    }

    resource = resource_from_dict(
        document,
        registry=registry,
    )

    assert isinstance(resource, ExampleResource)
    assert resource == ExampleResource(
        id="example-1",
        value="hello",
    )

    assert resource_to_dict(
        resource,
        registry=registry,
    ) == document


def test_unregistered_future_type_remains_generic() -> None:
    registry = create_default_resource_type_registry()

    document = {
        "type": "example.resource",
        "id": "example-1",
        "value": "hello",
    }

    resource = resource_from_dict(
        document,
        registry=registry,
    )

    assert isinstance(resource, GenericResource)

    assert resource_to_dict(
        resource,
        registry=registry,
    ) == document


def test_registry_rejects_duplicate_textual_resource_type() -> None:
    registry = ResourceTypeRegistry()

    registry.register(
        "example.resource",
        ExampleResource,
        _example_resource_from_dict,
        _example_resource_to_dict,
    )

    with pytest.raises(
        ValueError,
        match="resource type already registered",
    ):
        registry.register(
            "example.resource",
            Stimulus,
            lambda value: Stimulus(
                id=value["id"],
            ),
            lambda resource: {
                "type": "example.resource",
                "id": resource.id,
            },
        )


def test_registry_rejects_duplicate_python_type() -> None:
    registry = ResourceTypeRegistry()

    registry.register(
        "example.resource",
        ExampleResource,
        _example_resource_from_dict,
        _example_resource_to_dict,
    )

    with pytest.raises(
        ValueError,
        match="Python resource type already registered",
    ):
        registry.register(
            "another.example.resource",
            ExampleResource,
            _example_resource_from_dict,
            _example_resource_to_dict,
        )


def test_registered_serializer_must_return_matching_type() -> None:
    registry = ResourceTypeRegistry()

    def wrong_serializer(
        resource: ExampleResource,
    ) -> dict[str, Any]:
        return {
            "type": "wrong.resource",
            "id": resource.id,
            "value": resource.value,
        }

    registry.register(
        "example.resource",
        ExampleResource,
        _example_resource_from_dict,
        wrong_serializer,
    )

    with pytest.raises(
        ValueError,
        match="mismatched type field",
    ):
        resource_to_dict(
            ExampleResource(
                id="example-1",
                value="hello",
            ),
            registry=registry,
        )


def test_registered_serializer_must_return_matching_id() -> None:
    registry = ResourceTypeRegistry()

    def wrong_serializer(
        resource: ExampleResource,
    ) -> dict[str, Any]:
        return {
            "type": "example.resource",
            "id": "wrong-id",
            "value": resource.value,
        }

    registry.register(
        "example.resource",
        ExampleResource,
        _example_resource_from_dict,
        wrong_serializer,
    )

    with pytest.raises(
        ValueError,
        match="mismatched id field",
    ):
        resource_to_dict(
            ExampleResource(
                id="example-1",
                value="hello",
            ),
            registry=registry,
        )


def test_registered_parser_must_return_registered_python_type() -> None:
    registry = ResourceTypeRegistry()

    def wrong_parser(value: Any) -> Stimulus:
        return Stimulus(
            id="stimulus-1",
        )

    registry.register(
        "example.resource",
        ExampleResource,
        wrong_parser,
        _example_resource_to_dict,
    )

    with pytest.raises(
        TypeError,
        match="unexpected Python type",
    ):
        resource_from_dict(
            {
                "type": "example.resource",
                "id": "example-1",
                "value": "hello",
            },
            registry=registry,
        )


def test_graph_accepts_registered_future_typed_resource() -> None:
    registry = create_default_resource_type_registry()

    registry.register(
        "example.resource",
        ExampleResource,
        _example_resource_from_dict,
        _example_resource_to_dict,
    )

    resource = ExampleResource(
        id="example-1",
        value="hello",
    )

    graph = GenericResourceGraph(
        resources=[
            resource,
        ],
    )

    assert graph.require("example-1") is resource

    assert generic_graph_to_dict(
        graph,
        registry=registry,
    ) == {
        "format": GENERIC_RESOURCE_GRAPH_FORMAT,
        "version": GENERIC_RESOURCE_GRAPH_VERSION,
        "resources": [
            {
                "type": "example.resource",
                "id": "example-1",
                "value": "hello",
            },
        ],
    }


def test_registered_future_typed_resource_graph_round_trip() -> None:
    registry = create_default_resource_type_registry()

    registry.register(
        "example.resource",
        ExampleResource,
        _example_resource_from_dict,
        _example_resource_to_dict,
    )

    document = {
        "format": GENERIC_RESOURCE_GRAPH_FORMAT,
        "version": GENERIC_RESOURCE_GRAPH_VERSION,
        "future.document": {
            "preserve": True,
        },
        "resources": [
            {
                "type": "example.resource",
                "id": "example-1",
                "value": "hello",
            },
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "source": {
                    "resource_id": "example-1",
                },
            },
            {
                "type": "future.unknown",
                "id": "unknown-1",
                "payload": {
                    "nested": [
                        1,
                        2,
                        3,
                    ],
                },
            },
        ],
    }

    graph = generic_graph_from_dict(
        document,
        registry=registry,
    )

    example = graph.require("example-1")
    stimulus = graph.require("stimulus-1")
    unknown = graph.require("unknown-1")

    assert isinstance(example, ExampleResource)
    assert isinstance(stimulus, Stimulus)
    assert isinstance(unknown, GenericResource)

    assert stimulus.source is not None
    assert graph.resolve(stimulus.source) is example

    assert generic_graph_to_dict(
        graph,
        registry=registry,
    ) == document

    encoded = generic_graph_dumps(
        graph,
        registry=registry,
    )

    reparsed = generic_graph_loads(
        encoded,
        registry=registry,
    )

    assert isinstance(
        reparsed.require("example-1"),
        ExampleResource,
    )

    assert isinstance(
        reparsed.require("unknown-1"),
        GenericResource,
    )

    assert generic_graph_to_dict(
        reparsed,
        registry=registry,
    ) == document


def test_same_future_resource_is_generic_without_handler_and_typed_with_handler() -> None:
    document = {
        "type": "example.resource",
        "id": "example-1",
        "value": "hello",
    }

    unregistered_registry = (
        create_default_resource_type_registry()
    )

    generic = resource_from_dict(
        document,
        registry=unregistered_registry,
    )

    assert isinstance(
        generic,
        GenericResource,
    )

    registered_registry = (
        create_default_resource_type_registry()
    )

    registered_registry.register(
        "example.resource",
        ExampleResource,
        _example_resource_from_dict,
        _example_resource_to_dict,
    )

    typed = resource_from_dict(
        document,
        registry=registered_registry,
    )

    assert isinstance(
        typed,
        ExampleResource,
    )

    assert resource_to_dict(
        generic,
        registry=unregistered_registry,
    ) == document

    assert resource_to_dict(
        typed,
        registry=registered_registry,
    ) == document


def test_graph_rejects_resource_without_id_contract() -> None:
    class NoIdResource:
        pass

    with pytest.raises(
        TypeError,
        match="resources must expose an id attribute",
    ):
        GenericResourceGraph(
            resources=[
                NoIdResource(),
            ],
        )


@pytest.mark.parametrize(
    "invalid_id",
    [
        None,
        123,
        "",
    ],
)
def test_graph_rejects_invalid_structural_resource_id(
    invalid_id: Any,
) -> None:
    class InvalidIdResource:
        def __init__(
            self,
            resource_id: Any,
        ) -> None:
            self.id = resource_id

    with pytest.raises(
        (
            TypeError,
            ValueError,
        )
    ):
        GenericResourceGraph(
            resources=[
                InvalidIdResource(
                    invalid_id
                ),
            ],
        )


def test_unregistered_typed_resource_can_exist_in_graph_but_not_serialize() -> None:
    resource = ExampleResource(
        id="example-1",
        value="hello",
    )

    graph = GenericResourceGraph(
        resources=[
            resource,
        ],
    )

    assert graph.require(
        "example-1"
    ) is resource

    with pytest.raises(
        TypeError,
        match="no resource type handler is registered",
    ):
        generic_graph_to_dict(
            graph
        )


def _create_example_registry() -> ResourceTypeRegistry:
    registry = create_default_resource_type_registry()

    registry.register(
        "example.resource",
        ExampleResource,
        _example_resource_from_dict,
        _example_resource_to_dict,
    )

    return registry


def test_known_resources_uses_custom_registry_for_future_typed_resource() -> None:
    registry = _create_example_registry()

    stimulus = Stimulus(
        id="stimulus-1",
    )

    example = ExampleResource(
        id="example-1",
        value="hello",
    )

    generic = GenericResource(
        id="future-1",
        type="future.resource",
    )

    graph = GenericResourceGraph(
        resources=[
            stimulus,
            example,
            generic,
        ],
    )

    assert graph.known_resources(
        registry=registry,
    ) == [
        stimulus,
        example,
    ]


def test_known_resources_does_not_assume_unregistered_python_type() -> None:
    example = ExampleResource(
        id="example-1",
        value="hello",
    )

    graph = GenericResourceGraph(
        resources=[
            example,
        ],
    )

    assert graph.known_resources() == []


def test_unknown_resources_is_registry_aware() -> None:
    registry = _create_example_registry()

    example = ExampleResource(
        id="example-1",
        value="hello",
    )

    generic = GenericResource(
        id="future-1",
        type="future.resource",
    )

    graph = GenericResourceGraph(
        resources=[
            example,
            generic,
        ],
    )

    assert graph.unknown_resources(
        registry=registry,
    ) == [
        generic,
    ]

    assert graph.unknown_resources() == [
        example,
        generic,
    ]


def test_resources_with_type_uses_custom_registry() -> None:
    registry = _create_example_registry()

    example = ExampleResource(
        id="example-1",
        value="hello",
    )

    graph = GenericResourceGraph(
        resources=[
            example,
        ],
    )

    assert graph.resources_with_type(
        "example.resource",
        registry=registry,
    ) == [
        example,
    ]

    assert graph.resources_with_type(
        "example.resource",
    ) == []


def test_resources_with_type_combines_registered_and_generic_resources() -> None:
    registry = _create_example_registry()

    typed = ExampleResource(
        id="example-1",
        value="hello",
    )

    generic = GenericResource(
        id="example-2",
        type="example.resource",
        data={
            "value": "preserved",
        },
    )

    graph = GenericResourceGraph(
        resources=[
            typed,
            generic,
        ],
    )

    assert graph.resources_with_type(
        "example.resource",
        registry=registry,
    ) == [
        typed,
        generic,
    ]


@pytest.mark.parametrize(
    "method_name",
    [
        "known_resources",
        "unknown_resources",
    ],
)
def test_registry_aware_resource_queries_reject_invalid_registry(
    method_name: str,
) -> None:
    graph = GenericResourceGraph()

    method = getattr(
        graph,
        method_name,
    )

    with pytest.raises(
        TypeError,
        match="registry must be a ResourceTypeRegistry",
    ):
        method(
            registry=object(),
        )


def test_resources_with_type_rejects_invalid_registry() -> None:
    graph = GenericResourceGraph()

    with pytest.raises(
        TypeError,
        match="registry must be a ResourceTypeRegistry",
    ):
        graph.resources_with_type(
            "stimulus",
            registry=object(),
        )



@dataclass
class VersionedExampleResourceV01:
    id: str
    value: str


@dataclass
class VersionedExampleResourceV02:
    id: str
    value: str
    enabled: bool


def _versioned_example_v01_from_dict(
    value: Any,
) -> VersionedExampleResourceV01:
    if not isinstance(value, dict):
        raise TypeError("versioned example resource must be an object")

    return VersionedExampleResourceV01(
        id=value["id"],
        value=value["value"],
    )


def _versioned_example_v01_to_dict(
    resource: VersionedExampleResourceV01,
) -> dict[str, Any]:
    return {
        "type": "org.example.resource",
        "type_version": "0.1",
        "id": resource.id,
        "value": resource.value,
    }


def _versioned_example_v02_from_dict(
    value: Any,
) -> VersionedExampleResourceV02:
    if not isinstance(value, dict):
        raise TypeError("versioned example resource must be an object")

    return VersionedExampleResourceV02(
        id=value["id"],
        value=value["value"],
        enabled=value["enabled"],
    )


def _versioned_example_v02_to_dict(
    resource: VersionedExampleResourceV02,
) -> dict[str, Any]:
    return {
        "type": "org.example.resource",
        "type_version": "0.2",
        "id": resource.id,
        "value": resource.value,
        "enabled": resource.enabled,
    }


def _create_versioned_example_registry() -> ResourceTypeRegistry:
    registry = create_default_resource_type_registry()

    registry.register(
        "org.example.resource",
        VersionedExampleResourceV01,
        _versioned_example_v01_from_dict,
        _versioned_example_v01_to_dict,
        resource_type_version="0.1",
    )

    registry.register(
        "org.example.resource",
        VersionedExampleResourceV02,
        _versioned_example_v02_from_dict,
        _versioned_example_v02_to_dict,
        resource_type_version="0.2",
    )

    return registry


def test_generic_resource_preserves_type_version() -> None:
    document = {
        "type": "org.example.future-resource",
        "type_version": "0.1",
        "id": "future-1",
        "payload": {
            "value": 42,
        },
    }

    resource = generic_resource_from_dict(document)

    assert resource.type_version == "0.1"
    assert "type_version" not in resource.data
    assert generic_resource_to_dict(resource) == document


def test_generic_resource_rejects_reserved_type_version_in_data() -> None:
    with pytest.raises(
        ValueError,
        match="reserved field 'type_version'",
    ):
        GenericResource(
            id="future-1",
            type="org.example.future-resource",
            data={
                "type_version": "0.1",
            },
        )


@pytest.mark.parametrize(
    ("type_version", "exception_type"),
    [
        ("", ValueError),
        (123, TypeError),
    ],
)
def test_generic_resource_rejects_invalid_type_version(
    type_version: Any,
    exception_type: type[Exception],
) -> None:
    with pytest.raises(exception_type):
        GenericResource(
            id="future-1",
            type="org.example.future-resource",
            type_version=type_version,
        )


@pytest.mark.parametrize(
    ("type_version", "exception_type"),
    [
        (None, TypeError),
        ("", ValueError),
        (1, TypeError),
    ],
)
def test_generic_resource_parser_rejects_invalid_present_type_version(
    type_version: Any,
    exception_type: type[Exception],
) -> None:
    document = {
        "type": "org.example.future-resource",
        "type_version": type_version,
        "id": "future-1",
    }

    with pytest.raises(exception_type):
        generic_resource_from_dict(document)

    with pytest.raises(exception_type):
        resource_from_dict(document)


def test_generic_resource_parser_accepts_missing_type_version() -> None:
    document = {
        "type": "org.example.future-resource",
        "id": "future-1",
    }

    generic_resource = generic_resource_from_dict(document)
    resource = resource_from_dict(document)

    assert generic_resource.type_version is None
    assert isinstance(resource, GenericResource)
    assert resource.type_version is None


def test_registry_dispatches_same_resource_type_by_version() -> None:
    registry = _create_versioned_example_registry()

    resource_v01 = resource_from_dict(
        {
            "type": "org.example.resource",
            "type_version": "0.1",
            "id": "example-1",
            "value": "hello",
        },
        registry=registry,
    )

    resource_v02 = resource_from_dict(
        {
            "type": "org.example.resource",
            "type_version": "0.2",
            "id": "example-2",
            "value": "hello",
            "enabled": True,
        },
        registry=registry,
    )

    assert isinstance(
        resource_v01,
        VersionedExampleResourceV01,
    )
    assert isinstance(
        resource_v02,
        VersionedExampleResourceV02,
    )


def test_registry_exposes_versioned_resource_contracts() -> None:
    registry = _create_versioned_example_registry()

    assert (
        "org.example.resource",
        "0.1",
    ) in registry.resource_contracts()

    assert (
        "org.example.resource",
        "0.2",
    ) in registry.resource_contracts()

    assert "org.example.resource" in registry


def test_registry_rejects_duplicate_resource_type_version_pair() -> None:
    registry = ResourceTypeRegistry()

    registry.register(
        "org.example.resource",
        VersionedExampleResourceV01,
        _versioned_example_v01_from_dict,
        _versioned_example_v01_to_dict,
        resource_type_version="0.1",
    )

    with pytest.raises(
        ValueError,
        match="resource type already registered",
    ):
        registry.register(
            "org.example.resource",
            Stimulus,
            lambda value: Stimulus(id=value["id"]),
            lambda resource: {
                "type": "org.example.resource",
                "type_version": "0.1",
                "id": resource.id,
            },
            resource_type_version="0.1",
        )


def test_versioned_registry_requires_namespaced_resource_type() -> None:
    registry = ResourceTypeRegistry()

    with pytest.raises(
        ValueError,
        match="namespaced resource type identifier",
    ):
        registry.register(
            "resource",
            VersionedExampleResourceV01,
            _versioned_example_v01_from_dict,
            _versioned_example_v01_to_dict,
            resource_type_version="0.1",
        )


def test_unknown_resource_type_version_falls_back_to_generic() -> None:
    registry = _create_versioned_example_registry()

    document = {
        "type": "org.example.resource",
        "type_version": "9.9",
        "id": "example-future",
        "value": "preserve me",
        "future": {
            "enabled": True,
        },
    }

    resource = resource_from_dict(
        document,
        registry=registry,
    )

    assert isinstance(resource, GenericResource)
    assert resource.type_version == "9.9"
    assert resource_to_dict(
        resource,
        registry=registry,
    ) == document


def test_missing_version_does_not_select_versioned_handler() -> None:
    registry = _create_versioned_example_registry()

    document = {
        "type": "org.example.resource",
        "id": "example-unversioned",
        "value": "preserve me",
    }

    resource = resource_from_dict(
        document,
        registry=registry,
    )

    assert isinstance(resource, GenericResource)
    assert resource.type_version is None
    assert resource_to_dict(
        resource,
        registry=registry,
    ) == document


def test_versioned_resource_serializer_preserves_registered_contract() -> None:
    registry = _create_versioned_example_registry()

    resource = VersionedExampleResourceV01(
        id="example-1",
        value="hello",
    )

    assert resource_to_dict(
        resource,
        registry=registry,
    ) == {
        "type": "org.example.resource",
        "type_version": "0.1",
        "id": "example-1",
        "value": "hello",
    }


def test_versioned_serializer_must_return_matching_type_version() -> None:
    registry = ResourceTypeRegistry()

    def wrong_serializer(
        resource: VersionedExampleResourceV01,
    ) -> dict[str, Any]:
        return {
            "type": "org.example.resource",
            "type_version": "0.2",
            "id": resource.id,
            "value": resource.value,
        }

    registry.register(
        "org.example.resource",
        VersionedExampleResourceV01,
        _versioned_example_v01_from_dict,
        wrong_serializer,
        resource_type_version="0.1",
    )

    with pytest.raises(
        ValueError,
        match="mismatched type_version field",
    ):
        resource_to_dict(
            VersionedExampleResourceV01(
                id="example-1",
                value="hello",
            ),
            registry=registry,
        )


def test_legacy_rfc0007_resources_remain_unversioned() -> None:
    stimulus = Stimulus(
        id="stimulus-1",
    )

    document = resource_to_dict(stimulus)

    assert document == {
        "type": "stimulus",
        "id": "stimulus-1",
    }
    assert "type_version" not in document

    parsed = resource_from_dict(document)
    assert isinstance(parsed, Stimulus)


def test_versioned_generic_resource_graph_round_trip() -> None:
    registry = _create_versioned_example_registry()

    document = {
        "format": GENERIC_RESOURCE_GRAPH_FORMAT,
        "version": GENERIC_RESOURCE_GRAPH_VERSION,
        "resources": [
            {
                "type": "org.example.resource",
                "type_version": "0.1",
                "id": "example-1",
                "value": "hello",
            },
            {
                "type": "org.example.future-resource",
                "type_version": "3.0",
                "id": "future-1",
                "payload": {
                    "preserve": True,
                },
            },
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "source": {
                    "resource_id": "future-1",
                },
            },
        ],
    }

    graph = generic_graph_from_dict(
        document,
        registry=registry,
    )

    assert isinstance(
        graph.require("example-1"),
        VersionedExampleResourceV01,
    )

    future = graph.require("future-1")
    assert isinstance(future, GenericResource)
    assert future.type_version == "3.0"

    assert isinstance(
        graph.require("stimulus-1"),
        Stimulus,
    )

    assert generic_graph_to_dict(
        graph,
        registry=registry,
    ) == document
