"""Regression tests for the OpenSmell multi-source demonstration.

These tests verify that one GenericResourceGraph can independently produce:

1. a semantic RenderingPlan from an OdorNet Annotation;
2. a quantitative perceptual RenderingPlan from a Keller/Vosshall Observation.

No physical device is required.

The channel bindings used here are experimental demonstration policy.
They are not universal OpenSmell semantics.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opensmell.experimental.annotation import (
    register_annotation_resource_type,
)
from opensmell.experimental.generic_graph import (
    create_default_resource_type_registry,
    generic_graph_loads,
)
from opensmell.experimental.molecule import (
    Molecule,
    register_molecule_resource_type,
)
from opensmell.experimental.perceptual_channel_mapper import (
    PerceptualChannelBinding,
    PerceptualChannelMapper,
)
from opensmell.experimental.rendering import (
    RenderRequest,
)
from opensmell.experimental.resources import (
    Observation,
)
from opensmell.experimental.semantic_channel_mapper import (
    SemanticChannelBinding,
    SemanticChannelMapper,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXAMPLE_PATH = (
    PROJECT_ROOT
    / "examples"
    / "multisource_beta_pinene.osmell"
)


EXPECTED_MOLECULE_ID = (
    "2d5a1039-904c-5b19-a60f-71c1ada5bac2"
)

EXPECTED_OBSERVATION_ID = (
    "7c2fbfd4-ee9f-5e41-a268-a1f5de7c778f"
)

EXPECTED_STIMULUS_ID = (
    "71fae47c-4e96-5a80-a3f9-b6c987a68db1"
)


def load_example_graph():
    """Load the committed multi-source example."""

    registry = (
        create_default_resource_type_registry()
    )

    register_molecule_resource_type(
        registry
    )

    register_annotation_resource_type(
        registry
    )

    return generic_graph_loads(
        EXAMPLE_PATH.read_text(
            encoding="utf-8"
        ),
        registry=registry,
    )


def command_map(plan):
    """Return RenderingPlan commands indexed by channel."""

    return {
        command.channel: command.intensity
        for command in plan.commands
    }


def test_multisource_example_contains_five_resources():
    graph = load_example_graph()

    assert len(graph) == 5


def test_multisource_example_contains_one_molecule():
    graph = load_example_graph()

    molecules = [
        resource
        for resource in graph.resources
        if isinstance(
            resource,
            Molecule,
        )
    ]

    assert len(molecules) == 1
    assert (
        molecules[0].id
        == EXPECTED_MOLECULE_ID
    )


def test_multisource_example_contains_one_observation():
    graph = load_example_graph()

    observations = [
        resource
        for resource in graph.resources
        if isinstance(
            resource,
            Observation,
        )
    ]

    assert len(observations) == 1

    observation = observations[0]

    assert (
        observation.id
        == EXPECTED_OBSERVATION_ID
    )

    assert (
        observation.stimulus.resource_id
        == EXPECTED_STIMULUS_ID
    )


def test_semantic_plan_from_shared_graph():
    graph = load_example_graph()

    mapper = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                "floral",
                0,
                0.25,
            ),
            SemanticChannelBinding(
                "green&herbal",
                1,
                0.60,
            ),
            SemanticChannelBinding(
                "woody&mossy",
                2,
                1.00,
            ),
        ]
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=EXPECTED_MOLECULE_ID,
            duration=5.0,
        ),
    )

    commands = command_map(
        plan
    )

    assert set(commands) == {
        1,
        2,
    }

    assert commands[1] == pytest.approx(
        0.60
    )

    assert commands[2] == pytest.approx(
        1.00
    )

    assert 0 not in commands

    assert plan.duration == pytest.approx(
        5.0
    )

    assert (
        plan.extra["source_resource_id"]
        == EXPECTED_MOLECULE_ID
    )


def test_perceptual_plan_from_shared_graph():
    graph = load_example_graph()

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
            resource_id=EXPECTED_OBSERVATION_ID,
            duration=5.0,
        ),
    )

    commands = command_map(
        plan
    )

    assert set(commands) == {
        0,
        1,
        2,
    }

    assert commands[0] == pytest.approx(
        0.01
    )

    assert commands[1] == pytest.approx(
        0.86
    )

    assert commands[2] == pytest.approx(
        0.97
    )

    assert plan.duration == pytest.approx(
        5.0
    )

    assert (
        plan.extra["source_resource_id"]
        == EXPECTED_OBSERVATION_ID
    )


def test_same_graph_produces_two_distinct_plans():
    graph = load_example_graph()

    semantic_mapper = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                "floral",
                0,
                0.25,
            ),
            SemanticChannelBinding(
                "green&herbal",
                1,
                0.60,
            ),
            SemanticChannelBinding(
                "woody&mossy",
                2,
                1.00,
            ),
        ]
    )

    perceptual_mapper = PerceptualChannelMapper(
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

    semantic_plan = semantic_mapper.map(
        graph,
        RenderRequest(
            resource_id=EXPECTED_MOLECULE_ID,
            duration=5.0,
        ),
    )

    perceptual_plan = perceptual_mapper.map(
        graph,
        RenderRequest(
            resource_id=EXPECTED_OBSERVATION_ID,
            duration=5.0,
        ),
    )

    semantic_commands = command_map(
        semantic_plan
    )

    perceptual_commands = command_map(
        perceptual_plan
    )

    assert semantic_commands != perceptual_commands

    assert semantic_commands == {
        1: pytest.approx(0.60),
        2: pytest.approx(1.00),
    }

    assert perceptual_commands == {
        0: pytest.approx(0.01),
        1: pytest.approx(0.86),
        2: pytest.approx(0.97),
    }

    assert (
        semantic_plan.extra[
            "source_resource_id"
        ]
        == EXPECTED_MOLECULE_ID
    )

    assert (
        perceptual_plan.extra[
            "source_resource_id"
        ]
        == EXPECTED_OBSERVATION_ID
    )