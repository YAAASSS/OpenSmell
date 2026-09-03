"""Golden interoperability vectors for experimental OpenSmell Resource IDs.

These tests ensure that the experimental canonical source-identity encoding
and UUIDv5 generation remain stable.

The vectors are intended to be independently reproducible by implementations
in other programming languages.

Composite identity keys are structural ASCII role names. Unicode remains
supported in identity values.

Nothing in this module is normative OpenSmell 0.1.
"""

from __future__ import annotations

import json
from pathlib import Path

from opensmell.experimental.identifiers import (
    canonical_generation_name,
    deterministic_resource_id_from_source,
)


ROOT = Path(__file__).resolve().parents[1]

VECTORS_PATH = (
    ROOT
    / "examples"
    / "identifier_torture_vectors.json"
)


def load_vectors() -> list[dict]:
    """Load the cross-language golden interoperability vectors."""

    with VECTORS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_golden_vector_file_exists():
    """The published golden-vector file must remain available."""

    assert VECTORS_PATH.is_file()


def test_golden_vectors_are_not_empty():
    """The golden-vector corpus must not silently become empty."""

    vectors = load_vectors()
    assert vectors


def test_expected_torture_vector_count():
    """Lock the current interoperability corpus size."""

    vectors = load_vectors()
    assert len(vectors) == 17


def test_golden_canonical_generation_names():
    """Python must reproduce every published canonical generation string."""

    for vector in load_vectors():
        canonical = canonical_generation_name(
            dataset=vector["dataset"],
            resource_type=vector["resource_type"],
            source_identity=vector["source_identity"],
        )

        assert canonical == vector["canonical"], (
            f"Canonical generation mismatch for "
            f"{vector['name']!r}"
        )


def test_golden_utf8_octets():
    """Python must reproduce every published UTF-8 generation vector."""

    for vector in load_vectors():
        canonical = canonical_generation_name(
            dataset=vector["dataset"],
            resource_type=vector["resource_type"],
            source_identity=vector["source_identity"],
        )

        utf8_hex = canonical.encode(
            "utf-8"
        ).hex()

        assert utf8_hex == vector["utf8_hex"], (
            f"UTF-8 generation mismatch for "
            f"{vector['name']!r}"
        )


def test_golden_resource_ids():
    """Python must reproduce every published UUIDv5 Resource ID."""

    for vector in load_vectors():
        resource_id = (
            deterministic_resource_id_from_source(
                dataset=vector["dataset"],
                resource_type=vector["resource_type"],
                source_identity=vector["source_identity"],
            )
        )

        assert resource_id == vector["uuid"], (
            f"UUID mismatch for "
            f"{vector['name']!r}"
        )


def test_unicode_normalization_is_not_implicit():
    """Precomposed and decomposed Unicode remain distinct identities."""

    vectors = {
        vector["name"]: vector
        for vector in load_vectors()
    }

    nfc = vectors["Latin NFC"]
    decomposed = vectors[
        "Latin decomposed NFD-like"
    ]

    assert (
        nfc["source_identity"]
        != decomposed["source_identity"]
    )

    assert (
        nfc["canonical"]
        != decomposed["canonical"]
    )

    assert (
        nfc["utf8_hex"]
        != decomposed["utf8_hex"]
    )

    assert (
        nfc["uuid"]
        != decomposed["uuid"]
    )


def test_composite_ascii_key_order_is_canonical():
    """ASCII structural key order must be insertion-independent."""

    source_a = {
        "z_field": "ascii",
        "a_field": "first",
        "unicode_latin": "café",
        "unicode_cjk": "咖啡",
    }

    source_b = {
        "unicode_cjk": "咖啡",
        "a_field": "first",
        "z_field": "ascii",
        "unicode_latin": "café",
    }

    canonical_a = canonical_generation_name(
        dataset="torture",
        resource_type="target",
        source_identity=source_a,
    )

    canonical_b = canonical_generation_name(
        dataset="torture",
        resource_type="target",
        source_identity=source_b,
    )

    assert canonical_a == canonical_b


def test_composite_values_preserve_unicode():
    """Composite ASCII keys must not restrict Unicode identity values."""

    source_identity = {
        "latin": "café",
        "cjk": "咖啡",
        "emoji": "😀",
    }

    canonical = canonical_generation_name(
        dataset="torture",
        resource_type="target",
        source_identity=source_identity,
    )

    assert "café" in canonical
    assert "咖啡" in canonical
    assert "😀" in canonical


def test_composite_delimiter_boundaries_remain_distinct():
    """Composite identity must not collapse into delimiter concatenation."""

    first = deterministic_resource_id_from_source(
        dataset="dataset",
        resource_type="observation",
        source_identity={
            "stimulus": "a|b",
            "target": "c",
        },
    )

    second = deterministic_resource_id_from_source(
        dataset="dataset",
        resource_type="observation",
        source_identity={
            "stimulus": "a",
            "target": "b|c",
        },
    )

    assert first != second