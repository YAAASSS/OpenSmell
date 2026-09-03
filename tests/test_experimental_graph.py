"""Tests for the experimental OpenSmell resource graph."""

import pytest

from opensmell.experimental.graph import ResourceGraph
from opensmell.experimental.resources import (
    Observation,
    ObservationTarget,
    Reference,
    Result,
    ResultScheme,
    Stimulus,
)


def make_result(
    scheme_id: str = "org.opensmell.experimental.test",
    version: str = "0.1",
) -> Result:
    return Result(
        scheme=ResultScheme(
            id=scheme_id,
            version=version,
        ),
        data={
            "value": 1.0,
        },
    )


def make_graph() -> ResourceGraph:
    stimulus = Stimulus(
        id="stimulus-1",
    )

    target = ObservationTarget(
        id="target-1",
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference("stimulus-1"),
        target=Reference("target-1"),
        results=[
            make_result(),
        ],
    )

    return ResourceGraph(
        resources=[
            stimulus,
            target,
            observation,
        ]
    )


def test_empty_graph_is_allowed():
    graph = ResourceGraph()

    assert len(graph) == 0
    assert graph.resources == []
    assert graph.extra == {}


def test_graph_accepts_resources():
    graph = make_graph()

    assert len(graph) == 3


def test_graph_iteration_preserves_order():
    graph = make_graph()

    assert [resource.id for resource in graph] == [
        "stimulus-1",
        "target-1",
        "observation-1",
    ]


def test_ids_returns_all_resource_ids():
    graph = make_graph()

    assert graph.ids() == {
        "stimulus-1",
        "target-1",
        "observation-1",
    }


def test_get_returns_resource():
    graph = make_graph()

    resource = graph.get("stimulus-1")

    assert isinstance(resource, Stimulus)
    assert resource.id == "stimulus-1"


def test_get_returns_none_for_unknown_id():
    graph = make_graph()

    assert graph.get("missing") is None


def test_get_rejects_non_string_id():
    graph = make_graph()

    with pytest.raises(TypeError):
        graph.get(123)


def test_require_returns_resource():
    graph = make_graph()

    resource = graph.require("target-1")

    assert isinstance(resource, ObservationTarget)


def test_require_raises_for_unknown_resource():
    graph = make_graph()

    with pytest.raises(KeyError):
        graph.require("missing")


def test_duplicate_resource_ids_are_rejected():
    graph_resources = [
        Stimulus(id="same-id"),
        ObservationTarget(id="same-id"),
    ]

    with pytest.raises(ValueError):
        ResourceGraph(resources=graph_resources)


def test_resources_must_be_list():
    with pytest.raises(TypeError):
        ResourceGraph(resources=())


def test_resources_reject_unknown_object():
    with pytest.raises(TypeError):
        ResourceGraph(
            resources=[
                Stimulus(id="stimulus-1"),
                object(),
            ]
        )


def test_extra_is_preserved():
    graph = ResourceGraph(
        extra={
            "vendor.example": {
                "hello": "world",
            }
        }
    )

    assert graph.extra == {
        "vendor.example": {
            "hello": "world",
        }
    }


def test_extra_must_be_dict():
    with pytest.raises(TypeError):
        ResourceGraph(extra=[])


def test_resolve_stimulus_reference():
    graph = make_graph()

    reference = Reference("stimulus-1")

    resource = graph.resolve(reference)

    assert isinstance(resource, Stimulus)
    assert resource.id == "stimulus-1"


def test_resolve_target_reference():
    graph = make_graph()

    reference = Reference("target-1")

    resource = graph.resolve(reference)

    assert isinstance(resource, ObservationTarget)
    assert resource.id == "target-1"


def test_resolve_unknown_reference_returns_none():
    graph = make_graph()

    assert graph.resolve(Reference("missing")) is None


def test_resolve_rejects_non_reference():
    graph = make_graph()

    with pytest.raises(TypeError):
        graph.resolve("stimulus-1")


def test_references_collect_observation_references():
    graph = make_graph()

    references = graph.references()

    assert [reference.resource_id for reference in references] == [
        "stimulus-1",
        "target-1",
    ]


def test_references_collect_stimulus_source():
    source = Stimulus(
        id="source-resource",
    )

    stimulus = Stimulus(
        id="stimulus-1",
        source=Reference("source-resource"),
    )

    graph = ResourceGraph(
        resources=[
            source,
            stimulus,
        ]
    )

    references = graph.references()

    assert [reference.resource_id for reference in references] == [
        "source-resource",
    ]


def test_references_preserve_occurrences():
    stimulus = Stimulus(
        id="stimulus-1",
    )

    observation_1 = Observation(
        id="observation-1",
        stimulus=Reference("stimulus-1"),
    )

    observation_2 = Observation(
        id="observation-2",
        stimulus=Reference("stimulus-1"),
    )

    graph = ResourceGraph(
        resources=[
            stimulus,
            observation_1,
            observation_2,
        ]
    )

    references = graph.references()

    assert [reference.resource_id for reference in references] == [
        "stimulus-1",
        "stimulus-1",
    ]


