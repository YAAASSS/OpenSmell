"""Experimental bridge from Core OpenSmell Odor to ResourceGraph.

This module converts selected Core 0.1 odor representations into experimental
RFC-0008 resources so applications can consume Core odor information through
the experimental graph, navigation, and rendering layers.

The bridge currently understands:

- ``org.opensmell.chemical.smiles`` -> Molecule
- any other representation -> Annotation attached to that Molecule

A chemical SMILES representation is therefore required by this experimental
bridge. Unknown representation schemes are preserved as generic Annotation
payloads rather than rejected.

This module is experimental and non-normative. It does not modify the Core
OpenSmell 0.1 data model or define physical odor rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid5

from ..models import Odor, Representation
from .annotation import Annotation
from .generic_graph import GenericResourceGraph
from .molecule import Molecule
from .resources import Reference
from .scheme import Scheme as ExperimentalScheme


CHEMICAL_SMILES_SCHEME = "org.opensmell.chemical.smiles"
CHEMICAL_SMILES_SCHEME_VERSION = "0.1"

_BRIDGE_NAMESPACE = UUID(
    "7a4b0e4d-6e2a-4ef4-b3b1-32c3f610d2ab"
)


def _require_nonempty_string(
    value: Any,
    name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be a string"
        )

    if not value:
        raise ValueError(
            f"{name} must be non-empty"
        )

    return value


def _copy_json_value(
    value: Any,
) -> Any:
    if value is None:
        return None

    if isinstance(
        value,
        (bool, str, int, float),
    ):
        return value

    if isinstance(value, list):
        return [
            _copy_json_value(item)
            for item in value
        ]

    if isinstance(value, dict):
        result: dict[str, Any] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "extension object keys must be strings"
                )

            result[key] = _copy_json_value(
                item
            )

        return result

    raise TypeError(
        "bridge extensions must contain only "
        "JSON-compatible values"
    )


def _resource_id(
    odor_id: str,
    role: str,
) -> str:
    return str(
        uuid5(
            _BRIDGE_NAMESPACE,
            f"{odor_id}\n{role}",
        )
    )


@dataclass(frozen=True)
class OdorGraphBridgeResult:
    """Result of bridging one Core Odor into a GenericResourceGraph."""

    graph: GenericResourceGraph
    primary_resource_id: str
    annotation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.graph,
            GenericResourceGraph,
        ):
            raise TypeError(
                "OdorGraphBridgeResult.graph must be "
                "a GenericResourceGraph"
            )

        _require_nonempty_string(
            self.primary_resource_id,
            "OdorGraphBridgeResult.primary_resource_id",
        )

        if not isinstance(
            self.annotation_ids,
            tuple,
        ):
            raise TypeError(
                "OdorGraphBridgeResult.annotation_ids "
                "must be a tuple"
            )

        for annotation_id in self.annotation_ids:
            _require_nonempty_string(
                annotation_id,
                "OdorGraphBridgeResult.annotation_ids item",
            )


def bridge_odor_to_resource_graph(
    odor: Odor,
) -> OdorGraphBridgeResult:
    """Bridge one Core OpenSmell Odor into experimental graph resources.

    Exactly one supported chemical SMILES representation is currently
    required. Every non-chemical representation becomes an Annotation attached
    to the generated Molecule. Representation scheme identifiers, versions,
    data, and extension fields are preserved.

    Resource IDs are deterministic for a given Core odor ID and bridge role.
    """

    if not isinstance(
        odor,
        Odor,
    ):
        raise TypeError(
            "odor must be an Odor"
        )

    odor_id = _require_nonempty_string(
        odor.id,
        "Odor.id",
    )

    chemical_representations = [
        representation
        for representation in odor.representations
        if _is_supported_smiles_representation(
            representation
        )
    ]

    if not chemical_representations:
        raise ValueError(
            "odor requires a "
            "org.opensmell.chemical.smiles 0.1 "
            "representation"
        )

    if len(chemical_representations) > 1:
        raise ValueError(
            "odor contains multiple supported "
            "chemical SMILES representations"
        )

    chemical = chemical_representations[0]
    smiles = _extract_smiles(
        chemical
    )

    molecule_id = _resource_id(
        odor_id,
        "molecule",
    )

    molecule_extra = _copy_json_value(
        chemical.extra
    )

    molecule = Molecule(
        id=molecule_id,
        smiles=smiles,
        extra=molecule_extra,
    )

    resources: list[Any] = [
        molecule,
    ]
    annotation_ids: list[str] = []

    annotation_number = 0

    for representation in odor.representations:
        if representation is chemical:
            continue

        annotation_number += 1

        annotation_id = _resource_id(
            odor_id,
            (
                "annotation:"
                f"{annotation_number}:"
                f"{representation.type}:"
                f"{representation.scheme.id}:"
                f"{representation.scheme.version}"
            ),
        )

        annotation = Annotation(
            id=annotation_id,
            subject=Reference(
                resource_id=molecule_id,
            ),
            scheme=ExperimentalScheme(
                id=representation.scheme.id,
                version=representation.scheme.version,
                extra=_copy_json_value(
                    representation.scheme.extra
                ),
            ),
            data=_copy_json_value(
                representation.data
            ),
            extra=_annotation_extra(
                representation
            ),
        )

        resources.append(
            annotation
        )
        annotation_ids.append(
            annotation_id
        )

    graph = GenericResourceGraph(
        resources=resources
    )

    return OdorGraphBridgeResult(
        graph=graph,
        primary_resource_id=molecule_id,
        annotation_ids=tuple(
            annotation_ids
        ),
    )


def _is_supported_smiles_representation(
    representation: Representation,
) -> bool:
    return (
        representation.type == "chemical"
        and representation.scheme.id
        == CHEMICAL_SMILES_SCHEME
        and representation.scheme.version
        == CHEMICAL_SMILES_SCHEME_VERSION
    )


def _extract_smiles(
    representation: Representation,
) -> str:
    smiles = representation.data.get(
        "smiles"
    )

    if not isinstance(smiles, str):
        raise TypeError(
            "chemical SMILES representation data.smiles "
            "must be a string"
        )

    if not smiles:
        raise ValueError(
            "chemical SMILES representation data.smiles "
            "must be non-empty"
        )

    return smiles


def _annotation_extra(
    representation: Representation,
) -> dict[str, Any]:
    extra = _copy_json_value(
        representation.extra
    )

    extra["core_representation_type"] = (
        representation.type
    )

    return extra
