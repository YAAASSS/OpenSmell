"""Experimental semantic-to-channel mapper for OpenSmell.

This module demonstrates how scheme-defined semantic annotations in an
OpenSmell GenericResourceGraph can be consumed by a device-specific mapping
policy.

The mapping is deliberately external to OpenSmell representation data. A
descriptor such as ``floral`` has no universal channel or physical rendering
meaning in OpenSmell.

This mapper is illustrative only. It does not claim that activating configured
channels reproduces the annotated odor.

The mapper can also inspect DeviceCapabilities to determine whether its
configured bindings are technically compatible with a rendering target. This
compatibility check does not replace validation of an actual RenderingPlan by
the target device.

This module is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .annotation import Annotation
from .device_capabilities import DeviceCapabilities
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

    Device capability inspection is intentionally separate from ``map``.
    Applications may inspect whether the mapper configuration is compatible
    with a target before mapping. The target device must still validate every
    resulting RenderingPlan before execution.
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

    def compatible_bindings(
        self,
        capabilities: DeviceCapabilities,
    ) -> list[SemanticChannelBinding]:
        """Return bindings technically accepted by a target device.

        Compatibility here concerns only the channel and intensity encoded by
        each binding. Duration cannot be evaluated because a binding does not
        contain a rendering duration.

        This method does not modify the mapper configuration.
        """

        if not isinstance(
            capabilities,
            DeviceCapabilities,
        ):
            raise TypeError(
                "capabilities must be a DeviceCapabilities"
            )

        return [
            binding
            for binding in self._bindings
            if capabilities.accepts_command(
                DeviceCommand(
                    channel=binding.channel,
                    intensity=binding.intensity,
                )
            )
        ]

    def incompatible_bindings(
        self,
        capabilities: DeviceCapabilities,
    ) -> list[SemanticChannelBinding]:
        """Return bindings not technically accepted by a target device.

        A binding is incompatible when the device does not advertise its
        channel or when the configured intensity falls outside the advertised
        range.

        Duration constraints are deliberately outside this check.
        """

        if not isinstance(
            capabilities,
            DeviceCapabilities,
        ):
            raise TypeError(
                "capabilities must be a DeviceCapabilities"
            )

        return [
            binding
            for binding in self._bindings
            if not capabilities.accepts_command(
                DeviceCommand(
                    channel=binding.channel,
                    intensity=binding.intensity,
                )
            )
        ]

    def supports(
        self,
        capabilities: DeviceCapabilities,
    ) -> bool:
        """Return whether every configured binding is device-compatible.

        This is a configuration-level check only. A concrete RenderingPlan
        must still be validated by the target because request-specific
        constraints such as duration are not represented by mapper bindings.
        """

        if not isinstance(
            capabilities,
            DeviceCapabilities,
        ):
            raise TypeError(
                "capabilities must be a DeviceCapabilities"
            )

        return not self.incompatible_bindings(
            capabilities
        )

    def require_support(
        self,
        capabilities: DeviceCapabilities,
    ) -> None:
        """Raise ValueError when any configured binding is incompatible.

        The error identifies all incompatible descriptor/channel bindings so
        applications can diagnose mapper/device configuration mismatches
        before attempting rendering.
        """

        if not isinstance(
            capabilities,
            DeviceCapabilities,
        ):
            raise TypeError(
                "capabilities must be a DeviceCapabilities"
            )

        incompatible = self.incompatible_bindings(
            capabilities
        )

        if not incompatible:
            return

        details = ", ".join(
            (
                f"{binding.descriptor}"
                f" -> channel {binding.channel}"
                f" @ {binding.intensity}"
            )
            for binding in incompatible
        )

        raise ValueError(
            "semantic channel mapper is not compatible "
            f"with device {capabilities.device_id}: "
            f"{details}"
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