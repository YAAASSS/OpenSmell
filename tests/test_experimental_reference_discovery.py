"""Tests for experimental structural reference discovery."""

from __future__ import annotations

import pytest

from opensmell.experimental.annotation import Annotation
from opensmell.experimental.generic_graph import (
    GenericResource,
    GenericResourceGraph,
)
from opensmell.experimental.molecule import Molecule
from opensmell.experimental.reference_discovery import (
    DEFAULT_REFERENCE_DISCOVERY_REGISTRY,
    DiscoveredReference,
    ReferenceDiscoveryHandler,
    ReferenceDiscoveryRegistry,
    ReferenceIndex,
    build_reference_index,
    create_default_reference_discovery_registry,
    discover_graph_references,
    discover_known_references,
    discover_references,
    references_from,
    references_to,
    resolved_graph_references,
    unresolved_graph_references,
)
from opensmell.experimental.resources import (
    Observation,
    ObservationTarget,
    Reference,
    Result,
    ResultScheme,
    Stimulus,
)
from opensmell.experimental.scheme import Scheme


def make_annotation(
    annotation_id: str = "annotation-1",
    subject_id: str = "molecule-1",
) -> Annotation:
    return Annotation(
        id=annotation_id,
        subject=Reference(
            resource_id=subject_id
        ),
        scheme=Scheme(
            id="org.opensmell.semantic.annotations",
            version="0.1",
        ),
        data={
            "annotations": [],
        },
    )


def test_handler_accepts_valid_python_type_and_discoverer() -> None:
    handler = ReferenceDiscoveryHandler(
        python_type=Molecule,
        discoverer=lambda resource: [],
    )

    assert handler.python_type is Molecule
    assert callable(handler.discoverer)


def test_handler_rejects_non_type_python_type() -> None:
    with pytest.raises(TypeError):
        ReferenceDiscoveryHandler(
            python_type="Molecule",  # type: ignore[arg-type]
            discoverer=lambda resource: [],
        )


def test_handler_rejects_non_callable_discoverer() -> None:
    with pytest.raises(TypeError):
        ReferenceDiscoveryHandler(
            python_type=Molecule,
            discoverer=None,  # type: ignore[arg-type]
        )


def test_registry_registers_handler() -> None:
    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Molecule,
        lambda resource: [],
    )

    assert Molecule in registry

    handler = registry.handler_for_resource(
        Molecule(
            id="molecule-1",
            smiles="CCO",
        )
    )

    assert handler is not None
    assert handler.python_type is Molecule


def test_registry_rejects_duplicate_python_type() -> None:
    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Molecule,
        lambda resource: [],
    )

    with pytest.raises(ValueError):
        registry.register(
            Molecule,
            lambda resource: [],
        )


def test_registry_uses_exact_python_type() -> None:
    class MoleculeSubclass(Molecule):
        pass

    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Molecule,
        lambda resource: [],
    )

    resource = MoleculeSubclass(
        id="molecule-subclass",
        smiles="CCO",
    )

    assert registry.handler_for_resource(resource) is None


def test_registry_python_types_returns_registered_types() -> None:
    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Molecule,
        lambda resource: [],
    )

    registry.register(
        Annotation,
        lambda resource: [],
    )

    assert registry.python_types() == {
        Molecule,
        Annotation,
    }


def test_registry_contains_rejects_non_type_values() -> None:
    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Molecule,
        lambda resource: [],
    )

    assert "Molecule" not in registry
    assert 123 not in registry
    assert None not in registry


def test_discover_references_rejects_invalid_registry() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    with pytest.raises(TypeError):
        discover_references(
            molecule,
            registry=None,  # type: ignore[arg-type]
        )


def test_discover_references_returns_empty_for_unregistered_type() -> None:
    registry = ReferenceDiscoveryRegistry()

    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    assert discover_references(
        molecule,
        registry=registry,
    ) == []


def test_discover_references_rejects_non_list_discoverer_result() -> None:
    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Molecule,
        lambda resource: (),  # type: ignore[arg-type,return-value]
    )

    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    with pytest.raises(TypeError):
        discover_references(
            molecule,
            registry=registry,
        )


def test_discover_references_rejects_non_reference_items() -> None:
    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Molecule,
        lambda resource: ["molecule-2"],  # type: ignore[list-item,return-value]
    )

    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    with pytest.raises(TypeError):
        discover_references(
            molecule,
            registry=registry,
        )


def test_discover_references_returns_independent_list() -> None:
    reference = Reference(
        resource_id="molecule-2"
    )

    source = [reference]

    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Molecule,
        lambda resource: source,
    )

    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    discovered = discover_references(
        molecule,
        registry=registry,
    )

    assert discovered == [reference]
    assert discovered is not source

    discovered.clear()

    assert source == [reference]


