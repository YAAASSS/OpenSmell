"""OpenSmell multi-source interoperability demonstration.

This demonstration loads a single experimental .osmell GenericResourceGraph
and independently derives:

1. a semantic RenderingPlan from semantic Annotation resources;
2. a quantitative perceptual RenderingPlan from Observation resources.

The source datasets are not required at demonstration time.

The configured descriptor/property-to-channel bindings are experimental
device/application policy. They are not universal OpenSmell semantics.

This demonstration validates representation interoperability, mapping, and
optional physical device control. It does not claim physical odor
reproduction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from opensmell.experimental.annotation import (  # noqa: E402
    register_annotation_resource_type,
)
from opensmell.experimental.generic_graph import (  # noqa: E402
    GenericResourceGraph,
    create_default_resource_type_registry,
    generic_graph_loads,
)
from opensmell.experimental.molecule import (  # noqa: E402
    Molecule,
    register_molecule_resource_type,
)
from opensmell.experimental.perceptual_channel_mapper import (  # noqa: E402
    PerceptualChannelBinding,
    PerceptualChannelMapper,
)
from opensmell.experimental.protocol_device_adapter import (  # noqa: E402
    ProtocolDeviceAdapter,
)
from opensmell.experimental.rendering import (  # noqa: E402
    RenderingPlan,
    RenderRequest,
)
from opensmell.experimental.resources import (  # noqa: E402
    Observation,
)
from opensmell.experimental.semantic_channel_mapper import (  # noqa: E402
    SemanticChannelBinding,
    SemanticChannelMapper,
)
from opensmell.experimental.serial_device_transport import (  # noqa: E402
    SerialDeviceTransport,
)


EXPECTED_DEVICE_ID = (
    "opensmell-esp32-led-3ch-001"
)

DEFAULT_DURATION = 5.0


SEMANTIC_BINDINGS = [
    SemanticChannelBinding(
        descriptor="floral",
        channel=0,
        intensity=0.25,
    ),
    SemanticChannelBinding(
        descriptor="green&herbal",
        channel=1,
        intensity=0.60,
    ),
    SemanticChannelBinding(
        descriptor="woody&mossy",
        channel=2,
        intensity=1.00,
    ),
]


PERCEPTUAL_BINDINGS = [
    PerceptualChannelBinding(
        property="flower",
        channel=0,
    ),
    PerceptualChannelBinding(
        property="grass",
        channel=1,
    ),
    PerceptualChannelBinding(
        property="wood",
        channel=2,
    ),
]


def create_registry():
    """Create the registry required by the multi-source graph."""

    registry = (
        create_default_resource_type_registry()
    )

    register_molecule_resource_type(
        registry
    )

    register_annotation_resource_type(
        registry
    )

    return registry


def load_graph(
    path: Path,
) -> GenericResourceGraph:
    """Load one multi-source .osmell GenericResourceGraph."""

    text = path.read_text(
        encoding="utf-8"
    )

    registry = create_registry()

    return generic_graph_loads(
        text,
        registry=registry,
    )


def select_single_molecule(
    graph: GenericResourceGraph,
) -> Molecule:
    """Return the graph's single Molecule resource."""

    molecules = [
        resource
        for resource in graph.resources
        if isinstance(
            resource,
            Molecule,
        )
    ]

    if len(molecules) != 1:
        raise RuntimeError(
            "This demonstration requires exactly "
            "one Molecule resource; "
            f"found {len(molecules)}"
        )

    return molecules[0]


def select_single_observation(
    graph: GenericResourceGraph,
) -> Observation:
    """Return the graph's single Observation resource."""

    observations = [
        resource
        for resource in graph.resources
        if isinstance(
            resource,
            Observation,
        )
    ]

    if len(observations) != 1:
        raise RuntimeError(
            "This demonstration requires exactly "
            "one Observation resource; "
            f"found {len(observations)}"
        )

    return observations[0]


def build_semantic_plan(
    graph: GenericResourceGraph,
    molecule: Molecule,
    duration: float,
) -> RenderingPlan:
    """Build the semantic RenderingPlan."""

    mapper = SemanticChannelMapper(
        bindings=SEMANTIC_BINDINGS
    )

    return mapper.map(
        graph,
        RenderRequest(
            resource_id=molecule.id,
            duration=duration,
        ),
    )


def build_perceptual_plan(
    graph: GenericResourceGraph,
    observation: Observation,
    duration: float,
) -> RenderingPlan:
    """Build the quantitative perceptual RenderingPlan."""

    mapper = PerceptualChannelMapper(
        bindings=PERCEPTUAL_BINDINGS
    )

    return mapper.map(
        graph,
        RenderRequest(
            resource_id=observation.id,
            duration=duration,
        ),
    )


