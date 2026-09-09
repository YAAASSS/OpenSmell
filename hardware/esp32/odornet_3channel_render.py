"""Physical three-channel rendering experiment from an OdorNet record.

This script demonstrates the experimental path:

    enriched OdorNet record
        -> GenericResourceGraph
        -> semantic Annotation
        -> SemanticChannelMapper
        -> RenderingPlan
        -> ProtocolDeviceAdapter
        -> SerialDeviceTransport
        -> physical ESP32 outputs

The semantic-to-channel bindings and intensities below are experimental
device/application policy.

They do not claim that the LEDs reproduce the source odor, and the OdorNet
binary descriptor values are not interpreted as physical rendering
intensities.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from opensmell.experimental.odornet_enriched_adapter import (
    enriched_odornet_record_to_graph,
)
from opensmell.experimental.protocol_device_adapter import (
    ProtocolDeviceAdapter,
)
from opensmell.experimental.render_pipeline import (
    build_rendering_plan,
    render_to_device,
)
from opensmell.experimental.rendering import (
    RenderRequest,
)
from opensmell.experimental.semantic_channel_mapper import (
    SemanticChannelBinding,
    SemanticChannelMapper,
)
from opensmell.experimental.serial_device_transport import (
    SerialDeviceTransport,
)


DATASET_PATH = Path("examples/odornet_enriched.csv")

TARGET_ROW_INDEX = 37

EXPECTED_DEVICE_ID = (
    "opensmell-esp32-led-3ch-001"
)

RENDER_DURATION_SECONDS = 5.0


def load_record() -> dict[str, object]:
    """Load and normalize the selected enriched OdorNet record."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"OdorNet dataset not found: {DATASET_PATH}\n"
            "This dataset is external/local and is intentionally "
            "not tracked by the OpenSmell repository."
        )

    dataframe = pd.read_csv(
        DATASET_PATH
    )

    if TARGET_ROW_INDEX not in dataframe.index:
        raise RuntimeError(
            "OdorNet target row does not exist: "
            f"{TARGET_ROW_INDEX}"
        )

    row = dataframe.loc[
        TARGET_ROW_INDEX
    ]

    # pandas represents missing CSV cells as NaN.
    #
    # The experimental enriched OdorNet adapter expects missing
    # semantic values as None, so normalize pandas missing values
    # before conversion.
    record = {
        key: (
            None
            if pd.isna(value)
            else value
        )
        for key, value in row.to_dict().items()
    }

    return record


def present_descriptors(
    record: dict[str, object],
) -> list[str]:
    """Return semantic descriptors explicitly present in OdorNet."""

    descriptor_names = (
        "animalic&ambery",
        "sweety&gourmand",
        "floral",
        "fruity&vegetable",
        "pungent&disagreeable",
        "green&herbal",
        "nutty",
        "woody&mossy",
        "resinous&balsamic",
        "cooked",
        "odorless",
        "spice",
    )

    return [
        descriptor
        for descriptor in descriptor_names
        if record.get(descriptor) == 1
    ]


