"""Build and validate an experimental OpenSmell resource graph from Burton 2022.

This experiment combines:

- RFC-0006 deterministic Resource IDs;
- experimental Stimulus resources;
- experimental ObservationTarget resources;
- experimental Observation resources;
- versioned scheme-defined Result objects.

The Burton physiological DeltaF values are represented through
Observation.results.

The goal is not to standardize the result scheme used here.

The Burton 2022 dataset is external to OpenSmell and must be available
locally under:

    examples/burton_2022/
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from opensmell.experimental.graph import ResourceGraph
from opensmell.experimental.identifiers import (
    deterministic_resource_id_from_source,
)
from opensmell.experimental.resources import (
    Condition,
    ExternalIdentifier,
    Observation,
    ObservationTarget,
    Reference,
    Result,
    ResultScheme,
    Stimulus,
)


DATASET_ID = "burton_2022"

BIOLOGICAL_RESULT_SCHEME_ID = (
    "org.opensmell.experimental.biological.measurements"
)
BIOLOGICAL_RESULT_SCHEME_VERSION = "0.1"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = PROJECT_ROOT / "examples" / "burton_2022"


def find_dataset_file(filename: str) -> Path:
    direct_path = DATASET_ROOT / filename

    if direct_path.exists():
        return direct_path

    matches = list(
        DATASET_ROOT.rglob(filename)
    )

    if not matches:
        raise FileNotFoundError(
            f"Could not find {filename!r} below {DATASET_ROOT}"
        )

    if len(matches) > 1:
        raise RuntimeError(
            f"Found multiple copies of {filename!r}: "
            + ", ".join(
                str(path)
                for path in matches
            )
        )

    return matches[0]


def load_csv(filename: str) -> pd.DataFrame:
    return pd.read_csv(
        find_dataset_file(filename),
        index_col=0,
    )


def clean_source_value(
    value: Any,
) -> str | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if math.isnan(value):
            return None

        if value.is_integer():
            return str(
                int(value)
            )

        return str(value)

    text = str(value)

    if not text:
        return None

    return text


def resource_id(
    resource_type: str,
    source_identity: str | dict[str, str],
) -> str:
    return deterministic_resource_id_from_source(
        dataset=DATASET_ID,
        resource_type=resource_type,
        source_identity=source_identity,
    )


def require_column(
    dataframe: pd.DataFrame,
    candidates: tuple[str, ...],
    *,
    dataset_name: str,
) -> str:
    for candidate in candidates:
        if candidate in dataframe.columns:
            return candidate

    raise KeyError(
        f"Could not find expected column in {dataset_name}. "
        f"Tried {candidates}. "
        f"Available columns: {list(dataframe.columns)}"
    )


def get_behavior_stimulus_id(
    row_index: Any,
    row: pd.Series,
    stimulus_column: str | None,
) -> str | None:
    if stimulus_column is None:
        return clean_source_value(
            row_index
        )

    return clean_source_value(
        row[stimulus_column]
    )


def biological_result_scheme() -> ResultScheme:
    return ResultScheme(
        id=BIOLOGICAL_RESULT_SCHEME_ID,
        version=BIOLOGICAL_RESULT_SCHEME_VERSION,
    )


def make_delta_f_result(
    value: float,
) -> Result:
    return Result(
        scheme=biological_result_scheme(),
        data={
            "measurements": [
                {
                    "property": "delta_f",
                    "value": float(value),
                }
            ]
        },
    )


def get_delta_f_from_observation(
    observation: Observation,
) -> float:
    if len(
        observation.results
    ) != 1:
        raise AssertionError(
            "Burton Observation must contain exactly one Result."
        )

    result = observation.results[0]

    if (
        result.scheme.id
        != BIOLOGICAL_RESULT_SCHEME_ID
    ):
        raise AssertionError(
            "Unexpected Burton result scheme ID: "
            f"{result.scheme.id!r}"
        )

    if (
        result.scheme.version
        != BIOLOGICAL_RESULT_SCHEME_VERSION
    ):
        raise AssertionError(
            "Unexpected Burton result scheme version: "
            f"{result.scheme.version!r}"
        )

    measurements = result.data.get(
        "measurements"
    )

    if not isinstance(
        measurements,
        list,
    ):
        raise AssertionError(
            "Burton Result does not contain a measurements list."
        )

    if len(measurements) != 1:
        raise AssertionError(
            "Burton Result must contain exactly one measurement."
        )

    measurement = measurements[0]

    if not isinstance(
        measurement,
        dict,
    ):
        raise AssertionError(
            "Burton result measurement must be a dictionary."
        )

    if (
        measurement.get("property")
        != "delta_f"
    ):
        raise AssertionError(
            "Unexpected Burton measurement property."
        )

    value = measurement.get(
        "value"
    )

    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        (int, float),
    ):
        raise AssertionError(
            "Burton DeltaF result is not numeric."
        )

    return float(value)


def load_burton_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    return (
        load_csv("molecules.csv"),
        load_csv("stimuli.csv"),
        load_csv("subjects.csv"),
        load_csv("behavior.csv"),
    )


def build_molecule_ids(
    molecules: pd.DataFrame,
) -> dict[str, str]:
    molecule_ids: dict[
        str,
        str,
    ] = {}

    for source_index, row in molecules.iterrows():
        cid = clean_source_value(
            source_index
        )

        if (
            cid is None
            and "CID" in molecules.columns
        ):
            cid = clean_source_value(
                row["CID"]
            )

        if cid is None:
            raise ValueError(
                "Encountered Burton molecule without a usable "
                "source identity."
            )

        if cid in molecule_ids:
            raise ValueError(
                f"Duplicate Burton molecule source identity: {cid}"
            )

        molecule_ids[cid] = resource_id(
            "molecule",
            cid,
        )

    return molecule_ids


def build_stimuli(
    stimuli_df: pd.DataFrame,
    molecule_ids: dict[str, str],
) -> dict[str, Stimulus]:
    cid_column = require_column(
        stimuli_df,
        (
            "CID",
            "cid",
        ),
        dataset_name="stimuli.csv",
    )

    concentration_column = require_column(
        stimuli_df,
        (
            "Conc. (mols/L)",
            "Concentration",
            "concentration",
        ),
        dataset_name="stimuli.csv",
    )

    stimuli: dict[
        str,
        Stimulus,
    ] = {}

    for source_index, row in stimuli_df.iterrows():
        source_id = clean_source_value(
            source_index
        )

        if source_id is None:
            raise ValueError(
                "Encountered Burton stimulus without source identity."
            )

        cid = clean_source_value(
            row[cid_column]
        )

        concentration = row[
            concentration_column
        ]

        source_reference: Reference | None = None

        if cid is not None:
            molecule_resource_id = molecule_ids.get(
                cid
            )

            if molecule_resource_id is None:
                raise ValueError(
                    f"Stimulus {source_id!r} references "
                    f"unknown CID {cid!r}."
                )

            source_reference = Reference(
                resource_id=molecule_resource_id
            )

        conditions: list[
            Condition
        ] = []

        if not pd.isna(
            concentration
        ):
            conditions.append(
                Condition(
                    property="concentration",
                    value=float(
                        concentration
                    ),
                    unit="mol/L",
                )
            )

        stimuli[source_id] = Stimulus(
            id=resource_id(
                "stimulus",
                source_id,
            ),
            source=source_reference,
            identifiers=[
                ExternalIdentifier(
                    scheme="burton.stimulus",
                    value=source_id,
                )
            ],
            conditions=conditions,
        )

    return stimuli


def build_targets(
    subjects_df: pd.DataFrame,
    behavior_df: pd.DataFrame,
    behavior_target_column: str,
) -> tuple[
    dict[str, ObservationTarget],
    set[str],
    set[str],
]:
    declared_target_ids = {
        clean_source_value(
            index
        )
        for index in subjects_df.index
    }

    declared_target_ids.discard(
        None
    )

    referenced_target_ids = {
        clean_source_value(
            value
        )
        for value in behavior_df[
            behavior_target_column
        ]
    }

    referenced_target_ids.discard(
        None
    )

    unresolved_target_ids = (
        referenced_target_ids
        - declared_target_ids
    )

    unreferenced_target_ids = (
        declared_target_ids
        - referenced_target_ids
    )

    all_target_ids = (
        declared_target_ids
        | referenced_target_ids
    )

    targets: dict[
        str,
        ObservationTarget,
    ] = {}

    for source_id in sorted(
        all_target_ids
    ):
        targets[source_id] = ObservationTarget(
            id=resource_id(
                "target",
                source_id,
            ),
            identifiers=[
                ExternalIdentifier(
                    scheme="burton.target",
                    value=source_id,
                )
            ],
        )

    return (
        targets,
        unresolved_target_ids,
        unreferenced_target_ids,
    )


def build_observations(
    behavior_df: pd.DataFrame,
    stimuli: dict[str, Stimulus],
    targets: dict[str, ObservationTarget],
    *,
    stimulus_column: str | None,
    target_column: str,
    delta_f_column: str,
) -> list[Observation]:
    observations: list[
        Observation
    ] = []

    for row_index, row in behavior_df.iterrows():
        stimulus_source_id = get_behavior_stimulus_id(
            row_index,
            row,
            stimulus_column,
        )

        target_source_id = clean_source_value(
            row[target_column]
        )

        if stimulus_source_id is None:
            raise ValueError(
                "Behavior row has no stimulus."
            )

        if target_source_id is None:
            raise ValueError(
                "Behavior row has no target."
            )

        stimulus = stimuli.get(
            stimulus_source_id
        )

        target = targets.get(
            target_source_id
        )

        if stimulus is None:
            raise ValueError(
                f"Unknown stimulus {stimulus_source_id!r}."
            )

        if target is None:
            raise ValueError(
                f"Unknown target {target_source_id!r}."
            )

        delta_f = row[
            delta_f_column
        ]

        if pd.isna(
            delta_f
        ):
            raise ValueError(
                "Behavior row has missing DeltaF."
            )

        observation = Observation(
            id=resource_id(
                "observation",
                {
                    "stimulus": stimulus_source_id,
                    "target": target_source_id,
                },
            ),
            stimulus=Reference(
                resource_id=stimulus.id
            ),
            target=Reference(
                resource_id=target.id
            ),
            results=[
                make_delta_f_result(
                    float(delta_f)
                )
            ],
            context={
                "measurement_domain": "physiological",
            },
        )

        observations.append(
            observation
        )

    return observations


def validate_graph(
    *,
    molecules: pd.DataFrame,
    stimuli_df: pd.DataFrame,
    behavior_df: pd.DataFrame,
    molecule_ids: dict[str, str],
    stimuli: dict[str, Stimulus],
    targets: dict[str, ObservationTarget],
    observations: list[Observation],
    unresolved_target_ids: set[str],
    unreferenced_target_ids: set[str],
    target_column: str,
    delta_f_column: str,
) -> None:
    if len(molecule_ids) != len(molecules):
        raise AssertionError(
            "Molecule count changed."
        )

    if len(stimuli) != len(stimuli_df):
        raise AssertionError(
            "Stimulus count changed."
        )

    if len(observations) != len(behavior_df):
        raise AssertionError(
            "Observation count changed."
        )

    all_resource_ids = [
        *molecule_ids.values(),
        *(
            stimulus.id
            for stimulus in stimuli.values()
        ),
        *(
            target.id
            for target in targets.values()
        ),
        *(
            observation.id
            for observation in observations
        ),
    ]

    duplicate_resource_ids = [
        value
        for value, count
        in Counter(
            all_resource_ids
        ).items()
        if count > 1
    ]

    if duplicate_resource_ids:
        raise AssertionError(
            f"Resource ID collision: {duplicate_resource_ids[:10]}"
        )

    stimulus_ids = {
        stimulus.id
        for stimulus in stimuli.values()
    }

    target_ids = {
        target.id
        for target in targets.values()
    }

    for observation in observations:
        if (
            observation.stimulus.resource_id
            not in stimulus_ids
        ):
            raise AssertionError(
                "Unresolved stimulus Resource ID."
            )

        if observation.target is None:
            raise AssertionError(
                "Burton observation has no target."
            )

        if (
            observation.target.resource_id
            not in target_ids
        ):
            raise AssertionError(
                "Unresolved target Resource ID."
            )

        get_delta_f_from_observation(
            observation
        )

    for source_value, observation in zip(
        behavior_df[
            delta_f_column
        ].tolist(),
        observations,
        strict=True,
    ):
        if (
            float(source_value)
            != get_delta_f_from_observation(
                observation
            )
        ):
            raise AssertionError(
                "DeltaF changed during Result conversion."
            )

    if len(
        unresolved_target_ids
    ) != 4:
        raise AssertionError(
            "Expected 4 source-unresolved targets."
        )

    if len(
        unreferenced_target_ids
    ) != 4:
        raise AssertionError(
            "Expected 4 source-unreferenced targets."
        )


def print_report(
    *,
    molecules: pd.DataFrame,
    stimuli: dict[str, Stimulus],
    targets: dict[str, ObservationTarget],
    observations: list[Observation],
    unresolved_target_ids: set[str],
    unreferenced_target_ids: set[str],
) -> None:
    molecule_count = len(
        molecules
    )

    stimulus_count = len(
        stimuli
    )

    target_count = len(
        targets
    )

    observation_count = len(
        observations
    )

    total_resources = (
        molecule_count
        + stimulus_count
        + target_count
        + observation_count
    )

    with_source = sum(
        stimulus.source is not None
        for stimulus in stimuli.values()
    )

    with_conditions = sum(
        bool(stimulus.conditions)
        for stimulus in stimuli.values()
    )

    result_count = sum(
        len(observation.results)
        for observation in observations
    )

    zero_count = sum(
        get_delta_f_from_observation(
            observation
        ) == 0
        for observation in observations
    )

    all_resource_ids = [
        *(
            resource_id(
                "molecule",
                clean_source_value(index),
            )
            for index in molecules.index
        ),
        *(
            stimulus.id
            for stimulus in stimuli.values()
        ),
        *(
            target.id
            for target in targets.values()
        ),
        *(
            observation.id
            for observation in observations
        ),
    ]

    print()
    print(
        "OpenSmell experimental Burton Result resource graph"
    )
    print("=" * 72)

    print(
        f"Molecule identities          : {molecule_count:>10,}"
    )
    print(
        f"Stimulus resources           : {stimulus_count:>10,}"
    )
    print(
        f"Observation targets          : {target_count:>10,}"
    )
    print(
        f"Observations                 : {observation_count:>10,}"
    )
    print("-" * 72)
    print(
        f"Total resources              : {total_resources:>10,}"
    )

    print()
    print("Stimulus model")
    print("-" * 72)
    print(
        f"With resolved source         : {with_source:>10,}"
    )
    print(
        f"Without resolved source      : {stimulus_count - with_source:>10,}"
    )
    print(
        f"With conditions              : {with_conditions:>10,}"
    )
    print(
        f"Without conditions           : {stimulus_count - with_conditions:>10,}"
    )

    print()
    print("Result model")
    print("-" * 72)
    print(
        f"Result objects               : {result_count:>10,}"
    )
    print(
        f"DeltaF values preserved      : {observation_count:>10,}"
    )
    print(
        f"Zero DeltaF                  : {zero_count:>10,}"
    )
    print(
        f"Non-zero DeltaF              : {observation_count - zero_count:>10,}"
    )
    print(
        f"Result scheme ID             : {BIOLOGICAL_RESULT_SCHEME_ID}"
    )
    print(
        "Result scheme version        : "
        f"{BIOLOGICAL_RESULT_SCHEME_VERSION}"
    )

    print()
    print("Identity")
    print("-" * 72)
    print(
        f"All Resource IDs             : {len(all_resource_ids):>10,}"
    )
    print(
        f"Unique Resource IDs          : {len(set(all_resource_ids)):>10,}"
    )
    print(
        "Resource ID collisions       : "
        f"{len(all_resource_ids) - len(set(all_resource_ids)):>10,}"
    )

    print()
    print("Target references")
    print("-" * 72)
    print(
        f"Unresolved source IDs        : {len(unresolved_target_ids):>10,}"
    )
    print(
        f"Unreferenced source IDs      : {len(unreferenced_target_ids):>10,}"
    )

    empty_stimulus = stimuli.get(
        "empty"
    )

    if empty_stimulus is not None:
        print()
        print("Source-less stimulus example")
        print("-" * 72)
        print(
            "Source identity               : empty"
        )
        print(
            f"Resource ID                   : {empty_stimulus.id}"
        )
        print(
            "Resolved source               : "
            f"{empty_stimulus.source is not None}"
        )
        print(
            f"Conditions                    : {len(empty_stimulus.conditions)}"
        )

    if observations:
        example = observations[0]

        print()
        print("Observation example")
        print("-" * 72)
        print(
            f"Resource ID                   : {example.id}"
        )
        print(
            "Stimulus reference            : "
            f"{example.stimulus.resource_id}"
        )

        if example.target is not None:
            print(
                "Target reference              : "
                f"{example.target.resource_id}"
            )

        print(
            "Result scheme ID               : "
            f"{example.results[0].scheme.id}"
        )
        print(
            "Result scheme version          : "
            f"{example.results[0].scheme.version}"
        )
        print(
            "Result property                : delta_f"
        )
        print(
            "Result value                   : "
            f"{get_delta_f_from_observation(example)}"
        )

    print()
    print("Result")
    print("=" * 72)
    print("SUCCESS")
    print(
        "The experimental OpenSmell versioned Result architecture "
        "represented all Burton physiological observations without "
        "a universal Measurement model."
    )


def build_resource_graph() -> ResourceGraph:
    """Build the materialized experimental Burton 2022 ResourceGraph.

    The 186 deterministic molecule identities are intentionally not
    materialized because the current experimental graph has no normative
    molecule/Chemical resource class. Stimulus.source references to those
    molecule IDs therefore remain unresolved.

    The four target IDs referenced by behavior.csv but absent from
    subjects.csv are materialized as ObservationTarget resources, exactly as
    the existing Burton analysis does. Their source-level unresolved status
    is therefore distinct from ResourceGraph reference resolution.
    """

    (
        molecules,
        stimuli_df,
        subjects_df,
        behavior_df,
    ) = load_burton_data()

    target_column = require_column(
        behavior_df,
        (
            "Subject",
            "subject",
            "Target",
            "target",
        ),
        dataset_name="behavior.csv",
    )

    delta_f_column = require_column(
        behavior_df,
        (
            "DeltaF",
            "delta_f",
            "Delta F",
        ),
        dataset_name="behavior.csv",
    )

    molecule_ids = build_molecule_ids(
        molecules
    )

    stimuli = build_stimuli(
        stimuli_df,
        molecule_ids,
    )

    (
        targets,
        unresolved_target_ids,
        unreferenced_target_ids,
    ) = build_targets(
        subjects_df,
        behavior_df,
        target_column,
    )

    observations = build_observations(
        behavior_df,
        stimuli,
        targets,
        stimulus_column=None,
        target_column=target_column,
        delta_f_column=delta_f_column,
    )

    validate_graph(
        molecules=molecules,
        stimuli_df=stimuli_df,
        behavior_df=behavior_df,
        molecule_ids=molecule_ids,
        stimuli=stimuli,
        targets=targets,
        observations=observations,
        unresolved_target_ids=unresolved_target_ids,
        unreferenced_target_ids=unreferenced_target_ids,
        target_column=target_column,
        delta_f_column=delta_f_column,
    )

    return ResourceGraph(
        resources=[
            *stimuli.values(),
            *targets.values(),
            *observations,
        ]
    )


def main() -> None:
    print(
        "Loading Burton 2022 dataset..."
    )

    (
        molecules,
        stimuli_df,
        subjects_df,
        behavior_df,
    ) = load_burton_data()

    target_column = require_column(
        behavior_df,
        (
            "Subject",
            "subject",
            "Target",
            "target",
        ),
        dataset_name="behavior.csv",
    )

    delta_f_column = require_column(
        behavior_df,
        (
            "DeltaF",
            "delta_f",
            "Delta F",
        ),
        dataset_name="behavior.csv",
    )

    print(
        "Building molecule identities..."
    )

    molecule_ids = build_molecule_ids(
        molecules
    )

    print(
        "Building Stimulus resources..."
    )

    stimuli = build_stimuli(
        stimuli_df,
        molecule_ids,
    )

    print(
        "Building ObservationTarget resources..."
    )

    (
        targets,
        unresolved_target_ids,
        unreferenced_target_ids,
    ) = build_targets(
        subjects_df,
        behavior_df,
        target_column,
    )

    print(
        "Building Observation resources with versioned "
        "scheme-defined Results..."
    )

    observations = build_observations(
        behavior_df,
        stimuli,
        targets,
        stimulus_column=None,
        target_column=target_column,
        delta_f_column=delta_f_column,
    )

    print(
        "Validating versioned Result-based resource graph..."
    )

    validate_graph(
        molecules=molecules,
        stimuli_df=stimuli_df,
        behavior_df=behavior_df,
        molecule_ids=molecule_ids,
        stimuli=stimuli,
        targets=targets,
        observations=observations,
        unresolved_target_ids=unresolved_target_ids,
        unreferenced_target_ids=unreferenced_target_ids,
        target_column=target_column,
        delta_f_column=delta_f_column,
    )

    print_report(
        molecules=molecules,
        stimuli=stimuli,
        targets=targets,
        observations=observations,
        unresolved_target_ids=unresolved_target_ids,
        unreferenced_target_ids=unreferenced_target_ids,
    )


if __name__ == "__main__":
    main()