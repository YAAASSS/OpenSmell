"""Shared application policy for the CLI and local multi-source demo.

These bindings are demonstration choices, not SDK or olfactory definitions.
This module has no hardware transport dependency.
"""

from __future__ import annotations

from pathlib import Path

from opensmell.experimental.annotation import (
    register_annotation_resource_type,
)
from opensmell.experimental.generic_graph import (
    GenericResourceGraph,
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
    RenderingPlan,
    RenderRequest,
)
from opensmell.experimental.resources import (
    Observation,
)
from opensmell.experimental.semantic_channel_mapper import (
    SemanticChannelBinding,
    SemanticChannelMapper,
)


DEFAULT_DURATION = 5.0


SEMANTIC_BINDINGS = [
    SemanticChannelBinding(
        descriptor="floral",
        channel=0,
        intensity=0.25,
    ),
    SemanticChannelBinding(
        descriptor="green&herbal",
        channel=1,
        intensity=0.60,
    ),
    SemanticChannelBinding(
        descriptor="woody&mossy",
        channel=2,
        intensity=1.00,
    ),
]


PERCEPTUAL_BINDINGS = [
    PerceptualChannelBinding(
        property="flower",
        channel=0,
    ),
    PerceptualChannelBinding(
        property="grass",
        channel=1,
    ),
    PerceptualChannelBinding(
        property="wood",
        channel=2,
    ),
]


def create_registry():
    """Create the registry required by the multi-source graph."""

    registry = (
        create_default_resource_type_registry()
    )

    register_molecule_resource_type(
        registry
    )

    register_annotation_resource_type(
        registry
    )

    return registry


def load_graph(
    path: Path,
) -> GenericResourceGraph:
    """Load one multi-source .osmell GenericResourceGraph."""

    text = path.read_text(
        encoding="utf-8"
    )

    registry = create_registry()

    return generic_graph_loads(
        text,
        registry=registry,
    )


def select_single_molecule(
    graph: GenericResourceGraph,
) -> Molecule:
    """Return the graph's single Molecule resource."""

    molecules = [
        resource
        for resource in graph.resources
        if isinstance(
            resource,
            Molecule,
        )
    ]

    if len(molecules) != 1:
        raise RuntimeError(
            "This demonstration requires exactly "
            "one Molecule resource; "
            f"found {len(molecules)}"
        )

    return molecules[0]


def select_single_observation(
    graph: GenericResourceGraph,
) -> Observation:
    """Return the graph's single Observation resource."""

    observations = [
        resource
        for resource in graph.resources
        if isinstance(
            resource,
            Observation,
        )
    ]

    if len(observations) != 1:
        raise RuntimeError(
            "This demonstration requires exactly "
            "one Observation resource; "
            f"found {len(observations)}"
        )

    return observations[0]


def build_semantic_plan(
    graph: GenericResourceGraph,
    molecule: Molecule,
    duration: float,
) -> RenderingPlan:
    """Build the semantic RenderingPlan."""

    mapper = SemanticChannelMapper(
        bindings=SEMANTIC_BINDINGS
    )

    return mapper.map(
        graph,
        RenderRequest(
            resource_id=molecule.id,
            duration=duration,
        ),
    )


def build_perceptual_plan(
    graph: GenericResourceGraph,
    observation: Observation,
    duration: float,
) -> RenderingPlan:
    """Build the quantitative perceptual RenderingPlan."""

    mapper = PerceptualChannelMapper(
        bindings=PERCEPTUAL_BINDINGS
    )

    return mapper.map(
        graph,
        RenderRequest(
            resource_id=observation.id,
            duration=duration,
        ),
    )
