"""Experimental rendering device adapter contract for OpenSmell.

A DeviceAdapter represents the boundary between an OpenSmell RenderingPlan
and a concrete rendering target.

The contract is intentionally minimal. An adapter exposes the technical
capabilities of its target and accepts RenderingPlan objects for rendering.

This abstraction does not define:

- physical odor reproduction,
- cartridge or chemical semantics,
- transport protocols,
- connection lifecycle,
- scheduling,
- hardware discovery,
- universal channel meanings.

Concrete adapters may implement those concerns independently when required by
their hardware.

DeviceAdapter is a structural Protocol. Implementations do not need to inherit
from it explicitly.

Runtime protocol checks only establish structural compatibility. They do not
validate the runtime value of ``capabilities``. Use ``require_device_adapter``
when semantic runtime validation is required.

This module is experimental and non-normative.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .device_capabilities import DeviceCapabilities
from .rendering import RenderingPlan


@runtime_checkable
class DeviceAdapter(Protocol):
    """Minimal structural contract for a rendering target."""

    @property
    def capabilities(self) -> DeviceCapabilities:
        """Return the technical capabilities of the rendering target."""

        ...

    def render(
        self,
        plan: RenderingPlan,
    ) -> object:
        """Render a plan using the target implementation.

        Implementations determine their own return value. The protocol does
        not assign semantics to the returned object.

        A concrete adapter is responsible for rejecting plans that its target
        cannot execute.
        """

        ...


def require_device_adapter(
    adapter: Any,
) -> DeviceAdapter:
    """Validate and return a runtime-usable DeviceAdapter.

    ``isinstance(adapter, DeviceAdapter)`` is useful for structural runtime
    checks, but a runtime-checkable Protocol does not validate the concrete
    value stored in every annotated attribute.

    This helper therefore verifies the minimal runtime requirements required
    by the experimental rendering boundary:

    - the object structurally satisfies DeviceAdapter,
    - ``capabilities`` is a DeviceCapabilities instance,
    - ``render`` is callable.

    The validated adapter is returned unchanged.

    This function does not connect to hardware, inspect transport state, or
    determine whether a particular RenderingPlan is supported. Concrete plan
    compatibility remains the responsibility of DeviceCapabilities and the
    adapter implementation.
    """

    if not isinstance(
        adapter,
        DeviceAdapter,
    ):
        raise TypeError(
            "adapter must satisfy the DeviceAdapter protocol"
        )

    capabilities = adapter.capabilities

    if not isinstance(
        capabilities,
        DeviceCapabilities,
    ):
        raise TypeError(
            "adapter.capabilities must be a DeviceCapabilities"
        )

    render = adapter.render

    if not callable(
        render
    ):
        raise TypeError(
            "adapter.render must be callable"
        )

    return adapter