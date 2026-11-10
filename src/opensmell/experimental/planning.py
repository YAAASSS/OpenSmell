"""Experimental offline planning with explicit application-owned profiles.

This module never creates an adapter or opens a transport. Capability values are
supplied configuration, not a claim about a connected or measured device.
"""

from __future__ import annotations

from typing import Any

from .device_protocol import parse_capabilities_response
from .generic_graph import GenericResourceGraph
from .perceptual_channel_mapper import PerceptualChannelBinding, PerceptualChannelMapper
from .rendering import RenderRequest, RenderingPlan
from .semantic_channel_mapper import SemanticChannelBinding, SemanticChannelMapper


MAPPING_PROFILE_FORMAT = "org.opensmell.experimental.mapping-profile"


def plan_with_profile(
    graph: GenericResourceGraph,
    request: RenderRequest,
    profile: dict[str, Any],
) -> RenderingPlan:
    """Map a graph request and validate the plan against supplied capabilities.

    Profile 0.1 supports the existing semantic and perceptual demonstration
    mappers. No channel meaning or physical effect is inferred from input data.
    See Draft RFC-0015 for this experimental configuration envelope.
    """
    if not isinstance(profile, dict):
        raise TypeError("mapping profile must be an object")
    if profile.get("format") != MAPPING_PROFILE_FORMAT or profile.get("version") != "0.1":
        raise ValueError("unsupported mapping profile format/version")
    bindings = profile.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise ValueError("mapping profile bindings must be a non-empty array")
    if not all(isinstance(binding, dict) for binding in bindings):
        raise TypeError("mapping profile bindings must contain objects")
    if profile.get("mapper") == "semantic":
        mapper = SemanticChannelMapper([SemanticChannelBinding(**binding) for binding in bindings])
    elif profile.get("mapper") == "perceptual":
        mapper = PerceptualChannelMapper([PerceptualChannelBinding(**binding) for binding in bindings])
    else:
        raise ValueError("mapping profile mapper must be 'semantic' or 'perceptual'")
    capabilities = parse_capabilities_response(profile.get("capabilities"))
    require_support = getattr(mapper, "require_support", None)
    if require_support is not None:
        require_support(capabilities)
    plan = mapper.map(graph, request)
    capabilities.require_plan(plan)
    if not plan.commands:
        raise ValueError("mapping produced no commands; check the selected resource and bindings")
    return plan
