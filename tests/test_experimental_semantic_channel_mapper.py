"""Tests for the experimental semantic-to-channel mapper.

The mapper consumes RFC-0004-style semantic Annotation resources through the
generic graph and RFC-0011 structural reference discovery. Its channel mapping
is explicitly device/application policy and is not an OpenSmell semantic
definition or a claim of physical odor reproduction.
"""

from __future__ import annotations

from typing import Any

import pytest

from opensmell.experimental.annotation import (
    Annotation,
)
from opensmell.experimental.generic_graph import (
    GenericResource,
    GenericResourceGraph,
)
from opensmell.experimental.molecule import (
    Molecule,
)
from opensmell.experimental.reference_discovery import (
    build_reference_index,
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


def semantic_scheme() -> Scheme:
    return Scheme(
        id=SEMANTIC_ANNOTATIONS_SCHEME,
        version=SEMANTIC_ANNOTATIONS_SCHEME_VERSION,
    )


def annotation(
    resource_id: str,
    subject_id: str,
    entries: list[Any],
    *,
    scheme: Scheme | None = None,
) -> Annotation:
    return Annotation(
        id=resource_id,
        subject=Reference(
            resource_id=subject_id,
        ),
        scheme=(
            scheme
            if scheme is not None
            else semantic_scheme()
        ),
        data={
            "annotations": entries,
        },
    )


def mapper() -> SemanticChannelMapper:
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
                descriptor="woody&mossy",
                channel=3,
                intensity=0.40,
            ),
        ]
    )


def test_binding() -> None:
    binding = SemanticChannelBinding(
        descriptor="floral",
        channel=1,
        intensity=0.70,
    )

    assert binding.descriptor == "floral"
    assert binding.channel == 1
    assert binding.intensity == 0.70


@pytest.mark.parametrize(
    "descriptor",
    [
        "",
        None,
        1,
        False,
        [],
        {},
    ],
)
def test_binding_rejects_invalid_descriptor(
    descriptor: Any,
) -> None:
    with pytest.raises(
        (TypeError, ValueError)
    ):
        SemanticChannelBinding(
            descriptor=descriptor,
            channel=1,
            intensity=0.5,
        )


def test_binding_reuses_device_command_validation() -> None:
    with pytest.raises(ValueError):
        SemanticChannelBinding(
            descriptor="floral",
            channel=-1,
            intensity=0.5,
        )

    with pytest.raises(ValueError):
        SemanticChannelBinding(
            descriptor="floral",
            channel=1,
            intensity=1.5,
        )


def test_mapper_rejects_non_list_bindings() -> None:
    with pytest.raises(TypeError):
        SemanticChannelMapper(
            bindings=(),
        )


def test_mapper_rejects_invalid_binding_item() -> None:
    with pytest.raises(TypeError):
        SemanticChannelMapper(
            bindings=[
                {
                    "descriptor": "floral",
                    "channel": 1,
                    "intensity": 0.5,
                },
            ]
        )


def test_mapper_rejects_duplicate_descriptor() -> None:
    with pytest.raises(ValueError):
        SemanticChannelMapper(
            bindings=[
                SemanticChannelBinding(
                    descriptor="floral",
                    channel=1,
                    intensity=0.5,
                ),
                SemanticChannelBinding(
                    descriptor="floral",
                    channel=2,
                    intensity=0.5,
                ),
            ]
        )


def test_mapper_rejects_duplicate_channel() -> None:
    with pytest.raises(ValueError):
        SemanticChannelMapper(
            bindings=[
                SemanticChannelBinding(
                    descriptor="floral",
                    channel=1,
                    intensity=0.5,
                ),
                SemanticChannelBinding(
                    descriptor="woody",
                    channel=1,
                    intensity=0.5,
                ),
            ]
        )


