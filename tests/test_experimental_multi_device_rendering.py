"""Experimental multi-device rendering integration tests.

These tests demonstrate that the same OpenSmell olfactory information can be
mapped independently for different rendering devices.

The OpenSmell resources remain device-independent. Device-specific channel
assignments and intensities belong to mapper policy, while technical execution
constraints belong to DeviceCapabilities.

These tests do not claim that any configured channel physically reproduces an
odor. Channels are opaque, device-local identifiers.

This module is experimental and non-normative.
"""

from __future__ import annotations

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
from opensmell.experimental.rendering import (
    RenderRequest,
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


def make_graph() -> GenericResourceGraph:
    """Create device-independent olfactory information."""

    molecule = Molecule(
        id="molecule-coffee-example",
        smiles="CCO",
        extra={
            "example": True,
        },
    )

    annotation = Annotation(
        id="annotation-coffee-example",
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
                    "language": "en",
                    "state": "present",
                },
                {
                    "value": "sweety&gourmand",
                    "language": "en",
                    "state": "present",
                },
                {
                    "value": "spice",
                    "language": "en",
                    "state": "present",
                },
                {
                    "value": "woody&mossy",
                    "language": "en",
                    "state": "absent",
                },
            ],
        },
        extra={
            "example": True,
        },
    )

    return GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )


def make_device_a_capabilities() -> DeviceCapabilities:
    """Device A exposes channels 1, 2, and 3."""

    return DeviceCapabilities(
        device_id="device-a",
        channels=[
            DeviceChannelCapability(
                channel=1,
                min_intensity=0.0,
                max_intensity=0.80,
            ),
            DeviceChannelCapability(
                channel=2,
                min_intensity=0.0,
                max_intensity=0.70,
            ),
            DeviceChannelCapability(
                channel=3,
                min_intensity=0.0,
                max_intensity=0.50,
            ),
        ],
        min_duration=1.0,
        max_duration=10.0,
    )


def make_device_b_capabilities() -> DeviceCapabilities:
    """Device B exposes a completely different channel layout."""

    return DeviceCapabilities(
        device_id="device-b",
        channels=[
            DeviceChannelCapability(
                channel=4,
                min_intensity=0.0,
                max_intensity=0.90,
            ),
            DeviceChannelCapability(
                channel=7,
                min_intensity=0.0,
                max_intensity=0.60,
            ),
            DeviceChannelCapability(
                channel=9,
                min_intensity=0.0,
                max_intensity=0.40,
            ),
        ],
        min_duration=0.5,
        max_duration=5.0,
    )


def make_mapper_a() -> SemanticChannelMapper:
    """Device-specific mapping policy for Device A."""

    return SemanticChannelMapper(
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
                intensity=0.35,
            ),
        ]
    )


def make_mapper_b() -> SemanticChannelMapper:
    """Device-specific mapping policy for Device B."""

    return SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=7,
                intensity=0.50,
            ),
            SemanticChannelBinding(
                descriptor="sweety&gourmand",
                channel=4,
                intensity=0.80,
            ),
            SemanticChannelBinding(
                descriptor="spice",
                channel=9,
                intensity=0.30,
            ),
        ]
    )


def make_request() -> RenderRequest:
    return RenderRequest(
        resource_id="molecule-coffee-example",
        duration=4.0,
    )


def test_same_graph_produces_different_device_specific_plans() -> None:
    graph = make_graph()
    request = make_request()

    plan_a = make_mapper_a().map(
        graph,
        request,
    )

    plan_b = make_mapper_b().map(
        graph,
        request,
    )

    assert [
        (
            command.channel,
            command.intensity,
        )
        for command in plan_a.commands
    ] == [
        (1, 0.70),
        (2, 0.55),
        (3, 0.35),
    ]

    assert [
        (
            command.channel,
            command.intensity,
        )
        for command in plan_b.commands
    ] == [
        (7, 0.50),
        (4, 0.80),
        (9, 0.30),
    ]

    assert plan_a.commands != plan_b.commands

    assert plan_a.duration == 4.0
    assert plan_b.duration == 4.0

    assert (
        plan_a.extra["source_resource_id"]
        == plan_b.extra["source_resource_id"]
        == "molecule-coffee-example"
    )


def test_each_mapper_supports_its_target_device() -> None:
    mapper_a = make_mapper_a()
    mapper_b = make_mapper_b()

    capabilities_a = make_device_a_capabilities()
    capabilities_b = make_device_b_capabilities()

    assert mapper_a.supports(
        capabilities_a
    )

    assert mapper_b.supports(
        capabilities_b
    )

    mapper_a.require_support(
        capabilities_a
    )

    mapper_b.require_support(
        capabilities_b
    )


