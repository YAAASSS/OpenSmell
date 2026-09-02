"""PubChem enrichment utilities for OpenSmell."""

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class ChemicalIdentity:
    """Chemical identity information resolved from an external source."""

    title: str | None
    iupac_name: str | None
    canonical_smiles: str | None
    inchikey: str | None
    source: str = "PubChem"


class PubChemResolutionError(Exception):
    """Raised when PubChem cannot resolve a chemical identity."""


def resolve_smiles(
    smiles: str,
    *,
    timeout: float = 15,
) -> ChemicalIdentity:
    """Resolve a SMILES string using PubChem PUG REST."""

    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError(
            "smiles must be a non-empty string"
        )

    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
        "smiles/property/"
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
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            document = json.load(response)

        properties = document[
            "PropertyTable"
        ]["Properties"][0]

    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        KeyError,
        IndexError,
        json.JSONDecodeError,
    ) as error:
        raise PubChemResolutionError(
            f"PubChem could not resolve SMILES {smiles!r}"
        ) from error

    return ChemicalIdentity(
        title=properties.get("Title"),
        iupac_name=properties.get("IUPACName"),
        canonical_smiles=properties.get(
            "ConnectivitySMILES"
        ),
        inchikey=properties.get("InChIKey"),
    )