def test_default_registry_contains_expected_known_types() -> None:
    registry = create_default_reference_discovery_registry()

    assert registry.python_types() == {
        Stimulus,
        ObservationTarget,
        Observation,
        Molecule,
        Annotation,
    }


def test_default_registry_does_not_register_generic_resource() -> None:
    registry = create_default_reference_discovery_registry()

    assert GenericResource not in registry


def test_module_default_registry_contains_expected_types() -> None:
    assert DEFAULT_REFERENCE_DISCOVERY_REGISTRY.python_types() == {
        Stimulus,
        ObservationTarget,
        Observation,
        Molecule,
        Annotation,
    }


def test_stimulus_without_source_has_no_references() -> None:
    stimulus = Stimulus(
        id="stimulus-1"
    )

    assert discover_known_references(
        stimulus
    ) == []


def test_stimulus_source_is_discovered() -> None:
    source = Reference(
        resource_id="molecule-1"
    )

    stimulus = Stimulus(
        id="stimulus-1",
        source=source,
    )

    assert discover_known_references(
        stimulus
    ) == [source]


def test_observation_target_has_no_references() -> None:
    target = ObservationTarget(
        id="target-1"
    )

    assert discover_known_references(
        target
    ) == []


def test_observation_discovers_required_stimulus_reference() -> None:
    stimulus_reference = Reference(
        resource_id="stimulus-1"
    )

    observation = Observation(
        id="observation-1",
        stimulus=stimulus_reference,
    )

    assert discover_known_references(
        observation
    ) == [
        stimulus_reference,
    ]


def test_observation_discovers_stimulus_and_target_in_structural_order() -> None:
    stimulus_reference = Reference(
        resource_id="stimulus-1"
    )

    target_reference = Reference(
        resource_id="target-1"
    )

    observation = Observation(
        id="observation-1",
        stimulus=stimulus_reference,
        target=target_reference,
    )

    assert discover_known_references(
        observation
    ) == [
        stimulus_reference,
        target_reference,
    ]


def test_molecule_has_no_structural_references() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    assert discover_known_references(
        molecule
    ) == []


def test_annotation_subject_is_discovered() -> None:
    annotation = make_annotation()

    assert discover_known_references(
        annotation
    ) == [
        annotation.subject,
    ]


def test_annotation_scheme_data_is_not_scanned_for_resource_id() -> None:
    subject = Reference(
        resource_id="molecule-1"
    )

    annotation = Annotation(
        id="annotation-1",
        subject=subject,
        scheme=Scheme(
            id="org.example.scheme",
            version="1",
        ),
        data={
            "resource_id": "fake-resource",
            "nested": {
                "resource_id": "another-fake-resource",
            },
        },
    )

    assert discover_known_references(
        annotation
    ) == [
        subject,
    ]


def test_annotation_extra_is_not_scanned_for_resource_id() -> None:
    subject = Reference(
        resource_id="molecule-1"
    )

    annotation = Annotation(
        id="annotation-1",
        subject=subject,
        scheme=Scheme(
            id="org.example.scheme",
            version="1",
        ),
        data={},
        extra={
            "resource_id": "fake-resource",
            "nested": {
                "resource_id": "another-fake-resource",
            },
        },
    )

    assert discover_known_references(
        annotation
    ) == [
        subject,
    ]


def test_observation_result_data_is_not_scanned_for_resource_id() -> None:
    stimulus_reference = Reference(
        resource_id="stimulus-1"
    )

    observation = Observation(
        id="observation-1",
        stimulus=stimulus_reference,
        results=[
            Result(
                scheme=ResultScheme(
                    id="org.example.result",
                    version="1",
                ),
                data={
                    "resource_id": "fake-resource",
                    "nested": {
                        "resource_id": "another-fake-resource",
                    },
                },
            )
        ],
    )

    assert discover_known_references(
        observation
    ) == [
        stimulus_reference,
    ]


def test_observation_context_is_not_scanned_for_resource_id() -> None:
    stimulus_reference = Reference(
        resource_id="stimulus-1"
    )

    observation = Observation(
        id="observation-1",
        stimulus=stimulus_reference,
        context={
            "resource_id": "fake-resource",
            "nested": {
                "resource_id": "another-fake-resource",
            },
        },
    )

    assert discover_known_references(
        observation
    ) == [
        stimulus_reference,
    ]


def test_generic_resource_is_not_scanned_for_reference_like_data() -> None:
    resource = GenericResource(
        id="future-resource-1",
        type="org.example.future.resource",
        type_version="99.0",
        data={
            "subject": {
                "resource_id": "molecule-1",
            },
            "resource_id": "fake-resource",
            "nested": {
                "resource_id": "another-fake-resource",
            },
        },
    )

    assert discover_known_references(
        resource
    ) == []


