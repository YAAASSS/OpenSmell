"""Tests for the OpenSmell JSON Schema."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parent.parent

PUBLIC_SCHEMA = (
    ROOT
    / "schema"
    / "opensmell-0.1.schema.json"
)

PACKAGED_SCHEMA = (
    ROOT
    / "src"
    / "opensmell"
    / "schemas"
    / "opensmell-0.1.schema.json"
)


def test_public_and_packaged_schemas_are_identical():
    """The public and packaged schemas must stay synchronized."""

    public = PUBLIC_SCHEMA.read_text(
        encoding="utf-8"
    )

    packaged = PACKAGED_SCHEMA.read_text(
        encoding="utf-8"
    )

    assert public == packaged


def test_schema_is_valid_json_schema():
    """The OpenSmell schema must itself be a valid JSON Schema."""

    schema = json.loads(
        PUBLIC_SCHEMA.read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)