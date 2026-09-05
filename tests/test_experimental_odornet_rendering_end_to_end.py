"""End-to-end OdorNet rendering tests for OpenSmell.

These tests demonstrate an OdorNet-shaped record flowing through the existing
OpenSmell OdorNet adapter, then being bridged into the experimental resource
graph and rendering layers.

They also demonstrate that the same OpenSmell graph and RenderingPlan may be
accepted or rejected depending on the technical capabilities of the target
device.

The semantic-to-channel bindings are illustrative device policy only. They do
not claim that the configured channels physically reproduce the source odor.
"""

from __future__ import annotations

import pytest

from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    ANNOTATION_SCHEME_VERSION,
    from_record_with_annotations,
)
from opensmell.experimental.annotation import Annotation
from opensmell.experimental.device_capabilities import (
    DeviceCapabilities,
    DeviceChannelCapability,
)
from opensmell.experimental.generic_graph import GenericResourceGraph
from opensmell.experimental.molecule import Molecule
from opensmell.experimental.rendering import (
    RenderingPlan,
    RenderRequest,
)
from opensmell.experimental.resources import Reference
from opensmell.experimental.scheme import Scheme as ExperimentalScheme
from opensmell.experimental.semantic_channel_mapper import (
    SemanticChannelBinding,
    SemanticChannelMapper,
)
from opensmell.experimental.simulated_diffuser import SimulatedDiffuser


def make_odornet_graph() -> tuple[
    GenericResourceGraph,
    Molecule,
    Annotation,
]:
    """Build the shared OdorNet-shaped graph used by rendering tests."""

    record = {
        "SMILES": "CCO",
        "animalic&ambery": 0,
        "sweety&gourmand": 1,
        "floral": 1,
        "fruity&vegetable": 0,
        "pungent&disagreeable": 0,
        "green&herbal": 0,
        "nutty": None,
        "woody&mossy": 0,
        "resinous&balsamic": 0,
        "cooked": 0,
        "odorless": 0,
        "spice": 1,
    }

    odor = from_record_with_annotations(
        record,
        odor_id="odornet-demo",
    )

    chemical = next(
        representation
        for representation in odor.representations
        if representation.type == "chemical"
    )

    semantic = next(
        representation
        for representation in odor.representations
        if (
            representation.scheme.id
            == ANNOTATION_SCHEME_ID
            and representation.scheme.version
            == ANNOTATION_SCHEME_VERSION
        )
    )

    molecule = Molecule(
        id="molecule-odornet-demo",
        smiles=chemical.data["smiles"],
        extra={
            "provenance": chemical.extra["provenance"],
        },
    )

    annotation = Annotation(
        id="annotation-odornet-demo",
        subject=Reference(
            resource_id=molecule.id,
        ),
        scheme=ExperimentalScheme(
            id=semantic.scheme.id,
            version=semantic.scheme.version,
        ),
        data=semantic.data,
        extra={
            "provenance": semantic.extra["provenance"],
        },
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )

    return (
        graph,
        molecule,
        annotation,
    )


def make_mapper() -> SemanticChannelMapper:
    """Build the illustrative semantic-to-device mapping policy."""

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
            SemanticChannelBinding(
                descriptor="nutty",
                channel=4,
                intensity=0.80,
            ),
        ]
    )


def make_rendering_plan() -> tuple[
    GenericResourceGraph,
    Molecule,
    Annotation,
    RenderingPlan,
]:
    """Build the shared graph and map it to one RenderingPlan."""

    (
        graph,
        molecule,
        annotation,
    ) = make_odornet_graph()

    request = RenderRequest(
        resource_id=molecule.id,
        duration=4.0,
    )

    plan = make_mapper().map(
        graph,
        request,
    )

    return (
        graph,
        molecule,
        annotation,
        plan,
    )


