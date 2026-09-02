"""Enrich the OdorNet dataset with chemical identities from PubChem.

The script is designed for long-running enrichment jobs:

- preserves the original OdorNet data;
- resolves SMILES using PubChem PUG REST;
- stores results in a persistent cache;
- retries temporary failures;
- respects PubChem request-rate recommendations;
- can safely resume after interruption;
- periodically writes the enriched CSV.
"""

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


INPUT_FILE = Path("examples/odornet.csv")

OUTPUT_FILE = Path(
    "examples/odornet_enriched.csv"
)

CACHE_FILE = Path(
    "examples/pubchem_cache.json"
)

# PubChem asks clients not to exceed 5 requests/second.
# 0.30 s means a theoretical maximum of about 3.3 requests/s.
REQUEST_DELAY = 0.30

TIMEOUT = 20

MAX_RETRIES = 4

SAVE_EVERY = 25


def load_cache() -> dict[str, Any]:
    """Load the persistent PubChem cache."""

    if not CACHE_FILE.exists():
        return {}

    with CACHE_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_cache(
    cache: dict[str, Any],
) -> None:
    """Write the PubChem cache atomically."""

    temporary_file = CACHE_FILE.with_suffix(
        ".tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            cache,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_file.replace(
        CACHE_FILE
    )


def resolve_pubchem(
    smiles: str,
) -> dict[str, Any]:
    """Resolve one SMILES string using PubChem."""

    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/"
        "compound/smiles/property/"
        "Title,IUPACName,CanonicalSMILES,InChIKey/JSON"
    )

    body = urllib.parse.urlencode(
        {
            "smiles": smiles,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "User-Agent": "OpenSmell/0.1",
            "Content-Type":
                "application/x-www-form-urlencoded",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=TIMEOUT,
    ) as response:
        document = json.load(response)

    properties = document[
        "PropertyTable"
    ]["Properties"][0]

    return {
        "status": "resolved",
        "title": properties.get(
            "Title"
        ),
        "iupac_name": properties.get(
            "IUPACName"
        ),
        "canonical_smiles": properties.get(
            "ConnectivitySMILES"
        ),
        "inchikey": properties.get(
            "InChIKey"
        ),
    }


def resolve_with_retry(
    smiles: str,
) -> dict[str, Any]:
    """Resolve a SMILES with retry handling."""

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):
        try:
            return resolve_pubchem(
                smiles
            )

        except urllib.error.HTTPError as error:

            # 404 means PubChem could not find the compound.
            if error.code == 404:
                return {
                    "status": "not_found",
                    "title": None,
                    "iupac_name": None,
                    "canonical_smiles": None,
                    "inchikey": None,
                }

            # Temporary PubChem/server errors.
            if error.code in {
                429,
                500,
                502,
                503,
                504,
            }:
                wait = 2 ** attempt

                print(
                    f"    HTTP {error.code}, "
                    f"retry in {wait}s"
                )

                time.sleep(wait)
                continue

            return {
                "status": f"http_{error.code}",
                "title": None,
                "iupac_name": None,
                "canonical_smiles": None,
                "inchikey": None,
            }

        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
        ) as error:

            if attempt < MAX_RETRIES:
                wait = 2 ** attempt

                print(
                    "    Temporary error:",
                    error,
                )

                print(
                    f"    Retry in {wait}s"
                )

                time.sleep(wait)
                continue

            return {
                "status": "error",
                "title": None,
                "iupac_name": None,
                "canonical_smiles": None,
                "inchikey": None,
            }

    return {
        "status": "error",
        "title": None,
        "iupac_name": None,
        "canonical_smiles": None,
        "inchikey": None,
    }