def test_unknown_plain_python_object_returns_no_references() -> None:
    class UnknownResource:
        def __init__(self) -> None:
            self.id = "unknown-1"
            self.subject = Reference(
                resource_id="molecule-1"
            )

    resource = UnknownResource()

    assert discover_known_references(
        resource
    ) == []


def test_custom_resource_can_register_reference_discovery() -> None:
    class CustomResource:
        def __init__(
            self,
            resource_id: str,
            parent: Reference,
        ) -> None:
            self.id = resource_id
            self.parent = parent

    registry = ReferenceDiscoveryRegistry()

    registry.register(
        CustomResource,
        lambda resource: [
            resource.parent
        ],
    )

    parent = Reference(
        resource_id="parent-1"
    )

    resource = CustomResource(
        "custom-1",
        parent,
    )

    assert discover_references(
        resource,
        registry=registry,
    ) == [
        parent,
    ]


def test_custom_discovery_can_return_multiple_references() -> None:
    class CustomResource:
        def __init__(
            self,
            resource_id: str,
            references: list[Reference],
        ) -> None:
            self.id = resource_id
            self.references = references

    registry = ReferenceDiscoveryRegistry()

    registry.register(
        CustomResource,
        lambda resource: list(
            resource.references
        ),
    )

    first = Reference(
        resource_id="first"
    )

    second = Reference(
        resource_id="second"
    )

    resource = CustomResource(
        "custom-1",
        [
            first,
            second,
        ],
    )

    assert discover_references(
        resource,
        registry=registry,
    ) == [
        first,
        second,
    ]


def test_custom_discovery_can_return_duplicate_references() -> None:
    class CustomResource:
        pass

    registry = ReferenceDiscoveryRegistry()

    reference = Reference(
        resource_id="same-resource"
    )

    registry.register(
        CustomResource,
        lambda resource: [
            reference,
            reference,
        ],
    )

    assert discover_references(
        CustomResource(),
        registry=registry,
    ) == [
        reference,
        reference,
    ]


def test_reference_extensions_are_preserved() -> None:
    subject = Reference(
        resource_id="molecule-1",
        extra={
            "relationship": "primary-subject",
        },
    )

    annotation = Annotation(
        id="annotation-1",
        subject=subject,
        scheme=Scheme(
            id="org.example.scheme",
            version="1",
        ),
        data={},
    )

    discovered = discover_known_references(
        annotation
    )

    assert len(discovered) == 1
    assert discovered[0] is subject
    assert discovered[0].extra == {
        "relationship": "primary-subject",
    }


def test_discovery_does_not_require_reference_target_to_exist() -> None:
    annotation = make_annotation(
        subject_id="does-not-exist"
    )

    assert discover_known_references(
        annotation
    ) == [
        annotation.subject,
    ]


def test_discovery_does_not_resolve_references() -> None:
    annotation = make_annotation()

    discovered = discover_known_references(
        annotation
    )

    assert discovered == [
        annotation.subject,
    ]

    assert isinstance(
        discovered[0],
        Reference,
    )


def test_custom_registry_can_override_available_discovery_scope() -> None:
    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Molecule,
        lambda resource: [],
    )

    annotation = make_annotation()

    assert discover_references(
        annotation,
        registry=registry,
    ) == []


def test_default_registry_instances_are_independent() -> None:
    first = create_default_reference_discovery_registry()
    second = create_default_reference_discovery_registry()

    class CustomResource:
        pass

    first.register(
        CustomResource,
        lambda resource: [],
    )

    assert CustomResource in first
    assert CustomResource not in second


def test_reference_discovery_is_independent_of_resource_serialization_registry() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    assert discover_known_references(
        molecule
    ) == []


def test_generic_future_annotation_is_not_interpreted_as_known_annotation() -> None:
    future_annotation = GenericResource(
        id="annotation-future",
        type="org.opensmell.annotation",
        type_version="99.0",
        data={
            "subject": {
                "resource_id": "molecule-1",
            },
            "scheme": {
                "id": "org.example.future.scheme",
                "version": "99",
            },
            "data": {
                "resource_id": "fake-resource",
            },
        },
    )

    assert discover_known_references(
        future_annotation
    ) == []


def test_generic_known_type_name_without_typed_parsing_is_not_interpreted() -> None:
    generic_annotation = GenericResource(
        id="annotation-generic",
        type="org.opensmell.annotation",
        type_version="0.1",
        data={
            "subject": {
                "resource_id": "molecule-1",
            },
            "scheme": {
                "id": "org.example.scheme",
                "version": "1",
            },
            "data": {},
        },
    )

    assert discover_known_references(
        generic_annotation
    ) == []


def test_discovered_reference_accepts_valid_values() -> None:
    reference = Reference(
        resource_id="molecule-1"
    )

    discovered = DiscoveredReference(
        source_id="annotation-1",
        reference=reference,
    )

    assert discovered.source_id == "annotation-1"
    assert discovered.reference is reference
    assert discovered.target_id == "molecule-1"