def make_compatible_device_capabilities() -> DeviceCapabilities:
    """Capabilities that accept every command produced by the mapper."""

    return DeviceCapabilities(
        device_id="compatible-simulated-diffuser",
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


def test_real_odornet_shaped_record_to_simulated_diffuser() -> None:
    (
        graph,
        molecule,
        annotation,
        plan,
    ) = make_rendering_plan()

    assert len(graph.resources) == 2

    diffuser = SimulatedDiffuser()

    event = diffuser.render(
        plan
    )

    assert molecule.smiles == "CCO"

    assert molecule.extra["provenance"] == {
        "source": "OdorNet",
    }

    assert annotation.extra["provenance"] == {
        "source": "OdorNet",
    }

    assert [
        (
            command.channel,
            command.intensity,
        )
        for command in event.commands
    ] == [
        (2, 0.55),
        (1, 0.70),
        (3, 0.35),
    ]

    assert event.duration == 4.0

    assert (
        event.extra[
            "source_resource_id"
        ]
        == molecule.id
    )

    assert event.extra[
        "annotation_ids"
    ] == [
        annotation.id,
    ]


def test_odornet_rendering_plan_is_accepted_by_compatible_device() -> None:
    (
        _graph,
        molecule,
        annotation,
        plan,
    ) = make_rendering_plan()

    capabilities = (
        make_compatible_device_capabilities()
    )

    diffuser = SimulatedDiffuser(
        capabilities=capabilities,
    )

    assert capabilities.accepts_plan(
        plan
    )

    event = diffuser.render(
        plan
    )

    assert [
        (
            command.channel,
            command.intensity,
        )
        for command in event.commands
    ] == [
        (2, 0.55),
        (1, 0.70),
        (3, 0.35),
    ]

    assert event.duration == 4.0

    assert (
        event.extra[
            "source_resource_id"
        ]
        == molecule.id
    )

    assert event.extra[
        "annotation_ids"
    ] == [
        annotation.id,
    ]

    assert diffuser.events == [
        event,
    ]

    assert diffuser.last_event is event


def test_same_odornet_plan_is_rejected_by_device_missing_channel() -> None:
    (
        _graph,
        _molecule,
        _annotation,
        plan,
    ) = make_rendering_plan()

    incompatible_capabilities = DeviceCapabilities(
        device_id="limited-simulated-diffuser",
        channels=[
            DeviceChannelCapability(
                channel=1,
            ),
            DeviceChannelCapability(
                channel=2,
            ),
        ],
        min_duration=1.0,
        max_duration=10.0,
    )

    diffuser = SimulatedDiffuser(
        capabilities=incompatible_capabilities,
    )

    assert not incompatible_capabilities.accepts_plan(
        plan
    )

    with pytest.raises(
        ValueError,
        match="rendering channel is not supported",
    ):
        diffuser.render(
            plan
        )

    assert diffuser.events == []
    assert diffuser.last_event is None


def test_same_odornet_plan_is_rejected_by_device_intensity_limit() -> None:
    (
        _graph,
        _molecule,
        _annotation,
        plan,
    ) = make_rendering_plan()

    incompatible_capabilities = DeviceCapabilities(
        device_id="low-intensity-simulated-diffuser",
        channels=[
            DeviceChannelCapability(
                channel=1,
                min_intensity=0.0,
                max_intensity=0.60,
            ),
            DeviceChannelCapability(
                channel=2,
            ),
            DeviceChannelCapability(
                channel=3,
            ),
        ],
        min_duration=1.0,
        max_duration=10.0,
    )

    diffuser = SimulatedDiffuser(
        capabilities=incompatible_capabilities,
    )

    assert not incompatible_capabilities.accepts_plan(
        plan
    )

    with pytest.raises(
        ValueError,
        match="rendering intensity is not supported",
    ):
        diffuser.render(
            plan
        )

    assert diffuser.events == []
    assert diffuser.last_event is None


def test_same_odornet_plan_is_rejected_by_device_duration_limit() -> None:
    (
        _graph,
        _molecule,
        _annotation,
        plan,
    ) = make_rendering_plan()

    incompatible_capabilities = DeviceCapabilities(
        device_id="short-duration-simulated-diffuser",
        channels=[
            DeviceChannelCapability(
                channel=1,
            ),
            DeviceChannelCapability(
                channel=2,
            ),
            DeviceChannelCapability(
                channel=3,
            ),
        ],
        min_duration=0.1,
        max_duration=2.0,
    )

    diffuser = SimulatedDiffuser(
        capabilities=incompatible_capabilities,
    )

    assert not incompatible_capabilities.accepts_plan(
        plan
    )

    with pytest.raises(
        ValueError,
        match="rendering duration is not supported",
    ):
        diffuser.render(
            plan
        )

    assert diffuser.events == []
    assert diffuser.last_event is None


def test_same_odornet_graph_can_target_different_devices() -> None:
    (
        graph,
        molecule,
        _annotation,
    ) = make_odornet_graph()

    request = RenderRequest(
        resource_id=molecule.id,
        duration=4.0,
    )

    mapper = make_mapper()

    plan = mapper.map(
        graph,
        request,
    )

    compatible_diffuser = SimulatedDiffuser(
        capabilities=(
            make_compatible_device_capabilities()
        ),
    )

    incompatible_diffuser = SimulatedDiffuser(
        capabilities=DeviceCapabilities(
            device_id="different-device",
            channels=[
                DeviceChannelCapability(
                    channel=8,
                ),
                DeviceChannelCapability(
                    channel=9,
                ),
            ],
            min_duration=1.0,
            max_duration=10.0,
        ),
    )

    accepted_event = (
        compatible_diffuser.render(
            plan
        )
    )

    with pytest.raises(
        ValueError,
        match="rendering channel is not supported",
    ):
        incompatible_diffuser.render(
            plan
        )

    assert len(
        accepted_event.commands
    ) == 3

    assert (
        compatible_diffuser.last_event
        is accepted_event
    )

    assert (
        incompatible_diffuser.last_event
        is None
    )


def test_odornet_unknown_state_is_not_rendered() -> None:
    record = {
        "SMILES": "CCO",
        "floral": None,
    }

    odor = from_record_with_annotations(
        record,
        odor_id="odornet-unknown-demo",
    )

    semantic = next(
        representation
        for representation in odor.representations
        if (
            representation.scheme.id
            == ANNOTATION_SCHEME_ID
        )
    )

    molecule = Molecule(
        id="molecule-unknown-demo",
        smiles="CCO",
    )

    annotation = Annotation(
        id="annotation-unknown-demo",
        subject=Reference(
            resource_id=molecule.id,
        ),
        scheme=ExperimentalScheme(
            id=semantic.scheme.id,
            version=semantic.scheme.version,
        ),
        data=semantic.data,
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )

    mapper = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=1,
                intensity=1.0,
            ),
        ]
    )

    capabilities = DeviceCapabilities(
        device_id="unknown-state-demo-device",
        channels=[
            DeviceChannelCapability(
                channel=1,
            ),
        ],
        min_duration=0.5,
        max_duration=10.0,
    )

    diffuser = SimulatedDiffuser(
        capabilities=capabilities,
    )

    plan = mapper.map(
        graph,
        RenderRequest(
            resource_id=molecule.id,
            duration=1.0,
        ),
    )

    assert plan.commands == []

    assert capabilities.accepts_plan(
        plan
    )

    event = diffuser.render(
        plan
    )

    assert event.commands == ()