"""Find exact chemical identity intersections between OdorNet and Keller/Vosshall.

Keller/Vosshall normally exposes PubChem CIDs, but the supplied workbook also
contains rows where the CID field contains a CAS number. Those values are
resolved through PubChem as names/identifiers rather than being discarded.

The final cross-dataset match is based exclusively on PubChem InChIKey.

This tool is experimental analysis infrastructure. It does not modify the
OpenSmell data model.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

KELLER_PATH = PROJECT_ROOT / "examples" / "keller_vosshall.xlsx"
ODORNET_PATH = PROJECT_ROOT / "examples" / "odornet_enriched.csv"

DEFAULT_CACHE_PATH = (
    PROJECT_ROOT
    / "examples"
    / "keller_pubchem_identity_cache.json"
)

PUBCHEM_BASE_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"
)

USER_AGENT = "OpenSmell/0.1 experimental dataset analysis"

CAS_PATTERN = re.compile(
    r"^\d{2,7}-\d{2}-\d$"
)


def clean_value(value: Any) -> Any:
    """Convert pandas scalar values into ordinary Python values."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass

    return value


def classify_source_identifier(
    value: Any,
) -> tuple[str, str]:
    """Classify a Keller identifier as PubChem CID or CAS."""

    value = clean_value(value)

    if value is None:
        raise ValueError(
            "Keller chemical identifier is missing"
        )

    text = str(value).strip()

    if not text:
        raise ValueError(
            "Keller chemical identifier is empty"
        )

    if text.isdigit():
        cid = int(text)

        if cid <= 0:
            raise ValueError(
                f"PubChem CID must be positive, got {text!r}"
            )

        return "cid", str(cid)

    if CAS_PATTERN.fullmatch(text):
        return "cas", text

    raise ValueError(
        f"unsupported Keller chemical identifier: {text!r}"
    )


def load_keller() -> pd.DataFrame:
    """Load Keller/Vosshall using the workbook's real header row."""

    frame = pd.read_excel(
        KELLER_PATH,
        sheet_name="data",
        header=2,
    )

    frame.columns = [
        str(column).strip()
        for column in frame.columns
    ]

    required = {
        "C.A.S.",
        "CID",
        "Odor",
        "Odor dilution",
        "Subject # (this study)",
    }

    missing = required - set(frame.columns)

    if missing:
        raise RuntimeError(
            "Keller/Vosshall dataset is missing columns: "
            + ", ".join(sorted(missing))
        )

    return frame


def load_odornet() -> pd.DataFrame:
    """Load the locally enriched OdorNet dataset."""

    frame = pd.read_csv(
        ODORNET_PATH
    )

    required = {
        "SMILES",
        "PubChem_Status",
        "PubChem_Title",
        "PubChem_IUPACName",
        "PubChem_CanonicalSMILES",
        "PubChem_InChIKey",
    }

    missing = required - set(frame.columns)

    if missing:
        raise RuntimeError(
            "OdorNet dataset is missing columns: "
            + ", ".join(sorted(missing))
        )

    return frame


