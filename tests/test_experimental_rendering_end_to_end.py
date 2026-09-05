"""End-to-end tests for the experimental OpenSmell rendering pipeline.

These tests connect structured OpenSmell resources to the experimental
rendering layer and simulated diffuser.

The configured semantic-to-channel bindings are illustrative device policy.
They are not a scientific claim that the configured channels reproduce the
annotated odor.
"""

from __future__ import annotations

from opensmell.experimental.annotation import Annotation
from opensmell.experimental.generic_graph import GenericResourceGraph
from opensmell.experimental.molecule import Molecule
from opensmell.experimental.reference_discovery import build_reference_index
from opensmell.experimental.rendering import RenderRequest
from opensmell.experimental.resources import Reference
from opensmell.experimental.scheme import Scheme
from opensmell.experimental.semantic_channel_mapper import (
    SEMANTIC_ANNOTATIONS_SCHEME,
    SEMANTIC_ANNOTATIONS_SCHEME_VERSION,
    SemanticChannelBinding,
    SemanticChannelMapper,
)
from opensmell.experimental.simulated_diffuser import SimulatedDiffuser


def test_semantic_graph_to_simulated_diffuser_end_to_end() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-demo",
                smiles="CCO",
            ),
            Annotation(
                id="annotation-demo",
                subject=Reference(
                    resource_id="molecule-demo",
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
                            "value": "sweety&gourmand",
                            "state": "present",
                        },
                        {
                            "value": "spice",
                            "state": "absent",
                        },
                        {
                            "value": "woody&mossy",
                            "state": "unknown",
                        },
                    ],
                },
            ),
        ]
    )

    index = build_reference_index(graph)

    request = RenderRequest(
        resource_id="molecule-demo",
        duration=3.0,
    )

    mapper = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=1,
                intensity=0.70,
            ),
            SemanticChannelBinding(
                descriptor="sweety&gourmand",
                channel=2,
                intensity=0.55,
            ),
            SemanticChannelBinding(
                descriptor="spice",
                channel=3,
                intensity=0.90,
            ),
            SemanticChannelBinding(
                descriptor="woody&mossy",
                channel=4,
                intensity=0.40,
            ),
        ]
    )

    plan = mapper.map(
        graph,
        request,
        index=index,
    )

    diffuser = SimulatedDiffuser()
    event = diffuser.render(plan)

    assert [
        (command.channel, command.intensity)
        for command in event.commands
    ] == [
        (1, 0.70),
        (2, 0.55),
    ]
    assert event.duration == 3.0
    assert event.extra["source_resource_id"] == "molecule-demo"
    assert event.extra["annotation_ids"] == ["annotation-demo"]
    assert diffuser.last_event is event


def test_same_opensmell_graph_can_render_differently_for_two_devices() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-demo",
                smiles="CCO",
            ),
            Annotation(
                id="annotation-demo",
                subject=Reference(
                    resource_id="molecule-demo",
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
                            "value": "sweety&gourmand",
                            "state": "present",
                        },
                    ],
                },
            ),
        ]
    )

    request = RenderRequest(
        resource_id="molecule-demo",
        duration=2.0,
    )

    device_a_mapper = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=1,
                intensity=0.70,
            ),
            SemanticChannelBinding(
                descriptor="sweety&gourmand",
                channel=2,
                intensity=0.55,
            ),
        ]
    )

    device_b_mapper = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=8,
                intensity=0.30,
            ),
            SemanticChannelBinding(
                descriptor="sweety&gourmand",
                channel=4,
                intensity=0.85,
            ),
        ]
    )

    device_a = SimulatedDiffuser()
    device_b = SimulatedDiffuser()

    event_a = device_a.render(
        device_a_mapper.map(
            graph,
            request,
        )
    )
    event_b = device_b.render(
        device_b_mapper.map(
            graph,
            request,
        )
    )

    assert [
        (command.channel, command.intensity)
        for command in event_a.commands
    ] == [
        (1, 0.70),
        (2, 0.55),
    ]

    assert [
        (command.channel, command.intensity)
        for command in event_b.commands
    ] == [
        (8, 0.30),
        (4, 0.85),
    ]

    assert event_a.duration == event_b.duration == 2.0
    assert event_a.extra["source_resource_id"] == "molecule-demo"
    assert event_b.extra["source_resource_id"] == "molecule-demo"
