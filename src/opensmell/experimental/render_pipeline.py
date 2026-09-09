"""Experimental high-level rendering pipeline for OpenSmell.

This module provides a small orchestration layer that connects:

- device-independent OpenSmell resources,
- a RenderRequest,
- a mapping policy,
- DeviceCapabilities,
- and a DeviceAdapter.

The pipeline coordinates existing responsibilities without redefining them.

It does not define:

- physical odor reproduction,
- universal channel meanings,
- cartridge or chemical semantics,
- hardware transport,
- connection lifecycle,
- scheduling,
- device discovery.

Any mapper that implements the RenderingMapper contract can participate in the
pipeline. A mapper remains responsible for producing a RenderingPlan. The
target capabilities remain responsible for technical plan validation. The
adapter remains responsible for executing the plan.

A mapper may additionally expose ``require_support(capabilities)`` for an
early configuration-level compatibility check. This hook is optional because
not every mapping policy can determine compatibility before it has interpreted
a concrete request. Concrete RenderingPlan validation is always performed.

This module is experimental and non-normative.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .device_adapter import (
    DeviceAdapter,
    require_device_adapter,
)
from .device_capabilities import DeviceCapabilities
from .generic_graph import GenericResourceGraph
from .rendering import (
    RenderingPlan,
    RenderRequest,
)


@runtime_checkable
class RenderingMapper(Protocol):
    """Structural contract for a rendering mapping policy.

    A rendering mapper interprets a graph and request and returns a concrete
    RenderingPlan. The protocol deliberately does not prescribe semantic,
    perceptual, dataset, or device-specific interpretation rules.
    """

    def map(
        self,
        graph: GenericResourceGraph,
        request: RenderRequest,
    ) -> RenderingPlan:
        """Map one request to a concrete RenderingPlan."""
        ...


def _require_rendering_mapper(
    value: Any,
) -> RenderingMapper:
    if not isinstance(
        value,
        RenderingMapper,
    ):
        raise TypeError(
            "mapper must implement RenderingMapper"
        )

    return value


def _require_mapper_support_if_available(
    mapper: RenderingMapper,
    capabilities: DeviceCapabilities,
) -> None:
    """Run an optional mapper-level capability check when available."""

    require_support = getattr(
        mapper,
        "require_support",
        None,
    )

    if require_support is None:
        return

    if not callable(require_support):
        raise TypeError(
            "mapper.require_support must be callable"
        )

    require_support(
        capabilities
    )


def _build_validated_plan(
    graph: GenericResourceGraph,
    request: RenderRequest,
    mapper: Any,
    adapter: Any,
) -> tuple[DeviceAdapter, RenderingPlan]:
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

    rendering_mapper = _require_rendering_mapper(
        mapper
    )

    target: DeviceAdapter = require_device_adapter(
        adapter
    )

    _require_mapper_support_if_available(
        rendering_mapper,
        target.capabilities,
    )

    plan = rendering_mapper.map(
        graph,
        request,
    )

    if not isinstance(
        plan,
        RenderingPlan,
    ):
        raise TypeError(
            "mapper.map must return a RenderingPlan"
        )

    target.capabilities.require_plan(
        plan
    )

    return target, plan


def render_to_device(
    graph: GenericResourceGraph,
    request: RenderRequest,
    mapper: RenderingMapper,
    adapter: Any,
) -> object:
    """Map an OpenSmell request and render it through a device adapter.

    The operation is intentionally explicit:

    1. validate the graph, request, mapper, and adapter,
    2. run an optional mapper-level compatibility check,
    3. produce a RenderingPlan,
    4. validate the concrete plan against target capabilities,
    5. render the plan through the adapter.

    The optional compatibility hook can detect configuration errors before
    mapping when a mapper supports such inspection. Concrete plan validation
    is always performed because mapper-level checks cannot necessarily cover
    request-specific constraints such as duration or data-derived intensity.

    The adapter return value is returned unchanged.
    """

    target, plan = _build_validated_plan(
        graph,
        request,
        mapper,
        adapter,
    )

    return target.render(
        plan
    )


def build_rendering_plan(
    graph: GenericResourceGraph,
    request: RenderRequest,
    mapper: RenderingMapper,
    adapter: Any,
) -> RenderingPlan:
    """Build and validate a RenderingPlan without executing it.

    This is useful for inspection, logging, testing, previews, or applications
    that want to separate planning from execution.

    An optional mapper-level compatibility check is run when the mapper
    provides one. The resulting concrete plan must always satisfy the target
    DeviceCapabilities.
    """

    _, plan = _build_validated_plan(
        graph,
        request,
        mapper,
        adapter,
    )

    return plan