def load_cache(
    path: Path,
) -> dict[str, dict[str, Any]]:
    """Load the local Keller PubChem identity cache."""

    if not path.exists():
        return {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        value = json.load(handle)

    if not isinstance(value, dict):
        raise RuntimeError(
            "Keller PubChem cache must contain a JSON object"
        )

    result: dict[str, dict[str, Any]] = {}

    for key, entry in value.items():
        if not isinstance(key, str):
            raise RuntimeError(
                "Keller PubChem cache keys must be strings"
            )

        if not isinstance(entry, dict):
            raise RuntimeError(
                f"cache entry {key!r} must be an object"
            )

        result[key] = entry

    return result


def save_cache(
    path: Path,
    cache: dict[str, dict[str, Any]],
) -> None:
    """Save the identity cache deterministically."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ordered = {
        key: cache[key]
        for key in sorted(cache)
    }

    text = json.dumps(
        ordered,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )

    path.write_text(
        text + "\n",
        encoding="utf-8",
    )


def fetch_pubchem_properties(
    namespace: str,
    identifier: str,
    *,
    timeout: float,
) -> dict[str, Any]:
    """Resolve one PubChem identifier to chemical identity properties."""

    encoded = quote(
        identifier,
        safe="",
    )

    url = (
        f"{PUBCHEM_BASE_URL}/{namespace}/{encoded}/property/"
        "Title,IUPACName,CanonicalSMILES,InChIKey/JSON"
    )

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            raw = response.read()

    except HTTPError as error:
        return {
            "status": "http_error",
            "http_status": error.code,
        }

    except URLError as error:
        return {
            "status": "network_error",
            "error": str(error.reason),
        }

    except TimeoutError:
        return {
            "status": "network_error",
            "error": "timeout",
        }

    try:
        payload = json.loads(
            raw.decode("utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        return {
            "status": "invalid_response",
            "error": str(error),
        }

    try:
        properties = (
            payload["PropertyTable"]["Properties"]
        )
    except (
        KeyError,
        TypeError,
    ):
        return {
            "status": "invalid_response",
            "error": "missing PropertyTable.Properties",
        }

    if (
        not isinstance(properties, list)
        or not properties
    ):
        return {
            "status": "not_found",
        }

    item = properties[0]

    if not isinstance(item, dict):
        return {
            "status": "invalid_response",
            "error": "property entry is not an object",
        }

    returned_cid = item.get("CID")

    if returned_cid is None:
        return {
            "status": "invalid_response",
            "error": "PubChem response has no CID",
        }

    return {
        "status": "resolved",
        "cid": str(returned_cid),
        "title": item.get("Title"),
        "iupac_name": item.get("IUPACName"),
        "canonical_smiles": item.get(
            "ConnectivitySMILES",
            item.get("CanonicalSMILES"),
        ),
        "inchikey": item.get("InChIKey"),
    }


def resolve_source_identifier(
    source_kind: str,
    source_value: str,
    *,
    timeout: float,
) -> dict[str, Any]:
    """Resolve either a PubChem CID or a CAS identifier."""

    if source_kind == "cid":
        result = fetch_pubchem_properties(
            "cid",
            source_value,
            timeout=timeout,
        )
    elif source_kind == "cas":
        result = fetch_pubchem_properties(
            "name",
            source_value,
            timeout=timeout,
        )
    else:
        raise ValueError(
            f"unsupported source identifier kind: {source_kind}"
        )

    result["source_kind"] = source_kind
    result["source_value"] = source_value

    return result


def build_keller_molecule_index(
    frame: pd.DataFrame,
) -> dict[str, dict[str, Any]]:
    """Build unique Keller chemical identities from CID/CAS source fields."""

    result: dict[str, dict[str, Any]] = {}

    for _, row in frame.iterrows():
        raw_identifier = clean_value(
            row["CID"]
        )

        if raw_identifier is None:
            raw_identifier = clean_value(
                row["C.A.S."]
            )

        if raw_identifier is None:
            continue

        kind, value = classify_source_identifier(
            raw_identifier
        )

        key = f"{kind}:{value}"

        if key not in result:
            result[key] = {
                "source_kind": kind,
                "source_value": value,
                "names": set(),
                "cas_values": set(),
            }

        odor_name = clean_value(
            row["Odor"]
        )

        if isinstance(odor_name, str):
            odor_name = odor_name.strip()

            if odor_name:
                result[key]["names"].add(
                    odor_name
                )

        cas_value = clean_value(
            row["C.A.S."]
        )

        if isinstance(cas_value, str):
            cas_value = cas_value.strip()

            if cas_value:
                result[key]["cas_values"].add(
                    cas_value
                )

    return result


def resolve_keller_identities(
    molecules: dict[str, dict[str, Any]],
    cache: dict[str, dict[str, Any]],
    *,
    cache_path: Path,
    timeout: float,
    delay: float,
) -> None:
    """Resolve Keller chemical identifiers missing from the cache."""

    pending = [
        key
        for key in molecules
        if key not in cache
    ]

    if not pending:
        print(
            "All Keller chemical identifiers are already cached."
        )
        return

    print(
        f"Resolving {len(pending)} Keller chemical "
        "identifier(s) through PubChem..."
    )

    for index, key in enumerate(
        pending,
        start=1,
    ):
        molecule = molecules[key]

        result = resolve_source_identifier(
            molecule["source_kind"],
            molecule["source_value"],
            timeout=timeout,
        )

        cache[key] = result

        print(
            f"[{index:>3}/{len(pending)}] "
            f"{key} -> {result.get('status')}"
        )

        save_cache(
            cache_path,
            cache,
        )

        if index != len(pending):
            time.sleep(delay)


def build_odornet_index(
    frame: pd.DataFrame,
) -> dict[str, list[dict[str, Any]]]:
    """Index resolved OdorNet rows by exact PubChem InChIKey."""

    result: dict[str, list[dict[str, Any]]] = {}

    for row_index, row in frame.iterrows():
        if clean_value(
            row["PubChem_Status"]
        ) != "resolved":
            continue

        inchikey = clean_value(
            row["PubChem_InChIKey"]
        )

        if not isinstance(inchikey, str):
            continue

        inchikey = inchikey.strip()

        if not inchikey:
            continue

        result.setdefault(
            inchikey,
            [],
        ).append(
            {
                "row": int(row_index),
                "smiles": clean_value(
                    row["SMILES"]
                ),
                "title": clean_value(
                    row["PubChem_Title"]
                ),
                "iupac_name": clean_value(
                    row["PubChem_IUPACName"]
                ),
                "canonical_smiles": clean_value(
                    row["PubChem_CanonicalSMILES"]
                ),
                "inchikey": inchikey,
            }
        )

    return result


def find_intersections(
    molecules: dict[str, dict[str, Any]],
    cache: dict[str, dict[str, Any]],
    odornet_index: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Find exact InChIKey intersections."""

    matches: list[dict[str, Any]] = []

    for key in sorted(molecules):
        identity = cache.get(key)

        if not identity:
            continue

        if identity.get("status") != "resolved":
            continue

        inchikey = identity.get("inchikey")

        if not isinstance(inchikey, str):
            continue

        inchikey = inchikey.strip()

        if not inchikey:
            continue

        for odornet in odornet_index.get(
            inchikey,
            [],
        ):
            molecule = molecules[key]

            matches.append(
                {
                    "source_key": key,
                    "source_kind": molecule[
                        "source_kind"
                    ],
                    "source_value": molecule[
                        "source_value"
                    ],
                    "keller_names": sorted(
                        molecule["names"]
                    ),
                    "keller_cas": sorted(
                        molecule["cas_values"]
                    ),
                    "pubchem_cid": identity.get(
                        "cid"
                    ),
                    "inchikey": inchikey,
                    "pubchem_title": identity.get(
                        "title"
                    ),
                    "pubchem_iupac_name": identity.get(
                        "iupac_name"
                    ),
                    "pubchem_canonical_smiles": (
                        identity.get(
                            "canonical_smiles"
                        )
                    ),
                    "odornet_row": odornet[
                        "row"
                    ],
                    "odornet_title": odornet[
                        "title"
                    ],
                    "odornet_smiles": odornet[
                        "smiles"
                    ],
                }
            )

    return matches


def print_summary(
    molecules: dict[str, dict[str, Any]],
    cache: dict[str, dict[str, Any]],
    odornet_index: dict[str, list[dict[str, Any]]],
    matches: list[dict[str, Any]],
) -> None:
    """Print resolution and intersection statistics."""

    cid_count = sum(
        1
        for molecule in molecules.values()
        if molecule["source_kind"] == "cid"
    )

    cas_count = sum(
        1
        for molecule in molecules.values()
        if molecule["source_kind"] == "cas"
    )

    resolved_count = sum(
        1
        for key in molecules
        if (
            key in cache
            and cache[key].get("status")
            == "resolved"
        )
    )

    failed_count = len(molecules) - resolved_count

    matching_keys = {
        match["source_key"]
        for match in matches
    }

    print()
    print("=== Identity resolution summary ===")
    print()
    print(
        f"Keller unique chemical identifiers: "
        f"{len(molecules):,}"
    )
    print(
        f"  numeric PubChem CID identifiers: {cid_count:,}"
    )
    print(
        f"  CAS identifiers stored in CID field: {cas_count:,}"
    )
    print(
        f"Resolved by PubChem: "
        f"{resolved_count:,}/{len(molecules):,}"
    )
    print(
        f"Unresolved/failed: {failed_count:,}"
    )
    print()
    print(
        f"OdorNet resolved unique InChIKeys: "
        f"{len(odornet_index):,}"
    )
    print(
        f"Exact matching Keller chemicals: "
        f"{len(matching_keys):,}"
    )
    print(
        f"Exact Keller/OdorNet row matches: "
        f"{len(matches):,}"
    )


def print_matches(
    matches: list[dict[str, Any]],
) -> None:
    """Print exact chemical intersections."""

    print()
    print("=== Exact OdorNet / Keller intersections ===")
    print()

    if not matches:
        print("No exact InChIKey intersections found.")
        return

    for index, match in enumerate(
        matches,
        start=1,
    ):
        print(
            f"[{index}] "
            f"PubChem CID {match['pubchem_cid']}"
        )
        print(
            "    Keller source identifier: "
            f"{match['source_kind']}="
            f"{match['source_value']}"
        )
        print(
            "    Keller name(s): "
            + (
                "; ".join(
                    match["keller_names"]
                )
                or "<none>"
            )
        )
        print(
            "    Keller CAS: "
            + (
                "; ".join(
                    match["keller_cas"]
                )
                or "<none>"
            )
        )
        print(
            "    PubChem title: "
            f"{match['pubchem_title']}"
        )
        print(
            "    InChIKey: "
            f"{match['inchikey']}"
        )
        print(
            "    OdorNet row: "
            f"{match['odornet_row']}"
        )
        print(
            "    OdorNet title: "
            f"{match['odornet_title']}"
        )
        print(
            "    OdorNet SMILES: "
            f"{match['odornet_smiles']}"
        )
        print()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Find exact PubChem/InChIKey intersections "
            "between OdorNet and Keller/Vosshall."
        )
    )

    parser.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_CACHE_PATH,
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.12,
    )

    return parser.parse_args()