def test_discovered_reference_rejects_empty_source_id() -> None:
    with pytest.raises(ValueError):
        DiscoveredReference(
            source_id="",
            reference=Reference(
                resource_id="molecule-1"
            ),
        )


def test_discovered_reference_rejects_non_string_source_id() -> None:
    with pytest.raises(TypeError):
        DiscoveredReference(
            source_id=123,  # type: ignore[arg-type]
            reference=Reference(
                resource_id="molecule-1"
            ),
        )


def test_discovered_reference_rejects_non_reference() -> None:
    with pytest.raises(TypeError):
        DiscoveredReference(
            source_id="annotation-1",
            reference="molecule-1",  # type: ignore[arg-type]
        )


def test_discover_graph_references_rejects_invalid_graph() -> None:
    with pytest.raises(TypeError):
        discover_graph_references(
            None  # type: ignore[arg-type]
        )


def test_discover_graph_references_rejects_invalid_registry() -> None:
    graph = GenericResourceGraph()

    with pytest.raises(TypeError):
        discover_graph_references(
            graph,
            registry=None,  # type: ignore[arg-type]
        )


def test_empty_graph_has_no_discovered_references() -> None:
    graph = GenericResourceGraph()

    assert discover_graph_references(
        graph
    ) == []


def test_graph_discovers_annotation_subject() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    annotation = make_annotation()

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )

    discovered = discover_graph_references(
        graph
    )

    assert discovered == [
        DiscoveredReference(
            source_id="annotation-1",
            reference=annotation.subject,
        )
    ]


def test_graph_discovery_preserves_graph_and_reference_order() -> None:
    stimulus = Stimulus(
        id="stimulus-1"
    )

    target = ObservationTarget(
        id="target-1"
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        target=Reference(
            resource_id="target-1"
        ),
    )

    annotation = make_annotation(
        annotation_id="annotation-1",
        subject_id="observation-1",
    )

    graph = GenericResourceGraph(
        resources=[
            stimulus,
            target,
            observation,
            annotation,
        ]
    )

    discovered = discover_graph_references(
        graph
    )

    assert [
        (
            item.source_id,
            item.target_id,
        )
        for item in discovered
    ] == [
        (
            "observation-1",
            "stimulus-1",
        ),
        (
            "observation-1",
            "target-1",
        ),
        (
            "annotation-1",
            "observation-1",
        ),
    ]


def test_graph_discovery_includes_unresolved_references() -> None:
    annotation = make_annotation(
        subject_id="missing-resource"
    )

    graph = GenericResourceGraph(
        resources=[
            annotation,
        ]
    )

    discovered = discover_graph_references(
        graph
    )

    assert len(discovered) == 1
    assert discovered[0].source_id == "annotation-1"
    assert discovered[0].target_id == "missing-resource"


def test_graph_discovery_does_not_scan_generic_resources() -> None:
    generic = GenericResource(
        id="future-resource",
        type="org.example.future.resource",
        type_version="99",
        data={
            "subject": {
                "resource_id": "molecule-1",
            },
            "resource_id": "fake-resource",
        },
    )

    graph = GenericResourceGraph(
        resources=[
            generic,
        ]
    )

    assert discover_graph_references(
        graph
    ) == []


def test_graph_discovery_uses_custom_registry() -> None:
    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Annotation,
        lambda resource: [],
    )

    graph = GenericResourceGraph(
        resources=[
            make_annotation(),
        ]
    )

    assert discover_graph_references(
        graph,
        registry=registry,
    ) == []


def test_references_from_returns_outgoing_references() -> None:
    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        target=Reference(
            resource_id="target-1"
        ),
    )

    graph = GenericResourceGraph(
        resources=[
            observation,
        ]
    )

    discovered = references_from(
        graph,
        "observation-1",
    )

    assert [
        item.target_id
        for item in discovered
    ] == [
        "stimulus-1",
        "target-1",
    ]

    assert all(
        item.source_id == "observation-1"
        for item in discovered
    )


def test_references_from_missing_resource_returns_empty() -> None:
    graph = GenericResourceGraph()

    assert references_from(
        graph,
        "missing"
    ) == []


def test_references_from_rejects_empty_source_id() -> None:
    graph = GenericResourceGraph()

    with pytest.raises(ValueError):
        references_from(
            graph,
            "",
        )


def test_references_from_rejects_invalid_graph() -> None:
    with pytest.raises(TypeError):
        references_from(
            None,  # type: ignore[arg-type]
            "resource-1",
        )


def test_references_from_rejects_invalid_registry() -> None:
    graph = GenericResourceGraph()

    with pytest.raises(TypeError):
        references_from(
            graph,
            "resource-1",
            registry=None,  # type: ignore[arg-type]
        )


