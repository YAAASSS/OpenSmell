"""Experimental OpenSmell molecule resource.

This module defines the first namespaced, versioned OpenSmell resource type
built on top of the RFC-0008 Generic ResourceGraph experiment.

The resource identifies a chemical molecule. It does not describe an odor,
a stimulus presentation, a perceptual observation, or a rendering recipe.

Resource contract:

    type: org.opensmell.molecule
    type_version: 0.1

A molecule must provide at least one chemical identification mechanism:

- a SMILES string; or
- one or more ExternalIdentifier values.

SMILES is transported as an opaque non-empty string. This experimental model
does not perform chemical validation, canonicalization, normalization, or
equivalence checking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .generic_graph import ResourceTypeRegistry
from .graph_serialization import (
    external_identifier_from_dict,
    external_identifier_to_dict,
)
from .resources import ExternalIdentifier


MOLECULE_RESOURCE_TYPE = "org.opensmell.molecule"
MOLECULE_RESOURCE_TYPE_VERSION = "0.1"


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


def _require_extra(
    value: Any,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(
            "extra must be a dict"
        )

    return value


@dataclass
class Molecule:
    """Experimental chemical molecule resource.

    ``id`` is the OpenSmell Resource ID.

    ``smiles`` optionally transports a SMILES representation. OpenSmell treats
    the value as opaque text at this layer and does not claim that it is
    canonical or chemically valid.

    ``identifiers`` contains identifiers assigned by external systems or
    datasets, for example a PubChem CID.

    ``extra`` preserves unknown extension fields associated with the resource.
    """

    id: str
    smiles: str | None = None
    identifiers: list[ExternalIdentifier] = field(
        default_factory=list
    )
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.id,
            "Molecule.id",
        )

        if self.smiles is not None:
            _require_nonempty_string(
                self.smiles,
                "Molecule.smiles",
            )

        if not isinstance(self.identifiers, list):
            raise TypeError(
                "Molecule.identifiers must be a list"
            )

        for identifier in self.identifiers:
            if not isinstance(
                identifier,
                ExternalIdentifier,
            ):
                raise TypeError(
                    "Molecule.identifiers must contain "
                    "ExternalIdentifier values"
                )

        _require_extra(self.extra)

        reserved_extra_fields = {
            "type",
            "type_version",
            "id",
            "smiles",
            "identifiers",
        }

        conflicting_fields = (
            reserved_extra_fields
            & self.extra.keys()
        )

        if conflicting_fields:
            names = ", ".join(
                sorted(conflicting_fields)
            )
            raise ValueError(
                "Molecule.extra contains reserved "
                f"field(s): {names}"
            )

        if (
            self.smiles is None
            and not self.identifiers
        ):
            raise ValueError(
                "Molecule requires at least one chemical "
                "identifier: smiles or identifiers"
            )


def molecule_to_dict(
    molecule: Molecule,
) -> dict[str, Any]:
    """Serialize a Molecule using the RFC-0008 resource contract."""

    if not isinstance(molecule, Molecule):
        raise TypeError(
            "molecule must be a Molecule"
        )

    document = dict(molecule.extra)

    document.update(
        {
            "type": MOLECULE_RESOURCE_TYPE,
            "type_version": (
                MOLECULE_RESOURCE_TYPE_VERSION
            ),
            "id": molecule.id,
        }
    )

    if molecule.smiles is not None:
        document["smiles"] = molecule.smiles

    if molecule.identifiers:
        document["identifiers"] = [
            external_identifier_to_dict(
                identifier
            )
            for identifier in molecule.identifiers
        ]

    return document


def molecule_from_dict(
    value: Any,
) -> Molecule:
    """Parse a serialized Molecule resource."""

    if not isinstance(value, dict):
        raise TypeError(
            "molecule must be an object"
        )

    resource_type = _require_nonempty_string(
        value.get("type"),
        "molecule.type",
    )

    if resource_type != MOLECULE_RESOURCE_TYPE:
        raise ValueError(
            "unexpected molecule resource type"
        )

    resource_type_version = (
        _require_nonempty_string(
            value.get("type_version"),
            "molecule.type_version",
        )
    )

    if (
        resource_type_version
        != MOLECULE_RESOURCE_TYPE_VERSION
    ):
        raise ValueError(
            "unsupported molecule resource type_version"
        )

    resource_id = _require_nonempty_string(
        value.get("id"),
        "molecule.id",
    )

    if "smiles" in value:
        smiles = _require_nonempty_string(
            value["smiles"],
            "molecule.smiles",
        )
    else:
        smiles = None

    if "identifiers" in value:
        raw_identifiers = value["identifiers"]

        if not isinstance(
            raw_identifiers,
            list,
        ):
            raise TypeError(
                "molecule.identifiers must be a list"
            )

        identifiers = [
            external_identifier_from_dict(
                identifier
            )
            for identifier in raw_identifiers
        ]
    else:
        identifiers = []

    known_fields = {
        "type",
        "type_version",
        "id",
        "smiles",
        "identifiers",
    }

    extra = {
        key: item
        for key, item in value.items()
        if key not in known_fields
    }

    return Molecule(
        id=resource_id,
        smiles=smiles,
        identifiers=identifiers,
        extra=extra,
    )


def register_molecule_resource_type(
    registry: ResourceTypeRegistry,
) -> None:
    """Register Molecule 0.1 in an RFC-0008 resource registry."""

    if not isinstance(
        registry,
        ResourceTypeRegistry,
    ):
        raise TypeError(
            "registry must be a ResourceTypeRegistry"
        )

    registry.register(
        MOLECULE_RESOURCE_TYPE,
        Molecule,
        molecule_from_dict,
        molecule_to_dict,
        resource_type_version=(
            MOLECULE_RESOURCE_TYPE_VERSION
        ),
    )