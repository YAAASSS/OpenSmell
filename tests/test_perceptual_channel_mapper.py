"""Tests for the experimental perceptual channel mapper."""

from __future__ import annotations

import pytest

from opensmell.experimental.generic_graph import GenericResourceGraph
from opensmell.experimental.perceptual_channel_mapper import (
    PerceptualChannelBinding,
    PerceptualChannelMapper,
)
from opensmell.experimental.rendering import RenderRequest
from opensmell.experimental.resources import (
    Observation,
    Reference,
    Result,
    ResultScheme,
    Stimulus,
)


SCHEME_ID = "org.opensmell.perceptual.measurements"
SCHEME_VERSION = "0.1"


def _measurement(
    property_name: str,
    value: int | float,
    minimum: int | float = 0,
    maximum: int | float = 100,
) -> dict:
    return {
        "property": property_name,
        "value": value,
        "scale": {
            "min": minimum,
            "max": maximum,
        },
    }


def _graph_with_measurements(
    measurements: list[dict],
    *,
    scheme_id: str = SCHEME_ID,
    scheme_version: str = SCHEME_VERSION,
) -> tuple[GenericResourceGraph, str]:
    stimulus = Stimulus(
        id="stimulus-1",
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id=stimulus.id,
        ),
        results=[
            Result(
                scheme=ResultScheme(
                    id=scheme_id,
                    version=scheme_version,
                ),
                data={
                    "measurements": measurements,
                },
            )
        ],
    )

    graph = GenericResourceGraph(
        resources=[
            stimulus,
            observation,
        ]
    )

    return graph, observation.id


def test_maps_quantitative_measurements_to_channels() -> None:
    graph, observation_id = _graph_with_measurements(
        [
            _measurement("flower", 1),
            _measurement("grass", 86),
            _measurement("wood", 97),
        ]
    )

    mapper = PerceptualChannelMapper(
        bindings=[
            PerceptualChannelBinding(
                "flower",
                0,
            ),
            PerceptualChannelBinding(
                "grass",
                1,
            ),
            PerceptualChannelBinding(
                "wood",
                2,
            ),
        ]
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=observation_id,
            duration=5.0,
        ),
    )

    commands = {
        command.channel: command.intensity
        for command in plan.commands
    }

    assert commands == pytest.approx(
        {
            0: 0.01,
            1: 0.86,
            2: 0.97,
        }
    )

    assert plan.duration == 5.0

    assert plan.extra["mapper"] == (
        "org.opensmell.experimental."
        "perceptual-channel-mapper"
    )

    assert (
        plan.extra["source_resource_id"]
        == observation_id
    )

    assert plan.extra["result_indexes"] == [0]


def test_uses_explicit_measurement_scale() -> None:
    graph, observation_id = _graph_with_measurements(
        [
            _measurement(
                "flower",
                15,
                minimum=10,
                maximum=20,
            )
        ]
    )

    mapper = PerceptualChannelMapper(
        bindings=[
            PerceptualChannelBinding(
                "flower",
                0,
            )
        ]
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=observation_id,
            duration=1.0,
        ),
    )

    assert len(plan.commands) == 1
    assert plan.commands[0].channel == 0
    assert plan.commands[0].intensity == pytest.approx(
        0.5
    )


def test_zero_maps_to_zero_intensity() -> None:
    graph, observation_id = _graph_with_measurements(
        [
            _measurement(
                "flower",
                0,
            )
        ]
    )

    mapper = PerceptualChannelMapper(
        bindings=[
            PerceptualChannelBinding(
                "flower",
                0,
            )
        ]
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=observation_id,
            duration=1.0,
        ),
    )

    assert len(plan.commands) == 1
    assert plan.commands[0].intensity == pytest.approx(
        0.0
    )


def test_scale_maximum_maps_to_one() -> None:
    graph, observation_id = _graph_with_measurements(
        [
            _measurement(
                "flower",
                100,
            )
        ]
    )

    mapper = PerceptualChannelMapper(
        bindings=[
            PerceptualChannelBinding(
                "flower",
                0,
            )
        ]
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=observation_id,
            duration=1.0,
        ),
    )

    assert len(plan.commands) == 1
    assert plan.commands[0].intensity == pytest.approx(
        1.0
    )


