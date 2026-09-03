"""Evaluate identity stability of the experimental OpenSmell UUID model.

This experiment tests whether deterministic Resource IDs remain stable when
resource metadata changes while remaining isolated across datasets, resource
types, and source identities.

This tool does not modify the normative OpenSmell 0.1 core.
"""

from __future__ import annotations

from dataclasses import dataclass

from opensmell.experimental.identifiers import deterministic_resource_id


@dataclass(frozen=True)
class ExperimentalSourceResource:
    dataset: str
    resource_type: str
    source_id: str
    metadata: dict[str, object]


def generation_name(resource: ExperimentalSourceResource) -> str:
    """Construct the current experimental UUIDv5 generation name."""

    return (
        f"{resource.dataset}:"
        f"{resource.resource_type}:"
        f"{resource.source_id}"
    )


def resource_id(resource: ExperimentalSourceResource) -> str:
    """Generate the experimental deterministic Resource ID."""

    return deterministic_resource_id(generation_name(resource))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"FAILED: {message}")


def test_metadata_stability() -> None:
    print("1. Metadata stability")
    print("-" * 52)

    original = ExperimentalSourceResource(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_038",
        metadata={
            "mouse": "original-value",
            "hemisphere": "L",
        },
    )

    modified = ExperimentalSourceResource(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_038",
        metadata={
            "mouse": "changed-value",
            "hemisphere": "L",
            "new_metadata": "added later",
        },
    )

    original_id = resource_id(original)
    modified_id = resource_id(modified)

    print(f"Original UUID : {original_id}")
    print(f"Modified UUID : {modified_id}")

    require(
        original_id == modified_id,
        "metadata changes altered Resource ID",
    )

    print("Metadata changed, identity preserved: YES")


def test_dataset_isolation() -> None:
    print()
    print("2. Dataset isolation")
    print("-" * 52)

    burton = ExperimentalSourceResource(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_038",
        metadata={},
    )

    unrelated_dataset = ExperimentalSourceResource(
        dataset="example_other_dataset",
        resource_type="target",
        source_id="113L_038",
        metadata={},
    )

    burton_id = resource_id(burton)
    other_id = resource_id(unrelated_dataset)

    print(f"Burton UUID : {burton_id}")
    print(f"Other UUID  : {other_id}")

    require(
        burton_id != other_id,
        "same source ID in different datasets produced same Resource ID",
    )

    print("Same source ID, different dataset, different UUID: YES")


def test_resource_type_isolation() -> None:
    print()
    print("3. Resource type isolation")
    print("-" * 52)

    target = ExperimentalSourceResource(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_038",
        metadata={},
    )

    stimulus = ExperimentalSourceResource(
        dataset="burton_2022",
        resource_type="stimulus",
        source_id="113L_038",
        metadata={},
    )

    target_id = resource_id(target)
    stimulus_id = resource_id(stimulus)

    print(f"Target UUID   : {target_id}")
    print(f"Stimulus UUID : {stimulus_id}")

    require(
        target_id != stimulus_id,
        "same source ID across resource types produced same Resource ID",
    )

    print("Same source ID, different resource type, different UUID: YES")


def test_source_identity_isolation() -> None:
    print()
    print("4. Source identity isolation")
    print("-" * 52)

    first = ExperimentalSourceResource(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_038",
        metadata={},
    )

    second = ExperimentalSourceResource(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_039",
        metadata={},
    )

    first_id = resource_id(first)
    second_id = resource_id(second)

    print(f"113L_038 UUID : {first_id}")
    print(f"113L_039 UUID : {second_id}")

    require(
        first_id != second_id,
        "different source IDs produced same Resource ID",
    )

    print("Different source ID, different UUID: YES")


def test_dataset_revision_policy() -> None:
    print()
    print("5. Dataset revision policy")
    print("-" * 52)

    version_1 = ExperimentalSourceResource(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_038",
        metadata={
            "dataset_version": "1",
        },
    )

    version_2 = ExperimentalSourceResource(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_038",
        metadata={
            "dataset_version": "2",
        },
    )

    version_1_id = resource_id(version_1)
    version_2_id = resource_id(version_2)

    print(f"Version 1 UUID : {version_1_id}")
    print(f"Version 2 UUID : {version_2_id}")

    require(
        version_1_id == version_2_id,
        "dataset metadata revision altered Resource ID",
    )

    print("Dataset revision metadata does not alter identity: YES")


def test_exact_generation_name_stability() -> None:
    print()
    print("6. Generation-name determinism")
    print("-" * 52)

    resource = ExperimentalSourceResource(
        dataset="burton_2022",
        resource_type="target",
        source_id="113L_038",
        metadata={},
    )

    name = generation_name(resource)

    first = deterministic_resource_id(name)
    second = deterministic_resource_id(name)

    print(f"Generation name : {name}")
    print(f"First UUID      : {first}")
    print(f"Second UUID     : {second}")

    require(
        first == second,
        "identical generation names produced different Resource IDs",
    )

    print("Identical generation input, identical UUID: YES")


def main() -> None:
    print("OpenSmell RFC-0006 identity stability experiment")
    print("=" * 52)

    test_metadata_stability()
    test_dataset_isolation()
    test_resource_type_isolation()
    test_source_identity_isolation()
    test_dataset_revision_policy()
    test_exact_generation_name_stability()

    print()
    print("Result")
    print("=" * 52)
    print("SUCCESS")
    print()
    print(
        "The current experimental generation model separates "
        "resource identity from mutable metadata while isolating "
        "datasets, resource types, and source identities."
    )


if __name__ == "__main__":
    main()