def test_references_to_returns_incoming_references() -> None:
    first = make_annotation(
        annotation_id="annotation-1",
        subject_id="molecule-1",
    )

    second = make_annotation(
        annotation_id="annotation-2",
        subject_id="molecule-1",
    )

    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            first,
            second,
        ]
    )

    discovered = references_to(
        graph,
        "molecule-1",
    )

    assert [
        item.source_id
        for item in discovered
    ] == [
        "annotation-1",
        "annotation-2",
    ]


def test_references_to_can_find_unresolved_target() -> None:
    annotation = make_annotation(
        subject_id="missing-resource"
    )

    graph = GenericResourceGraph(
        resources=[
            annotation,
        ]
    )

    discovered = references_to(
        graph,
        "missing-resource",
    )

    assert len(discovered) == 1
    assert discovered[0].source_id == "annotation-1"
    assert discovered[0].target_id == "missing-resource"


def test_references_to_unknown_target_without_edges_returns_empty() -> None:
    graph = GenericResourceGraph()

    assert references_to(
        graph,
        "missing"
    ) == []


def test_references_to_rejects_empty_target_id() -> None:
    graph = GenericResourceGraph()

    with pytest.raises(ValueError):
        references_to(
            graph,
            "",
        )


def test_references_to_rejects_invalid_graph() -> None:
    with pytest.raises(TypeError):
        references_to(
            None,  # type: ignore[arg-type]
            "resource-1",
        )


def test_references_to_rejects_invalid_registry() -> None:
    graph = GenericResourceGraph()

    with pytest.raises(TypeError):
        references_to(
            graph,
            "resource-1",
            registry=None,  # type: ignore[arg-type]
        )


def test_resolved_graph_references_returns_only_existing_targets() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    resolved_annotation = make_annotation(
        annotation_id="annotation-resolved",
        subject_id="molecule-1",
    )

    unresolved_annotation = make_annotation(
        annotation_id="annotation-unresolved",
        subject_id="missing-resource",
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            resolved_annotation,
            unresolved_annotation,
        ]
    )

    discovered = resolved_graph_references(
        graph
    )

    assert [
        (
            item.source_id,
            item.target_id,
        )
        for item in discovered
    ] == [
        (
            "annotation-resolved",
            "molecule-1",
        )
    ]


def test_unresolved_graph_references_returns_only_missing_targets() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    resolved_annotation = make_annotation(
        annotation_id="annotation-resolved",
        subject_id="molecule-1",
    )

    unresolved_annotation = make_annotation(
        annotation_id="annotation-unresolved",
        subject_id="missing-resource",
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            resolved_annotation,
            unresolved_annotation,
        ]
    )

    discovered = unresolved_graph_references(
        graph
    )

    assert [
        (
            item.source_id,
            item.target_id,
        )
        for item in discovered
    ] == [
        (
            "annotation-unresolved",
            "missing-resource",
        )
    ]


def test_resolved_and_unresolved_partition_all_discovered_references() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    first = make_annotation(
        annotation_id="annotation-1",
        subject_id="molecule-1",
    )

    second = make_annotation(
        annotation_id="annotation-2",
        subject_id="missing-resource",
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            first,
            second,
        ]
    )

    all_references = discover_graph_references(
        graph
    )

    resolved = resolved_graph_references(
        graph
    )

    unresolved = unresolved_graph_references(
        graph
    )

    assert resolved + unresolved == all_references


def test_resolved_reference_can_be_resolved_through_graph() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    annotation = make_annotation()

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )

    discovered = discover_graph_references(
        graph
    )

    assert len(discovered) == 1

    resolved = graph.resolve(
        discovered[0].reference
    )

    assert resolved is molecule


def test_discovered_reference_preserves_reference_extensions() -> None:
    subject = Reference(
        resource_id="molecule-1",
        extra={
            "relationship": "primary-subject",
        },
    )

    annotation = Annotation(
        id="annotation-1",
        subject=subject,
        scheme=Scheme(
            id="org.example.scheme",
            version="1",
        ),
        data={},
    )

    graph = GenericResourceGraph(
        resources=[
            annotation,
        ]
    )

    discovered = discover_graph_references(
        graph
    )

    assert len(discovered) == 1
    assert discovered[0].reference is subject
    assert discovered[0].reference.extra == {
        "relationship": "primary-subject",
    }


def test_multiple_references_to_same_target_remain_distinct_edges() -> None:
    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="same-target"
        ),
        target=Reference(
            resource_id="same-target"
        ),
    )

    graph = GenericResourceGraph(
        resources=[
            observation,
        ]
    )

    discovered = discover_graph_references(
        graph
    )

    assert len(discovered) == 2

    assert [
        item.target_id
        for item in discovered
    ] == [
        "same-target",
        "same-target",
    ]


