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

The mapper remains responsible for producing a RenderingPlan. The target
capabilities remain responsible for technical plan validation. The adapter
remains responsible for executing the plan.

This module is experimental and non-normative.
"""

from __future__ import annotations

from typing import Any

from .device_adapter import (
    DeviceAdapter,
    require_device_adapter,
)
from .generic_graph import (
    GenericResourceGraph,
)
from .rendering import (
    RenderingPlan,
    RenderRequest,
)
from .semantic_channel_mapper import (
    SemanticChannelMapper,
)


def render_to_device(
    graph: GenericResourceGraph,
    request: RenderRequest,
    mapper: SemanticChannelMapper,
    adapter: Any,
) -> object:
    """Map an OpenSmell request and render it through a device adapter.

    The operation is intentionally explicit:

    1. validate the graph, request, mapper, and adapter,
    2. verify mapper configuration compatibility with the target,
    3. produce a RenderingPlan,
    4. validate the concrete plan against target capabilities,
    5. render the plan through the adapter.

    Mapper compatibility is checked before mapping so configuration errors can
    be detected early.

    Concrete plan validation is still performed because mapper compatibility
    does not cover request-specific constraints such as duration.

    The adapter return value is returned unchanged.
    """

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

    if not isinstance(
        mapper,
        SemanticChannelMapper,
    ):
        raise TypeError(
            "mapper must be a SemanticChannelMapper"
        )

    target: DeviceAdapter = require_device_adapter(
        adapter
    )

    mapper.require_support(
        target.capabilities
    )

    plan = mapper.map(
        graph,
        request,
    )

    target.capabilities.require_plan(
        plan
    )

    return target.render(
        plan
    )


def build_rendering_plan(
    graph: GenericResourceGraph,
    request: RenderRequest,
    mapper: SemanticChannelMapper,
    adapter: Any,
) -> RenderingPlan:
    """Build and validate a RenderingPlan without executing it.

    This is useful for inspection, logging, testing, previews, or applications
    that want to separate planning from execution.

    The mapper configuration must be compatible with the target, and the
    resulting concrete plan must satisfy the target DeviceCapabilities.
    """

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

    if not isinstance(
        mapper,
        SemanticChannelMapper,
    ):
        raise TypeError(
            "mapper must be a SemanticChannelMapper"
        )

    target: DeviceAdapter = require_device_adapter(
        adapter
    )

    mapper.require_support(
        target.capabilities
    )

    plan = mapper.map(
        graph,
        request,
    )

    target.capabilities.require_plan(
        plan
    )

    return plan