def test_unconfigured_measurement_is_ignored() -> None:
    graph, observation_id = _graph_with_measurements(
        [
            _measurement(
                "unconfigured-property",
                50,
            )
        ]
    )

    mapper = PerceptualChannelMapper(
        bindings=[
            PerceptualChannelBinding(
                "flower",
                0,
            )
        ]
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=observation_id,
            duration=1.0,
        ),
    )

    assert plan.commands == []


def test_wrong_scheme_is_ignored() -> None:
    graph, observation_id = _graph_with_measurements(
        [
            _measurement(
                "flower",
                100,
            )
        ],
        scheme_id="example.other.scheme",
    )

    mapper = PerceptualChannelMapper(
        bindings=[
            PerceptualChannelBinding(
                "flower",
                0,
            )
        ]
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=observation_id,
            duration=1.0,
        ),
    )

    assert plan.commands == []
    assert plan.extra["result_indexes"] == []


def test_wrong_scheme_version_is_ignored() -> None:
    graph, observation_id = _graph_with_measurements(
        [
            _measurement(
                "flower",
                100,
            )
        ],
        scheme_version="999",
    )

    mapper = PerceptualChannelMapper(
        bindings=[
            PerceptualChannelBinding(
                "flower",
                0,
            )
        ]
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=observation_id,
            duration=1.0,
        ),
    )

    assert plan.commands == []
    assert plan.extra["result_indexes"] == []


def test_duplicate_property_binding_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="duplicate perceptual property binding",
    ):
        PerceptualChannelMapper(
            bindings=[
                PerceptualChannelBinding(
                    "flower",
                    0,
                ),
                PerceptualChannelBinding(
                    "flower",
                    1,
                ),
            ]
        )


def test_duplicate_channel_binding_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="duplicate device channel binding",
    ):
        PerceptualChannelMapper(
            bindings=[
                PerceptualChannelBinding(
                    "flower",
                    0,
                ),
                PerceptualChannelBinding(
                    "grass",
                    0,
                ),
            ]
        )


def test_non_observation_resource_is_rejected() -> None:
    stimulus = Stimulus(
        id="stimulus-1",
    )

    graph = GenericResourceGraph(
        resources=[
            stimulus,
        ]
    )

    mapper = PerceptualChannelMapper(
        bindings=[]
    )

    with pytest.raises(
        ValueError,
        match=(
            "perceptual channel mapper requires "
            "an Observation resource"
        ),
    ):
        mapper.map(
            graph,
            RenderRequest(
                resource_id=stimulus.id,
                duration=1.0,
            ),
        )


def test_missing_resource_is_rejected() -> None:
    graph = GenericResourceGraph(
        resources=[]
    )

    mapper = PerceptualChannelMapper(
        bindings=[]
    )

    with pytest.raises(
        ValueError,
        match="render request resource does not exist",
    ):
        mapper.map(
            graph,
            RenderRequest(
                resource_id="missing-resource",
                duration=1.0,
            ),
        )


def test_malformed_measurements_are_ignored() -> None:
    graph, observation_id = _graph_with_measurements(
        [
            {},
            {
                "property": "flower",
                "value": "not-numeric",
                "scale": {
                    "min": 0,
                    "max": 100,
                },
            },
            {
                "property": "grass",
                "value": 50,
                "scale": {
                    "min": 100,
                    "max": 0,
                },
            },
            {
                "property": "wood",
                "value": 101,
                "scale": {
                    "min": 0,
                    "max": 100,
                },
            },
        ]
    )

    mapper = PerceptualChannelMapper(
        bindings=[
            PerceptualChannelBinding(
                "flower",
                0,
            ),
            PerceptualChannelBinding(
                "grass",
                1,
            ),
            PerceptualChannelBinding(
                "wood",
                2,
            ),
        ]
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=observation_id,
            duration=1.0,
        ),
    )

    assert plan.commands == []


def test_only_one_command_is_emitted_per_channel() -> None:
    graph, observation_id = _graph_with_measurements(
        [
            _measurement(
                "flower",
                25,
            ),
            _measurement(
                "flower",
                75,
            ),
        ]
    )

    mapper = PerceptualChannelMapper(
        bindings=[
            PerceptualChannelBinding(
                "flower",
                0,
            )
        ]
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=observation_id,
            duration=1.0,
        ),
    )

    assert len(plan.commands) == 1
    assert plan.commands[0].channel == 0
    assert plan.commands[0].intensity == pytest.approx(
        0.25
    )