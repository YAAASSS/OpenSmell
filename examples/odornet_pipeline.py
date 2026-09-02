"""End-to-end OdorNet -> OpenSmell -> PubChem demonstration."""

import csv

import opensmell
from opensmell.adapters import odornet
from opensmell.enrichment import (
    PubChemResolutionError,
    resolve_smiles,
)


INPUT_FILE = "examples/odornet.csv"
OUTPUT_FILE = "examples/odornet-enriched-example.osmell"


def normalize_odornet_record(
    record: dict[str, str],
) -> dict:
    """Convert CSV strings into values expected by the OdorNet adapter."""

    normalized = {}

    for key, value in record.items():
        if key == "SMILES":
            normalized[key] = value
        elif value == "1.0":
            normalized[key] = 1
        elif value == "0.0":
            normalized[key] = 0
        elif value == "":
            normalized[key] = None
        else:
            normalized[key] = value

    return normalized


def main() -> None:
    # Read one real OdorNet record.
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)
        raw_record = next(reader)

    record = normalize_odornet_record(
        raw_record
    )

    smiles = record["SMILES"]

    print("=== OdorNet ===")
    print("SMILES:", smiles)

    # Convert OdorNet data into OpenSmell.
    odor = odornet.from_record(
        record
    )

    print()
    print("=== OpenSmell ===")
    print("Odor ID:", odor.id)

    for representation in odor.representations:
        print(
            "-",
            representation.type,
            "|",
            representation.scheme.id,
        )

    # Resolve the molecule using PubChem.
    print()
    print("=== PubChem enrichment ===")

    try:
        identity = resolve_smiles(
            smiles
        )

        print("Source:", identity.source)
        print("Title:", identity.title)
        print(
            "IUPAC name:",
            identity.iupac_name,
        )
        print(
            "Canonical SMILES:",
            identity.canonical_smiles,
        )
        print(
            "InChIKey:",
            identity.inchikey,
        )

    except PubChemResolutionError as error:
        print("Enrichment failed:")
        print(error)

    # Serialize the OpenSmell odor.
    opensmell.dump(
        odor,
        OUTPUT_FILE,
    )

    print()
    print("=== Output ===")
    print("Written to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()