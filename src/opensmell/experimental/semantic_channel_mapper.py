"""Experimental semantic-to-channel mapper for OpenSmell.

This module demonstrates how scheme-defined semantic annotations in an
OpenSmell GenericResourceGraph can be consumed by a device-specific mapping
policy.

The mapping is deliberately external to OpenSmell representation data. A
descriptor such as ``floral`` has no universal channel or physical rendering
meaning in OpenSmell.

This mapper is illustrative only. It does not claim that activating configured
channels reproduces the annotated odor.

This module is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .annotation import Annotation
from .generic_graph import GenericResourceGraph
from .reference_discovery import (
    ReferenceIndex,
    build_reference_index,
)
from .rendering import (
    DeviceCommand,
    RenderingPlan,
    RenderRequest,
)


SEMANTIC_ANNOTATIONS_SCHEME = (
    "org.opensmell.semantic.annotations"
)
SEMANTIC_ANNOTATIONS_SCHEME_VERSION = "0.1"


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


@dataclass(frozen=True)
class SemanticChannelBinding:
    """Device-specific mapping for one semantic descriptor."""

    descriptor: str
    channel: int
    intensity: float

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.descriptor,
            "SemanticChannelBinding.descriptor",
        )

        command = DeviceCommand(
            channel=self.channel,
            intensity=self.intensity,
        )

        object.__setattr__(
            self,
            "channel",
            command.channel,
        )
        object.__setattr__(
            self,
            "intensity",
            command.intensity,
        )


class SemanticChannelMapper:
    """Map positive semantic annotations to configured device channels.

    Only Annotation resources using
    ``org.opensmell.semantic.annotations`` version ``0.1`` are interpreted.

    The mapper expects RFC-0004-style annotation data containing an
    ``annotations`` list. Entries with ``state == "present"`` are candidates
    for mapping. Absent, unknown, malformed, and unconfigured entries do not
    produce device commands.

    The binding table is device/application policy, not an OpenSmell semantic
    definition.
    """

    def __init__(
        self,
        bindings: list[SemanticChannelBinding],
    ) -> None:
        if not isinstance(bindings, list):
            raise TypeError(
                "bindings must be a list"
            )

        by_descriptor: dict[
            str,
            SemanticChannelBinding,
        ] = {}

        channels: set[int] = set()

        for binding in bindings:
            if not isinstance(
                binding,
                SemanticChannelBinding,
            ):
                raise TypeError(
                    "bindings must contain "
                    "SemanticChannelBinding values"
                )

            if binding.descriptor in by_descriptor:
                raise ValueError(
                    "duplicate semantic descriptor binding: "
                    f"{binding.descriptor}"
                )

            if binding.channel in channels:
                raise ValueError(
                    "duplicate device channel binding: "
                    f"{binding.channel}"
                )

            by_descriptor[
                binding.descriptor
            ] = binding
            channels.add(
                binding.channel
            )

        self._bindings = tuple(bindings)
        self._by_descriptor = by_descriptor

    @property
    def bindings(
        self,
    ) -> list[SemanticChannelBinding]:
        """Return a copy of the configured binding list."""

        return list(
            self._bindings
        )

    def map(
        self,
        graph: GenericResourceGraph,
        request: RenderRequest,
        *,
        index: ReferenceIndex | None = None,
    ) -> RenderingPlan:
        """Map one graph resource request to a RenderingPlan."""

        if not isinstance(
            graph,
            GenericResourceGraph,
        ):
            raise TypeError(
                "graph must be a GenericResourceGraph"
            )

        if not isinstance(
            request,
            RenderRequest,
        ):
            raise TypeError(
                "request must be a RenderRequest"
            )

        subject = graph.get(
            request.resource_id
        )

        if subject is None:
            raise ValueError(
                "render request resource does not exist: "
                f"{request.resource_id}"
            )

        if index is None:
            index = build_reference_index(
                graph
            )
        elif not isinstance(
            index,
            ReferenceIndex,
        ):
            raise TypeError(
                "index must be a ReferenceIndex"
            )
        elif index.graph is not graph:
            raise ValueError(
                "index was built for a different graph"
            )

        commands: list[DeviceCommand] = []
        used_channels: set[int] = set()
        annotation_ids: list[str] = []

        for discovered in index.references_to(
            request.resource_id
        ):
            annotation = graph.get(
                discovered.source_id
            )

            if not isinstance(
                annotation,
                Annotation,
            ):
                continue

            if (
                annotation.scheme.id
                != SEMANTIC_ANNOTATIONS_SCHEME
                or annotation.scheme.version
                != SEMANTIC_ANNOTATIONS_SCHEME_VERSION
            ):
                continue

            annotation_ids.append(
                annotation.id
            )

            for descriptor in self._present_descriptors(
                annotation
            ):
                binding = self._by_descriptor.get(
                    descriptor
                )

                if binding is None:
                    continue

                if binding.channel in used_channels:
                    continue

                commands.append(
                    DeviceCommand(
                        channel=binding.channel,
                        intensity=binding.intensity,
                    )
                )
                used_channels.add(
                    binding.channel
                )

        return RenderingPlan(
            commands=commands,
            duration=request.duration,
            extra={
                "mapper": (
                    "org.opensmell.experimental."
                    "semantic-channel-mapper"
                ),
                "source_resource_id": (
                    request.resource_id
                ),
                "annotation_ids": (
                    annotation_ids
                ),
            },
        )

    @staticmethod
    def _present_descriptors(
        annotation: Annotation,
    ) -> list[str]:
        annotations = annotation.data.get(
            "annotations"
        )

        if not isinstance(
            annotations,
            list,
        ):
            return []

        result: list[str] = []

        for item in annotations:
            if not isinstance(
                item,
                dict,
            ):
                continue

            if item.get("state") != "present":
                continue

            value = item.get("value")

            if not isinstance(
                value,
                str,
            ):
                continue

            if not value:
                continue

            result.append(
                value
            )

        return result
