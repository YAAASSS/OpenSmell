"""Run the first end-to-end OpenSmell rendering demonstration.

This example starts with an OdorNet-shaped record, converts it with the
existing OpenSmell adapter, bridges the Core Odor into the experimental
ResourceGraph, maps positive semantic annotations through a device-specific
policy, and sends the resulting RenderingPlan to a SimulatedDiffuser.

The channel bindings below are illustrative only. They are not a scientific
claim that these channels reproduce the source odor.
"""

from __future__ import annotations

from opensmell.adapters.odornet import (
    ANNOTATION_SCHEME_ID,
    from_record_with_annotations,
)
from opensmell.experimental.annotation import Annotation
from opensmell.experimental.odor_graph_bridge import (
    bridge_odor_to_resource_graph,
)
from opensmell.experimental.rendering import RenderRequest
from opensmell.experimental.semantic_channel_mapper import (
    SemanticChannelBinding,
    SemanticChannelMapper,
)
from opensmell.experimental.simulated_diffuser import SimulatedDiffuser


def main() -> None:
    record = {
        "SMILES": "CCO",
        "animalic&ambery": 0,
        "sweety&gourmand": 1,
        "floral": 1,
        "fruity&vegetable": 0,
        "pungent&disagreeable": 0,
        "green&herbal": 0,
        "nutty": None,
        "woody&mossy": 0,
        "resinous&balsamic": 0,
        "cooked": 0,
        "odorless": 0,
        "spice": 1,
    }

    print("OpenSmell experimental rendering demo")
    print("=" * 37)
    print()
    print("Source: OdorNet-shaped example record")
    print(f"SMILES: {record['SMILES']}")
    print()

    odor = from_record_with_annotations(
        record,
        odor_id="odornet-rendering-demo",
    )

    semantic = next(
        representation
        for representation in odor.representations
        if representation.scheme.id
        == ANNOTATION_SCHEME_ID
    )

    print("Semantic information:")
    for item in semantic.data["annotations"]:
        if item["state"] == "present":
            print(
                f"  {item['value']:<24} : present"
            )
    print()

    result = bridge_odor_to_resource_graph(
        odor
    )

    annotation = result.graph.require(
        result.annotation_ids[0]
    )

    if not isinstance(
        annotation,
        Annotation,
    ):
        raise RuntimeError(
            "expected bridged Annotation resource"
        )

    print("OpenSmell ResourceGraph:")
    print(
        "  Molecule:   "
        f"{result.primary_resource_id}"
    )
    print(
        "  Annotation: "
        f"{annotation.id}"
    )
    print(
        "  Subject:    "
        f"{annotation.subject.resource_id}"
    )
    print()

    request = RenderRequest(
        resource_id=result.primary_resource_id,
        duration=4.0,
    )

    bindings = [
        SemanticChannelBinding(
            descriptor="floral",
            channel=1,
            intensity=0.70,
        ),
        SemanticChannelBinding(
            descriptor="sweety&gourmand",
            channel=2,
            intensity=0.55,
        ),
        SemanticChannelBinding(
            descriptor="spice",
            channel=3,
            intensity=0.35,
        ),
        SemanticChannelBinding(
            descriptor="nutty",
            channel=4,
            intensity=0.80,
        ),
    ]

    mapper = SemanticChannelMapper(
        bindings=bindings
    )

    print("Render request:")
    print(
        f"  Resource: {request.resource_id}"
    )
    print(
        f"  Duration: {request.duration:.1f} s"
    )
    print()

    print("Device-specific demo policy:")
    for binding in bindings:
        print(
            f"  {binding.descriptor:<24} "
            f"-> channel {binding.channel} "
            f"@ {binding.intensity:.2f}"
        )
    print()

    plan = mapper.map(
        result.graph,
        request,
    )

    print("RenderingPlan:")
    if plan.commands:
        for command in plan.commands:
            print(
                f"  Channel {command.channel}: "
                f"{command.intensity:.2f}"
            )
    else:
        print("  No mapped commands")
    print(
        f"  Duration: {plan.duration:.1f} s"
    )
    print()

    diffuser = SimulatedDiffuser()
    event = diffuser.render(
        plan
    )

    print("SimulatedDiffuser:")
    for command in event.commands:
        print(
            f"  Recorded channel "
            f"{command.channel} @ "
            f"{command.intensity:.2f}"
        )
    print(
        f"  Recorded duration: "
        f"{event.duration:.1f} s"
    )
    print()
    print(
        "Rendering completed successfully "
        "(simulation only)."
    )


if __name__ == "__main__":
    main()
