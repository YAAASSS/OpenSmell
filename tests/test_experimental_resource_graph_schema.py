"""Conformance tests for the experimental OpenSmell ResourceGraph JSON Schema."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = (
    ROOT
    / "schema"
    / "experimental-resource-graph-0.1.schema.json"
)

VECTORS_PATH = (
    ROOT
    / "examples"
    / "resource_graph_interop_vectors.json"
)


def _load_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


SCHEMA = _load_json(SCHEMA_PATH)
VECTOR_DOCUMENT = _load_json(VECTORS_PATH)

VALIDATOR = Draft202012Validator(SCHEMA)

VECTORS = VECTOR_DOCUMENT["vectors"]

VECTOR_NAMES = [
    vector["name"]
    for vector in VECTORS
]


def _graph(name: str) -> dict[str, Any]:
    for vector in VECTORS:
        if vector["name"] == name:
            return copy.deepcopy(vector["graph"])

    raise AssertionError(
        f"unknown interoperability vector: {name}"
    )


def _assert_invalid(document: Any) -> None:
    with pytest.raises(ValidationError):
        VALIDATOR.validate(document)


# ---------------------------------------------------------------------------
# Schema integrity
# ---------------------------------------------------------------------------


def test_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(SCHEMA)


def test_schema_identity() -> None:
    assert (
        SCHEMA["$schema"]
        == "https://json-schema.org/draft/2020-12/schema"
    )

    assert (
        SCHEMA["$id"]
        == (
            "https://opensmell.org/schema/"
            "experimental-resource-graph-0.1.schema.json"
        )
    )


# ---------------------------------------------------------------------------
# Positive conformance vectors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "vector_name",
    VECTOR_NAMES,
)
def test_interoperability_vector_conforms(
    vector_name: str,
) -> None:
    document = _graph(vector_name)

    VALIDATOR.validate(document)


def test_empty_resource_graph_is_valid() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [],
    }

    VALIDATOR.validate(document)


def test_unresolved_reference_is_structurally_valid() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "source": {
                    "resource_id": "not-present-in-graph",
                },
            },
        ],
    }

    VALIDATOR.validate(document)


def test_unknown_result_scheme_is_valid() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": {
                    "resource_id": "stimulus-1",
                },
                "results": [
                    {
                        "scheme": {
                            "id": "example.unknown.scheme",
                            "version": "99",
                        },
                        "data": {
                            "anything": "is scheme-defined",
                        },
                    },
                ],
            },
        ],
    }

    VALIDATOR.validate(document)


def test_extension_fields_are_structurally_valid() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "example_extension": {
                    "future": True,
                },
            },
        ],
        "document_extension": {
            "future": True,
        },
    }

    VALIDATOR.validate(document)


def test_condition_value_may_be_null() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "conditions": [
                    {
                        "property": "example.condition",
                        "value": None,
                    },
                ],
            },
        ],
    }

    VALIDATOR.validate(document)


# ---------------------------------------------------------------------------
# Invalid document envelope
# ---------------------------------------------------------------------------


def test_missing_format_is_invalid() -> None:
    document = _graph("basic_graph")
    del document["format"]

    _assert_invalid(document)


def test_wrong_format_is_invalid() -> None:
    document = _graph("basic_graph")
    document["format"] = "example.invalid"

    _assert_invalid(document)


def test_missing_version_is_invalid() -> None:
    document = _graph("basic_graph")
    del document["version"]

    _assert_invalid(document)


def test_wrong_version_is_invalid() -> None:
    document = _graph("basic_graph")
    document["version"] = "999"

    _assert_invalid(document)


def test_missing_resources_is_invalid() -> None:
    document = _graph("basic_graph")
    del document["resources"]

    _assert_invalid(document)


def test_resources_must_be_array() -> None:
    document = _graph("basic_graph")
    document["resources"] = {}

    _assert_invalid(document)


# ---------------------------------------------------------------------------
# Invalid resource discrimination and identity
# ---------------------------------------------------------------------------


def test_unknown_resource_type_is_invalid() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "future_resource",
                "id": "resource-1",
            },
        ],
    }

    _assert_invalid(document)


def test_resource_type_is_required() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "id": "resource-1",
            },
        ],
    }

    _assert_invalid(document)


def test_resource_id_is_required() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
            },
        ],
    }

    _assert_invalid(document)


def test_resource_id_must_not_be_empty() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "",
            },
        ],
    }

    _assert_invalid(document)


def test_resource_id_must_be_string() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": 123,
            },
        ],
    }

    _assert_invalid(document)


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------


def test_reference_requires_resource_id() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "source": {},
            },
        ],
    }

    _assert_invalid(document)


def test_reference_resource_id_must_not_be_empty() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "source": {
                    "resource_id": "",
                },
            },
        ],
    }

    _assert_invalid(document)


def test_reference_must_be_object_or_null_where_optional() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "source": "molecule-1",
            },
        ],
    }

    _assert_invalid(document)


# ---------------------------------------------------------------------------
# External identifiers
# ---------------------------------------------------------------------------


def test_external_identifier_requires_scheme() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "identifiers": [
                    {
                        "value": "123",
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_external_identifier_requires_value() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "identifiers": [
                    {
                        "scheme": "example.id",
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_external_identifier_values_must_not_be_empty() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "identifiers": [
                    {
                        "scheme": "",
                        "value": "",
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------


def test_condition_requires_property() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "conditions": [
                    {
                        "value": 1.0,
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_condition_requires_value() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "conditions": [
                    {
                        "property": "concentration",
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_condition_property_must_not_be_empty() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "conditions": [
                    {
                        "property": "",
                        "value": 1.0,
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_condition_unit_must_not_be_empty() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "stimulus",
                "id": "stimulus-1",
                "conditions": [
                    {
                        "property": "concentration",
                        "value": 1.0,
                        "unit": "",
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------


def test_observation_requires_stimulus() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
            },
        ],
    }

    _assert_invalid(document)


def test_observation_stimulus_must_be_reference() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": "stimulus-1",
            },
        ],
    }

    _assert_invalid(document)


def test_observation_context_must_be_object() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": {
                    "resource_id": "stimulus-1",
                },
                "context": [],
            },
        ],
    }

    _assert_invalid(document)


def test_observation_results_must_be_array() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": {
                    "resource_id": "stimulus-1",
                },
                "results": {},
            },
        ],
    }

    _assert_invalid(document)


# ---------------------------------------------------------------------------
# Results and ResultScheme
# ---------------------------------------------------------------------------


def test_result_requires_scheme() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": {
                    "resource_id": "stimulus-1",
                },
                "results": [
                    {
                        "data": {},
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_result_requires_data() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": {
                    "resource_id": "stimulus-1",
                },
                "results": [
                    {
                        "scheme": {
                            "id": "example.scheme",
                            "version": "0.1",
                        },
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_result_data_must_be_object() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": {
                    "resource_id": "stimulus-1",
                },
                "results": [
                    {
                        "scheme": {
                            "id": "example.scheme",
                            "version": "0.1",
                        },
                        "data": [],
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_result_scheme_requires_id() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": {
                    "resource_id": "stimulus-1",
                },
                "results": [
                    {
                        "scheme": {
                            "version": "0.1",
                        },
                        "data": {},
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_result_scheme_requires_version() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": {
                    "resource_id": "stimulus-1",
                },
                "results": [
                    {
                        "scheme": {
                            "id": "example.scheme",
                        },
                        "data": {},
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_result_scheme_id_must_not_be_empty() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": {
                    "resource_id": "stimulus-1",
                },
                "results": [
                    {
                        "scheme": {
                            "id": "",
                            "version": "0.1",
                        },
                        "data": {},
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)


def test_result_scheme_version_must_not_be_empty() -> None:
    document = {
        "format": "org.opensmell.experimental.resource-graph",
        "version": "0.1",
        "resources": [
            {
                "type": "observation",
                "id": "observation-1",
                "stimulus": {
                    "resource_id": "stimulus-1",
                },
                "results": [
                    {
                        "scheme": {
                            "id": "example.scheme",
                            "version": "",
                        },
                        "data": {},
                    },
                ],
            },
        ],
    }

    _assert_invalid(document)