def test_mappers_are_not_interchangeable_between_devices() -> None:
    mapper_a = make_mapper_a()
    mapper_b = make_mapper_b()

    capabilities_a = make_device_a_capabilities()
    capabilities_b = make_device_b_capabilities()

    assert not mapper_a.supports(
        capabilities_b
    )

    assert not mapper_b.supports(
        capabilities_a
    )


def test_each_plan_is_accepted_by_its_target_device() -> None:
    graph = make_graph()
    request = make_request()

    plan_a = make_mapper_a().map(
        graph,
        request,
    )

    plan_b = make_mapper_b().map(
        graph,
        request,
    )

    capabilities_a = make_device_a_capabilities()
    capabilities_b = make_device_b_capabilities()

    assert capabilities_a.accepts_plan(
        plan_a
    )

    assert capabilities_b.accepts_plan(
        plan_b
    )


def test_each_plan_is_rejected_by_the_other_device() -> None:
    graph = make_graph()
    request = make_request()

    plan_a = make_mapper_a().map(
        graph,
        request,
    )

    plan_b = make_mapper_b().map(
        graph,
        request,
    )

    capabilities_a = make_device_a_capabilities()
    capabilities_b = make_device_b_capabilities()

    assert not capabilities_a.accepts_plan(
        plan_b
    )

    assert not capabilities_b.accepts_plan(
        plan_a
    )


def test_two_simulated_devices_render_their_own_plans() -> None:
    graph = make_graph()
    request = make_request()

    mapper_a = make_mapper_a()
    mapper_b = make_mapper_b()

    capabilities_a = make_device_a_capabilities()
    capabilities_b = make_device_b_capabilities()

    plan_a = mapper_a.map(
        graph,
        request,
    )

    plan_b = mapper_b.map(
        graph,
        request,
    )

    diffuser_a = SimulatedDiffuser(
        capabilities=capabilities_a,
    )

    diffuser_b = SimulatedDiffuser(
        capabilities=capabilities_b,
    )

    event_a = diffuser_a.render(
        plan_a
    )

    event_b = diffuser_b.render(
        plan_b
    )

    assert event_a.duration == 4.0
    assert event_b.duration == 4.0

    assert [
        command.channel
        for command in event_a.commands
    ] == [
        1,
        2,
        3,
    ]

    assert [
        command.channel
        for command in event_b.commands
    ] == [
        7,
        4,
        9,
    ]

    assert diffuser_a.events == [
        event_a
    ]

    assert diffuser_b.events == [
        event_b
    ]


def test_graph_contains_no_device_specific_channel_information() -> None:
    graph = make_graph()

    molecule = graph.require(
        "molecule-coffee-example"
    )

    annotation = graph.require(
        "annotation-coffee-example"
    )

    assert isinstance(
        molecule,
        Molecule,
    )

    assert isinstance(
        annotation,
        Annotation,
    )

    assert "channel" not in molecule.extra
    assert "device_id" not in molecule.extra

    assert "channel" not in annotation.data
    assert "device_id" not in annotation.data

    assert "channel" not in annotation.extra
    assert "device_id" not in annotation.extra


def test_mapping_does_not_mutate_shared_graph_information() -> None:
    graph = make_graph()
    request = make_request()

    molecule_before = graph.require(
        "molecule-coffee-example"
    )

    annotation_before = graph.require(
        "annotation-coffee-example"
    )

    molecule_smiles = molecule_before.smiles
    molecule_extra = dict(
        molecule_before.extra
    )

    annotation_data = {
        "annotations": [
            dict(entry)
            for entry in annotation_before.data[
                "annotations"
            ]
        ]
    }

    annotation_extra = dict(
        annotation_before.extra
    )

    make_mapper_a().map(
        graph,
        request,
    )

    make_mapper_b().map(
        graph,
        request,
    )

    molecule_after = graph.require(
        "molecule-coffee-example"
    )

    annotation_after = graph.require(
        "annotation-coffee-example"
    )

    assert molecule_after.smiles == molecule_smiles
    assert molecule_after.extra == molecule_extra

    assert annotation_after.data == annotation_data
    assert annotation_after.extra == annotation_extra


def test_same_request_identity_is_preserved_across_device_mappings() -> None:
    graph = make_graph()
    request = make_request()

    plan_a = make_mapper_a().map(
        graph,
        request,
    )

    plan_b = make_mapper_b().map(
        graph,
        request,
    )

    assert (
        plan_a.extra["source_resource_id"]
        == request.resource_id
    )

    assert (
        plan_b.extra["source_resource_id"]
        == request.resource_id
    )

    assert (
        plan_a.extra["annotation_ids"]
        == plan_b.extra["annotation_ids"]
        == ["annotation-coffee-example"]
    )