def test_unresolved_reference_is_allowed():
    observation = Observation(
        id="observation-1",
        stimulus=Reference("missing-stimulus"),
    )

    graph = ResourceGraph(
        resources=[
            observation,
        ]
    )

    assert len(graph) == 1


def test_unresolved_references_are_reported():
    observation = Observation(
        id="observation-1",
        stimulus=Reference("missing-stimulus"),
        target=Reference("missing-target"),
    )

    graph = ResourceGraph(
        resources=[
            observation,
        ]
    )

    unresolved = graph.unresolved_references()

    assert [reference.resource_id for reference in unresolved] == [
        "missing-stimulus",
        "missing-target",
    ]


def test_duplicate_unresolved_reference_occurrences_are_preserved():
    observation_1 = Observation(
        id="observation-1",
        stimulus=Reference("missing"),
    )

    observation_2 = Observation(
        id="observation-2",
        stimulus=Reference("missing"),
    )

    graph = ResourceGraph(
        resources=[
            observation_1,
            observation_2,
        ]
    )

    unresolved = graph.unresolved_references()

    assert [reference.resource_id for reference in unresolved] == [
        "missing",
        "missing",
    ]


def test_unresolved_reference_ids_are_unique():
    observation_1 = Observation(
        id="observation-1",
        stimulus=Reference("missing"),
    )

    observation_2 = Observation(
        id="observation-2",
        stimulus=Reference("missing"),
        target=Reference("another-missing"),
    )

    graph = ResourceGraph(
        resources=[
            observation_1,
            observation_2,
        ]
    )

    assert graph.unresolved_reference_ids() == {
        "missing",
        "another-missing",
    }


def test_graph_is_fully_resolved():
    graph = make_graph()

    assert graph.is_fully_resolved() is True


def test_graph_with_unresolved_reference_is_not_fully_resolved():
    observation = Observation(
        id="observation-1",
        stimulus=Reference("missing"),
    )

    graph = ResourceGraph(
        resources=[
            observation,
        ]
    )

    assert graph.is_fully_resolved() is False


def test_resources_of_type_returns_stimuli():
    graph = make_graph()

    resources = graph.resources_of_type(Stimulus)

    assert len(resources) == 1
    assert resources[0].id == "stimulus-1"


def test_resources_of_type_returns_targets():
    graph = make_graph()

    resources = graph.resources_of_type(ObservationTarget)

    assert len(resources) == 1
    assert resources[0].id == "target-1"


def test_resources_of_type_returns_observations():
    graph = make_graph()

    resources = graph.resources_of_type(Observation)

    assert len(resources) == 1
    assert resources[0].id == "observation-1"


def test_resources_of_type_rejects_unknown_class():
    graph = make_graph()

    with pytest.raises(TypeError):
        graph.resources_of_type(Result)


def test_result_payload_is_not_scanned_for_references():
    stimulus = Stimulus(
        id="stimulus-1",
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference("stimulus-1"),
        results=[
            Result(
                scheme=ResultScheme(
                    id="vendor.example.references",
                    version="99.0",
                ),
                data={
                    "resource_id": "missing-resource",
                    "nested": {
                        "resource_id": "another-missing-resource",
                    },
                },
            )
        ],
    )

    graph = ResourceGraph(
        resources=[
            stimulus,
            observation,
        ]
    )

    assert graph.is_fully_resolved() is True
    assert graph.unresolved_references() == []


def test_unknown_result_scheme_does_not_affect_graph():
    stimulus = Stimulus(
        id="stimulus-1",
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference("stimulus-1"),
        results=[
            Result(
                scheme=ResultScheme(
                    id="vendor.example.unknown",
                    version="123.456",
                ),
                data={
                    "value": -0.0,
                },
            )
        ],
    )

    graph = ResourceGraph(
        resources=[
            stimulus,
            observation,
        ]
    )

    assert graph.is_fully_resolved() is True

    result = observation.results[0]

    assert result.scheme.id == "vendor.example.unknown"
    assert result.scheme.version == "123.456"
    assert result.data["value"] == -0.0


def test_graph_preserves_multiple_result_schemes():
    stimulus = Stimulus(
        id="stimulus-1",
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference("stimulus-1"),
        results=[
            Result(
                scheme=ResultScheme(
                    id="scheme.one",
                    version="0.1",
                ),
                data={
                    "value": 1,
                },
            ),
            Result(
                scheme=ResultScheme(
                    id="scheme.two",
                    version="7.0",
                ),
                data={
                    "value": 2,
                },
            ),
        ],
    )

    graph = ResourceGraph(
        resources=[
            stimulus,
            observation,
        ]
    )

    assert len(graph) == 2

    assert [
        (result.scheme.id, result.scheme.version)
        for result in observation.results
    ] == [
        ("scheme.one", "0.1"),
        ("scheme.two", "7.0"),
    ]