def print_plan(
    title: str,
    plan: RenderingPlan,
) -> None:
    """Display one RenderingPlan."""

    print()
    print(title)
    print("-" * 72)

    print(
        "Mapper:",
        plan.extra.get(
            "mapper"
        ),
    )

    print(
        "Source:",
        plan.extra.get(
            "source_resource_id"
        ),
    )

    print(
        "Duration:",
        plan.duration,
    )

    if not plan.commands:
        print(
            "Commands: none"
        )
        return

    for command in sorted(
        plan.commands,
        key=lambda item: item.channel,
    ):
        print(
            f"channel {command.channel}"
            f" -> {command.intensity:.2f}"
        )


def render_plan(
    plan: RenderingPlan,
    *,
    port: str,
) -> None:
    """Send one RenderingPlan to the physical ESP32."""

    if not plan.commands:
        raise RuntimeError(
            "Refusing to render an empty "
            "RenderingPlan"
        )

    print()
    print(
        "Opening physical device:",
        port,
    )

    with SerialDeviceTransport(
        port=port,
        baudrate=115200,
        timeout=2.0,
        startup_delay=2.0,
        discard_initial_input=True,
    ) as transport:

        adapter = ProtocolDeviceAdapter(
            transport
        )

        print(
            "Device ID:",
            adapter.device_id,
        )

        if (
            adapter.device_id
            != EXPECTED_DEVICE_ID
        ):
            raise RuntimeError(
                "Unexpected physical device: "
                f"{adapter.device_id!r}"
            )

        adapter.capabilities.require_plan(
            plan
        )

        response = adapter.render(
            plan
        )

        print(
            "Device response:",
            response,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Demonstrate independent semantic and "
            "quantitative perceptual interpretations "
            "from one OpenSmell .osmell graph."
        )
    )

    parser.add_argument(
        "path",
        type=Path,
        help="Path to the multi-source .osmell file",
    )

    parser.add_argument(
        "--render",
        choices=(
            "none",
            "semantic",
            "perceptual",
        ),
        default="none",
        help=(
            "Optionally send one derived plan "
            "to the physical device "
            "(default: none)"
        ),
    )

    parser.add_argument(
        "--port",
        default="COM8",
        help=(
            "ESP32 serial port "
            "(default: COM8)"
        ),
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=DEFAULT_DURATION,
        help=(
            "Rendering duration in seconds "
            f"(default: {DEFAULT_DURATION})"
        ),
    )

    args = parser.parse_args()

    print(
        "Loading .osmell:",
        args.path,
    )

    graph = load_graph(
        args.path
    )

    print(
        "GenericResourceGraph resources:",
        len(graph),
    )

    molecule = (
        select_single_molecule(
            graph
        )
    )

    observation = (
        select_single_observation(
            graph
        )
    )

    print()
    print("Shared graph resources")
    print("-" * 72)

    print(
        "Molecule:",
        molecule.id,
    )

    print(
        "Observation:",
        observation.id,
    )

    print(
        "Observation stimulus:",
        observation.stimulus.resource_id,
    )

    semantic_plan = (
        build_semantic_plan(
            graph,
            molecule,
            args.duration,
        )
    )

    perceptual_plan = (
        build_perceptual_plan(
            graph,
            observation,
            args.duration,
        )
    )

    print_plan(
        "OdorNet semantic interpretation",
        semantic_plan,
    )

    print_plan(
        "Keller/Vosshall perceptual interpretation",
        perceptual_plan,
    )

    print()
    print("Comparison")
    print("-" * 72)

    semantic_commands = {
        command.channel: command.intensity
        for command in semantic_plan.commands
    }

    perceptual_commands = {
        command.channel: command.intensity
        for command in perceptual_plan.commands
    }

    channels = sorted(
        set(semantic_commands)
        | set(perceptual_commands)
    )

    print(
        "channel | semantic | perceptual"
    )
    print(
        "--------+----------+-----------"
    )

    for channel in channels:
        semantic_value = (
            semantic_commands.get(
                channel
            )
        )

        perceptual_value = (
            perceptual_commands.get(
                channel
            )
        )

        semantic_text = (
            "-"
            if semantic_value is None
            else f"{semantic_value:.2f}"
        )

        perceptual_text = (
            "-"
            if perceptual_value is None
            else f"{perceptual_value:.2f}"
        )

        print(
            f"{channel:^7} | "
            f"{semantic_text:^8} | "
            f"{perceptual_text:^10}"
        )

    if args.render == "none":
        print()
        print(
            "Physical rendering: skipped"
        )
        print()
        print("SUCCESS")
        print(
            "One .osmell file produced two "
            "independent RenderingPlans."
        )
        return

    if args.render == "semantic":
        selected_plan = (
            semantic_plan
        )
        selected_name = (
            "semantic"
        )
    else:
        selected_plan = (
            perceptual_plan
        )
        selected_name = (
            "perceptual"
        )

    print()
    print(
        "Selected physical rendering:",
        selected_name,
    )

    render_plan(
        selected_plan,
        port=args.port,
    )

    print()
    print("SUCCESS")
    print(
        "One .osmell file produced two "
        "independent RenderingPlans and the "
        f"{selected_name} plan was sent to "
        "the physical device."
    )


if __name__ == "__main__":
    main()