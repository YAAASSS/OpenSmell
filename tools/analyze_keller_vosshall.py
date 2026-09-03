"""Analyze the Keller/Vosshall psychophysical olfaction dataset.

This tool characterizes the source dataset before any OpenSmell
representation is designed for it.

It intentionally reports observed values and missingness without assigning
OpenSmell semantics to missing cells.
"""

from pathlib import Path
from typing import Any

import pandas as pd


DATASET_PATH = Path("examples/keller_vosshall.xlsx")

IDENTITY_COLUMNS = [
    "C.A.S.",
    "Catalogue #*",
    "CID",
    "Odor",
    "Odor dilution",
]

EXPERIMENT_COLUMNS = [
    "Subject # (this study)",
    "Subject # (DREAM challenge)",
    "VIAL #",
    "CAN OR CAN'T SMELL",
    "KNOW OR DON'T KNOW THE SMELL",
    "THE ODOR IS:",
]

GLOBAL_RATINGS = [
    "HOW STRONG IS THE SMELL?",
    "HOW PLEASANT IS THE SMELL?",
    "HOW FAMILIAR IS THE SMELL?",
]

DESCRIPTOR_COLUMNS = [
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
]


def load_dataset(path: Path) -> pd.DataFrame:
    """Load the actual observation table from the source workbook."""

    if not path.exists():
        raise SystemExit(f"Dataset not found: {path}")

    # Row 1: document title
    # Row 2: grouped column descriptions
    # Row 3: actual column names
    #
    # Therefore the third physical row is used as the DataFrame header.
    dataframe = pd.read_excel(
        path,
        sheet_name="data",
        header=2,
    )

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    return dataframe


def validate_columns(dataframe: pd.DataFrame) -> None:
    """Ensure that the expected source columns are present."""

    expected = (
        IDENTITY_COLUMNS
        + EXPERIMENT_COLUMNS
        + GLOBAL_RATINGS
        + DESCRIPTOR_COLUMNS
    )

    missing = [
        column
        for column in expected
        if column not in dataframe.columns
    ]

    if missing:
        raise SystemExit(
            "Dataset is missing expected columns:\n  "
            + "\n  ".join(missing)
        )


def print_section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def value_counts(
    dataframe: pd.DataFrame,
    column: str,
) -> None:
    """Print observed source values, including missing cells."""

    counts = dataframe[column].value_counts(
        dropna=False
    )

    print(f"\n{column}")

    for value, count in counts.items():
        if pd.isna(value):
            display = "<missing>"
        else:
            display = repr(value)

        print(f"  {display}: {count:,}")


def numeric_summary(
    dataframe: pd.DataFrame,
    column: str,
) -> None:
    """Describe a numeric experimental column."""

    values = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )

    present = int(values.notna().sum())
    missing = int(values.isna().sum())

    print(f"\n{column}")
    print(f"  present: {present:,}")
    print(f"  missing: {missing:,}")

    if present:
        print(f"  min:     {values.min():g}")
        print(f"  max:     {values.max():g}")
        print(f"  mean:    {values.mean():.3f}")
        print(f"  median:  {values.median():.3f}")
        print(
            "  unique numeric values: "
            f"{values.nunique():,}"
        )


def descriptor_summary(
    dataframe: pd.DataFrame,
) -> None:
    """Describe the 20 quantitative descriptor columns."""

    print(
        "\nDescriptor".ljust(24)
        + "Present".rjust(10)
        + "Missing".rjust(10)
        + "Min".rjust(8)
        + "Max".rjust(8)
    )

    for column in DESCRIPTOR_COLUMNS:
        values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        present = int(values.notna().sum())
        missing = int(values.isna().sum())

        minimum: Any = "-"
        maximum: Any = "-"

        if present:
            minimum = f"{values.min():g}"
            maximum = f"{values.max():g}"

        print(
            column.ljust(24)
            + f"{present:,}".rjust(10)
            + f"{missing:,}".rjust(10)
            + str(minimum).rjust(8)
            + str(maximum).rjust(8)
        )


