"""Tests for the experimental Core Odor to ResourceGraph bridge."""

from __future__ import annotations

from typing import Any

import pytest

from opensmell import builders
from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    ANNOTATION_SCHEME_VERSION,
    from_record_with_annotations,
)
from opensmell.experimental.annotation import Annotation
from opensmell.experimental.molecule import Molecule
from opensmell.experimental.odor_graph_bridge import (
    OdorGraphBridgeResult,
    bridge_odor_to_resource_graph,
)
from opensmell.experimental.reference_discovery import (
    build_reference_index,
)
from opensmell.experimental.rendering import RenderRequest
from opensmell.experimental.semantic_channel_mapper import (
    SemanticChannelBinding,
    SemanticChannelMapper,
)
from opensmell.experimental.simulated_diffuser import SimulatedDiffuser
from opensmell.models import Odor, Representation, Scheme


def odornet_record() -> dict[str, Any]:
    return {
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


def test_bridge_odornet_odor_to_molecule_and_annotation() -> None:
    odor = from_record_with_annotations(
        odornet_record(),
        odor_id="odor-demo",
    )

    result = bridge_odor_to_resource_graph(
        odor
    )

    assert isinstance(
        result,
        OdorGraphBridgeResult,
    )
    assert len(result.graph.resources) == 2
    assert len(result.annotation_ids) == 1

    molecule = result.graph.require(
        result.primary_resource_id
    )
    annotation = result.graph.require(
        result.annotation_ids[0]
    )

    assert isinstance(
        molecule,
        Molecule,
    )
    assert molecule.smiles == "CCO"
    assert molecule.extra["provenance"] == {
        "source": "OdorNet",
    }

    assert isinstance(
        annotation,
        Annotation,
    )
    assert (
        annotation.subject.resource_id
        == molecule.id
    )
    assert (
        annotation.scheme.id
        == ANNOTATION_SCHEME_ID
    )
    assert (
        annotation.scheme.version
        == ANNOTATION_SCHEME_VERSION
    )
    assert annotation.extra["provenance"] == {
        "source": "OdorNet",
    }
    assert (
        annotation.extra[
            "core_representation_type"
        ]
        == "semantic"
    )


def test_bridge_preserves_annotation_data() -> None:
    odor = from_record_with_annotations(
        odornet_record(),
        odor_id="odor-demo",
    )

    semantic = next(
        representation
        for representation in odor.representations
        if representation.scheme.id
        == ANNOTATION_SCHEME_ID
    )

    result = bridge_odor_to_resource_graph(
        odor
    )

    annotation = result.graph.require(
        result.annotation_ids[0]
    )

    assert isinstance(
        annotation,
        Annotation,
    )
    assert annotation.data == semantic.data


def test_bridge_does_not_alias_representation_data() -> None:
    odor = from_record_with_annotations(
        odornet_record(),
        odor_id="odor-demo",
    )

    semantic = next(
        representation
        for representation in odor.representations
        if representation.scheme.id
        == ANNOTATION_SCHEME_ID
    )

    result = bridge_odor_to_resource_graph(
        odor
    )

    annotation = result.graph.require(
        result.annotation_ids[0]
    )

    assert isinstance(
        annotation,
        Annotation,
    )

    semantic.data["annotations"][0][
        "state"
    ] = "changed"

    assert (
        annotation.data["annotations"][0][
            "state"
        ]
        != "changed"
    )


def test_bridge_resource_ids_are_deterministic() -> None:
    first = bridge_odor_to_resource_graph(
        from_record_with_annotations(
            odornet_record(),
            odor_id="odor-demo",
        )
    )

    second = bridge_odor_to_resource_graph(
        from_record_with_annotations(
            odornet_record(),
            odor_id="odor-demo",
        )
    )

    assert (
        first.primary_resource_id
        == second.primary_resource_id
    )
    assert (
        first.annotation_ids
        == second.annotation_ids
    )


def test_bridge_different_odor_ids_produce_different_resource_ids() -> None:
    first = bridge_odor_to_resource_graph(
        from_record_with_annotations(
            odornet_record(),
            odor_id="odor-a",
        )
    )

    second = bridge_odor_to_resource_graph(
        from_record_with_annotations(
            odornet_record(),
            odor_id="odor-b",
        )
    )

    assert (
        first.primary_resource_id
        != second.primary_resource_id
    )
    assert (
        first.annotation_ids
        != second.annotation_ids
    )


def test_bridge_reference_is_discoverable_and_resolved() -> None:
    result = bridge_odor_to_resource_graph(
        from_record_with_annotations(
            odornet_record(),
            odor_id="odor-demo",
        )
    )

    index = build_reference_index(
        result.graph
    )

    incoming = index.references_to(
        result.primary_resource_id
    )

    assert len(incoming) == 1
    assert (
        incoming[0].source_id
        == result.annotation_ids[0]
    )
    assert (
        incoming[0].target_id
        == result.primary_resource_id
    )


def test_bridge_can_feed_rendering_pipeline() -> None:
    result = bridge_odor_to_resource_graph(
        from_record_with_annotations(
            odornet_record(),
            odor_id="odor-demo",
        )
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
                intensity=0.35,
            ),
            SemanticChannelBinding(
                descriptor="nutty",
                channel=4,
                intensity=0.80,
            ),
        ]
    )

    plan = mapper.map(
        result.graph,
        RenderRequest(
            resource_id=(
                result.primary_resource_id
            ),
            duration=4.0,
        ),
    )

    event = SimulatedDiffuser().render(
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


def test_bridge_multiple_nonchemical_representations_become_annotations() -> None:
    odor = Odor(
        id="odor-multiple",
        representations=[
            builders.chemical_smiles(
                "CCO"
            ),
            Representation(
                type="semantic",
                scheme=Scheme(
                    id="org.example.semantic",
                    version="1.0",
                ),
                data={
                    "labels": [
                        "example",
                    ],
                },
            ),
            Representation(
                type="perceptual",
                scheme=Scheme(
                    id="org.example.perceptual",
                    version="2.0",
                ),
                data={
                    "score": 0.5,
                },
            ),
        ],
    )

    result = bridge_odor_to_resource_graph(
        odor
    )

    assert len(result.annotation_ids) == 2
    assert len(result.graph.resources) == 3

    first = result.graph.require(
        result.annotation_ids[0]
    )
    second = result.graph.require(
        result.annotation_ids[1]
    )

    assert isinstance(
        first,
        Annotation,
    )
    assert isinstance(
        second,
        Annotation,
    )
    assert first.scheme.id == (
        "org.example.semantic"
    )
    assert second.scheme.id == (
        "org.example.perceptual"
    )
    assert first.extra[
        "core_representation_type"
    ] == "semantic"
    assert second.extra[
        "core_representation_type"
    ] == "perceptual"


def test_bridge_preserves_scheme_extensions() -> None:
    odor = Odor(
        id="odor-scheme-extra",
        representations=[
            builders.chemical_smiles(
                "CCO"
            ),
            Representation(
                type="semantic",
                scheme=Scheme(
                    id="org.example.semantic",
                    version="1.0",
                    extra={
                        "vendor": "example",
                    },
                ),
                data={
                    "labels": [
                        "test",
                    ],
                },
            ),
        ],
    )

    result = bridge_odor_to_resource_graph(
        odor
    )

    annotation = result.graph.require(
        result.annotation_ids[0]
    )

    assert isinstance(
        annotation,
        Annotation,
    )
    assert annotation.scheme.extra == {
        "vendor": "example",
    }


def test_bridge_requires_odor() -> None:
    with pytest.raises(TypeError):
        bridge_odor_to_resource_graph(
            {}
        )


def test_bridge_requires_supported_smiles_representation() -> None:
    odor = Odor(
        id="odor-no-smiles",
        representations=[
            Representation(
                type="semantic",
                scheme=Scheme(
                    id="org.example.semantic",
                    version="1.0",
                ),
                data={
                    "labels": [
                        "example",
                    ],
                },
            ),
        ],
    )

    with pytest.raises(ValueError):
        bridge_odor_to_resource_graph(
            odor
        )


def test_bridge_rejects_multiple_supported_smiles_representations() -> None:
    odor = Odor(
        id="odor-two-smiles",
        representations=[
            builders.chemical_smiles(
                "CCO"
            ),
            builders.chemical_smiles(
                "CCN"
            ),
        ],
    )

    with pytest.raises(ValueError):
        bridge_odor_to_resource_graph(
            odor
        )


@pytest.mark.parametrize(
    "smiles",
    [
        "",
        None,
        123,
        False,
    ],
)
def test_bridge_rejects_invalid_smiles_payload(
    smiles: Any,
) -> None:
    odor = Odor(
        id="odor-invalid-smiles",
        representations=[
            Representation(
                type="chemical",
                scheme=Scheme(
                    id=(
                        "org.opensmell.chemical.smiles"
                    ),
                    version="0.1",
                ),
                data={
                    "smiles": smiles,
                },
            ),
        ],
    )

    with pytest.raises(
        (TypeError, ValueError)
    ):
        bridge_odor_to_resource_graph(
            odor
        )
