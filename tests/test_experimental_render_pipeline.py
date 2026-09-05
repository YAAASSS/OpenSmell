"""Tests for the experimental high-level rendering pipeline.

The pipeline coordinates device-independent OpenSmell information, mapping
policy, target capabilities, and a DeviceAdapter.

These tests validate orchestration only. They do not claim physical odor
reproduction or define universal channel semantics.

This module is experimental and non-normative.
"""

from __future__ import annotations

from typing import Any

import pytest

from opensmell.experimental.annotation import (
    Annotation,
)
from opensmell.experimental.device_capabilities import (
    DeviceCapabilities,
    DeviceChannelCapability,
)
from opensmell.experimental.generic_graph import (
    GenericResourceGraph,
)
from opensmell.experimental.molecule import (
    Molecule,
)
from opensmell.experimental.render_pipeline import (
    build_rendering_plan,
    render_to_device,
)
from opensmell.experimental.rendering import (
    RenderRequest,
    RenderingPlan,
)
from opensmell.experimental.resources import (
    Reference,
)
from opensmell.experimental.scheme import (
    Scheme,
)
from opensmell.experimental.semantic_channel_mapper import (
    SEMANTIC_ANNOTATIONS_SCHEME,
    SEMANTIC_ANNOTATIONS_SCHEME_VERSION,
    SemanticChannelBinding,
    SemanticChannelMapper,
)
from opensmell.experimental.simulated_diffuser import (
    SimulatedDiffuser,
)


def graph() -> GenericResourceGraph:
    molecule = Molecule(
        id="pipeline-molecule",
        smiles="CCO",
    )

    annotation = Annotation(
        id="pipeline-annotation",
        subject=Reference(
            resource_id=molecule.id,
        ),
        scheme=Scheme(
            id=SEMANTIC_ANNOTATIONS_SCHEME,
            version=SEMANTIC_ANNOTATIONS_SCHEME_VERSION,
        ),
        data={
            "annotations": [
                {
                    "value": "floral",
                    "state": "present",
                },
                {
                    "value": "spice",
                    "state": "present",
                },
                {
                    "value": "woody&mossy",
                    "state": "absent",
                },
            ],
        },
    )

    return GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )


def mapper() -> SemanticChannelMapper:
    return SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=1,
                intensity=0.7,
            ),
            SemanticChannelBinding(
                descriptor="spice",
                channel=2,
                intensity=0.4,
            ),
        ]
    )


def capabilities() -> DeviceCapabilities:
    return DeviceCapabilities(
        device_id="pipeline-device",
        channels=[
            DeviceChannelCapability(
                channel=1,
                min_intensity=0.0,
                max_intensity=0.8,
            ),
            DeviceChannelCapability(
                channel=2,
                min_intensity=0.0,
                max_intensity=0.5,
            ),
        ],
        min_duration=1.0,
        max_duration=5.0,
    )


def request(
    duration: float = 3.0,
) -> RenderRequest:
    return RenderRequest(
        resource_id="pipeline-molecule",
        duration=duration,
    )


def adapter() -> SimulatedDiffuser:
    return SimulatedDiffuser(
        capabilities=capabilities(),
    )


def test_build_rendering_plan_returns_validated_plan() -> None:
    target = adapter()

    plan = build_rendering_plan(
        graph(),
        request(),
        mapper(),
        target,
    )

    assert isinstance(
        plan,
        RenderingPlan,
    )

    assert [
        (
            command.channel,
            command.intensity,
        )
        for command in plan.commands
    ] == [
        (1, 0.7),
        (2, 0.4),
    ]

    assert plan.duration == 3.0

    assert target.capabilities is not None
    assert target.capabilities.accepts_plan(
        plan
    )


def test_build_rendering_plan_does_not_execute_adapter() -> None:
    target = adapter()

    plan = build_rendering_plan(
        graph(),
        request(),
        mapper(),
        target,
    )

    assert isinstance(
        plan,
        RenderingPlan,
    )

    assert target.events == []


def test_render_to_device_executes_validated_plan() -> None:
    target = adapter()

    event = render_to_device(
        graph(),
        request(),
        mapper(),
        target,
    )

    assert event.duration == 3.0

    assert [
        (
            command.channel,
            command.intensity,
        )
        for command in event.commands
    ] == [
        (1, 0.7),
        (2, 0.4),
    ]

    assert target.events == [
        event
    ]


def test_render_to_device_returns_adapter_result_unchanged() -> None:
    target = adapter()

    result = render_to_device(
        graph(),
        request(),
        mapper(),
        target,
    )

    assert result is target.last_event


