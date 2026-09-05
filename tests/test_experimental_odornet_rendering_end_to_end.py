"""End-to-end OdorNet rendering tests for OpenSmell.

These tests demonstrate a real OdorNet-shaped record flowing through the
existing OpenSmell OdorNet adapter, then being bridged into the experimental
resource graph and rendering layers.

The semantic-to-channel bindings are illustrative device policy only. They do
not claim that the configured channels physically reproduce the source odor.
"""

from __future__ import annotations

from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    ANNOTATION_SCHEME_VERSION,
    from_record_with_annotations,
)
from opensmell.experimental.annotation import Annotation
from opensmell.experimental.generic_graph import GenericResourceGraph
from opensmell.experimental.molecule import Molecule
from opensmell.experimental.rendering import RenderRequest
from opensmell.experimental.resources import Reference
from opensmell.experimental.scheme import Scheme as ExperimentalScheme
from opensmell.experimental.semantic_channel_mapper import (
    SemanticChannelBinding,
    SemanticChannelMapper,
)
from opensmell.experimental.simulated_diffuser import SimulatedDiffuser


def test_real_odornet_shaped_record_to_simulated_diffuser() -> None:
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

    request = RenderRequest(
        resource_id=molecule.id,
        duration=4.0,
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
        graph,
        request,
    )

    diffuser = SimulatedDiffuser()
    event = diffuser.render(plan)

    assert molecule.smiles == "CCO"
    assert molecule.extra["provenance"] == {
        "source": "OdorNet",
    }
    assert annotation.extra["provenance"] == {
        "source": "OdorNet",
    }

    assert [
        (command.channel, command.intensity)
        for command in event.commands
    ] == [
        (2, 0.55),
        (1, 0.70),
        (3, 0.35),
    ]
    assert event.duration == 4.0
    assert event.extra["source_resource_id"] == molecule.id
    assert event.extra["annotation_ids"] == [
        annotation.id,
    ]


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
        if representation.scheme.id == ANNOTATION_SCHEME_ID
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

    event = SimulatedDiffuser().render(
        mapper.map(
            graph,
            RenderRequest(
                resource_id=molecule.id,
                duration=1.0,
            ),
        )
    )

    assert event.commands == ()