def test_bindings_property_returns_copy() -> None:
    semantic_mapper = mapper()

    bindings = semantic_mapper.bindings
    bindings.clear()

    assert len(
        semantic_mapper.bindings
    ) == 3


def test_map_present_annotations() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            annotation(
                "annotation-1",
                "molecule-1",
                [
                    {
                        "value": "floral",
                        "state": "present",
                    },
                    {
                        "value": "sweety&gourmand",
                        "state": "present",
                    },
                    {
                        "value": "woody&mossy",
                        "state": "present",
                    },
                ],
            ),
        ]
    )

    plan = mapper().map(
        graph,
        RenderRequest(
            resource_id="molecule-1",
            duration=3.0,
        ),
    )

    assert [
        (
            command.channel,
            command.intensity,
        )
        for command in plan.commands
    ] == [
        (1, 0.70),
        (2, 0.55),
        (3, 0.40),
    ]
    assert plan.duration == 3.0
    assert plan.extra[
        "source_resource_id"
    ] == "molecule-1"
    assert plan.extra[
        "annotation_ids"
    ] == [
        "annotation-1",
    ]


def test_map_ignores_absent_unknown_and_unconfigured() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            annotation(
                "annotation-1",
                "molecule-1",
                [
                    {
                        "value": "floral",
                        "state": "absent",
                    },
                    {
                        "value": "woody&mossy",
                        "state": "unknown",
                    },
                    {
                        "value": "sweety&gourmand",
                        "state": "present",
                    },
                    {
                        "value": "not-configured",
                        "state": "present",
                    },
                ],
            ),
        ]
    )

    plan = mapper().map(
        graph,
        RenderRequest(
            resource_id="molecule-1",
            duration=2.0,
        ),
    )

    assert [
        command.channel
        for command in plan.commands
    ] == [2]


def test_map_ignores_wrong_scheme() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            annotation(
                "annotation-1",
                "molecule-1",
                [
                    {
                        "value": "floral",
                        "state": "present",
                    },
                ],
                scheme=Scheme(
                    id="org.example.semantic",
                    version="0.1",
                ),
            ),
        ]
    )

    plan = mapper().map(
        graph,
        RenderRequest(
            resource_id="molecule-1",
            duration=1.0,
        ),
    )

    assert plan.commands == []
    assert plan.extra[
        "annotation_ids"
    ] == []


def test_map_ignores_wrong_scheme_version() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            annotation(
                "annotation-1",
                "molecule-1",
                [
                    {
                        "value": "floral",
                        "state": "present",
                    },
                ],
                scheme=Scheme(
                    id=SEMANTIC_ANNOTATIONS_SCHEME,
                    version="0.2",
                ),
            ),
        ]
    )

    plan = mapper().map(
        graph,
        RenderRequest(
            resource_id="molecule-1",
            duration=1.0,
        ),
    )

    assert plan.commands == []


def test_map_ignores_malformed_annotation_entries() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            annotation(
                "annotation-1",
                "molecule-1",
                [
                    None,
                    "floral",
                    {},
                    {
                        "state": "present",
                    },
                    {
                        "value": "",
                        "state": "present",
                    },
                    {
                        "value": 1,
                        "state": "present",
                    },
                    {
                        "value": "floral",
                        "state": "invalid",
                    },
                    {
                        "value": "floral",
                        "state": "present",
                    },
                ],
            ),
        ]
    )

    plan = mapper().map(
        graph,
        RenderRequest(
            resource_id="molecule-1",
            duration=1.0,
        ),
    )

    assert [
        command.channel
        for command in plan.commands
    ] == [1]


def test_map_ignores_non_list_annotations_payload() -> None:
    semantic_annotation = Annotation(
        id="annotation-1",
        subject=Reference(
            resource_id="molecule-1",
        ),
        scheme=semantic_scheme(),
        data={
            "annotations": {
                "value": "floral",
                "state": "present",
            },
        },
    )

    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            semantic_annotation,
        ]
    )

    plan = mapper().map(
        graph,
        RenderRequest(
            resource_id="molecule-1",
            duration=1.0,
        ),
    )

    assert plan.commands == []