def test_unknown_resource_does_not_create_false_incoming_reference() -> None:
    generic = GenericResource(
        id="future-resource",
        type="org.example.future.resource",
        data={
            "resource_id": "molecule-1",
            "subject": {
                "resource_id": "molecule-1",
            },
        },
    )

    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            generic,
        ]
    )

    assert references_to(
        graph,
        "molecule-1",
    ) == []


def test_future_annotation_generic_resource_does_not_create_edge() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    future_annotation = GenericResource(
        id="annotation-future",
        type="org.opensmell.annotation",
        type_version="99.0",
        data={
            "subject": {
                "resource_id": "molecule-1",
            },
            "scheme": {
                "id": "org.example.future.scheme",
                "version": "99",
            },
            "data": {},
        },
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            future_annotation,
        ]
    )

    assert discover_graph_references(
        graph
    ) == []


def test_graph_discovery_does_not_mutate_graph() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    annotation = make_annotation()

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ],
        extra={
            "extension": {
                "preserve": True,
            }
        },
    )

    original_resources = list(
        graph.resources
    )

    original_extra = {
        "extension": {
            "preserve": True,
        }
    }

    discover_graph_references(
        graph
    )

    assert graph.resources == original_resources
    assert graph.extra == original_extra


def test_graph_discovery_with_custom_registry_can_ignore_known_types() -> None:
    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Molecule,
        lambda resource: [],
    )

    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            make_annotation(),
        ]
    )

    assert discover_graph_references(
        graph,
        registry=registry,
    ) == []


def test_graph_discovery_with_custom_resource_type() -> None:
    class CustomResource:
        def __init__(
            self,
            resource_id: str,
            parent: Reference,
        ) -> None:
            self.id = resource_id
            self.parent = parent

    parent = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    custom = CustomResource(
        resource_id="custom-1",
        parent=Reference(
            resource_id="molecule-1"
        ),
    )

    graph = GenericResourceGraph(
        resources=[
            parent,
            custom,
        ]
    )

    registry = ReferenceDiscoveryRegistry()

    registry.register(
        CustomResource,
        lambda resource: [
            resource.parent
        ],
    )

    discovered = discover_graph_references(
        graph,
        registry=registry,
    )

    assert len(discovered) == 1
    assert discovered[0].source_id == "custom-1"
    assert discovered[0].target_id == "molecule-1"


def test_resolved_graph_references_rejects_invalid_graph() -> None:
    with pytest.raises(TypeError):
        resolved_graph_references(
            None  # type: ignore[arg-type]
        )


def test_resolved_graph_references_rejects_invalid_registry() -> None:
    graph = GenericResourceGraph()

    with pytest.raises(TypeError):
        resolved_graph_references(
            graph,
            registry=None,  # type: ignore[arg-type]
        )


def test_unresolved_graph_references_rejects_invalid_graph() -> None:
    with pytest.raises(TypeError):
        unresolved_graph_references(
            None  # type: ignore[arg-type]
        )


def test_unresolved_graph_references_rejects_invalid_registry() -> None:
    graph = GenericResourceGraph()

    with pytest.raises(TypeError):
        unresolved_graph_references(
            graph,
            registry=None,  # type: ignore[arg-type]
        )


def test_reference_index_rejects_invalid_graph() -> None:
    with pytest.raises(TypeError):
        ReferenceIndex(
            None  # type: ignore[arg-type]
        )


def test_reference_index_rejects_invalid_registry() -> None:
    graph = GenericResourceGraph()

    with pytest.raises(TypeError):
        ReferenceIndex(
            graph,
            registry="invalid",  # type: ignore[arg-type]
        )


def test_reference_index_empty_graph() -> None:
    graph = GenericResourceGraph()

    index = ReferenceIndex(
        graph
    )

    assert index.graph is graph
    assert len(index) == 0
    assert index.references() == []
    assert index.resolved() == []
    assert index.unresolved() == []


def test_build_reference_index_returns_reference_index() -> None:
    graph = GenericResourceGraph()

    index = build_reference_index(
        graph
    )

    assert isinstance(
        index,
        ReferenceIndex,
    )

    assert index.graph is graph


def test_reference_index_contains_all_discovered_references() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    annotation = make_annotation()

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )

    expected = discover_graph_references(
        graph
    )

    index = build_reference_index(
        graph
    )

    assert index.references() == expected
    assert len(index) == len(expected)


def test_reference_index_references_from() -> None:
    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        target=Reference(
            resource_id="target-1"
        ),
    )

    graph = GenericResourceGraph(
        resources=[
            observation,
        ]
    )

    index = build_reference_index(
        graph
    )

    assert [
        edge.target_id
        for edge in index.references_from(
            "observation-1"
        )
    ] == [
        "stimulus-1",
        "target-1",
    ]


def test_reference_index_references_from_missing_source() -> None:
    index = build_reference_index(
        GenericResourceGraph()
    )

    assert index.references_from(
        "missing"
    ) == []


