"""Read a supported graph and call the real mappers, without device access."""

from dataclasses import asdict
from pathlib import Path

from opensmell.experimental.annotation import Annotation
from opensmell.experimental.generic_graph import generic_graph_loads, generic_graph_to_dict
from opensmell.experimental.resources import ObservationTarget, Stimulus
from opensmell.experimental.semantic_channel_mapper import (
    SEMANTIC_ANNOTATIONS_SCHEME, SEMANTIC_ANNOTATIONS_SCHEME_VERSION,
)
from tools import multisource_demo as demo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = PROJECT_ROOT / "examples" / "multisource_beta_pinene.osmell"


class PreviewError(ValueError):
    """A diagnostic suitable for the local interface."""


def preview(text: str, *, policy: str = "semantic", duration: float = 5.0) -> dict:
    """Compute both plans for one molecule and its linked observation.

    The serialized resources are returned without filling missing values or
    inventing provenance. The plan representation is application JSON, not the
    Device Protocol. No transport or device adapter is involved.
    """
    if policy not in ("semantic", "perceptual"):
        raise PreviewError("Unknown policy: choose semantic or perceptual.")
    registry = demo.create_registry()
    try:
        graph = generic_graph_loads(text, registry=registry)
    except (TypeError, ValueError, RecursionError) as exc:
        raise PreviewError(
            "Invalid file or unsupported format. An experimental generic graph "
            "version 0.1 is required, not a Core document for opensmell.load(). "
            f"Details: {exc}"
        ) from exc
    try:
        molecule = demo.select_single_molecule(graph)
        observation = demo.select_single_observation(graph)
    except RuntimeError as exc:
        raise PreviewError(
            "Incompatible graph: this application requires exactly one molecule "
            f"and one observation. Details: {exc}"
        ) from exc
    stimulus = graph.get(observation.stimulus.resource_id)
    if (not isinstance(stimulus, Stimulus) or stimulus.source is None
            or stimulus.source.resource_id != molecule.id):
        raise PreviewError(
            "Incompatible graph: the observation’s stimulus must be present "
            "and reference the single molecule."
        )
    target = graph.get(observation.target.resource_id) if observation.target else None
    if observation.target is not None and not isinstance(target, ObservationTarget):
        raise PreviewError("Incompatible graph: the observation’s target is missing or incompatible.")
    annotations = [
        item for item in graph.resources
        if isinstance(item, Annotation)
        and item.subject.resource_id == molecule.id
        and item.scheme.id == SEMANTIC_ANNOTATIONS_SCHEME
        and item.scheme.version == SEMANTIC_ANNOTATIONS_SCHEME_VERSION
    ]
    if not annotations:
        raise PreviewError(
            "Incompatible graph: a semantic.annotations 0.1 Annotation "
            "must reference the molecule."
        )
    try:
        semantic = demo.build_semantic_plan(graph, molecule, duration)
        perceptual = demo.build_perceptual_plan(graph, observation, duration)
    except (TypeError, ValueError, OverflowError) as exc:
        raise PreviewError(
            "Cannot generate preview: check the data and duration "
            f"(a finite number greater than zero, in seconds). Details: {exc}"
        ) from exc
    if not perceptual.commands:
        raise PreviewError(
            "Graph incompatible with the perceptual policy: no usable "
            "flower, grass or wood measurement for the perceptual.measurements "
            "0.1 mapper (a valid numeric value and explicit min/max scale are required)."
        )
    document = generic_graph_to_dict(graph, registry=registry)
    resources = {item["id"]: item for item in document["resources"]}
    return {
        "policy": policy,
        "document": document,
        "molecule": resources[molecule.id],
        "annotations": [resources[item.id] for item in annotations],
        "observation": resources[observation.id],
        "stimulus": resources[stimulus.id],
        "target": resources[target.id] if target is not None else None,
        "plans": {"semantic": asdict(semantic), "perceptual": asdict(perceptual)},
        "bindings": {
            "semantic": [asdict(binding) for binding in demo.SEMANTIC_BINDINGS],
            "perceptual": [asdict(binding) for binding in demo.PERCEPTUAL_BINDINGS],
        },
    }
