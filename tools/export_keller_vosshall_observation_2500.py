"""Export one Keller/Vosshall observation as an experimental .osmell graph.

This tool extracts one already-modelled Keller/Vosshall psychophysical
observation from the experimental OpenSmell ResourceGraph and writes a
self-contained graph containing:

- its Stimulus;
- its ObservationTarget;
- its Observation.

The Stimulus.source molecule reference may remain unresolved, as permitted
by the experimental ResourceGraph architecture.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from analyze_keller_vosshall_resource_graph import (  # noqa: E402
    build_resource_graph,
    clean_source_value,
    get_perceptual_measurements,
    load_dataset,
    require_column,
)

from opensmell.experimental.graph import (  # noqa: E402
    ResourceGraph,
)
from opensmell.experimental.graph_serialization import (  # noqa: E402
    dumps,
    loads,
)
from opensmell.experimental.resources import (  # noqa: E402
    Observation,
    ObservationTarget,
    Stimulus,
)


TARGET_SOURCE_ROW = 2500

EXPECTED_CID = "61918"
EXPECTED_ODOR = "2-Acetyl-3-ethylpyrazine"
EXPECTED_DILUTION = "1/1,000"
EXPECTED_SUBJECT = "3"

EXPECTED_MEASUREMENTS = {
    "FLOWER": 26.0,
    "GRASS": 38.0,
    "WOOD": 89.0,
}

OUTPUT_PATH = (
    PROJECT_ROOT
    / "examples"
    / "keller_vosshall_observation_2500.osmell"
)


def find_target_observation(
    graph: ResourceGraph,
    dataframe,
) -> Observation:
    row = dataframe.loc[
        TARGET_SOURCE_ROW
    ]

    cid_column = require_column(
        dataframe,
        ("CID",),
        dataset_name="Keller/Vosshall",
    )

    odor_column = require_column(
        dataframe,
        ("Odor",),
        dataset_name="Keller/Vosshall",
    )

    dilution_column = require_column(
        dataframe,
        ("Odor dilution",),
        dataset_name="Keller/Vosshall",
    )

    subject_column = require_column(
        dataframe,
        ("Subject # (this study)",),
        dataset_name="Keller/Vosshall",
    )

    cid = clean_source_value(
        row[cid_column]
    )

    odor = clean_source_value(
        row[odor_column]
    )

    dilution = clean_source_value(
        row[dilution_column]
    )

    subject = clean_source_value(
        row[subject_column]
    )

    if cid != EXPECTED_CID:
        raise RuntimeError(
            f"Unexpected CID: {cid!r}"
        )

    if odor != EXPECTED_ODOR:
        raise RuntimeError(
            f"Unexpected odor: {odor!r}"
        )

    if dilution != EXPECTED_DILUTION:
        raise RuntimeError(
            f"Unexpected dilution: {dilution!r}"
        )

    if subject != EXPECTED_SUBJECT:
        raise RuntimeError(
            f"Unexpected subject: {subject!r}"
        )

    matches: list[Observation] = []

    for resource in graph.resources:
        if not isinstance(
            resource,
            Observation,
        ):
            continue

        target = graph.resolve(
            resource.target
        )

        stimulus = graph.resolve(
            resource.stimulus
        )

        if not isinstance(
            target,
            ObservationTarget,
        ):
            continue

        if not isinstance(
            stimulus,
            Stimulus,
        ):
            continue

        target_subject = None

        for identifier in target.identifiers:
            if (
                identifier.scheme
                == "keller_vosshall.subject"
            ):
                target_subject = (
                    identifier.value
                )
                break

        if target_subject != subject:
            continue

        stimulus_dilution = None

        for condition in stimulus.conditions:
            if condition.property == "dilution":
                stimulus_dilution = str(
                    condition.value
                )
                break

        if stimulus_dilution != dilution:
            continue

        measurements = (
            get_perceptual_measurements(
                resource
            )
        )

        measurement_map = {
            str(measurement.get("property")):
                measurement
            for measurement in measurements
        }

        matches_expected = True

        for (
            property_name,
            expected_value,
        ) in EXPECTED_MEASUREMENTS.items():

            measurement = (
                measurement_map.get(
                    property_name
                )
            )

            if measurement is None:
                matches_expected = False
                break

            if (
                float(measurement["value"])
                != expected_value
            ):
                matches_expected = False
                break

        if matches_expected:
            matches.append(
                resource
            )

    if len(matches) != 1:
        raise RuntimeError(
            "Could not uniquely resolve source row "
            f"{TARGET_SOURCE_ROW}; matches={len(matches)}"
        )

    return matches[0]


def validate_exported_graph(
    graph: ResourceGraph,
) -> None:
    stimuli = graph.resources_of_type(
        Stimulus
    )

    targets = graph.resources_of_type(
        ObservationTarget
    )

    observations = graph.resources_of_type(
        Observation
    )

    if len(stimuli) != 1:
        raise RuntimeError(
            "Expected exactly one Stimulus"
        )

    if len(targets) != 1:
        raise RuntimeError(
            "Expected exactly one ObservationTarget"
        )

    if len(observations) != 1:
        raise RuntimeError(
            "Expected exactly one Observation"
        )

    observation = observations[0]

    if (
        observation.stimulus.resource_id
        != stimuli[0].id
    ):
        raise RuntimeError(
            "Observation stimulus reference changed"
        )

    if observation.target is None:
        raise RuntimeError(
            "Observation target is missing"
        )

    if (
        observation.target.resource_id
        != targets[0].id
    ):
        raise RuntimeError(
            "Observation target reference changed"
        )

    measurements = (
        get_perceptual_measurements(
            observation
        )
    )

    measurement_map = {
        str(measurement.get("property")):
            measurement
        for measurement in measurements
    }

    for (
        property_name,
        expected_value,
    ) in EXPECTED_MEASUREMENTS.items():

        measurement = measurement_map.get(
            property_name
        )

        if measurement is None:
            raise RuntimeError(
                f"Missing measurement after round-trip: "
                f"{property_name}"
            )

        if (
            float(measurement["value"])
            != expected_value
        ):
            raise RuntimeError(
                f"Measurement changed after round-trip: "
                f"{property_name}"
            )

        scale = measurement.get(
            "scale"
        )

        if scale != {
            "min": 0,
            "max": 100,
        }:
            raise RuntimeError(
                f"Scale changed for {property_name}: "
                f"{scale!r}"
            )


def main() -> None:
    print(
        "Loading Keller/Vosshall source dataset..."
    )

    dataframe = load_dataset()

    print(
        f"Loaded {len(dataframe):,} observations."
    )

    print(
        "Building complete OpenSmell ResourceGraph..."
    )

    graph = build_resource_graph()

    print(
        f"Complete graph resources: {len(graph):,}"
    )

    observation = find_target_observation(
        graph,
        dataframe,
    )

    stimulus = graph.resolve(
        observation.stimulus
    )

    if not isinstance(
        stimulus,
        Stimulus,
    ):
        raise RuntimeError(
            "Observation stimulus could not be resolved"
        )

    if observation.target is None:
        raise RuntimeError(
            "Observation target is missing"
        )

    target = graph.resolve(
        observation.target
    )

    if not isinstance(
        target,
        ObservationTarget,
    ):
        raise RuntimeError(
            "Observation target could not be resolved"
        )

    export_graph = ResourceGraph(
        resources=[
            stimulus,
            target,
            observation,
        ],
        extra={
            "source_dataset": "Keller/Vosshall",
            "source_row": TARGET_SOURCE_ROW,
            "experiment": (
                "single_psychophysical_observation"
            ),
        },
    )

    print()
    print("Export graph")
    print("-" * 72)
    print(
        "Stimulus ID    :",
        stimulus.id,
    )
    print(
        "Target ID      :",
        target.id,
    )
    print(
        "Observation ID :",
        observation.id,
    )

    text = dumps(
        export_graph,
        indent=2,
    )

    OUTPUT_PATH.write_text(
        text + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "Written:",
        OUTPUT_PATH,
    )

    print(
        "File size:",
        OUTPUT_PATH.stat().st_size,
        "bytes",
    )

    print()
    print(
        "Reloading .osmell from disk..."
    )

    reloaded_text = (
        OUTPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    reloaded = loads(
        reloaded_text
    )

    validate_exported_graph(
        reloaded
    )

    print(
        "Reloaded resources:",
        len(reloaded),
    )

    print(
        "Unresolved references:",
        len(
            reloaded.unresolved_references()
        ),
    )

    print()
    print("Measurements after round-trip")
    print("-" * 72)

    reloaded_observation = (
        reloaded.resources_of_type(
            Observation
        )[0]
    )

    measurement_map = {
        str(measurement.get("property")):
            measurement
        for measurement
        in get_perceptual_measurements(
            reloaded_observation
        )
    }

    for property_name in (
        "FLOWER",
        "GRASS",
        "WOOD",
    ):
        measurement = measurement_map[
            property_name
        ]

        print(
            f"{property_name:6} = "
            f"{measurement['value']} "
            f"[{measurement['scale']['min']}.."
            f"{measurement['scale']['max']}]"
        )

    print()
    print("SUCCESS")
    print(
        "Keller/Vosshall observation was exported "
        "to .osmell and reconstructed without "
        "changing the selected perceptual measurements."
    )


if __name__ == "__main__":
    main()