def test_map_collects_multiple_annotations_in_graph_order() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            annotation(
                "annotation-1",
                "molecule-1",
                [
                    {
                        "value": "floral",
                        "state": "present",
                    },
                ],
            ),
            annotation(
                "annotation-2",
                "molecule-1",
                [
                    {
                        "value": "sweety&gourmand",
                        "state": "present",
                    },
                ],
            ),
        ]
    )

    plan = mapper().map(
        graph,
        RenderRequest(
            resource_id="molecule-1",
            duration=1.0,
        ),
    )

    assert [
        command.channel
        for command in plan.commands
    ] == [
        1,
        2,
    ]
    assert plan.extra[
        "annotation_ids"
    ] == [
        "annotation-1",
        "annotation-2",
    ]


def test_map_deduplicates_channel_across_annotations() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            annotation(
                "annotation-1",
                "molecule-1",
                [
                    {
                        "value": "floral",
                        "state": "present",
                    },
                ],
            ),
            annotation(
                "annotation-2",
                "molecule-1",
                [
                    {
                        "value": "floral",
                        "state": "present",
                    },
                ],
            ),
        ]
    )

    plan = mapper().map(
        graph,
        RenderRequest(
            resource_id="molecule-1",
            duration=1.0,
        ),
    )

    assert [
        command.channel
        for command in plan.commands
    ] == [1]


def test_map_ignores_non_annotation_incoming_reference() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            GenericResource(
                id="future-1",
                type="org.example.future",
                type_version="1.0",
                data={
                    "subject": {
                        "resource_id": "molecule-1",
                    },
                },
            ),
        ]
    )

    plan = mapper().map(
        graph,
        RenderRequest(
            resource_id="molecule-1",
            duration=1.0,
        ),
    )

    assert plan.commands == []


def test_map_requires_existing_resource() -> None:
    graph = GenericResourceGraph(
        resources=[]
    )

    with pytest.raises(ValueError):
        mapper().map(
            graph,
            RenderRequest(
                resource_id="missing",
                duration=1.0,
            ),
        )


def test_map_rejects_wrong_graph_type() -> None:
    with pytest.raises(TypeError):
        mapper().map(
            {},
            RenderRequest(
                resource_id="molecule-1",
                duration=1.0,
            ),
        )


def test_map_rejects_wrong_request_type() -> None:
    with pytest.raises(TypeError):
        mapper().map(
            GenericResourceGraph(
                resources=[]
            ),
            {},
        )


def test_map_accepts_prebuilt_reference_index() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
            annotation(
                "annotation-1",
                "molecule-1",
                [
                    {
                        "value": "floral",
                        "state": "present",
                    },
                ],
            ),
        ]
    )

    index = build_reference_index(
        graph
    )

    plan = mapper().map(
        graph,
        RenderRequest(
            resource_id="molecule-1",
            duration=1.0,
        ),
        index=index,
    )

    assert [
        command.channel
        for command in plan.commands
    ] == [1]


def test_map_rejects_index_for_different_graph() -> None:
    first_graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
        ]
    )
    second_graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
        ]
    )

    index = build_reference_index(
        first_graph
    )

    with pytest.raises(ValueError):
        mapper().map(
            second_graph,
            RenderRequest(
                resource_id="molecule-1",
                duration=1.0,
            ),
            index=index,
        )


def test_map_rejects_invalid_index_type() -> None:
    graph = GenericResourceGraph(
        resources=[
            Molecule(
                id="molecule-1",
                smiles="CCO",
            ),
        ]
    )

    with pytest.raises(TypeError):
        mapper().map(
            graph,
            RenderRequest(
                resource_id="molecule-1",
                duration=1.0,
            ),
            index={},
        )
