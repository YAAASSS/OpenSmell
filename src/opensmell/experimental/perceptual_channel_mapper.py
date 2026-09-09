"""Experimental perceptual-measurement-to-channel mapper for OpenSmell.

This module demonstrates how quantitative perceptual measurements stored in
an OpenSmell GenericResourceGraph can be consumed by a device-specific
mapping policy.

The mapping is deliberately external to OpenSmell representation data.
A perceptual property such as ``flower`` has no universal channel or physical
rendering meaning in OpenSmell.

Measurement values are normalized using the explicit scale carried by each
measurement:

    normalized = (value - min) / (max - min)

The mapper does not assume a fixed 0..100 scale.

This mapper is illustrative only. It does not claim that activating configured
channels reproduces the measured odor.

This module is experimental and non-normative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .generic_graph import GenericResourceGraph
from .rendering import (
    DeviceCommand,
    RenderingPlan,
    RenderRequest,
)
from .resources import Observation


PERCEPTUAL_MEASUREMENTS_SCHEME = (
    "org.opensmell.perceptual.measurements"
)

PERCEPTUAL_MEASUREMENTS_SCHEME_VERSION = "0.1"


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
class PerceptualChannelBinding:
    """Device-specific mapping for one perceptual property."""

    property: str
    channel: int

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.property,
            "PerceptualChannelBinding.property",
        )

        # DeviceCommand performs the same channel validation used by the
        # rendering subsystem. Intensity 0.0 is only a temporary validation
        # value here; actual intensity comes from normalized measurement data.
        command = DeviceCommand(
            channel=self.channel,
            intensity=0.0,
        )

        object.__setattr__(
            self,
            "channel",
            command.channel,
        )


class PerceptualChannelMapper:
    """Map quantitative perceptual measurements to device channels.

    Only Observation results using
    ``org.opensmell.perceptual.measurements`` version ``0.1`` are
    interpreted.

    Each configured perceptual property maps to one device channel.

    Intensity is derived from the measurement's explicit numeric scale:

        (value - min) / (max - min)

    The binding table is device/application policy, not an OpenSmell
    perceptual definition.

    This mapper does not know about Keller/Vosshall or any other source
    dataset.
    """

    def __init__(
        self,
        bindings: list[PerceptualChannelBinding],
    ) -> None:
        if not isinstance(bindings, list):
            raise TypeError(
                "bindings must be a list"
            )

        by_property: dict[
            str,
            PerceptualChannelBinding,
        ] = {}

        channels: set[int] = set()

        for binding in bindings:
            if not isinstance(
                binding,
                PerceptualChannelBinding,
            ):
                raise TypeError(
                    "bindings must contain "
                    "PerceptualChannelBinding values"
                )

            if binding.property in by_property:
                raise ValueError(
                    "duplicate perceptual property binding: "
                    f"{binding.property}"
                )

            if binding.channel in channels:
                raise ValueError(
                    "duplicate device channel binding: "
                    f"{binding.channel}"
                )

            by_property[
                binding.property
            ] = binding

            channels.add(
                binding.channel
            )

        self._bindings = tuple(
            bindings
        )

        self._by_property = (
            by_property
        )

    @property
    def bindings(
        self,
    ) -> list[PerceptualChannelBinding]:
        """Return a copy of the configured binding list."""

        return list(
            self._bindings
        )

    def map(
        self,
        graph: GenericResourceGraph,
        request: RenderRequest,
    ) -> RenderingPlan:
        """Map one Observation resource to a RenderingPlan."""

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

        resource = graph.get(
            request.resource_id
        )

        if resource is None:
            raise ValueError(
                "render request resource does not exist: "
                f"{request.resource_id}"
            )

        if not isinstance(
            resource,
            Observation,
        ):
            raise ValueError(
                "perceptual channel mapper requires "
                "an Observation resource"
            )

        commands: list[
            DeviceCommand
        ] = []

        used_channels: set[int] = set()

        result_indexes: list[int] = []

        for result_index, result in enumerate(
            resource.results
        ):
            if (
                result.scheme.id
                != PERCEPTUAL_MEASUREMENTS_SCHEME
                or result.scheme.version
                != PERCEPTUAL_MEASUREMENTS_SCHEME_VERSION
            ):
                continue

            measurements = (
                result.data.get(
                    "measurements"
                )
            )

            if not isinstance(
                measurements,
                list,
            ):
                continue

            result_used = False

            for measurement in measurements:
                parsed = (
                    self._parse_measurement(
                        measurement
                    )
                )

                if parsed is None:
                    continue

                (
                    property_name,
                    normalized,
                ) = parsed

                binding = (
                    self._by_property.get(
                        property_name
                    )
                )

                if binding is None:
                    continue

                if (
                    binding.channel
                    in used_channels
                ):
                    continue

                commands.append(
                    DeviceCommand(
                        channel=(
                            binding.channel
                        ),
                        intensity=normalized,
                    )
                )

                used_channels.add(
                    binding.channel
                )

                result_used = True

            if result_used:
                result_indexes.append(
                    result_index
                )

        return RenderingPlan(
            commands=commands,
            duration=request.duration,
            extra={
                "mapper": (
                    "org.opensmell.experimental."
                    "perceptual-channel-mapper"
                ),
                "source_resource_id": (
                    request.resource_id
                ),
                "result_indexes": (
                    result_indexes
                ),
            },
        )

    @staticmethod
    def _parse_measurement(
        measurement: Any,
    ) -> tuple[str, float] | None:
        """Return property and normalized intensity for one measurement."""

        if not isinstance(
            measurement,
            dict,
        ):
            return None

        property_name = (
            measurement.get(
                "property"
            )
        )

        if (
            not isinstance(
                property_name,
                str,
            )
            or not property_name
        ):
            return None

        value = measurement.get(
            "value"
        )

        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (int, float),
            )
        ):
            return None

        scale = measurement.get(
            "scale"
        )

        if not isinstance(
            scale,
            dict,
        ):
            return None

        minimum = scale.get(
            "min"
        )

        maximum = scale.get(
            "max"
        )

        if (
            isinstance(minimum, bool)
            or not isinstance(
                minimum,
                (int, float),
            )
            or isinstance(maximum, bool)
            or not isinstance(
                maximum,
                (int, float),
            )
        ):
            return None

        if minimum >= maximum:
            return None

        if not (
            minimum
            <= value
            <= maximum
        ):
            return None

        normalized = (
            (float(value) - float(minimum))
            / (
                float(maximum)
                - float(minimum)
            )
        )

        return (
            property_name,
            normalized,
        )