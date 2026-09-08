"""Regression tests for strict JSON handling in the OpenSmell Core."""

from __future__ import annotations

import json

import pytest

from opensmell import dump, load_document
from opensmell.exceptions import OpenSmellValidationError
from opensmell.models import Document, Odor, Representation, Scheme
from opensmell.validation import validate_document


def _valid_document_dict() -> dict:
    return {
        "opensmell": "0.1",
        "odor": {
            "id": "urn:example:strict-json",
            "representations": [
                {
                    "type": "future",
                    "scheme": {
                        "id": "urn:example:scheme",
                        "version": "1",
                    },
                    "data": {
                        "value": "example",
                    },
                }
            ],
        },
    }


def _valid_document_model(data: object) -> Document:
    return Document(
        odor=Odor(
            id="urn:example:strict-json",
            representations=[
                Representation(
                    type="future",
                    scheme=Scheme(
                        id="urn:example:scheme",
                        version="1",
                    ),
                    data=data,
                )
            ],
        ),
        version="0.1",
    )


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_validate_document_rejects_non_finite_numbers(value: float) -> None:
    document = _valid_document_dict()
    document["odor"]["representations"][0]["data"] = {
        "value": value,
    }

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


def test_validate_document_rejects_non_string_object_key() -> None:
    document = _valid_document_dict()
    document["odor"]["representations"][0]["data"] = {
        1: "not-a-json-object-key",
    }

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


@pytest.mark.parametrize(
    "value",
    [
        (1, 2, 3),
        {1, 2, 3},
        b"not-json",
        object(),
    ],
)
def test_validate_document_rejects_non_json_python_values(
    value: object,
) -> None:
    document = _valid_document_dict()
    document["odor"]["representations"][0]["data"] = {
        "value": value,
    }

    with pytest.raises(OpenSmellValidationError):
        validate_document(document)


@pytest.mark.parametrize(
    "constant",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_load_document_rejects_non_standard_json_constants(
    tmp_path,
    constant: str,
) -> None:
    path = tmp_path / "invalid.osmell"

    path.write_text(
        (
            "{"
            '"opensmell":"0.1",'
            '"odor":{'
            '"id":"urn:example:strict-json",'
            '"representations":[{'
            '"type":"future",'
            '"scheme":{'
            '"id":"urn:example:scheme",'
            '"version":"1"'
            "},"
            f'"data":{{"value":{constant}}}'
            "}]"
            "}"
            "}"
        ),
        encoding="utf-8",
    )

    with pytest.raises(OpenSmellValidationError):
        load_document(path)


def test_load_document_rejects_number_that_overflows_to_infinity(
    tmp_path,
) -> None:
    path = tmp_path / "overflow.osmell"

    path.write_text(
        (
            "{"
            '"opensmell":"0.1",'
            '"odor":{'
            '"id":"urn:example:strict-json",'
            '"representations":[{'
            '"type":"future",'
            '"scheme":{'
            '"id":"urn:example:scheme",'
            '"version":"1"'
            "},"
            '"data":{"value":1e400}'
            "}]"
            "}"
            "}"
        ),
        encoding="utf-8",
    )

    with pytest.raises(OpenSmellValidationError):
        load_document(path)


def test_dump_rejects_non_finite_number(tmp_path) -> None:
    path = tmp_path / "invalid.osmell"

    document = _valid_document_model(
        {
            "value": float("nan"),
        }
    )

    with pytest.raises(OpenSmellValidationError):
        dump(document, path)

    assert not path.exists()


def test_failed_dump_does_not_overwrite_existing_file(tmp_path) -> None:
    path = tmp_path / "existing.osmell"
    original = "existing content that must survive\n"
    path.write_text(original, encoding="utf-8")

    document = _valid_document_model(
        {
            "value": {1, 2, 3},
        }
    )

    with pytest.raises(OpenSmellValidationError):
        dump(document, path)

    assert path.read_text(encoding="utf-8") == original


def test_dump_produces_standard_json(tmp_path) -> None:
    path = tmp_path / "valid.osmell"

    document = _valid_document_model(
        {
            "integer": 123,
            "number": 1.25,
            "boolean": True,
            "null": None,
            "array": [1, "two", False],
            "object": {
                "nested": "value",
            },
        }
    )

    dump(document, path)

    parsed = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(value)
        ),
    )

    assert parsed["odor"]["representations"][0]["data"] == {
        "integer": 123,
        "number": 1.25,
        "boolean": True,
        "null": None,
        "array": [1, "two", False],
        "object": {
            "nested": "value",
        },
    }