"""Evaluate the experimental OpenSmell Resource ID model on Burton 2022.

This experiment evaluates the generalized OpenSmell source-identity model
against the complete processed Burton 2022 dataset.

Atomic source identities are used for:

    molecules
    stimuli
    targets

Composite source identities are used for:

    observations

Nothing in this module is part of the normative OpenSmell 0.1 specification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

import pandas as pd

from opensmell.experimental.identifiers import (
    SourceIdentity,
    canonical_generation_name,
    deterministic_resource_id_from_source,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

MOLECULES_PATH = EXAMPLES / "molecules.csv"
STIMULI_PATH = EXAMPLES / "stimuli.csv"
SUBJECTS_PATH = EXAMPLES / "subjects.csv"
BEHAVIOR_PATH = EXAMPLES / "behavior.csv"

DATASET_ID = "burton_2022"


IdentityKey: TypeAlias = str


@dataclass(frozen=True)
class ResourceIdentity:
    """Experimental identity record used only by this analysis."""

    resource_type: str
    source_identity: SourceIdentity
    generation_name: str
    resource_id: str


def require_column(
    df: pd.DataFrame,
    candidates: list[str],
    table: str,
) -> str:
    """Return the first matching column name."""

    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    raise RuntimeError(
        f"Could not find expected column in {table}.\n"
        f"Candidates: {candidates}\n"
        f"Available: {list(df.columns)}"
    )


def normalize_source_value(value: object) -> str:
    """Convert a source identifier to stable text without semantic rewriting."""

    if pd.isna(value):
        raise ValueError("source identifier cannot be missing")

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value)


def source_identity_key(
    source_identity: SourceIdentity,
) -> IdentityKey:
    """Create a comparison key for an atomic or composite source identity.

    This key is used only by this analysis for dictionary/set comparison.

    It is NOT an OpenSmell Resource ID and is NOT UUID generation material.
    """

    if isinstance(source_identity, str):
        return json.dumps(
            source_identity,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    return json.dumps(
        source_identity,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def make_identity(
    resource_type: str,
    source_identity: SourceIdentity,
) -> ResourceIdentity:
    """Create one deterministic experimental OpenSmell identity."""

    generation_name = canonical_generation_name(
        dataset=DATASET_ID,
        resource_type=resource_type,
        source_identity=source_identity,
    )

    resource_id = deterministic_resource_id_from_source(
        dataset=DATASET_ID,
        resource_type=resource_type,
        source_identity=source_identity,
    )

    return ResourceIdentity(
        resource_type=resource_type,
        source_identity=source_identity,
        generation_name=generation_name,
        resource_id=resource_id,
    )


def build_identity_graph() -> dict[str, list[ResourceIdentity]]:
    """Build experimental identities from the Burton processed tables."""

    molecules = pd.read_csv(MOLECULES_PATH)
    stimuli = pd.read_csv(STIMULI_PATH)
    subjects = pd.read_csv(SUBJECTS_PATH)
    behavior = pd.read_csv(BEHAVIOR_PATH)

    molecule_cid = require_column(
        molecules,
        ["CID", "cid"],
        "molecules.csv",
    )

    stimulus_id = require_column(
        stimuli,
        [
            "Stimulus",
            "stimulus",
            "Stimulus ID",
            "stimulus_id",
        ],
        "stimuli.csv",
    )

    subject_id = require_column(
        subjects,
        [
            "Subject",
            "Subject ID",
            "subject",
            "subject_id",
        ],
        "subjects.csv",
    )

    behavior_stimulus = require_column(
        behavior,
        [
            "Stimulus",
            "stimulus",
            "Stimulus ID",
            "stimulus_id",
        ],
        "behavior.csv",
    )

    behavior_subject = require_column(
        behavior,
        [
            "Subject",
            "Subject ID",
            "subject",
            "subject_id",
        ],
        "behavior.csv",
    )

    # ------------------------------------------------------------------
    # Molecules
    # ------------------------------------------------------------------

    molecule_ids = [
        make_identity(
            "molecule",
            normalize_source_value(value),
        )
        for value in molecules[molecule_cid].dropna().unique()
    ]

    # ------------------------------------------------------------------
    # Stimuli
    # ------------------------------------------------------------------

    stimulus_ids = [
        make_identity(
            "stimulus",
            normalize_source_value(value),
        )
        for value in stimuli[stimulus_id].dropna().unique()
    ]

    # ------------------------------------------------------------------
    # Targets
    # ------------------------------------------------------------------

    declared_targets = {
        normalize_source_value(value)
        for value in subjects[subject_id].dropna().unique()
    }

    referenced_targets = {
        normalize_source_value(value)
        for value in behavior[behavior_subject].dropna().unique()
    }

    # Preserve both declared and referenced target identities.
    #
    # A target referenced by behavior but missing from subjects.csv remains
    # identifiable without inventing target metadata.
    all_target_source_ids = (
        declared_targets
        |
        referenced_targets
    )

    target_ids = [
        make_identity(
            "target",
            source_id,
        )
        for source_id in sorted(all_target_source_ids)
    ]

    # ------------------------------------------------------------------
    # Observations
    # ------------------------------------------------------------------

    observation_pairs = (
        behavior[
            [
                behavior_stimulus,
                behavior_subject,
            ]
        ]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )

    observation_ids: list[ResourceIdentity] = []

    for stimulus, target in observation_pairs:
        stimulus_text = normalize_source_value(stimulus)
        target_text = normalize_source_value(target)

        # IMPORTANT:
        #
        # Observation identity is composite.
        #
        # We deliberately DO NOT concatenate values using:
        #
        #     stimulus|target
        #
        # because delimiter-based identity construction can be ambiguous.
        #
        # Field boundaries are preserved structurally.
        source_identity: SourceIdentity = {
            "stimulus": stimulus_text,
            "target": target_text,
        }

        observation_ids.append(
            make_identity(
                "observation",
                source_identity,
            )
        )

    return {
        "molecule": molecule_ids,
        "stimulus": stimulus_ids,
        "target": target_ids,
        "observation": observation_ids,
    }


def flatten_graph(
    graph: dict[str, list[ResourceIdentity]],
) -> list[ResourceIdentity]:
    """Flatten all resource categories into one list."""

    return [
        identity
        for identities in graph.values()
        for identity in identities
    ]


def resource_mapping(
    graph: dict[str, list[ResourceIdentity]],
) -> dict[tuple[str, IdentityKey], str]:
    """Map source identity to generated Resource ID."""

    return {
        (
            item.resource_type,
            source_identity_key(item.source_identity),
        ): item.resource_id
        for item in flatten_graph(graph)
    }


def generation_name_mapping(
    graph: dict[str, list[ResourceIdentity]],
) -> dict[tuple[str, IdentityKey], str]:
    """Map source identity to canonical generation name."""

    return {
        (
            item.resource_type,
            source_identity_key(item.source_identity),
        ): item.generation_name
        for item in flatten_graph(graph)
    }


def check_determinism() -> None:
    """Build the graph twice and require identical Resource IDs."""

    first = build_identity_graph()
    second = build_identity_graph()

    if resource_mapping(first) != resource_mapping(second):
        raise RuntimeError(
            "FAILED: independent imports produced different Resource IDs"
        )


def check_generation_name_determinism() -> None:
    """Require identical canonical generation names across imports."""

    first = build_identity_graph()
    second = build_identity_graph()

    if generation_name_mapping(first) != generation_name_mapping(second):
        raise RuntimeError(
            "FAILED: independent imports produced different canonical "
            "generation names"
        )


def check_uuid_collisions(
    graph: dict[str, list[ResourceIdentity]],
) -> list[tuple[str, list[ResourceIdentity]]]:
    """Find UUIDs assigned to distinct source resources."""

    resources = flatten_graph(graph)

    by_uuid: dict[str, list[ResourceIdentity]] = {}

    for resource in resources:
        by_uuid.setdefault(
            resource.resource_id,
            [],
        ).append(resource)

    collisions = []

    for resource_id, identities in by_uuid.items():
        unique_sources = {
            (
                item.resource_type,
                source_identity_key(item.source_identity),
            )
            for item in identities
        }

        if len(unique_sources) > 1:
            collisions.append(
                (
                    resource_id,
                    identities,
                )
            )

    return collisions


def check_generation_name_collisions(
    graph: dict[str, list[ResourceIdentity]],
) -> list[tuple[str, list[ResourceIdentity]]]:
    """Find canonical names assigned to distinct resources."""

    resources = flatten_graph(graph)

    by_name: dict[str, list[ResourceIdentity]] = {}

    for resource in resources:
        by_name.setdefault(
            resource.generation_name,
            [],
        ).append(resource)

    collisions = []

    for generation_name, identities in by_name.items():
        unique_sources = {
            (
                item.resource_type,
                source_identity_key(item.source_identity),
            )
            for item in identities
        }

        if len(unique_sources) > 1:
            collisions.append(
                (
                    generation_name,
                    identities,
                )
            )

    return collisions


def analyze_target_sets() -> tuple[
    set[str],
    set[str],
    set[str],
    set[str],
]:
    """Compare declared Burton targets with behavior references."""

    subjects = pd.read_csv(SUBJECTS_PATH)
    behavior = pd.read_csv(BEHAVIOR_PATH)

    subject_id = require_column(
        subjects,
        [
            "Subject",
            "Subject ID",
            "subject",
            "subject_id",
        ],
        "subjects.csv",
    )

    behavior_subject = require_column(
        behavior,
        [
            "Subject",
            "Subject ID",
            "subject",
            "subject_id",
        ],
        "behavior.csv",
    )

    declared = {
        normalize_source_value(value)
        for value in subjects[subject_id].dropna().unique()
    }

    referenced = {
        normalize_source_value(value)
        for value in behavior[behavior_subject].dropna().unique()
    }

    unresolved = referenced - declared
    unreferenced = declared - referenced

    return (
        declared,
        referenced,
        unresolved,
        unreferenced,
    )


def check_merge_behavior(
    graph: dict[str, list[ResourceIdentity]],
) -> None:
    """Simulate merging independently generated equivalent graphs."""

    second_graph = build_identity_graph()

    first_map = resource_mapping(graph)
    second_map = resource_mapping(second_graph)

    if first_map != second_map:
        raise RuntimeError(
            "FAILED: equivalent independently generated graphs do not merge "
            "onto the same Resource IDs"
        )

    merged_by_uuid: dict[
        str,
        set[tuple[str, IdentityKey]],
    ] = {}

    for item in (
        flatten_graph(graph)
        +
        flatten_graph(second_graph)
    ):
        merged_by_uuid.setdefault(
            item.resource_id,
            set(),
        ).add(
            (
                item.resource_type,
                source_identity_key(item.source_identity),
            )
        )

    ambiguous = {
        resource_id: identities
        for resource_id, identities in merged_by_uuid.items()
        if len(identities) > 1
    }

    if ambiguous:
        raise RuntimeError(
            f"FAILED: graph merge produced "
            f"{len(ambiguous)} ambiguous UUIDs"
        )


def check_source_identity_preservation(
    graph: dict[str, list[ResourceIdentity]],
) -> bool:
    """Require every resource to retain source identity."""

    for item in flatten_graph(graph):
        if isinstance(item.source_identity, str):
            if not item.source_identity:
                return False

        elif isinstance(item.source_identity, dict):
            if not item.source_identity:
                return False

        else:
            return False

    return True


def check_observation_identities(
    graph: dict[str, list[ResourceIdentity]],
) -> None:
    """Require every Burton observation to use composite identity."""

    observations = graph["observation"]

    for observation in observations:
        identity = observation.source_identity

        if not isinstance(identity, dict):
            raise RuntimeError(
                "FAILED: observation uses atomic source identity"
            )

        if set(identity) != {
            "stimulus",
            "target",
        }:
            raise RuntimeError(
                "FAILED: observation source identity does not contain "
                "exactly stimulus and target"
            )


def show_target_example(
    graph: dict[str, list[ResourceIdentity]],
    source_id: str,
) -> None:
    """Print one atomic target identity example."""

    for identity in graph["target"]:
        if identity.source_identity == source_id:
            print(f"Source identity : {identity.source_identity}")
            print(f"Resource type   : {identity.resource_type}")
            print(f"Generation name : {identity.generation_name}")
            print(f"Resource UUID   : {identity.resource_id}")
            return


def show_observation_example(
    graph: dict[str, list[ResourceIdentity]],
) -> None:
    """Print one composite observation identity example."""

    observations = graph["observation"]

    if not observations:
        print("No observations available.")
        return

    identity = observations[0]

    print(
        "Source identity : "
        + json.dumps(
            identity.source_identity,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )

    print(
        f"Resource type   : {identity.resource_type}"
    )

    print(
        f"Generation name : {identity.generation_name}"
    )

    print(
        f"Resource UUID   : {identity.resource_id}"
    )


def main() -> None:
    print(
        "OpenSmell RFC-0006 Burton structured identity experiment"
    )
    print("=" * 64)

    graph = build_identity_graph()

    for resource_type, identities in graph.items():
        print(
            f"{resource_type.capitalize():<20}: "
            f"{len(identities):>8,}"
        )

    resources = flatten_graph(graph)

    unique_uuids = {
        item.resource_id
        for item in resources
    }

    unique_generation_names = {
        item.generation_name
        for item in resources
    }

    print("-" * 64)

    print(
        f"{'Total resources':<20}: "
        f"{len(resources):>8,}"
    )

    print(
        f"{'Unique UUIDs':<20}: "
        f"{len(unique_uuids):>8,}"
    )

    print(
        f"{'Unique names':<20}: "
        f"{len(unique_generation_names):>8,}"
    )

    uuid_collisions = check_uuid_collisions(
        graph
    )

    name_collisions = check_generation_name_collisions(
        graph
    )

    print(
        f"{'UUID collisions':<20}: "
        f"{len(uuid_collisions):>8,}"
    )

    print(
        f"{'Name collisions':<20}: "
        f"{len(name_collisions):>8,}"
    )

    # --------------------------------------------------------------
    # Structured observations
    # --------------------------------------------------------------

    print()
    print("Structured observation identity")
    print("-" * 64)

    check_observation_identities(graph)

    print(
        "All observations use composite source identity: YES"
    )

    print(
        "Observation identity fields: stimulus + target"
    )

    # --------------------------------------------------------------
    # Canonical generation
    # --------------------------------------------------------------

    print()
    print("Canonical generation")
    print("-" * 64)

    check_generation_name_determinism()

    print(
        "Independent canonical generation names identical: YES"
    )

    # --------------------------------------------------------------
    # UUID determinism
    # --------------------------------------------------------------

    print()
    print("UUID determinism")
    print("-" * 64)

    check_determinism()

    print(
        "Independent import #1 == import #2: YES"
    )

    # --------------------------------------------------------------
    # Merge
    # --------------------------------------------------------------

    print()
    print("Graph merge")
    print("-" * 64)

    check_merge_behavior(graph)

    print(
        "Equivalent graphs merge without ambiguity: YES"
    )

    # --------------------------------------------------------------
    # Targets
    # --------------------------------------------------------------

    print()
    print("Target references")
    print("-" * 64)

    (
        declared,
        referenced,
        unresolved,
        unreferenced,
    ) = analyze_target_sets()

    print(
        f"Declared targets    : {len(declared):,}"
    )

    print(
        f"Referenced targets  : {len(referenced):,}"
    )

    print(
        f"Unresolved targets  : {len(unresolved):,}"
    )

    print(
        f"Unreferenced targets: {len(unreferenced):,}"
    )

    if unresolved:
        print()
        print(
            "Unresolved source target identifiers:"
        )

        for source_id in sorted(unresolved):
            resource = make_identity(
                "target",
                source_id,
            )

            print(
                f"  {source_id:<20} -> "
                f"{resource.resource_id}"
            )

    if unreferenced:
        print()
        print(
            "Declared but unreferenced source target identifiers:"
        )

        for source_id in sorted(unreferenced):
            resource = make_identity(
                "target",
                source_id,
            )

            print(
                f"  {source_id:<20} -> "
                f"{resource.resource_id}"
            )

    # --------------------------------------------------------------
    # Preservation
    # --------------------------------------------------------------

    print()
    print("Source identity preservation")
    print("-" * 64)

    preserved = check_source_identity_preservation(
        graph
    )

    print(
        "Every resource retains source identity: "
        f"{'YES' if preserved else 'NO'}"
    )

    # --------------------------------------------------------------
    # Examples
    # --------------------------------------------------------------

    print()
    print("Atomic identity example")
    print("-" * 64)

    show_target_example(
        graph,
        "113L_038",
    )

    print()
    print("Composite identity example")
    print("-" * 64)

    show_observation_example(
        graph
    )

    # --------------------------------------------------------------
    # Result
    # --------------------------------------------------------------

    print()
    print("Result")
    print("=" * 64)

    if name_collisions:
        print("FAILED")
        print()
        print(
            "Canonical generation-name collisions:"
        )

        for generation_name, identities in name_collisions:
            print(generation_name)

            for identity in identities:
                print(
                    f"  {identity.resource_type}: "
                    f"{source_identity_key(identity.source_identity)}"
                )

        raise SystemExit(1)

    if uuid_collisions:
        print("FAILED")
        print()
        print("UUID collisions:")

        for resource_id, identities in uuid_collisions:
            print(resource_id)

            for identity in identities:
                print(
                    f"  {identity.resource_type}: "
                    f"{source_identity_key(identity.source_identity)}"
                )

        raise SystemExit(1)

    if not preserved:
        print(
            "FAILED: source identity was lost"
        )
        raise SystemExit(1)

    if len(unique_generation_names) != len(resources):
        print(
            "FAILED: generation-name count does not match "
            "resource count"
        )
        raise SystemExit(1)

    if len(unique_uuids) != len(resources):
        print(
            "FAILED: UUID count does not match resource count"
        )
        raise SystemExit(1)

    print("SUCCESS")
    print()

    print(
        "The structured experimental Resource ID model preserved "
        "all Burton identities without observed generation-name "
        "or UUID collisions."
    )

    print(
        "Atomic and composite source identities were handled by "
        "the same canonical UUIDv5 generation pipeline."
    )


if __name__ == "__main__":
    main()