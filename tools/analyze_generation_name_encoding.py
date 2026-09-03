"""Evaluate canonical UUIDv5 generation-name encoding for OpenSmell.

This experiment compares:

1. the current colon-concatenated generation name;
2. a canonical JSON generation name.

Nothing in this module modifies the normative OpenSmell 0.1 core.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from opensmell.experimental.identifiers import deterministic_resource_id


@dataclass(frozen=True)
class IdentityComponents:
    dataset: str
    resource_type: str
    source_id: str


def legacy_generation_name(identity: IdentityComponents) -> str:
    """Current experimental colon-separated encoding."""

    return (
        f"{identity.dataset}:"
        f"{identity.resource_type}:"
        f"{identity.source_id}"
    )


def canonical_generation_name(identity: IdentityComponents) -> str:
    """Encode identity components as deterministic canonical JSON.

    Rules used by this experiment:

    - UTF-8 compatible Unicode text;
    - fixed field names;
    - lexicographically sorted object keys;
    - no insignificant whitespace;
    - source strings preserved exactly;
    - JSON escaping performed by the standard JSON serializer.
    """

    payload = {
        "dataset": identity.dataset,
        "resource_type": identity.resource_type,
        "source_id": identity.source_id,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"FAILED: {message}")


def test_legacy_ambiguity() -> None:
    print("1. Legacy delimiter ambiguity")
    print("-" * 60)

    first = IdentityComponents(
        dataset="abc:def",
        resource_type="target",
        source_id="123",
    )

    second = IdentityComponents(
        dataset="abc",
        resource_type="def:target",
        source_id="123",
    )

    first_name = legacy_generation_name(first)
    second_name = legacy_generation_name(second)

    print(f"Identity A : {first}")
    print(f"Identity B : {second}")
    print()
    print(f"Legacy A   : {first_name}")
    print(f"Legacy B   : {second_name}")

    require(
        first != second,
        "test identities unexpectedly equal",
    )

    require(
        first_name == second_name,
        "legacy ambiguity could not be reproduced",
    )

    first_uuid = deterministic_resource_id(first_name)
    second_uuid = deterministic_resource_id(second_name)

    print()
    print(f"UUID A     : {first_uuid}")
    print(f"UUID B     : {second_uuid}")

    require(
        first_uuid == second_uuid,
        "identical legacy generation names produced different UUIDs",
    )

    print()
    print("Different identities collapse to same generation name: YES")
    print("Different identities therefore produce same UUIDv5: YES")


def test_canonical_json_separation() -> None:
    print()
    print("2. Canonical JSON separation")
    print("-" * 60)

    first = IdentityComponents(
        dataset="abc:def",
        resource_type="target",
        source_id="123",
    )

    second = IdentityComponents(
        dataset="abc",
        resource_type="def:target",
        source_id="123",
    )

    first_name = canonical_generation_name(first)
    second_name = canonical_generation_name(second)

    print(f"Canonical A : {first_name}")
    print(f"Canonical B : {second_name}")

    require(
        first_name != second_name,
        "canonical encoding collapsed different identities",
    )

    first_uuid = deterministic_resource_id(first_name)
    second_uuid = deterministic_resource_id(second_name)

    print()
    print(f"UUID A      : {first_uuid}")
    print(f"UUID B      : {second_uuid}")

    require(
        first_uuid != second_uuid,
        "different canonical identities produced same UUID",
    )

    print()
    print("Different identities remain structurally distinct: YES")
    print("Different identities produce different UUIDv5 values: YES")


def test_canonical_determinism() -> None:
    print()
    print("3. Canonical serialization determinism")
    print("-" * 60)

    identity = IdentityComponents(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_038",
    )

    first_name = canonical_generation_name(identity)
    second_name = canonical_generation_name(identity)

    first_uuid = deterministic_resource_id(first_name)
    second_uuid = deterministic_resource_id(second_name)

    print(f"Generation name : {first_name}")
    print(f"First UUID      : {first_uuid}")
    print(f"Second UUID     : {second_uuid}")

    require(
        first_name == second_name,
        "same identity produced different canonical serialization",
    )

    require(
        first_uuid == second_uuid,
        "same canonical identity produced different UUIDs",
    )

    print()
    print("Canonical serialization stable: YES")
    print("UUIDv5 generation stable: YES")


def test_special_characters() -> None:
    print()
    print("4. Special-character preservation")
    print("-" * 60)

    identities = [
        IdentityComponents(
            dataset="dataset:alpha",
            resource_type="target",
            source_id="abc:def",
        ),
        IdentityComponents(
            dataset="dataset",
            resource_type="alpha:target",
            source_id="abc:def",
        ),
        IdentityComponents(
            dataset="dataset",
            resource_type="target",
            source_id='abc"def',
        ),
        IdentityComponents(
            dataset="dataset",
            resource_type="target",
            source_id="abc\\def",
        ),
        IdentityComponents(
            dataset="dataset",
            resource_type="target",
            source_id="café",
        ),
        IdentityComponents(
            dataset="dataset",
            resource_type="target",
            source_id="咖啡",
        ),
    ]

    names = [
        canonical_generation_name(identity)
        for identity in identities
    ]

    uuids = [
        deterministic_resource_id(name)
        for name in names
    ]

    for identity, name, resource_uuid in zip(
        identities,
        names,
        uuids,
    ):
        print()
        print(f"Identity : {identity}")
        print(f"Encoded  : {name}")
        print(f"UUID     : {resource_uuid}")

    require(
        len(names) == len(set(names)),
        "special-character identities produced duplicate generation names",
    )

    require(
        len(uuids) == len(set(uuids)),
        "special-character identities produced duplicate UUIDs",
    )

    print()
    print("All canonical names unique: YES")
    print("All generated UUIDs unique: YES")


def test_field_boundary_preservation() -> None:
    print()
    print("5. Field-boundary preservation")
    print("-" * 60)

    cases = [
        (
            IdentityComponents("a:b", "c", "d"),
            IdentityComponents("a", "b:c", "d"),
        ),
        (
            IdentityComponents("a", "b:c", "d"),
            IdentityComponents("a", "b", "c:d"),
        ),
        (
            IdentityComponents("a:b:c", "d", "e"),
            IdentityComponents("a", "b:c:d", "e"),
        ),
    ]

    for index, (first, second) in enumerate(cases, start=1):
        legacy_a = legacy_generation_name(first)
        legacy_b = legacy_generation_name(second)

        canonical_a = canonical_generation_name(first)
        canonical_b = canonical_generation_name(second)

        print()
        print(f"Case {index}")
        print(f"Legacy A    : {legacy_a}")
        print(f"Legacy B    : {legacy_b}")
        print(f"Canonical A : {canonical_a}")
        print(f"Canonical B : {canonical_b}")

        require(
            legacy_a == legacy_b,
            f"legacy ambiguity not reproduced in case {index}",
        )

        require(
            canonical_a != canonical_b,
            f"canonical encoding ambiguous in case {index}",
        )

    print()
    print("Legacy delimiter ambiguities reproduced: YES")
    print("Canonical JSON preserves field boundaries: YES")


def test_metadata_exclusion() -> None:
    print()
    print("6. Metadata exclusion")
    print("-" * 60)

    # Metadata is deliberately absent from IdentityComponents.
    #
    # This makes the identity construction structurally independent
    # from mutable resource metadata.

    identity = IdentityComponents(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_038",
    )

    name = canonical_generation_name(identity)
    resource_uuid = deterministic_resource_id(name)

    print(f"Canonical name : {name}")
    print(f"UUID           : {resource_uuid}")

    require(
        "metadata" not in name,
        "metadata unexpectedly participated in identity encoding",
    )

    print()
    print("Mutable metadata excluded from generation material: YES")


def main() -> None:
    print("OpenSmell RFC-0006 generation-name encoding experiment")
    print("=" * 60)

    test_legacy_ambiguity()
    test_canonical_json_separation()
    test_canonical_determinism()
    test_special_characters()
    test_field_boundary_preservation()
    test_metadata_exclusion()

    print()
    print("Result")
    print("=" * 60)
    print("SUCCESS")
    print()
    print(
        "The delimiter-based generation-name encoding is ambiguous. "
        "Canonical JSON preserves identity-component boundaries and "
        "provides deterministic generation material for UUIDv5."
    )


if __name__ == "__main__":
    main()