def main() -> None:
    """Run the dataset intersection analysis."""

    args = parse_args()

    print("Loading Keller/Vosshall...")
    keller = load_keller()

    print(
        f"Keller observations: {len(keller):,}"
    )

    molecules = build_keller_molecule_index(
        keller
    )

    print(
        f"Keller unique chemical identifiers: "
        f"{len(molecules):,}"
    )

    print()
    print("Loading enriched OdorNet...")
    odornet = load_odornet()

    print(
        f"OdorNet rows: {len(odornet):,}"
    )

    odornet_index = build_odornet_index(
        odornet
    )

    print(
        f"OdorNet resolved unique InChIKeys: "
        f"{len(odornet_index):,}"
    )

    print()
    print(
        f"Loading Keller PubChem cache: {args.cache}"
    )

    cache = load_cache(
        args.cache
    )

    print(
        f"Cached Keller identities: "
        f"{len(cache):,}"
    )

    print()

    resolve_keller_identities(
        molecules,
        cache,
        cache_path=args.cache,
        timeout=args.timeout,
        delay=args.delay,
    )

    matches = find_intersections(
        molecules,
        cache,
        odornet_index,
    )

    print_summary(
        molecules,
        cache,
        odornet_index,
        matches,
    )

    print_matches(
        matches
    )


if __name__ == "__main__":
    main()