def test_reference_index_references_from_rejects_empty_id() -> None:
    index = build_reference_index(
        GenericResourceGraph()
    )

    with pytest.raises(ValueError):
        index.references_from(
            ""
        )


def test_reference_index_references_to() -> None:
    first = make_annotation(
        annotation_id="annotation-1",
        subject_id="molecule-1",
    )

    second = make_annotation(
        annotation_id="annotation-2",
        subject_id="molecule-1",
    )

    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            first,
            second,
        ]
    )

    index = build_reference_index(
        graph
    )

    assert [
        edge.source_id
        for edge in index.references_to(
            "molecule-1"
        )
    ] == [
        "annotation-1",
        "annotation-2",
    ]


def test_reference_index_references_to_unresolved_target() -> None:
    annotation = make_annotation(
        subject_id="missing-resource"
    )

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                annotation,
            ]
        )
    )

    incoming = index.references_to(
        "missing-resource"
    )

    assert len(incoming) == 1
    assert incoming[0].source_id == "annotation-1"
    assert incoming[0].target_id == "missing-resource"


def test_reference_index_references_to_rejects_empty_id() -> None:
    index = build_reference_index(
        GenericResourceGraph()
    )

    with pytest.raises(ValueError):
        index.references_to(
            ""
        )


def test_reference_index_partitions_resolved_and_unresolved() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    resolved_annotation = make_annotation(
        annotation_id="annotation-resolved",
        subject_id="molecule-1",
    )

    unresolved_annotation = make_annotation(
        annotation_id="annotation-unresolved",
        subject_id="missing-resource",
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            resolved_annotation,
            unresolved_annotation,
        ]
    )

    index = build_reference_index(
        graph
    )

    assert [
        (
            edge.source_id,
            edge.target_id,
        )
        for edge in index.resolved()
    ] == [
        (
            "annotation-resolved",
            "molecule-1",
        )
    ]

    assert [
        (
            edge.source_id,
            edge.target_id,
        )
        for edge in index.unresolved()
    ] == [
        (
            "annotation-unresolved",
            "missing-resource",
        )
    ]


def test_reference_index_resolved_and_unresolved_cover_all_edges() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            make_annotation(
                annotation_id="annotation-1",
                subject_id="molecule-1",
            ),
            make_annotation(
                annotation_id="annotation-2",
                subject_id="missing-resource",
            ),
        ]
    )

    index = build_reference_index(
        graph
    )

    assert (
        index.resolved()
        + index.unresolved()
        == index.references()
    )


def test_reference_index_resolve() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    annotation = make_annotation()

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                molecule,
                annotation,
            ]
        )
    )

    edge = index.references()[0]

    assert index.resolve(
        edge
    ) is molecule


def test_reference_index_resolve_unresolved_returns_none() -> None:
    annotation = make_annotation(
        subject_id="missing-resource"
    )

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                annotation,
            ]
        )
    )

    edge = index.references()[0]

    assert index.resolve(
        edge
    ) is None


def test_reference_index_resolve_rejects_non_discovered_reference() -> None:
    index = build_reference_index(
        GenericResourceGraph()
    )

    with pytest.raises(TypeError):
        index.resolve(
            Reference(
                resource_id="molecule-1"
            )  # type: ignore[arg-type]
        )


def test_reference_index_does_not_scan_generic_resources() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    generic = GenericResource(
        id="future-resource",
        type="org.example.future.resource",
        type_version="99",
        data={
            "subject": {
                "resource_id": "molecule-1",
            },
            "resource_id": "molecule-1",
        },
    )

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                molecule,
                generic,
            ]
        )
    )

    assert len(index) == 0
    assert index.references_to(
        "molecule-1"
    ) == []


def test_reference_index_future_annotation_remains_uninterpreted() -> None:
    future_annotation = GenericResource(
        id="annotation-future",
        type="org.opensmell.annotation",
        type_version="99.0",
        data={
            "subject": {
                "resource_id": "molecule-1",
            },
            "scheme": {
                "id": "org.example.future.scheme",
                "version": "99",
            },
            "data": {},
        },
    )

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                Molecule(
                    id="molecule-1",
                    smiles="CCO",
                ),
                future_annotation,
            ]
        )
    )

    assert index.references() == []


def test_reference_index_preserves_duplicate_edges() -> None:
    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="same-target"
        ),
        target=Reference(
            resource_id="same-target"
        ),
    )

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                observation,
            ]
        )
    )

    outgoing = index.references_from(
        "observation-1"
    )

    incoming = index.references_to(
        "same-target"
    )

    assert len(outgoing) == 2
    assert len(incoming) == 2

    assert outgoing == incoming