def create_mapper() -> SemanticChannelMapper:
    """Create the experimental three-channel device policy."""

    return SemanticChannelMapper(
        bindings=[
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
    )


def print_dataset_information(
    record: dict[str, object],
) -> None:
    """Display the external source data used by the experiment."""

    print()
    print("=== OdorNet source record ===")
    print()

    print(
        "Row:",
        TARGET_ROW_INDEX,
    )

    print(
        "PubChem title:",
        record.get("PubChem_Title"),
    )

    print(
        "SMILES:",
        record.get("SMILES"),
    )

    print(
        "InChIKey:",
        record.get("PubChem_InChIKey"),
    )

    print()
    print("Descriptors marked present by OdorNet:")

    for descriptor in present_descriptors(
        record
    ):
        print(
            f"  - {descriptor}"
        )


def print_graph_information(
    result,
) -> None:
    """Display identifiers created by the OpenSmell adapter."""

    print()
    print("=== OpenSmell ResourceGraph ===")
    print()

    print(
        "Molecule resource:",
        result.molecule_id,
    )

    print(
        "Annotation resource:",
        result.annotation_id,
    )

    print(
        "Resource count:",
        len(result.graph.resources),
    )


def print_device_information(
    adapter: ProtocolDeviceAdapter,
) -> None:
    """Display the physical device discovered through the protocol."""

    capabilities = adapter.capabilities

    print()
    print("=== Physical device ===")
    print()

    print(
        "Device ID:",
        adapter.device_id,
    )

    print(
        "Duration range:",
        capabilities.min_duration,
        "to",
        capabilities.max_duration,
        "seconds",
    )

    print()
    print("Advertised channels:")

    for channel in capabilities.channels:
        print(
            "  - channel",
            channel.channel,
            "intensity",
            channel.min_intensity,
            "to",
            channel.max_intensity,
        )


def print_mapping_policy(
    mapper: SemanticChannelMapper,
) -> None:
    """Display the experimental semantic-to-device policy."""

    print()
    print("=== Experimental mapping policy ===")
    print()

    for binding in mapper.bindings:
        print(
            f"  {binding.descriptor}"
            f" -> channel {binding.channel}"
            f" @ {binding.intensity:.2f}"
        )

    print()
    print(
        "NOTE: these intensities are device/application policy."
    )
    print(
        "They are NOT OdorNet odor-intensity measurements."
    )


def print_rendering_plan(
    plan,
) -> None:
    """Display the actual plan produced by OpenSmell."""

    print()
    print("=== OpenSmell RenderingPlan ===")
    print()

    print(
        "Duration:",
        plan.duration,
        "seconds",
    )

    print(
        "Commands:"
    )

    for command in plan.commands:
        print(
            f"  channel {command.channel}"
            f" -> {command.intensity:.2f}"
        )

    print()
    print(
        "Source resource:",
        plan.extra.get(
            "source_resource_id"
        ),
    )

    print(
        "Annotations used:",
        plan.extra.get(
            "annotation_ids"
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Render one enriched OdorNet record through "
            "the experimental OpenSmell three-channel "
            "ESP32 pipeline."
        )
    )

    parser.add_argument(
        "--port",
        required=True,
        help="ESP32 serial port.",
    )

    args = parser.parse_args()

    record = load_record()

    print_dataset_information(
        record
    )

    result = (
        enriched_odornet_record_to_graph(
            record
        )
    )

    print_graph_information(
        result
    )

    mapper = create_mapper()

    print_mapping_policy(
        mapper
    )

    request = RenderRequest(
        resource_id=result.molecule_id,
        duration=RENDER_DURATION_SECONDS,
    )

    print()
    print(
        f"Opening serial device on {args.port}..."
    )

    with SerialDeviceTransport(
        port=args.port,
        baudrate=115200,
        timeout=2.0,
        startup_delay=2.0,
        discard_initial_input=True,
    ) as transport:

        adapter = ProtocolDeviceAdapter(
            transport
        )

        print_device_information(
            adapter
        )

        if (
            adapter.device_id
            != EXPECTED_DEVICE_ID
        ):
            raise RuntimeError(
                "Unexpected physical device: "
                f"{adapter.device_id!r}; expected "
                f"{EXPECTED_DEVICE_ID!r}"
            )

        plan = build_rendering_plan(
            result.graph,
            request,
            mapper,
            adapter,
        )

        print_rendering_plan(
            plan
        )

        print()
        print(
            "Executing physical render..."
        )

        response = render_to_device(
            result.graph,
            request,
            mapper,
            adapter,
        )

        print(
            "Device response:",
            response,
        )

    print()
    print("SUCCESS")
    print(
        "OdorNet -> OpenSmell -> mapper -> "
        "Device Protocol -> ESP32 completed."
    )


if __name__ == "__main__":
    main()