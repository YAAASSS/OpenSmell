"""Interoperability vectors for experimental OpenSmell Resource IDs."""

import pytest

from opensmell.experimental.identifiers import (
    OPENSMELL_EXPERIMENTAL_NAMESPACE,
    canonical_generation_name,
    deterministic_resource_id,
    deterministic_resource_id_from_source,
)


def test_atomic_canonical_name():
    name = canonical_generation_name(
        dataset="burton_2022",
        resource_type="target",
        source_identity="113L_038",
    )

    assert name == (
        '{"dataset":"burton_2022",'
        '"resource_type":"target",'
        '"source_identity":"113L_038"}'
    )


def test_composite_canonical_name():
    name = canonical_generation_name(
        dataset="burton_2022",
        resource_type="observation",
        source_identity={
            "stimulus": "5460048_0",
            "target": "113L_038",
        },
    )

    assert name == (
        '{"dataset":"burton_2022",'
        '"resource_type":"observation",'
        '"source_identity":{'
        '"stimulus":"5460048_0",'
        '"target":"113L_038"'
        '}}'
    )


def test_composite_key_order_does_not_change_identity():
    first = deterministic_resource_id_from_source(
        "burton_2022",
        "observation",
        {
            "stimulus": "5460048_0",
            "target": "113L_038",
        },
    )

    second = deterministic_resource_id_from_source(
        "burton_2022",
        "observation",
        {
            "target": "113L_038",
            "stimulus": "5460048_0",
        },
    )

    assert first == second


def test_composite_field_boundaries_are_preserved():
    first = deterministic_resource_id_from_source(
        "dataset",
        "observation",
        {
            "stimulus": "a|b",
            "target": "c",
        },
    )

    second = deterministic_resource_id_from_source(
        "dataset",
        "observation",
        {
            "stimulus": "a",
            "target": "b|c",
        },
    )

    assert first != second


def test_atomic_and_composite_identity_are_distinct():
    atomic = deterministic_resource_id_from_source(
        "dataset",
        "observation",
        "stimulus=a,target=b",
    )

    composite = deterministic_resource_id_from_source(
        "dataset",
        "observation",
        {
            "stimulus": "a",
            "target": "b",
        },
    )

    assert atomic != composite


def test_unicode_is_preserved():
    name = canonical_generation_name(
        "dataset",
        "target",
        "咖啡",
    )

    assert "咖啡" in name

    assert "\\u" not in name


def test_special_characters_are_escaped_by_json():
    name = canonical_generation_name(
        "dataset",
        "target",
        'abc"def\\ghi',
    )

    assert 'abc\\"def\\\\ghi' in name


def test_generation_is_deterministic():
    first = deterministic_resource_id_from_source(
        "burton_2022",
        "target",
        "113L_038",
    )

    second = deterministic_resource_id_from_source(
        "burton_2022",
        "target",
        "113L_038",
    )

    assert first == second


def test_low_level_and_high_level_generation_agree():
    name = canonical_generation_name(
        "burton_2022",
        "target",
        "113L_038",
    )

    assert deterministic_resource_id(name) == (
        deterministic_resource_id_from_source(
            "burton_2022",
            "target",
            "113L_038",
        )
    )


def test_experimental_namespace_vector():
    assert str(OPENSMELL_EXPERIMENTAL_NAMESPACE) == (
        "7f0f1d72-83c7-4f57-a1f6-4bc43bb26e58"
    )


@pytest.mark.parametrize(
    "dataset,resource_type,source_identity",
    [
        ("", "target", "123"),
        ("dataset", "", "123"),
        ("dataset", "target", ""),
        (None, "target", "123"),
        ("dataset", None, "123"),
        ("dataset", "target", None),
        (123, "target", "123"),
        ("dataset", 123, "123"),
        ("dataset", "target", {}),
        ("dataset", "target", {"": "123"}),
        ("dataset", "target", {"subject": ""}),
        ("dataset", "target", {"subject": 123}),
        ("dataset", "target", ["123"]),
    ],
)
def test_invalid_source_identity_components(
    dataset,
    resource_type,
    source_identity,
):
    with pytest.raises(ValueError):
        deterministic_resource_id_from_source(
            dataset,
            resource_type,
            source_identity,
        )


def test_metadata_is_not_part_of_identity_api():
    first = deterministic_resource_id_from_source(
        "burton_2022",
        "target",
        "113L_038",
    )

    second = deterministic_resource_id_from_source(
        "burton_2022",
        "target",
        "113L_038",
    )

    assert first == second