def test_reference_index_preserves_reference_extensions() -> None:
    subject = Reference(
        resource_id="molecule-1",
        extra={
            "relationship": "primary-subject",
        },
    )

    annotation = Annotation(
        id="annotation-1",
        subject=subject,
        scheme=Scheme(
            id="org.example.scheme",
            version="1",
        ),
        data={},
    )

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                annotation,
            ]
        )
    )

    edge = index.references()[0]

    assert edge.reference is subject
    assert edge.reference.extra == {
        "relationship": "primary-subject",
    }


def test_reference_index_returns_independent_reference_lists() -> None:
    annotation = make_annotation()

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                annotation,
            ]
        )
    )

    first = index.references()
    second = index.references()

    assert first == second
    assert first is not second

    first.clear()

    assert len(index) == 1
    assert len(index.references()) == 1


def test_reference_index_returns_independent_outgoing_lists() -> None:
    annotation = make_annotation()

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                annotation,
            ]
        )
    )

    first = index.references_from(
        "annotation-1"
    )

    first.clear()

    assert len(
        index.references_from(
            "annotation-1"
        )
    ) == 1


def test_reference_index_returns_independent_incoming_lists() -> None:
    annotation = make_annotation()

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                annotation,
            ]
        )
    )

    first = index.references_to(
        "molecule-1"
    )

    first.clear()

    assert len(
        index.references_to(
            "molecule-1"
        )
    ) == 1


def test_reference_index_uses_custom_registry() -> None:
    registry = ReferenceDiscoveryRegistry()

    registry.register(
        Annotation,
        lambda resource: [],
    )

    graph = GenericResourceGraph(
        resources=[
            make_annotation(),
        ]
    )

    index = build_reference_index(
        graph,
        registry=registry,
    )

    assert len(index) == 0


def test_reference_index_supports_custom_resource_type() -> None:
    class CustomResource:
        def __init__(
            self,
            resource_id: str,
            parent: Reference,
        ) -> None:
            self.id = resource_id
            self.parent = parent

    custom = CustomResource(
        resource_id="custom-1",
        parent=Reference(
            resource_id="molecule-1"
        ),
    )

    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            custom,
        ]
    )

    registry = ReferenceDiscoveryRegistry()

    registry.register(
        CustomResource,
        lambda resource: [
            resource.parent
        ],
    )

    index = build_reference_index(
        graph,
        registry=registry,
    )

    assert len(index) == 1

    edge = index.references()[0]

    assert edge.source_id == "custom-1"
    assert edge.target_id == "molecule-1"
    assert index.resolve(edge) is molecule


def test_reference_index_is_snapshot_of_discovered_edges() -> None:
    annotation = make_annotation()

    graph = GenericResourceGraph(
        resources=[
            annotation,
        ]
    )

    index = build_reference_index(
        graph
    )

    assert len(index) == 1

    graph.resources.append(
        make_annotation(
            annotation_id="annotation-2",
            subject_id="molecule-2",
        )
    )

    assert len(index) == 1

    rebuilt = build_reference_index(
        graph
    )

    assert len(rebuilt) == 2


def test_reference_index_resolution_partition_is_snapshot() -> None:
    annotation = make_annotation(
        subject_id="molecule-1"
    )

    graph = GenericResourceGraph(
        resources=[
            annotation,
        ]
    )

    index = build_reference_index(
        graph
    )

    assert len(index.resolved()) == 0
    assert len(index.unresolved()) == 1

    graph.resources.append(
        Molecule(
            id="molecule-1",
            smiles="CCO",
        )
    )

    assert len(index.resolved()) == 0
    assert len(index.unresolved()) == 1

    rebuilt = build_reference_index(
        graph
    )

    assert len(rebuilt.resolved()) == 1
    assert len(rebuilt.unresolved()) == 0


def test_reference_index_order_matches_direct_discovery() -> None:
    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        target=Reference(
            resource_id="target-1"
        ),
    )

    annotation = make_annotation(
        subject_id="observation-1"
    )

    graph = GenericResourceGraph(
        resources=[
            observation,
            annotation,
        ]
    )

    direct = discover_graph_references(
        graph
    )

    index = build_reference_index(
        graph
    )

    assert index.references() == direct


def test_reference_index_outgoing_and_incoming_share_same_edges() -> None:
    annotation = make_annotation()

    index = build_reference_index(
        GenericResourceGraph(
            resources=[
                annotation,
            ]
        )
    )

    outgoing = index.references_from(
        "annotation-1"
    )

    incoming = index.references_to(
        "molecule-1"
    )

    assert len(outgoing) == 1
    assert len(incoming) == 1
    assert outgoing[0] is incoming[0]


def test_build_reference_index_none_registry_uses_default() -> None:
    annotation = make_annotation()

    graph = GenericResourceGraph(
        resources=[
            annotation,
        ]
    )

    index = build_reference_index(
        graph,
        registry=None,
    )

    assert len(index) == 1
    assert index.references()[0].source_id == "annotation-1"
    assert index.references()[0].target_id == "molecule-1"