def test_pipeline_rejects_mapper_incompatible_with_device() -> None:
    incompatible_mapper = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=9,
                intensity=0.7,
            ),
        ]
    )

    target = adapter()

    with pytest.raises(
        ValueError,
        match=(
            "semantic channel mapper is not compatible"
        ),
    ):
        render_to_device(
            graph(),
            request(),
            incompatible_mapper,
            target,
        )

    assert target.events == []


def test_pipeline_rejects_request_duration_before_render() -> None:
    target = adapter()

    with pytest.raises(
        ValueError,
    ):
        render_to_device(
            graph(),
            request(
                duration=10.0,
            ),
            mapper(),
            target,
        )

    assert target.events == []


def test_build_plan_rejects_request_duration() -> None:
    target = adapter()

    with pytest.raises(
        ValueError,
    ):
        build_rendering_plan(
            graph(),
            request(
                duration=10.0,
            ),
            mapper(),
            target,
        )

    assert target.events == []


def test_pipeline_rejects_legacy_unconstrained_simulator() -> None:
    target = SimulatedDiffuser()

    with pytest.raises(
        TypeError,
        match=(
            "adapter.capabilities must be "
            "a DeviceCapabilities"
        ),
    ):
        render_to_device(
            graph(),
            request(),
            mapper(),
            target,
        )

    assert target.events == []


@pytest.mark.parametrize(
    "invalid_graph",
    [
        None,
        {},
        [],
        "graph",
    ],
)
def test_pipeline_rejects_invalid_graph(
    invalid_graph: Any,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "graph must be a GenericResourceGraph"
        ),
    ):
        render_to_device(
            invalid_graph,
            request(),
            mapper(),
            adapter(),
        )


@pytest.mark.parametrize(
    "invalid_request",
    [
        None,
        {},
        [],
        "request",
    ],
)
def test_pipeline_rejects_invalid_request(
    invalid_request: Any,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a RenderRequest"
        ),
    ):
        render_to_device(
            graph(),
            invalid_request,
            mapper(),
            adapter(),
        )


@pytest.mark.parametrize(
    "invalid_mapper",
    [
        None,
        {},
        [],
        "mapper",
    ],
)
def test_pipeline_rejects_invalid_mapper(
    invalid_mapper: Any,
) -> None:
    with pytest.raises(
        TypeError,
        match=(
            "mapper must be a SemanticChannelMapper"
        ),
    ):
        render_to_device(
            graph(),
            request(),
            invalid_mapper,
            adapter(),
        )


def test_build_plan_rejects_invalid_graph() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "graph must be a GenericResourceGraph"
        ),
    ):
        build_rendering_plan(
            {},
            request(),
            mapper(),
            adapter(),
        )


def test_build_plan_rejects_invalid_request() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "request must be a RenderRequest"
        ),
    ):
        build_rendering_plan(
            graph(),
            {},
            mapper(),
            adapter(),
        )


def test_build_plan_rejects_invalid_mapper() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "mapper must be a SemanticChannelMapper"
        ),
    ):
        build_rendering_plan(
            graph(),
            request(),
            {},
            adapter(),
        )


def test_same_information_can_render_through_two_pipeline_targets() -> None:
    shared_graph = graph()
    shared_request = request()

    mapper_a = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=1,
                intensity=0.7,
            ),
            SemanticChannelBinding(
                descriptor="spice",
                channel=2,
                intensity=0.4,
            ),
        ]
    )

    capabilities_a = DeviceCapabilities(
        device_id="pipeline-device-a",
        channels=[
            DeviceChannelCapability(
                channel=1,
            ),
            DeviceChannelCapability(
                channel=2,
            ),
        ],
        min_duration=1.0,
        max_duration=5.0,
    )

    target_a = SimulatedDiffuser(
        capabilities=capabilities_a,
    )

    mapper_b = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=7,
                intensity=0.5,
            ),
            SemanticChannelBinding(
                descriptor="spice",
                channel=9,
                intensity=0.3,
            ),
        ]
    )

    capabilities_b = DeviceCapabilities(
        device_id="pipeline-device-b",
        channels=[
            DeviceChannelCapability(
                channel=7,
            ),
            DeviceChannelCapability(
                channel=9,
            ),
        ],
        min_duration=1.0,
        max_duration=5.0,
    )

    target_b = SimulatedDiffuser(
        capabilities=capabilities_b,
    )

    event_a = render_to_device(
        shared_graph,
        shared_request,
        mapper_a,
        target_a,
    )

    event_b = render_to_device(
        shared_graph,
        shared_request,
        mapper_b,
        target_b,
    )

    assert [
        command.channel
        for command in event_a.commands
    ] == [
        1,
        2,
    ]

    assert [
        command.channel
        for command in event_b.commands
    ] == [
        7,
        9,
    ]

    assert (
        event_a.extra["source_resource_id"]
        == event_b.extra["source_resource_id"]
        == shared_request.resource_id
    )