def detection_missingness(
    dataframe: pd.DataFrame,
) -> None:
    """Compare detection responses with rating availability."""

    detection_column = "CAN OR CAN'T SMELL"

    print_section("DETECTION VS RATING AVAILABILITY")

    grouped = dataframe.groupby(
        detection_column,
        dropna=False,
    )

    rating_columns = (
        GLOBAL_RATINGS
        + DESCRIPTOR_COLUMNS
    )

    for detection_value, group in grouped:
        print()
        print(
            f"Detection state: {detection_value!r} "
            f"({len(group):,} rows)"
        )

        for column in rating_columns:
            present = int(group[column].notna().sum())

            print(
                f"  {column}: "
                f"{present:,}/{len(group):,} present"
            )


def descriptor_count_per_observation(
    dataframe: pd.DataFrame,
) -> None:
    """Count populated descriptor ratings per observation."""

    print_section("DESCRIPTORS PER OBSERVATION")

    counts = dataframe[
        DESCRIPTOR_COLUMNS
    ].notna().sum(axis=1)

    distribution = counts.value_counts().sort_index()

    for descriptor_count, rows in distribution.items():
        print(
            f"{int(descriptor_count):2d} populated "
            f"descriptor ratings: {int(rows):,} rows"
        )


def dilution_summary(
    dataframe: pd.DataFrame,
) -> None:
    """Report source dilution values without interpreting them."""

    print_section("ODOR DILUTIONS")

    counts = dataframe[
        "Odor dilution"
    ].value_counts(dropna=False)

    for value, count in counts.items():
        if pd.isna(value):
            display = "<missing>"
        else:
            display = repr(value)

        print(f"{display}: {count:,}")


def subject_summary(
    dataframe: pd.DataFrame,
) -> None:
    """Report observations by experimental subject."""

    print_section("SUBJECTS")

    column = "Subject # (this study)"

    counts = dataframe[column].value_counts(
        dropna=False
    )

    print(
        "Unique subjects: "
        f"{dataframe[column].nunique(dropna=True):,}"
    )

    print(
        "Minimum observations per subject: "
        f"{counts.min():,}"
    )

    print(
        "Maximum observations per subject: "
        f"{counts.max():,}"
    )


def molecule_summary(
    dataframe: pd.DataFrame,
) -> None:
    """Report molecule identifiers represented in the experiment."""

    print_section("MOLECULES")

    print(
        "Unique PubChem CIDs: "
        f"{dataframe['CID'].nunique(dropna=True):,}"
    )

    print(
        "Unique CAS values: "
        f"{dataframe['C.A.S.'].nunique(dropna=True):,}"
    )

    print(
        "Unique odor names: "
        f"{dataframe['Odor'].nunique(dropna=True):,}"
    )


def main() -> None:
    dataframe = load_dataset(DATASET_PATH)
    validate_columns(dataframe)

    print("KELLER/VOSSHALL DATASET ANALYSIS")
    print("===============================")
    print(f"Dataset: {DATASET_PATH}")
    print(f"Observations: {len(dataframe):,}")
    print(f"Columns: {len(dataframe.columns):,}")

    molecule_summary(dataframe)
    subject_summary(dataframe)
    dilution_summary(dataframe)

    print_section("DETECTION")
    value_counts(
        dataframe,
        "CAN OR CAN'T SMELL",
    )

    print_section("RECOGNITION")
    value_counts(
        dataframe,
        "KNOW OR DON'T KNOW THE SMELL",
    )

    print_section("GLOBAL PERCEPTUAL RATINGS")

    for column in GLOBAL_RATINGS:
        numeric_summary(dataframe, column)

    print_section("QUANTITATIVE DESCRIPTORS")
    descriptor_summary(dataframe)

    descriptor_count_per_observation(dataframe)

    detection_missingness(dataframe)

    print()
    print("ANALYSIS COMPLETE")
    print("-----------------")
    print(
        "No OpenSmell semantics were assigned to "
        "missing source values."
    )


if __name__ == "__main__":
    main()