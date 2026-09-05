"""Heterogeneous graph tests for experimental structural reference discovery.

This module deliberately combines several OpenSmell experimental resource
families in one GenericResourceGraph.

The goal is to test the architectural boundary explored by the structural
reference-discovery prototype:

- known typed resources expose only their declared structural References;
- unknown GenericResource payloads remain opaque;
- Result.data, Annotation.data, context, and extension data remain opaque;
- unresolved structural References remain discoverable and indexable;
- incoming and outgoing navigation works across heterogeneous resource types;
- discovery order remains deterministic;
- ReferenceIndex remains a snapshot of discovered relationships.

This is experimental validation only. It does not define a normative OpenSmell
relationship model and does not create RFC-0011.
"""

from __future__ import annotations

from opensmell.experimental.annotation import Annotation
from opensmell.experimental.generic_graph import (
    GenericResource,
    GenericResourceGraph,
)
from opensmell.experimental.molecule import Molecule
from opensmell.experimental.reference_discovery import (
    ReferenceIndex,
    build_reference_index,
    discover_graph_references,
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


MOLECULE_ID = "molecule-1"
STIMULUS_ID = "stimulus-1"
TARGET_ID = "target-1"
OBSERVATION_ID = "observation-1"
ANNOTATION_ID = "annotation-1"
UNRESOLVED_ANNOTATION_ID = "annotation-unresolved"
MISSING_RESOURCE_ID = "missing-resource"
UNKNOWN_RESOURCE_ID = "unknown-resource-1"
FUTURE_ANNOTATION_ID = "future-annotation-1"


def make_heterogeneous_graph() -> GenericResourceGraph:
    """Build a graph containing known, unknown, and unresolved relationships."""

    molecule = Molecule(
        id=MOLECULE_ID,
        smiles="CCO",
        extra={
            "fake_reference": {
                "resource_id": TARGET_ID,
            }
        },
    )

    stimulus = Stimulus(
        id=STIMULUS_ID,
        source=Reference(
            resource_id=MOLECULE_ID,
            extra={"role": "source"},
        ),
        extra={
            "fake_reference": {
                "resource_id": TARGET_ID,
            }
        },
    )

    target = ObservationTarget(
        id=TARGET_ID,
        extra={
            "fake_reference": {
                "resource_id": MOLECULE_ID,
            }
        },
    )

    observation = Observation(
        id=OBSERVATION_ID,
        stimulus=Reference(
            resource_id=STIMULUS_ID,
            extra={"role": "stimulus"},
        ),
        target=Reference(
            resource_id=TARGET_ID,
            extra={"role": "target"},
        ),
        results=[
            Result(
                scheme=ResultScheme(
                    id="org.example.result",
                    version="0.1",
                ),
                data={
                    "value": 42,
                    "fake_reference": {
                        "resource_id": MOLECULE_ID,
                    },
                },
                extra={
                    "another_fake_reference": {
                        "resource_id": MISSING_RESOURCE_ID,
                    }
                },
            )
        ],
        context={
            "fake_reference": {
                "resource_id": MOLECULE_ID,
            }
        },
        extra={
            "fake_reference": {
                "resource_id": TARGET_ID,
            }
        },
    )

    annotation = Annotation(
        id=ANNOTATION_ID,
        subject=Reference(
            resource_id=MOLECULE_ID,
            extra={"role": "subject"},
        ),
        scheme=Scheme(
            id="org.example.annotation",
            version="0.1",
        ),
        data={
            "label": "example",
            "fake_reference": {
                "resource_id": OBSERVATION_ID,
            },
        },
        extra={
            "fake_reference": {
                "resource_id": TARGET_ID,
            }
        },
    )

    unresolved_annotation = Annotation(
        id=UNRESOLVED_ANNOTATION_ID,
        subject=Reference(
            resource_id=MISSING_RESOURCE_ID,
            extra={"reason": "intentionally-unresolved"},
        ),
        scheme=Scheme(
            id="org.example.annotation",
            version="0.1",
        ),
        data={"label": "unresolved example"},
    )

    unknown_resource = GenericResource(
        id=UNKNOWN_RESOURCE_ID,
        type="org.example.unknown-resource",
        type_version="0.1",
        data={
            "resource_id": MOLECULE_ID,
            "nested": {"resource_id": TARGET_ID},
            "list": [{"resource_id": STIMULUS_ID}],
        },
    )

    # This deliberately resembles a future Annotation contract. Because the
    # implementation does not understand that exact version, it is represented
    # as GenericResource and must remain uninterpreted by reference discovery.
    future_annotation = GenericResource(
        id=FUTURE_ANNOTATION_ID,
        type="org.opensmell.annotation",
        type_version="999.0",
        data={
            "subject": {"resource_id": MOLECULE_ID},
            "scheme": {
                "id": "org.example.future-annotation",
                "version": "999.0",
            },
            "data": {"resource_id": TARGET_ID},
        },
    )

    return GenericResourceGraph(
        resources=[
            molecule,
            stimulus,
            target,
            observation,
            annotation,
            unresolved_annotation,
            unknown_resource,
            future_annotation,
        ],
        extra={
            "fake_reference": {
                "resource_id": MOLECULE_ID,
            }
        },
    )


def edge_pairs(index: ReferenceIndex) -> list[tuple[str, str]]:
    """Return ordered source-target pairs from an index."""

    return [
        (edge.source_id, edge.target_id)
        for edge in index.references()
    ]


def expected_edge_pairs() -> list[tuple[str, str]]:
    """Return the only structural relationships expected from the graph."""

    return [
        (STIMULUS_ID, MOLECULE_ID),
        (OBSERVATION_ID, STIMULUS_ID),
        (OBSERVATION_ID, TARGET_ID),
        (ANNOTATION_ID, MOLECULE_ID),
        (UNRESOLVED_ANNOTATION_ID, MISSING_RESOURCE_ID),
    ]


def test_discovers_only_expected_structural_references() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    assert edge_pairs(index) == expected_edge_pairs()
    assert len(index) == 5


def test_discovery_preserves_graph_and_per_resource_order() -> None:
    graph = make_heterogeneous_graph()

    discovered = discover_graph_references(graph)

    assert [
        (edge.source_id, edge.target_id)
        for edge in discovered
    ] == expected_edge_pairs()


def test_stimulus_source_is_indexed() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    edges = index.references_from(STIMULUS_ID)

    assert len(edges) == 1
    assert edges[0].target_id == MOLECULE_ID
    assert edges[0].reference.extra == {"role": "source"}


def test_observation_stimulus_and_target_are_indexed_in_order() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    edges = index.references_from(OBSERVATION_ID)

    assert [edge.target_id for edge in edges] == [
        STIMULUS_ID,
        TARGET_ID,
    ]
    assert edges[0].reference.extra == {"role": "stimulus"}
    assert edges[1].reference.extra == {"role": "target"}


def test_annotation_subject_is_indexed() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    edges = index.references_from(ANNOTATION_ID)

    assert len(edges) == 1
    assert edges[0].target_id == MOLECULE_ID
    assert edges[0].reference.extra == {"role": "subject"}


def test_molecule_receives_references_from_multiple_resource_types() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    incoming = index.references_to(MOLECULE_ID)

    assert [edge.source_id for edge in incoming] == [
        STIMULUS_ID,
        ANNOTATION_ID,
    ]


def test_observation_target_receives_only_real_structural_reference() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    incoming = index.references_to(TARGET_ID)

    assert [edge.source_id for edge in incoming] == [OBSERVATION_ID]


def test_unknown_generic_resource_payload_is_not_scanned() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    assert index.references_from(UNKNOWN_RESOURCE_ID) == []
    assert UNKNOWN_RESOURCE_ID not in {
        edge.source_id
        for edge in index.references()
    }


def test_future_annotation_generic_resource_is_not_interpreted() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    assert index.references_from(FUTURE_ANNOTATION_ID) == []
    assert FUTURE_ANNOTATION_ID not in {
        edge.source_id
        for edge in index.references_to(MOLECULE_ID)
    }


def test_opaque_payloads_and_extensions_do_not_create_false_edges() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    # Many opaque payloads deliberately contain dictionaries that look like
    # {"resource_id": ...}. None of them may become structural graph edges.
    assert len(index) == 5
    assert edge_pairs(index) == expected_edge_pairs()


def test_resolved_and_unresolved_partitions_are_correct() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    assert [
        (edge.source_id, edge.target_id)
        for edge in index.resolved()
    ] == [
        (STIMULUS_ID, MOLECULE_ID),
        (OBSERVATION_ID, STIMULUS_ID),
        (OBSERVATION_ID, TARGET_ID),
        (ANNOTATION_ID, MOLECULE_ID),
    ]

    assert [
        (edge.source_id, edge.target_id)
        for edge in index.unresolved()
    ] == [
        (UNRESOLVED_ANNOTATION_ID, MISSING_RESOURCE_ID),
    ]


def test_unresolved_target_is_queryable_even_when_resource_is_missing() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    incoming = index.references_to(MISSING_RESOURCE_ID)

    assert len(incoming) == 1
    assert incoming[0].source_id == UNRESOLVED_ANNOTATION_ID
    assert incoming[0].target_id == MISSING_RESOURCE_ID
    assert incoming[0].reference.extra == {
        "reason": "intentionally-unresolved"
    }
    assert index.resolve(incoming[0]) is None


def test_all_resolved_edges_resolve_to_expected_resource() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    for edge in index.resolved():
        resolved = index.resolve(edge)

        assert resolved is not None
        assert resolved.id == edge.target_id


def test_resources_without_structural_references_have_no_outgoing_edges() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    assert index.references_from(MOLECULE_ID) == []
    assert index.references_from(TARGET_ID) == []
    assert index.references_from(UNKNOWN_RESOURCE_ID) == []
    assert index.references_from(FUTURE_ANNOTATION_ID) == []


def test_missing_source_and_unreferenced_target_queries_are_empty() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    assert index.references_from("not-in-graph") == []
    assert index.references_to("unreferenced-missing-resource") == []


def test_reference_extensions_survive_discovery() -> None:
    index = build_reference_index(make_heterogeneous_graph())

    by_pair = {
        (edge.source_id, edge.target_id): edge
        for edge in index.references()
    }

    assert by_pair[(STIMULUS_ID, MOLECULE_ID)].reference.extra == {
        "role": "source"
    }
    assert by_pair[(OBSERVATION_ID, STIMULUS_ID)].reference.extra == {
        "role": "stimulus"
    }
    assert by_pair[(OBSERVATION_ID, TARGET_ID)].reference.extra == {
        "role": "target"
    }
    assert by_pair[(ANNOTATION_ID, MOLECULE_ID)].reference.extra == {
        "role": "subject"
    }
    assert by_pair[
        (UNRESOLVED_ANNOTATION_ID, MISSING_RESOURCE_ID)
    ].reference.extra == {
        "reason": "intentionally-unresolved"
    }


def test_reference_index_is_snapshot_for_discovered_edges() -> None:
    graph = make_heterogeneous_graph()
    index = build_reference_index(graph)

    graph.resources.append(
        Annotation(
            id="annotation-added-later",
            subject=Reference(resource_id=MOLECULE_ID),
            scheme=Scheme(
                id="org.example.annotation",
                version="0.1",
            ),
            data={"label": "added after index construction"},
        )
    )

    assert len(index) == 5
    assert "annotation-added-later" not in {
        edge.source_id
        for edge in index.references()
    }

    rebuilt = build_reference_index(graph)

    assert len(rebuilt) == 6
    assert "annotation-added-later" in {
        edge.source_id
        for edge in rebuilt.references()
    }


def test_graph_contains_all_expected_resource_families() -> None:
    graph = make_heterogeneous_graph()

    assert isinstance(graph.get(MOLECULE_ID), Molecule)
    assert isinstance(graph.get(STIMULUS_ID), Stimulus)
    assert isinstance(graph.get(TARGET_ID), ObservationTarget)
    assert isinstance(graph.get(OBSERVATION_ID), Observation)
    assert isinstance(graph.get(ANNOTATION_ID), Annotation)
    assert isinstance(graph.get(UNRESOLVED_ANNOTATION_ID), Annotation)
    assert isinstance(graph.get(UNKNOWN_RESOURCE_ID), GenericResource)
    assert isinstance(graph.get(FUTURE_ANNOTATION_ID), GenericResource)
