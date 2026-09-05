"""End-to-end tests for the experimental protocol rendering pipeline.

These tests exercise the complete software path:

GenericResourceGraph
    -> RenderRequest
    -> SemanticChannelMapper
    -> rendering pipeline
    -> ProtocolDeviceAdapter
    -> JSON device protocol
    -> MemoryDeviceTransport

The final transport remains in-memory. No physical hardware or odor
reproduction is involved.

This module is experimental and non-normative.
"""

from __future__ import annotations

import pytest

from opensmell.experimental.annotation import Annotation
from opensmell.experimental.device_capabilities import (
    DeviceCapabilities,
    DeviceChannelCapability,
)
from opensmell.experimental.device_protocol import (
    capabilities_response,
    dumps_message,
    hello_response,
    loads_message,
    ok_response,
)
from opensmell.experimental.device_transport import (
    MemoryDeviceTransport,
)
from opensmell.experimental.generic_graph import (
    GenericResourceGraph,
)
from opensmell.experimental.molecule import Molecule
from opensmell.experimental.protocol_device_adapter import (
    ProtocolDeviceAdapter,
)
from opensmell.experimental.render_pipeline import (
    build_rendering_plan,
    render_to_device,
)
from opensmell.experimental.rendering import RenderRequest
from opensmell.experimental.resources import Reference
from opensmell.experimental.scheme import Scheme
from opensmell.experimental.semantic_channel_mapper import (
    SEMANTIC_ANNOTATIONS_SCHEME,
    SEMANTIC_ANNOTATIONS_SCHEME_VERSION,
    SemanticChannelBinding,
    SemanticChannelMapper,
)


DEVICE_ID = "protocol-e2e-device"
MOLECULE_ID = "protocol-e2e-molecule"
ANNOTATION_ID = "protocol-e2e-annotation"


def graph() -> GenericResourceGraph:
    molecule = Molecule(
        id=MOLECULE_ID,
        smiles="CCO",
    )

    annotation = Annotation(
        id=ANNOTATION_ID,
        subject=Reference(
            resource_id=MOLECULE_ID,
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
                    "value": "nutty",
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
                channel=0,
                intensity=0.7,
            ),
            SemanticChannelBinding(
                descriptor="spice",
                channel=2,
                intensity=0.4,
            ),
            SemanticChannelBinding(
                descriptor="nutty",
                channel=3,
                intensity=0.5,
            ),
        ]
    )


def capabilities() -> DeviceCapabilities:
    return DeviceCapabilities(
        device_id=DEVICE_ID,
        channels=[
            DeviceChannelCapability(
                channel=0,
                min_intensity=0.0,
                max_intensity=1.0,
            ),
            DeviceChannelCapability(
                channel=2,
                min_intensity=0.0,
                max_intensity=0.8,
            ),
            DeviceChannelCapability(
                channel=3,
                min_intensity=0.0,
                max_intensity=0.8,
            ),
        ],
        min_duration=1.0,
        max_duration=10.0,
    )


def transport(
    *,
    include_render_response: bool = True,
) -> MemoryDeviceTransport:
    responses = [
        dumps_message(
            hello_response(
                DEVICE_ID
            )
        ),
        dumps_message(
            capabilities_response(
                capabilities()
            )
        ),
    ]

    if include_render_response:
        responses.append(
            dumps_message(
                ok_response()
            )
        )

    return MemoryDeviceTransport(
        responses=responses
    )


def test_complete_pipeline_reaches_protocol_transport() -> None:
    memory = transport()

    device = ProtocolDeviceAdapter(
        memory
    )

    result = render_to_device(
        graph(),
        RenderRequest(
            resource_id=MOLECULE_ID,
            duration=4.0,
        ),
        mapper(),
        device,
    )

    assert result == {
        "protocol_version": "0.1",
        "type": "ok",
    }

    assert len(memory.messages) == 3

    assert loads_message(
        memory.messages[0]
    ) == {
        "protocol_version": "0.1",
        "type": "hello",
    }

    assert loads_message(
        memory.messages[1]
    ) == {
        "protocol_version": "0.1",
        "type": "get_capabilities",
    }

    assert loads_message(
        memory.messages[2]
    ) == {
        "protocol_version": "0.1",
        "type": "render",
        "duration": 4.0,
        "commands": [
            {
                "channel": 0,
                "intensity": 0.7,
            },
            {
                "channel": 2,
                "intensity": 0.4,
            },
        ],
    }


def test_absent_annotation_does_not_reach_device() -> None:
    memory = transport()

    device = ProtocolDeviceAdapter(
        memory
    )

    render_to_device(
        graph(),
        RenderRequest(
            resource_id=MOLECULE_ID,
            duration=4.0,
        ),
        mapper(),
        device,
    )

    render_message = loads_message(
        memory.messages[2]
    )

    channels = [
        command["channel"]
        for command in render_message["commands"]
    ]

    assert channels == [
        0,
        2,
    ]

    assert 3 not in channels


