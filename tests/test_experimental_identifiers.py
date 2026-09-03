"""Tests for experimental OpenSmell Resource ID utilities.

Nothing tested here is normative OpenSmell 0.1.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from opensmell.experimental.identifiers import (
    OPENSMELL_EXPERIMENTAL_NAMESPACE,
    canonical_generation_name,
    deterministic_resource_id,
    deterministic_resource_id_from_source,
    new_resource_id,
    validate_resource_id,
)


def test_experimental_namespace_is_fixed():
    """The experimental namespace must remain stable during experiments."""

    assert str(
        OPENSMELL_EXPERIMENTAL_NAMESPACE
    ) == "7f0f1d72-83c7-4f57-a1f6-4bc43bb26e58"


def test_new_resource_id_returns_uuid4():
    """New opaque resources use UUIDv4."""

    resource_id = new_resource_id()
    parsed = UUID(resource_id)

    assert parsed.version == 4
    assert str(parsed) == resource_id


def test_new_resource_ids_are_distinct():
    """Independent UUIDv4 generation should produce distinct IDs."""

    first = new_resource_id()
    second = new_resource_id()

    assert first != second


def test_deterministic_resource_id_is_stable():
    """The same canonical name must produce the same UUIDv5."""

    first = deterministic_resource_id(
        "example-resource"
    )

    second = deterministic_resource_id(
        "example-resource"
    )

    assert first == second
    assert UUID(first).version == 5


def test_deterministic_resource_id_changes_with_name():
    """Different generation names must produce different UUIDs."""

    first = deterministic_resource_id(
        "resource-a"
    )

    second = deterministic_resource_id(
        "resource-b"
    )

    assert first != second


def test_deterministic_resource_id_rejects_empty_name():
    """A deterministic generation name must not be empty."""

    with pytest.raises(ValueError):
        deterministic_resource_id("")


def test_canonical_generation_name_atomic():
    """Atomic source identities must produce deterministic JSON."""

    canonical = canonical_generation_name(
        dataset="burton_2022",
        resource_type="target",
        source_identity="113L_038",
    )

    assert canonical == (
        '{"dataset":"burton_2022",'
        '"resource_type":"target",'
        '"source_identity":"113L_038"}'
    )


def test_canonical_generation_name_composite():
    """Composite source identities must preserve their structure."""

    canonical = canonical_generation_name(
        dataset="burton_2022",
        resource_type="observation",
        source_identity={
            "stimulus": "1001_3.12e-13",
            "target": "111L_001",
        },
    )

    assert canonical == (
        '{"dataset":"burton_2022",'
        '"resource_type":"observation",'
        '"source_identity":{'
        '"stimulus":"1001_3.12e-13",'
        '"target":"111L_001"'
        '}}'
    )


def test_composite_source_identity_order_is_stable():
    """Dictionary insertion order must not change canonical identity."""

    first = canonical_generation_name(
        dataset="dataset",
        resource_type="observation",
        source_identity={
            "stimulus": "abc",
            "target": "xyz",
        },
    )

    second = canonical_generation_name(
        dataset="dataset",
        resource_type="observation",
        source_identity={
            "target": "xyz",
            "stimulus": "abc",
        },
    )

    assert first == second


def test_structural_delimiter_boundaries_are_preserved():
    """Structured source identity must avoid delimiter ambiguity."""

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


def test_atomic_and_composite_identity_are_distinct():
    """Atomic text and structured identity must remain different."""

    atomic = deterministic_resource_id_from_source(
        dataset="dataset",
        resource_type="target",
        source_identity="target=123",
    )

    composite = deterministic_resource_id_from_source(
        dataset="dataset",
        resource_type="target",
        source_identity={
            "target": "123",
        },
    )

    assert atomic != composite


def test_dataset_is_part_of_identity():
    """The same source identifier in different datasets is distinct."""

    first = deterministic_resource_id_from_source(
        dataset="dataset_a",
        resource_type="target",
        source_identity="123",
    )

    second = deterministic_resource_id_from_source(
        dataset="dataset_b",
        resource_type="target",
        source_identity="123",
    )

    assert first != second


def test_resource_type_is_part_of_identity():
    """The same source identity used for different resource types is distinct."""

    first = deterministic_resource_id_from_source(
        dataset="dataset",
        resource_type="target",
        source_identity="123",
    )

    second = deterministic_resource_id_from_source(
        dataset="dataset",
        resource_type="stimulus",
        source_identity="123",
    )

    assert first != second


def test_source_identity_is_part_of_identity():
    """Changing the source identity must change the Resource ID."""

    first = deterministic_resource_id_from_source(
        dataset="dataset",
        resource_type="target",
        source_identity="123",
    )

    second = deterministic_resource_id_from_source(
        dataset="dataset",
        resource_type="target",
        source_identity="124",
    )

    assert first != second


def test_unicode_source_identity_is_preserved():
    """Unicode source values must remain valid generation material."""

    canonical = canonical_generation_name(
        dataset="dataset",
        resource_type="target",
        source_identity="咖啡",
    )

    assert "咖啡" in canonical


def test_unicode_composite_values_are_preserved():
    """Composite identity values may contain arbitrary Unicode scalars."""

    canonical = canonical_generation_name(
        dataset="dataset",
        resource_type="observation",
        source_identity={
            "stimulus": "café",
            "target": "咖啡😀",
        },
    )

    assert "café" in canonical
    assert "咖啡😀" in canonical


def test_unicode_normalization_is_not_implicit():
    """NFC and decomposed source strings remain distinct."""

    nfc = deterministic_resource_id_from_source(
        dataset="dataset",
        resource_type="target",
        source_identity="café",
    )

    decomposed = deterministic_resource_id_from_source(
        dataset="dataset",
        resource_type="target",
        source_identity="cafe\u0301",
    )

    assert nfc != decomposed


@pytest.mark.parametrize(
    "key",
    [
        "é",
        "咖",
        "😀",
        "\uE000",
        "Uppercase",
        "with space",
        "1starts_with_digit",
    ],
)
def test_composite_source_identity_rejects_invalid_structural_keys(
    key,
):
    """Composite keys must use the canonical ASCII structural grammar."""

    with pytest.raises(ValueError):
        canonical_generation_name(
            dataset="dataset",
            resource_type="target",
            source_identity={
                key: "value",
            },
        )


@pytest.mark.parametrize(
    "key",
    [
        "a",
        "target",
        "source_id",
        "source-id",
        "source.id",
        "field1",
        "a.b-c_d9",
    ],
)
def test_composite_source_identity_accepts_valid_structural_keys(
    key,
):
    """Valid lowercase ASCII structural keys must remain accepted."""

    canonical = canonical_generation_name(
        dataset="dataset",
        resource_type="target",
        source_identity={
            key: "value",
        },
    )

    assert key in canonical


@pytest.mark.parametrize(
    "source_identity",
    [
        "\ud800",
        "\udfff",
        "before\ud800after",
        {
            "target": "\ud800",
        },
        {
            "target": "\udfff",
        },
        {
            "target": "before\ud800after",
        },
    ],
)
def test_source_identity_rejects_unicode_surrogates(
    source_identity,
):
    """Identity strings must contain Unicode scalar values only."""

    with pytest.raises(ValueError):
        canonical_generation_name(
            dataset="dataset",
            resource_type="target",
            source_identity=source_identity,
        )


def test_dataset_rejects_unicode_surrogate():
    """Dataset identity must contain Unicode scalar values only."""

    with pytest.raises(ValueError):
        canonical_generation_name(
            dataset="dataset\ud800",
            resource_type="target",
            source_identity="123",
        )


def test_resource_type_rejects_unicode_surrogate():
    """Resource type must contain Unicode scalar values only."""

    with pytest.raises(ValueError):
        canonical_generation_name(
            dataset="dataset",
            resource_type="target\ud800",
            source_identity="123",
        )


@pytest.mark.parametrize(
    "source_identity",
    [
        "",
        {},
        [],
        123,
        None,
    ],
)
def test_invalid_source_identity_is_rejected(
    source_identity,
):
    """Invalid source-identity structures must be rejected."""

    with pytest.raises(ValueError):
        canonical_generation_name(
            dataset="dataset",
            resource_type="target",
            source_identity=source_identity,
        )


@pytest.mark.parametrize(
    "source_identity",
    [
        {
            "target": "",
        },
        {
            "target": 123,
        },
        {
            "": "value",
        },
    ],
)
def test_invalid_composite_source_identity_is_rejected(
    source_identity,
):
    """Composite identities require valid non-empty string components."""

    with pytest.raises(ValueError):
        canonical_generation_name(
            dataset="dataset",
            resource_type="target",
            source_identity=source_identity,
        )


def test_empty_dataset_is_rejected():
    """Dataset identity must not be empty."""

    with pytest.raises(ValueError):
        canonical_generation_name(
            dataset="",
            resource_type="target",
            source_identity="123",
        )


def test_empty_resource_type_is_rejected():
    """Resource type must not be empty."""

    with pytest.raises(ValueError):
        canonical_generation_name(
            dataset="dataset",
            resource_type="",
            source_identity="123",
        )


def test_validate_resource_id_accepts_uuid4():
    """Canonical UUIDv4 syntax must be accepted."""

    resource_id = new_resource_id()

    validate_resource_id(
        resource_id
    )


def test_validate_resource_id_accepts_uuid5():
    """Canonical UUIDv5 syntax must be accepted."""

    resource_id = deterministic_resource_id(
        "example"
    )

    validate_resource_id(
        resource_id
    )


def test_validate_resource_id_does_not_restrict_uuid_version():
    """Validation concerns UUID syntax, not producer generation policy."""

    uuid1 = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

    validate_resource_id(
        uuid1
    )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-a-uuid",
        "123",
        "f485e8192af5502a94894554ec11716c",
        "F485E819-2AF5-502A-9489-4554EC11716C",
    ],
)
def test_validate_resource_id_rejects_noncanonical_values(
    value,
):
    """Only canonical lowercase UUID textual syntax is accepted."""

    with pytest.raises(ValueError):
        validate_resource_id(
            value
        )