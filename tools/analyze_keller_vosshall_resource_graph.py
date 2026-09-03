"""Build and validate an experimental OpenSmell resource graph from Keller/Vosshall.

This experiment tests the OpenSmell experimental resource architecture on
human psychophysical olfactory observations.

It combines:

- RFC-0006 deterministic Resource IDs;
- molecule identities;
- Stimulus resources;
- ObservationTarget resources;
- Observation resources;
- multiple versioned scheme-defined Result objects per Observation.

Categorical observation results and quantitative perceptual measurements are
kept in separate Result schemes.

The generic Observation model does not define a universal Measurement class.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

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


DATASET_ID = "keller_vosshall"

CATEGORICAL_RESULT_SCHEME_ID = (
    "org.opensmell.experimental.observation.categories"
)
CATEGORICAL_RESULT_SCHEME_VERSION = "0.1"

PERCEPTUAL_RESULT_SCHEME_ID = (
    "org.opensmell.perceptual.measurements"
)
PERCEPTUAL_RESULT_SCHEME_VERSION = "0.1" 

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = (
    PROJECT_ROOT
    / "examples"
    / "keller_vosshall.xlsx"
)

DESCRIPTOR_NAMES = (
    "EDIBLE",
    "BAKERY",
    "SWEET",
    "FRUIT",
    "FISH",
    "GARLIC",
    "SPICES",
    "COLD",
    "SOUR",
    "BURNT",
    "ACID",
    "WARM",
    "MUSKY",
    "SWEATY",
    "AMMONIA/URINOUS",
    "DECAYED",
    "WOOD",
    "GRASS",
    "FLOWER",
    "CHEMICAL",
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
    normalized_columns = {
        str(column).strip(): column
        for column in dataframe.columns
    }

    for candidate in candidates:
        candidate = candidate.strip()

        if candidate in normalized_columns:
            return normalized_columns[
                candidate
            ]

    raise KeyError(
        f"Could not find expected column in {dataset_name}. "
        f"Tried {candidates}. "
        f"Available columns: {list(dataframe.columns)}"
    )


def require_descriptor_columns(
    dataframe: pd.DataFrame,
) -> dict[str, str]:
    normalized_columns = {
        str(column).strip(): column
        for column in dataframe.columns
    }

    resolved: dict[
        str,
        str,
    ] = {}

    for descriptor in DESCRIPTOR_NAMES:
        if descriptor not in normalized_columns:
            raise KeyError(
                f"Missing descriptor {descriptor!r}."
            )

        resolved[
            descriptor
        ] = normalized_columns[
            descriptor
        ]

    return resolved


def numeric_value(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, bool):
        return None

    if isinstance(
        value,
        (int, float),
    ):
        return float(value)

    return None


def normalize_detection(
    value: Any,
) -> str:
    text = clean_source_value(
        value
    )

    if text is None:
        return "unknown"

    normalized = (
        text
        .strip()
        .lower()
    )

    if (
        "can't smell"
        in normalized
        or "cannot smell"
        in normalized
    ):
        return "not_detected"

    if (
        "can smell"
        in normalized
        or "i smell something"
        in normalized
    ):
        return "detected"

    return "unknown"


def make_categorical_result(
    *,
    detection: str,
    recognition: str | None,
) -> Result:
    data: dict[
        str,
        Any,
    ] = {
        "detection": detection,
    }

    if recognition is not None:
        data[
            "recognition"
        ] = recognition

    return Result(
        scheme=ResultScheme(
            id=CATEGORICAL_RESULT_SCHEME_ID,
            version=CATEGORICAL_RESULT_SCHEME_VERSION,
        ),
        data=data,
    )


def make_perceptual_result(
    measurements: list[
        dict[str, Any]
    ],
) -> Result:
    return Result(
        scheme=ResultScheme(
            id=PERCEPTUAL_RESULT_SCHEME_ID,
            version=PERCEPTUAL_RESULT_SCHEME_VERSION,
        ),
        data={
            "measurements": measurements,
        },
    )


def get_categorical_result(
    observation: Observation,
) -> Result:
    matches = [
        result
        for result in observation.results
        if (
            result.scheme.id
            == CATEGORICAL_RESULT_SCHEME_ID
            and result.scheme.version
            == CATEGORICAL_RESULT_SCHEME_VERSION
        )
    ]

    if len(matches) != 1:
        raise AssertionError(
            "Observation must contain exactly one categorical Result."
        )

    return matches[0]


def get_perceptual_result(
    observation: Observation,
) -> Result | None:
    matches = [
        result
        for result in observation.results
        if (
            result.scheme.id
            == PERCEPTUAL_RESULT_SCHEME_ID
            and result.scheme.version
            == PERCEPTUAL_RESULT_SCHEME_VERSION
        )
    ]

    if len(matches) > 1:
        raise AssertionError(
            "Observation contains multiple perceptual Results."
        )

    if not matches:
        return None

    return matches[0]


def get_perceptual_measurements(
    observation: Observation,
) -> list[dict[str, Any]]:
    result = get_perceptual_result(
        observation
    )

    if result is None:
        return []

    measurements = result.data.get(
        "measurements"
    )

    if not isinstance(
        measurements,
        list,
    ):
        raise AssertionError(
            "Perceptual Result does not contain measurements."
        )

    return measurements


def load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    return pd.read_excel(
        DATASET_PATH,
        sheet_name="data",
        header=2,
    )


def build_molecule_ids(
    dataframe: pd.DataFrame,
    cid_column: str,
) -> dict[str, str]:
    molecule_ids: dict[
        str,
        str,
    ] = {}

    for value in dataframe[
        cid_column
    ]:
        cid = clean_source_value(
            value
        )

        if cid is None:
            raise ValueError(
                "Row without CID."
            )

        if cid not in molecule_ids:
            molecule_ids[
                cid
            ] = resource_id(
                "molecule",
                cid,
            )

    return molecule_ids


def build_stimuli(
    dataframe: pd.DataFrame,
    *,
    cid_column: str,
    dilution_column: str,
    molecule_ids: dict[str, str],
) -> dict[
    tuple[str, str],
    Stimulus,
]:
    stimuli: dict[
        tuple[str, str],
        Stimulus,
    ] = {}

    for _, row in dataframe.iterrows():
        cid = clean_source_value(
            row[cid_column]
        )

        dilution = clean_source_value(
            row[dilution_column]
        )

        if cid is None or dilution is None:
            raise ValueError(
                "Stimulus missing CID or dilution."
            )

        key = (
            cid,
            dilution,
        )

        if key in stimuli:
            continue

        molecule_id = molecule_ids[
            cid
        ]

        stimuli[
            key
        ] = Stimulus(
            id=resource_id(
                "stimulus",
                {
                    "cid": cid,
                    "dilution": dilution,
                },
            ),
            source=Reference(
                resource_id=molecule_id
            ),
            conditions=[
                Condition(
                    property="dilution",
                    value=dilution,
                )
            ],
        )

    return stimuli


def build_targets(
    dataframe: pd.DataFrame,
    *,
    subject_column: str,
) -> dict[
    str,
    ObservationTarget,
]:
    targets: dict[
        str,
        ObservationTarget,
    ] = {}

    for value in dataframe[
        subject_column
    ]:
        subject = clean_source_value(
            value
        )

        if subject is None:
            raise ValueError(
                "Row without subject."
            )

        if subject in targets:
            continue

        targets[
            subject
        ] = ObservationTarget(
            id=resource_id(
                "target",
                subject,
            ),
            identifiers=[
                ExternalIdentifier(
                    scheme="keller_vosshall.subject",
                    value=subject,
                )
            ],
            extra={
                "kind": "human_subject",
            },
        )

    return targets


def build_quantitative_measurements(
    row: pd.Series,
    *,
    intensity_column: str,
    pleasantness_column: str,
    familiarity_column: str,
    descriptor_columns: dict[str, str],
) -> list[
    dict[str, Any]
]:
    measurements: list[
        dict[str, Any]
    ] = []

    for (
        property_name,
        column,
    ) in (
        (
            "intensity",
            intensity_column,
        ),
        (
            "pleasantness",
            pleasantness_column,
        ),
        (
            "familiarity",
            familiarity_column,
        ),
    ):
        value = numeric_value(
            row[column]
        )

        if value is not None:
            measurements.append(
                {
                    "property": property_name,
                    "value": value,
                    "scale": {
                        "min": 0,
                        "max": 100,
                    },
                }
            )

    for (
        descriptor,
        column,
    ) in descriptor_columns.items():
        value = numeric_value(
            row[column]
        )

        if value is not None:
            measurements.append(
                {
                    "property": descriptor,
                    "value": value,
                    "scale": {
                        "min": 0,
                        "max": 100,
                    },
                }
            )

    return measurements


def build_observations(
    dataframe: pd.DataFrame,
    *,
    subject_column: str,
    cid_column: str,
    dilution_column: str,
    detection_column: str,
    recognition_column: str,
    intensity_column: str,
    pleasantness_column: str,
    familiarity_column: str,
    descriptor_columns: dict[str, str],
    stimuli: dict[
        tuple[str, str],
        Stimulus,
    ],
    targets: dict[
        str,
        ObservationTarget,
    ],
) -> list[Observation]:
    observations: list[
        Observation
    ] = []

    occurrence_counter: defaultdict[
        tuple[str, str, str],
        int,
    ] = defaultdict(
        int
    )

    for _, row in dataframe.iterrows():
        subject = clean_source_value(
            row[subject_column]
        )

        cid = clean_source_value(
            row[cid_column]
        )

        dilution = clean_source_value(
            row[dilution_column]
        )

        if (
            subject is None
            or cid is None
            or dilution is None
        ):
            raise ValueError(
                "Observation identity is incomplete."
            )

        key = (
            cid,
            dilution,
        )

        stimulus = stimuli[
            key
        ]

        target = targets[
            subject
        ]

        occurrence_key = (
            subject,
            cid,
            dilution,
        )

        occurrence_counter[
            occurrence_key
        ] += 1

        occurrence = str(
            occurrence_counter[
                occurrence_key
            ]
        )

        detection = normalize_detection(
            row[detection_column]
        )

        recognition = clean_source_value(
            row[recognition_column]
        )

        quantitative = (
            build_quantitative_measurements(
                row,
                intensity_column=intensity_column,
                pleasantness_column=pleasantness_column,
                familiarity_column=familiarity_column,
                descriptor_columns=descriptor_columns,
            )
        )

        results = [
            make_categorical_result(
                detection=detection,
                recognition=recognition,
            )
        ]

        if quantitative:
            results.append(
                make_perceptual_result(
                    quantitative
                )
            )

        observations.append(
            Observation(
                id=resource_id(
                    "observation",
                    {
                        "cid": cid,
                        "dilution": dilution,
                        "occurrence": occurrence,
                        "subject": subject,
                    },
                ),
                stimulus=Reference(
                    resource_id=stimulus.id
                ),
                target=Reference(
                    resource_id=target.id
                ),
                results=results,
                context={
                    "measurement_domain": "psychophysical",
                },
            )
        )

    return observations


def validate_graph(
    *,
    dataframe: pd.DataFrame,
    molecule_ids: dict[str, str],
    stimuli: dict[
        tuple[str, str],
        Stimulus,
    ],
    targets: dict[
        str,
        ObservationTarget,
    ],
    observations: list[
        Observation
    ],
) -> None:
    if len(dataframe) != 55_000:
        raise AssertionError(
            "Expected 55,000 rows."
        )

    if len(molecule_ids) != 480:
        raise AssertionError(
            "Expected 480 molecules."
        )

    if len(stimuli) != 960:
        raise AssertionError(
            "Expected 960 stimuli."
        )

    if len(targets) != 55:
        raise AssertionError(
            "Expected 55 targets."
        )

    if len(observations) != 55_000:
        raise AssertionError(
            "Expected 55,000 observations."
        )

    detection_counts: Counter[
        str
    ] = Counter()

    perceptual_results = 0
    numeric_measurements = 0
    with_numeric = 0
    without_numeric = 0

    for observation in observations:
        categorical = get_categorical_result(
            observation
        )

        detection_counts[
            categorical.data["detection"]
        ] += 1

        measurements = (
            get_perceptual_measurements(
                observation
            )
        )

        if measurements:
            perceptual_results += 1
            with_numeric += 1
            numeric_measurements += len(
                measurements
            )
        else:
            without_numeric += 1

    if (
        detection_counts[
            "detected"
        ]
        != 41_289
    ):
        raise AssertionError(
            "Detected count changed."
        )

    if (
        detection_counts[
            "not_detected"
        ]
        != 13_711
    ):
        raise AssertionError(
            "Not-detected count changed."
        )

    if (
        detection_counts[
            "unknown"
        ]
        != 0
    ):
        raise AssertionError(
            "Unexpected unknown detection."
        )

    if perceptual_results != 41_289:
        raise AssertionError(
            "Perceptual Result count changed."
        )

    if with_numeric != 41_289:
        raise AssertionError(
            "Numeric observation count changed."
        )

    if without_numeric != 13_711:
        raise AssertionError(
            "Non-numeric observation count changed."
        )

    if numeric_measurements != 263_683:
        raise AssertionError(
            "Numeric measurement count changed."
        )

    all_ids = [
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

    if len(all_ids) != len(set(all_ids)):
        raise AssertionError(
            "Resource ID collision."
        )


def print_report(
    *,
    dataframe: pd.DataFrame,
    molecule_ids: dict[str, str],
    stimuli: dict[
        tuple[str, str],
        Stimulus,
    ],
    targets: dict[
        str,
        ObservationTarget,
    ],
    observations: list[
        Observation
    ],
    descriptor_columns: dict[
        str,
        str,
    ],
) -> None:
    detection_counts: Counter[
        str
    ] = Counter()

    categorical_count = 0
    perceptual_count = 0
    numeric_count = 0
    recognition_count = 0
    with_numeric = 0
    without_numeric = 0

    for observation in observations:
        categorical = get_categorical_result(
            observation
        )

        categorical_count += 1

        detection_counts[
            categorical.data["detection"]
        ] += 1

        if (
            "recognition"
            in categorical.data
        ):
            recognition_count += 1

        measurements = (
            get_perceptual_measurements(
                observation
            )
        )

        if measurements:
            perceptual_count += 1
            with_numeric += 1
            numeric_count += len(
                measurements
            )
        else:
            without_numeric += 1

    all_ids = [
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

    print()
    print(
        "OpenSmell experimental Keller/Vosshall Result resource graph"
    )
    print("=" * 76)

    print(
        f"Source rows                  : {len(dataframe):>10,}"
    )
    print(
        f"Molecule identities          : {len(molecule_ids):>10,}"
    )
    print(
        f"Stimulus resources           : {len(stimuli):>10,}"
    )
    print(
        f"Observation targets          : {len(targets):>10,}"
    )
    print(
        f"Observations                 : {len(observations):>10,}"
    )

    print()
    print("Detection")
    print("-" * 76)
    print(
        f"Detected                     : {detection_counts['detected']:>10,}"
    )
    print(
        f"Not detected                 : {detection_counts['not_detected']:>10,}"
    )
    print(
        f"Unknown                      : {detection_counts['unknown']:>10,}"
    )

    print()
    print("Scheme-defined Results")
    print("-" * 76)
    print(
        f"Categorical Results          : {categorical_count:>10,}"
    )
    print(
        f"Perceptual Results           : {perceptual_count:>10,}"
    )
    print(
        f"Total Result objects         : {categorical_count + perceptual_count:>10,}"
    )
    print(
        f"Recognition values           : {recognition_count:>10,}"
    )
    print(
        f"Numeric measurements         : {numeric_count:>10,}"
    )
    print(
        f"Observations with numeric    : {with_numeric:>10,}"
    )
    print(
        f"Observations without numeric : {without_numeric:>10,}"
    )

    print()
    print("Schemes")
    print("-" * 76)
    print(
        f"Categorical ID               : {CATEGORICAL_RESULT_SCHEME_ID}"
    )
    print(
        f"Categorical version          : {CATEGORICAL_RESULT_SCHEME_VERSION}"
    )
    print(
        f"Perceptual ID                : {PERCEPTUAL_RESULT_SCHEME_ID}"
    )
    print(
        f"Perceptual version           : {PERCEPTUAL_RESULT_SCHEME_VERSION}"
    )

    print()
    print("Descriptors")
    print("-" * 76)
    print(
        f"Descriptor columns           : {len(descriptor_columns):>10,}"
    )

    for descriptor in descriptor_columns:
        print(
            f"  - {descriptor}"
        )

    print()
    print("Identity")
    print("-" * 76)
    print(
        f"All Resource IDs             : {len(all_ids):>10,}"
    )
    print(
        f"Unique Resource IDs          : {len(set(all_ids)):>10,}"
    )
    print(
        "Resource ID collisions       : "
        f"{len(all_ids) - len(set(all_ids)):>10,}"
    )

    if observations:
        example = observations[
            0
        ]

        categorical = (
            get_categorical_result(
                example
            )
        )

        measurements = (
            get_perceptual_measurements(
                example
            )
        )

        print()
        print("Observation example")
        print("-" * 76)
        print(
            f"Resource ID                  : {example.id}"
        )
        print(
            "Stimulus reference           : "
            f"{example.stimulus.resource_id}"
        )

        if example.target is not None:
            print(
                "Target reference             : "
                f"{example.target.resource_id}"
            )

        print(
            f"Result objects               : {len(example.results)}"
        )
        print(
            "Categorical scheme ID        : "
            f"{categorical.scheme.id}"
        )
        print(
            "Categorical scheme version   : "
            f"{categorical.scheme.version}"
        )
        print(
            "Detection                    : "
            f"{categorical.data.get('detection')}"
        )
        print(
            "Recognition                  : "
            f"{categorical.data.get('recognition')}"
        )

        perceptual = get_perceptual_result(
            example
        )

        if perceptual is not None:
            print(
                "Perceptual scheme ID         : "
                f"{perceptual.scheme.id}"
            )
            print(
                "Perceptual scheme version    : "
                f"{perceptual.scheme.version}"
            )

        print(
            f"Numeric measurements         : {len(measurements)}"
        )

        for measurement in measurements[
            :6
        ]:
            print(
                f"  {measurement['property']} = "
                f"{measurement['value']}"
            )

    print()
    print("Result")
    print("=" * 76)
    print("SUCCESS")
    print(
        "The experimental OpenSmell versioned Result architecture represented "
        "the Keller/Vosshall psychophysical graph without a universal "
        "Measurement model."
    )


def main() -> None:
    print(
        "Loading Keller/Vosshall dataset..."
    )

    dataframe = load_dataset()

    print(
        f"Loaded {len(dataframe):,} source rows."
    )

    subject_column = require_column(
        dataframe,
        (
            "Subject # (this study)",
        ),
        dataset_name="Keller/Vosshall",
    )

    cid_column = require_column(
        dataframe,
        (
            "CID",
        ),
        dataset_name="Keller/Vosshall",
    )

    dilution_column = require_column(
        dataframe,
        (
            "Odor dilution",
        ),
        dataset_name="Keller/Vosshall",
    )

    detection_column = require_column(
        dataframe,
        (
            "CAN OR CAN'T SMELL",
        ),
        dataset_name="Keller/Vosshall",
    )

    recognition_column = require_column(
        dataframe,
        (
            "KNOW OR DON'T KNOW THE SMELL",
        ),
        dataset_name="Keller/Vosshall",
    )

    intensity_column = require_column(
        dataframe,
        (
            "HOW STRONG IS THE SMELL?",
        ),
        dataset_name="Keller/Vosshall",
    )

    pleasantness_column = require_column(
        dataframe,
        (
            "HOW PLEASANT IS THE SMELL?",
        ),
        dataset_name="Keller/Vosshall",
    )

    familiarity_column = require_column(
        dataframe,
        (
            "HOW FAMILIAR IS THE SMELL?",
        ),
        dataset_name="Keller/Vosshall",
    )

    descriptor_columns = (
        require_descriptor_columns(
            dataframe
        )
    )

    print()
    print("Resolved columns:")
    print(
        f"  subject        -> {subject_column}"
    )
    print(
        f"  cid            -> {cid_column}"
    )
    print(
        f"  dilution       -> {dilution_column}"
    )
    print(
        f"  detection      -> {detection_column}"
    )
    print(
        f"  recognition    -> {recognition_column}"
    )
    print(
        f"  intensity      -> {intensity_column}"
    )
    print(
        f"  pleasantness   -> {pleasantness_column}"
    )
    print(
        f"  familiarity    -> {familiarity_column}"
    )

    print()
    print(
        f"Resolved {len(descriptor_columns)} "
        "protocol-defined descriptor columns."
    )

    print("Descriptors:")

    for descriptor in descriptor_columns:
        print(
            f"  - {descriptor}"
        )

    print()
    print(
        "Building molecule identities..."
    )

    molecule_ids = build_molecule_ids(
        dataframe,
        cid_column,
    )

    print(
        "Building Stimulus resources..."
    )

    stimuli = build_stimuli(
        dataframe,
        cid_column=cid_column,
        dilution_column=dilution_column,
        molecule_ids=molecule_ids,
    )

    print(
        "Building ObservationTarget resources..."
    )

    targets = build_targets(
        dataframe,
        subject_column=subject_column,
    )

    print(
        "Building Observation resources with versioned scheme-defined Results..."
    )

    observations = build_observations(
        dataframe,
        subject_column=subject_column,
        cid_column=cid_column,
        dilution_column=dilution_column,
        detection_column=detection_column,
        recognition_column=recognition_column,
        intensity_column=intensity_column,
        pleasantness_column=pleasantness_column,
        familiarity_column=familiarity_column,
        descriptor_columns=descriptor_columns,
        stimuli=stimuli,
        targets=targets,
    )

    print(
        "Validating versioned Result-based resource graph..."
    )

    validate_graph(
        dataframe=dataframe,
        molecule_ids=molecule_ids,
        stimuli=stimuli,
        targets=targets,
        observations=observations,
    )

    print_report(
        dataframe=dataframe,
        molecule_ids=molecule_ids,
        stimuli=stimuli,
        targets=targets,
        observations=observations,
        descriptor_columns=descriptor_columns,
    )


if __name__ == "__main__":
    main()