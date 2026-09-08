"""End-to-end software pipeline tests using the real Geraniol .osmell example.

These tests intentionally stop before DeviceTransport.

They verify that a real OpenSmell document can travel through:

    .osmell
        ->
    Core Odor
        ->
    ResourceGraph
        ->
    SemanticChannelMapper
        ->
    RenderingPlan

without requiring an ESP32, serial port, or any other physical device.

Physical transport and hardware validation are documented separately.
"""

from pathlib import Path

import opensmell

from opensmell.experimental.odor_graph_bridge import (
    bridge_odor_to_resource_graph,
)
from opensmell.experimental.rendering import (
    RenderRequest,
)
from opensmell.experimental.semantic_channel_mapper import (
    SemanticChannelBinding,
    SemanticChannelMapper,
)


GERANIOL_PATH = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "geraniol.osmell"
)

EXPECTED_SMILES = "CC(C)=CCC/C(C)=C/CO"

EXPECTED_DESCRIPTOR = "floral"

TEST_CHANNEL = 0

TEST_INTENSITY = 0.7

TEST_DURATION = 4.0


def load_geraniol():
    """Load the committed Geraniol OpenSmell example."""

    assert GERANIOL_PATH.is_file()

    return opensmell.load(
        GERANIOL_PATH
    )


def find_smiles(odor) -> str:
    """Return the chemical SMILES representation."""

    for representation in odor.representations:
        if (
            representation.scheme.id
            == "org.opensmell.chemical.smiles"
        ):
            return representation.data[
                "smiles"
            ]

    raise AssertionError(
        "Geraniol has no chemical SMILES representation"
    )


def find_semantic_states(
    odor,
) -> dict[str, str]:
    """Return semantic annotation states."""

    for representation in odor.representations:
        if (
            representation.scheme.id
            == "org.opensmell.semantic.annotations"
        ):
            return {
                annotation["value"]:
                    annotation["state"]
                for annotation
                in representation.data[
                    "annotations"
                ]
            }

    raise AssertionError(
        "Geraniol has no semantic annotation representation"
    )


def build_rendering_plan():
    """Build the test rendering plan from geraniol.osmell."""

    odor = load_geraniol()

    bridge = bridge_odor_to_resource_graph(
        odor
    )

    mapper = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor=EXPECTED_DESCRIPTOR,
                channel=TEST_CHANNEL,
                intensity=TEST_INTENSITY,
            ),
        ]
    )

    request = RenderRequest(
        resource_id=bridge.primary_resource_id,
        duration=TEST_DURATION,
    )

    plan = mapper.map(
        bridge.graph,
        request,
    )

    return (
        odor,
        bridge,
        plan,
    )


def test_geraniol_example_loads_as_core_odor():
    odor = load_geraniol()

    assert odor.id.startswith(
        "urn:uuid:"
    )

    assert odor.metadata is not None

    assert (
        odor.metadata.labels["en"]
        == "Geraniol"
    )


def test_geraniol_preserves_original_odornet_smiles():
    odor = load_geraniol()

    assert (
        find_smiles(odor)
        == EXPECTED_SMILES
    )


def test_geraniol_preserves_all_odornet_annotation_states():
    odor = load_geraniol()

    states = find_semantic_states(
        odor
    )

    assert len(states) == 12

    assert (
        states[EXPECTED_DESCRIPTOR]
        == "present"
    )

    assert (
        states["pungent&disagreeable"]
        == "absent"
    )

    assert (
        states["animalic&ambery"]
        == "unknown"
    )


def test_geraniol_bridges_to_resource_graph():
    odor = load_geraniol()

    bridge = bridge_odor_to_resource_graph(
        odor
    )

    assert bridge.primary_resource_id

    assert len(
        bridge.annotation_ids
    ) == 1


def test_geraniol_floral_annotation_maps_to_channel_zero():
    (
        _odor,
        _bridge,
        plan,
    ) = build_rendering_plan()

    assert len(
        plan.commands
    ) == 1

    command = plan.commands[0]

    assert (
        command.channel
        == TEST_CHANNEL
    )

    assert (
        command.intensity
        == TEST_INTENSITY
    )


def test_geraniol_rendering_plan_preserves_requested_duration():
    (
        _odor,
        _bridge,
        plan,
    ) = build_rendering_plan()

    assert (
        plan.duration
        == TEST_DURATION
    )


def test_geraniol_pipeline_is_deterministic_for_same_document():
    (
        _odor_a,
        bridge_a,
        plan_a,
    ) = build_rendering_plan()

    (
        _odor_b,
        bridge_b,
        plan_b,
    ) = build_rendering_plan()

    assert (
        bridge_a.primary_resource_id
        == bridge_b.primary_resource_id
    )

    assert (
        bridge_a.annotation_ids
        == bridge_b.annotation_ids
    )

    assert (
        plan_a
        == plan_b
    )