def write_enriched_csv(
    records: list[dict[str, str]],
    cache: dict[str, Any],
) -> None:
    """Write the enriched OdorNet dataset."""

    if not records:
        return

    original_fields = list(
        records[0].keys()
    )

    extra_fields = [
        "PubChem_Status",
        "PubChem_Title",
        "PubChem_IUPACName",
        "PubChem_CanonicalSMILES",
        "PubChem_InChIKey",
    ]

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=(
                original_fields
                + extra_fields
            ),
        )

        writer.writeheader()

        for record in records:
            output = dict(record)

            smiles = record.get(
                "SMILES",
                "",
            )

            identity = cache.get(
                smiles,
                {},
            )

            output[
                "PubChem_Status"
            ] = identity.get(
                "status",
                "pending",
            )

            output[
                "PubChem_Title"
            ] = identity.get(
                "title",
                "",
            ) or ""

            output[
                "PubChem_IUPACName"
            ] = identity.get(
                "iupac_name",
                "",
            ) or ""

            output[
                "PubChem_CanonicalSMILES"
            ] = identity.get(
                "canonical_smiles",
                "",
            ) or ""

            output[
                "PubChem_InChIKey"
            ] = identity.get(
                "inchikey",
                "",
            ) or ""

            writer.writerow(
                output
            )


def main() -> None:
    """Run the OdorNet enrichment job."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_FILE}"
        )

    print("Loading OdorNet...")

    with INPUT_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file
        )

        records = list(
            reader
        )

    print(
        "Dataset rows:",
        len(records),
    )

    # Deduplicate the structures before querying PubChem.
    smiles_values = []

    seen = set()

    for record in records:
        smiles = record.get(
            "SMILES",
            "",
        ).strip()

        if not smiles:
            continue

        if smiles in seen:
            continue

        seen.add(smiles)
        smiles_values.append(
            smiles
        )

    print(
        "Unique SMILES:",
        len(smiles_values),
    )

    cache = load_cache()

    print(
        "Already cached:",
        len(cache),
    )

    remaining = [
        smiles
        for smiles in smiles_values
        if smiles not in cache
    ]

    print(
        "Remaining:",
        len(remaining),
    )

    print()
    print(
        "Press Ctrl+C at any time "
        "to stop safely."
    )
    print()

    completed_this_run = 0

    try:
        for index, smiles in enumerate(
            remaining,
            start=1,
        ):
            overall_done = (
                len(cache) + 1
            )

            print(
                f"[{index}/{len(remaining)}] "
                f"[total cache {overall_done}/"
                f"{len(smiles_values)}]"
            )

            print(
                "  SMILES:",
                smiles,
            )

            result = resolve_with_retry(
                smiles
            )

            cache[smiles] = result

            completed_this_run += 1

            print(
                "  Status:",
                result["status"],
            )

            if result.get("title"):
                print(
                    "  Name:",
                    result["title"],
                )

            if (
                completed_this_run
                % SAVE_EVERY
                == 0
            ):
                save_cache(
                    cache
                )

                write_enriched_csv(
                    records,
                    cache,
                )

                print(
                    "  Checkpoint saved."
                )

            time.sleep(
                REQUEST_DELAY
            )

    except KeyboardInterrupt:
        print()
        print(
            "Interrupted by user."
        )

    finally:
        print()
        print(
            "Saving cache..."
        )

        save_cache(
            cache
        )

        print(
            "Writing enriched CSV..."
        )

        write_enriched_csv(
            records,
            cache,
        )

    resolved = sum(
        1
        for value in cache.values()
        if value.get("status")
        == "resolved"
    )

    not_found = sum(
        1
        for value in cache.values()
        if value.get("status")
        == "not_found"
    )

    errors = (
        len(cache)
        - resolved
        - not_found
    )

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(
        "Dataset rows:",
        len(records),
    )

    print(
        "Unique SMILES:",
        len(smiles_values),
    )

    print(
        "Cached:",
        len(cache),
    )

    print(
        "Resolved:",
        resolved,
    )

    print(
        "Not found:",
        not_found,
    )

    print(
        "Errors:",
        errors,
    )

    print()
    print(
        "Output:",
        OUTPUT_FILE,
    )

    print(
        "Cache:",
        CACHE_FILE,
    )


if __name__ == "__main__":
    main()