"""Tests for PubChem enrichment utilities."""

import io
import json
import urllib.error

import pytest

from opensmell.enrichment.pubchem import (
    PubChemResolutionError,
    resolve_smiles,
)


class FakeResponse:
    """Minimal fake HTTP response."""

    def __init__(self, document):
        self._data = json.dumps(document).encode("utf-8")

    def __enter__(self):
        return io.BytesIO(self._data)

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_resolve_smiles(monkeypatch):
    document = {
        "PropertyTable": {
            "Properties": [
                {
                    "Title": "Heptyl butyrate",
                    "IUPACName": "heptyl butanoate",
                    "ConnectivitySMILES": "CCCCCCCOC(=O)CCC",
                    "InChIKey": "JPQHLIYIQARLQM-UHFFFAOYSA-N",
                }
            ]
        }
    }

    def fake_urlopen(request, timeout):
        return FakeResponse(document)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        fake_urlopen,
    )

    identity = resolve_smiles(
        "CCCCCCCOC(=O)CCC"
    )

    assert identity.title == "Heptyl butyrate"
    assert identity.iupac_name == "heptyl butanoate"
    assert (
        identity.canonical_smiles
        == "CCCCCCCOC(=O)CCC"
    )
    assert (
        identity.inchikey
        == "JPQHLIYIQARLQM-UHFFFAOYSA-N"
    )


def test_resolve_smiles_uses_post(monkeypatch):
    captured = {}

    document = {
        "PropertyTable": {
            "Properties": [
                {}
            ]
        }
    }

    def fake_urlopen(request, timeout):
        captured["method"] = request.get_method()
        captured["data"] = request.data

        return FakeResponse(document)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        fake_urlopen,
    )

    resolve_smiles(
        r"C/C=C(\C)C(=O)OCCCC"
    )

    assert captured["method"] == "POST"
    assert captured["data"] is not None


def test_empty_smiles_is_rejected():
    with pytest.raises(ValueError):
        resolve_smiles("")


def test_whitespace_smiles_is_rejected():
    with pytest.raises(ValueError):
        resolve_smiles("   ")


def test_pubchem_http_error(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url="https://pubchem.ncbi.nlm.nih.gov/",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(
        "urllib.request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(PubChemResolutionError):
        resolve_smiles("invalid")


def test_missing_pubchem_properties(monkeypatch):
    document = {
        "PropertyTable": {
            "Properties": []
        }
    }

    def fake_urlopen(request, timeout):
        return FakeResponse(document)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        fake_urlopen,
    )

    with pytest.raises(PubChemResolutionError):
        resolve_smiles("CCO")