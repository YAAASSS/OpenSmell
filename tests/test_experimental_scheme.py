"""Tests for the experimental generic Scheme model."""

from __future__ import annotations

import pytest

from opensmell.experimental.scheme import (
    Scheme,
    scheme_from_dict,
    scheme_to_dict,
)


def test_scheme_accepts_valid_values() -> None:
    scheme = Scheme(
        id="org.example.scheme",
        version="0.1",
    )

    assert scheme.id == "org.example.scheme"
    assert scheme.version == "0.1"
    assert scheme.extra == {}


@pytest.mark.parametrize(
    ("field", "value", "exception"),
    [
        ("id", "", ValueError),
        ("id", None, TypeError),
        ("id", 123, TypeError),
        ("version", "", ValueError),
        ("version", None, TypeError),
        ("version", 123, TypeError),
    ],
)
def test_scheme_rejects_invalid_strings(
    field: str,
    value: object,
    exception: type[Exception],
) -> None:
    kwargs = {
        "id": "org.example.scheme",
        "version": "0.1",
    }

    kwargs[field] = value

    with pytest.raises(exception):
        Scheme(**kwargs)


def test_scheme_requires_dict_extra() -> None:
    with pytest.raises(TypeError):
        Scheme(
            id="org.example.scheme",
            version="0.1",
            extra=[],
        )


def test_scheme_rejects_non_json_extension_value() -> None:
    with pytest.raises(TypeError):
        Scheme(
            id="org.example.scheme",
            version="0.1",
            extra={
                "invalid": object(),
            },
        )


def test_scheme_rejects_non_string_extension_key() -> None:
    with pytest.raises(TypeError):
        Scheme(
            id="org.example.scheme",
            version="0.1",
            extra={
                "nested": {
                    1: "invalid",
                }
            },
        )


def test_scheme_copies_extra_on_construction() -> None:
    extra = {
        "metadata": {
            "value": 1,
        }
    }

    scheme = Scheme(
        id="org.example.scheme",
        version="0.1",
        extra=extra,
    )

    nested = extra["metadata"]
    assert isinstance(nested, dict)

    nested["value"] = 999

    assert scheme.extra == {
        "metadata": {
            "value": 1,
        }
    }


def test_scheme_serialization() -> None:
    scheme = Scheme(
        id="org.example.scheme",
        version="0.1",
    )

    assert scheme_to_dict(
        scheme
    ) == {
        "id": "org.example.scheme",
        "version": "0.1",
    }


def test_scheme_preserves_extensions() -> None:
    scheme = Scheme(
        id="org.example.scheme",
        version="0.1",
        extra={
            "vocabulary": {
                "id": "org.example.vocabulary",
                "version": "2",
            },
            "unicode": "аромат 🌸",
        },
    )

    document = scheme_to_dict(
        scheme
    )

    recovered = scheme_from_dict(
        document
    )

    assert recovered == scheme
    assert scheme_to_dict(
        recovered
    ) == document


def test_scheme_serialization_returns_independent_data() -> None:
    scheme = Scheme(
        id="org.example.scheme",
        version="0.1",
        extra={
            "metadata": {
                "value": 1,
            }
        },
    )

    document = scheme_to_dict(
        scheme
    )

    metadata = document["metadata"]
    assert isinstance(
        metadata,
        dict,
    )

    metadata["value"] = 999

    assert scheme.extra == {
        "metadata": {
            "value": 1,
        }
    }


def test_scheme_parser_requires_object() -> None:
    with pytest.raises(TypeError):
        scheme_from_dict(
            []
        )


@pytest.mark.parametrize(
    "missing_field",
    [
        "id",
        "version",
    ],
)
def test_scheme_parser_requires_identity_fields(
    missing_field: str,
) -> None:
    document = {
        "id": "org.example.scheme",
        "version": "0.1",
    }

    del document[
        missing_field
    ]

    with pytest.raises(TypeError):
        scheme_from_dict(
            document
        )


def test_scheme_parser_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        scheme_from_dict(
            {
                "id": "",
                "version": "0.1",
            }
        )


def test_scheme_parser_rejects_empty_version() -> None:
    with pytest.raises(ValueError):
        scheme_from_dict(
            {
                "id": "org.example.scheme",
                "version": "",
            }
        )


def test_scheme_parser_preserves_unknown_fields() -> None:
    document = {
        "id": "org.example.scheme",
        "version": "0.1",
        "future": {
            "nested": [
                1,
                True,
                None,
                "value",
            ]
        },
    }

    scheme = scheme_from_dict(
        document
    )

    assert scheme.extra == {
        "future": {
            "nested": [
                1,
                True,
                None,
                "value",
            ]
        }
    }

    assert scheme_to_dict(
        scheme
    ) == document


def test_scheme_does_not_require_namespaced_id() -> None:
    scheme = Scheme(
        id="legacy-or-experimental",
        version="anything",
    )

    assert (
        scheme.id
        == "legacy-or-experimental"
    )
    assert scheme.version == "anything"


def test_scheme_does_not_interpret_version() -> None:
    scheme = Scheme(
        id="org.example.scheme",
        version="future-version-alpha",
    )

    assert (
        scheme.version
        == "future-version-alpha"
    )


def test_scheme_does_not_interpret_payloads() -> None:
    scheme = Scheme(
        id="org.opensmell.semantic.annotations",
        version="0.1",
    )

    assert (
        scheme.id
        == "org.opensmell.semantic.annotations"
    )