def test_render_request_identity_survives_to_plan_metadata() -> None:
    memory = transport(
        include_render_response=False
    )

    device = ProtocolDeviceAdapter(
        memory
    )

    plan = build_rendering_plan(
        graph(),
        RenderRequest(
            resource_id=MOLECULE_ID,
            duration=4.0,
        ),
        mapper(),
        device,
    )

    assert (
        plan.extra["source_resource_id"]
        == MOLECULE_ID
    )

    assert (
        plan.extra["annotation_ids"]
        == [ANNOTATION_ID]
    )

    assert len(memory.messages) == 2


def test_device_capabilities_are_discovered_before_mapping() -> None:
    memory = transport(
        include_render_response=False
    )

    device = ProtocolDeviceAdapter(
        memory
    )

    assert device.device_id == DEVICE_ID

    assert [
        channel.channel
        for channel in device.capabilities.channels
    ] == [
        0,
        2,
        3,
    ]

    plan = build_rendering_plan(
        graph(),
        RenderRequest(
            resource_id=MOLECULE_ID,
            duration=4.0,
        ),
        mapper(),
        device,
    )

    assert device.capabilities.accepts_plan(
        plan
    )


def test_incompatible_mapper_is_rejected_before_render_message() -> None:
    memory = transport()

    device = ProtocolDeviceAdapter(
        memory
    )

    incompatible_mapper = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=99,
                intensity=0.7,
            ),
        ]
    )

    with pytest.raises(
        ValueError,
    ):
        render_to_device(
            graph(),
            RenderRequest(
                resource_id=MOLECULE_ID,
                duration=4.0,
            ),
            incompatible_mapper,
            device,
        )

    assert len(memory.messages) == 2

    assert memory.remaining_responses == [
        dumps_message(
            ok_response()
        )
    ]


def test_invalid_duration_is_rejected_before_render_message() -> None:
    memory = transport()

    device = ProtocolDeviceAdapter(
        memory
    )

    with pytest.raises(
        ValueError,
    ):
        render_to_device(
            graph(),
            RenderRequest(
                resource_id=MOLECULE_ID,
                duration=20.0,
            ),
            mapper(),
            device,
        )

    assert len(memory.messages) == 2


def test_same_graph_can_target_different_protocol_devices() -> None:
    shared_graph = graph()
    shared_request = RenderRequest(
        resource_id=MOLECULE_ID,
        duration=4.0,
    )

    device_a_capabilities = DeviceCapabilities(
        device_id="device-a",
        channels=[
            DeviceChannelCapability(
                channel=0,
            ),
            DeviceChannelCapability(
                channel=2,
            ),
        ],
        min_duration=1.0,
        max_duration=10.0,
    )

    transport_a = MemoryDeviceTransport(
        responses=[
            dumps_message(
                hello_response(
                    "device-a"
                )
            ),
            dumps_message(
                capabilities_response(
                    device_a_capabilities
                )
            ),
            dumps_message(
                ok_response()
            ),
        ]
    )

    device_a = ProtocolDeviceAdapter(
        transport_a
    )

    mapper_a = SemanticChannelMapper(
        bindings=[
            SemanticChannelBinding(
                descriptor="floral",
                channel=0,
                intensity=0.7,
            ),
            SemanticChannelBinding(
                descriptor="spice",
                channel=2,
                intensity=0.4,
            ),
        ]
    )

    device_b_capabilities = DeviceCapabilities(
        device_id="device-b",
        channels=[
            DeviceChannelCapability(
                channel=7,
            ),
            DeviceChannelCapability(
                channel=9,
            ),
        ],
        min_duration=1.0,
        max_duration=10.0,
    )

    transport_b = MemoryDeviceTransport(
        responses=[
            dumps_message(
                hello_response(
                    "device-b"
                )
            ),
            dumps_message(
                capabilities_response(
                    device_b_capabilities
                )
            ),
            dumps_message(
                ok_response()
            ),
        ]
    )

    device_b = ProtocolDeviceAdapter(
        transport_b
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

    render_to_device(
        shared_graph,
        shared_request,
        mapper_a,
        device_a,
    )

    render_to_device(
        shared_graph,
        shared_request,
        mapper_b,
        device_b,
    )

    message_a = loads_message(
        transport_a.messages[2]
    )

    message_b = loads_message(
        transport_b.messages[2]
    )

    assert [
        command["channel"]
        for command in message_a["commands"]
    ] == [
        0,
        2,
    ]

    assert [
        command["channel"]
        for command in message_b["commands"]
    ] == [
        7,
        9,
    ]

    assert shared_request.resource_id == MOLECULE_ID