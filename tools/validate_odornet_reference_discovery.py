"""Validate structural reference discovery on the complete OdorNet graph.

This experiment reuses the existing OdorNet Molecule + Annotation mapping from
``validate_odornet_annotation_resources.py`` and tests the experimental
structural reference discovery layer on the resulting RFC-0008
GenericResourceGraph.

Each OdorNet row becomes:

- one Molecule resource; and
- one Annotation resource whose subject references that Molecule.

The experiment expects exactly one structural graph reference per Annotation:

    Annotation --subject--> Molecule

The twelve semantic annotation states stored inside each Annotation payload are
scheme-defined data and MUST NOT be interpreted as structural graph references.

For the complete OdorNet dataset this means:

- 8,892 Molecule resources;
- 8,892 Annotation resources;
- 17,784 total graph resources;
- 106,704 semantic annotation states;
- exactly 8,892 discovered structural references;
- exactly 8,892 resolved structural references;
- zero unresolved structural references;
- zero false structural references.

This is an experimental validation tool. It does not define a normative
OpenSmell specification.
"""

from __future__ import annotations

import csv
from pathlib import Path
from time import perf_counter

from opensmell.experimental.annotation import Annotation
from opensmell.experimental.generic_graph import GenericResourceGraph
from opensmell.experimental.molecule import Molecule
from opensmell.experimental.reference_discovery import (
    DiscoveredReference,
    ReferenceIndex,
    build_reference_index,
)

from validate_odornet_annotation_resources import (
    DATASET_PATH,
    EXPECTED_ANNOTATION_COUNT,
    EXPECTED_ROW_COUNT,
    annotation_from_odornet_record,
    annotation_states,
    molecule_from_odornet_record,
    validate_dataset_header,
)


EXPECTED_MOLECULE_COUNT = EXPECTED_ROW_COUNT
EXPECTED_RESOURCE_COUNT = EXPECTED_ROW_COUNT * 2
EXPECTED_STRUCTURAL_REFERENCE_COUNT = EXPECTED_ROW_COUNT


def require_dataset() -> Path:
    """Return the OdorNet dataset path or terminate clearly."""

    if not DATASET_PATH.exists():
        raise SystemExit(
            f"Dataset not found: {DATASET_PATH}"
        )

    return DATASET_PATH


def build_odornet_graph() -> tuple[
    GenericResourceGraph,
    list[Molecule],
    list[Annotation],
    dict[str, str],
]:
    """Build the complete Molecule + Annotation OdorNet graph."""

    dataset_path = require_dataset()

    molecules: list[Molecule] = []
    annotations: list[Annotation] = []

    expected_subjects: dict[str, str] = {}

    semantic_state_count = 0

    with dataset_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(
            csv_file
        )

        validate_dataset_header(
            reader.fieldnames
        )

        print(
            "Dataset header validated."
        )

        for dataset_index, record in enumerate(
            reader,
            start=1,
        ):
            row_number = (
                dataset_index + 1
            )

            molecule_id = (
                f"odornet-molecule-"
                f"{dataset_index}"
            )

            annotation_id = (
                f"odornet-annotation-"
                f"{dataset_index}"
            )

            molecule = (
                molecule_from_odornet_record(
                    record,
                    resource_id=molecule_id,
                    row_number=row_number,
                )
            )

            annotation = (
                annotation_from_odornet_record(
                    record,
                    resource_id=annotation_id,
                    molecule_resource_id=molecule_id,
                    row_number=row_number,
                )
            )

            states = annotation_states(
                annotation
            )

            semantic_state_count += len(
                states
            )

            molecules.append(
                molecule
            )

            annotations.append(
                annotation
            )

            expected_subjects[
                annotation_id
            ] = molecule_id

            if (
                dataset_index % 1000
                == 0
            ):
                print(
                    "Created "
                    f"{dataset_index:,} "
                    "Molecule + Annotation pairs"
                )

    if len(molecules) != EXPECTED_MOLECULE_COUNT:
        raise SystemExit(
            "Unexpected Molecule count: "
            f"{len(molecules):,}; "
            f"expected {EXPECTED_MOLECULE_COUNT:,}"
        )

    if len(annotations) != EXPECTED_ROW_COUNT:
        raise SystemExit(
            "Unexpected Annotation count: "
            f"{len(annotations):,}; "
            f"expected {EXPECTED_ROW_COUNT:,}"
        )

    if semantic_state_count != EXPECTED_ANNOTATION_COUNT:
        raise SystemExit(
            "Unexpected semantic annotation state count: "
            f"{semantic_state_count:,}; "
            f"expected {EXPECTED_ANNOTATION_COUNT:,}"
        )

    graph = GenericResourceGraph(
        resources=[
            *molecules,
            *annotations,
        ]
    )

    if len(graph.resources) != EXPECTED_RESOURCE_COUNT:
        raise SystemExit(
            "Unexpected graph resource count: "
            f"{len(graph.resources):,}; "
            f"expected {EXPECTED_RESOURCE_COUNT:,}"
        )

    return (
        graph,
        molecules,
        annotations,
        expected_subjects,
    )


def validate_discovered_edge(
    graph: GenericResourceGraph,
    discovered: DiscoveredReference,
    expected_subjects: dict[str, str],
) -> str | None:
    """Validate one discovered OdorNet structural reference.

    Returns an error description when the edge is invalid, otherwise None.
    """

    expected_target = expected_subjects.get(
        discovered.source_id
    )

    if expected_target is None:
        return (
            f"{discovered.source_id}: "
            "discovered reference originates from a resource "
            "that is not an expected Annotation"
        )

    if discovered.target_id != expected_target:
        return (
            f"{discovered.source_id}: "
            f"expected target {expected_target!r}, "
            f"actual {discovered.target_id!r}"
        )

    source = graph.get(
        discovered.source_id
    )

    if not isinstance(
        source,
        Annotation,
    ):
        return (
            f"{discovered.source_id}: "
            "discovered source is not an Annotation"
        )

    if discovered.reference is not source.subject:
        return (
            f"{discovered.source_id}: "
            "discovered reference is not the Annotation "
            "subject Reference object"
        )

    target = graph.resolve(
        discovered.reference
    )

    if not isinstance(
        target,
        Molecule,
    ):
        return (
            f"{discovered.source_id}: "
            f"target {discovered.target_id!r} "
            "did not resolve to a Molecule"
        )

    if target.id != expected_target:
        return (
            f"{discovered.source_id}: "
            f"resolved target is {target.id!r}; "
            f"expected {expected_target!r}"
        )

    return None


def main() -> None:
    """Run indexed OdorNet structural reference discovery validation."""

    total_start = perf_counter()

    dataset_path = require_dataset()

    print(
        f"Dataset: {dataset_path}"
    )

    graph_start = perf_counter()

    (
        graph,
        molecules,
        annotations,
        expected_subjects,
    ) = build_odornet_graph()

    graph_seconds = (
        perf_counter()
        - graph_start
    )

    print()
    print(
        "Building structural ReferenceIndex..."
    )

    index_start = perf_counter()

    index: ReferenceIndex = build_reference_index(
        graph
    )

    index_seconds = (
        perf_counter()
        - index_start
    )

    discovered = index.references()
    resolved = index.resolved()
    unresolved = index.unresolved()

    print(
        "Validating discovered edges..."
    )

    edge_validation_start = perf_counter()

    edge_errors: list[str] = []
    seen_sources: set[str] = set()

    for edge in discovered:
        error = validate_discovered_edge(
            graph,
            edge,
            expected_subjects,
        )

        if error is not None:
            edge_errors.append(
                error
            )

        if edge.source_id in seen_sources:
            edge_errors.append(
                f"{edge.source_id}: "
                "more than one structural reference "
                "was discovered for this Annotation"
            )

        seen_sources.add(
            edge.source_id
        )

    missing_annotation_edges = sorted(
        set(expected_subjects)
        - seen_sources
    )

    unexpected_edge_sources = sorted(
        seen_sources
        - set(expected_subjects)
    )

    edge_validation_seconds = (
        perf_counter()
        - edge_validation_start
    )

    print(
        "Validating indexed outgoing reference queries..."
    )

    outgoing_start = perf_counter()

    outgoing_query_errors: list[str] = []

    for annotation in annotations:
        outgoing = index.references_from(
            annotation.id
        )

        if len(outgoing) != 1:
            outgoing_query_errors.append(
                f"{annotation.id}: "
                f"expected 1 outgoing reference, "
                f"found {len(outgoing)}"
            )
            continue

        edge = outgoing[0]

        expected_target = expected_subjects[
            annotation.id
        ]

        if edge.target_id != expected_target:
            outgoing_query_errors.append(
                f"{annotation.id}: "
                f"expected outgoing target "
                f"{expected_target!r}, "
                f"actual {edge.target_id!r}"
            )

    annotation_outgoing_seconds = (
        perf_counter()
        - outgoing_start
    )

    molecule_outgoing_start = perf_counter()

    molecule_outgoing_errors: list[str] = []

    for molecule in molecules:
        outgoing = index.references_from(
            molecule.id
        )

        if outgoing:
            molecule_outgoing_errors.append(
                f"{molecule.id}: "
                f"expected 0 outgoing references, "
                f"found {len(outgoing)}"
            )

    molecule_outgoing_seconds = (
        perf_counter()
        - molecule_outgoing_start
    )

    print(
        "Validating indexed incoming reference queries..."
    )

    incoming_start = perf_counter()

    incoming_query_errors: list[str] = []

    for molecule in molecules:
        incoming = index.references_to(
            molecule.id
        )

        if len(incoming) != 1:
            incoming_query_errors.append(
                f"{molecule.id}: "
                f"expected 1 incoming reference, "
                f"found {len(incoming)}"
            )
            continue

        edge = incoming[0]

        expected_annotation_id = (
            "odornet-annotation-"
            + molecule.id.removeprefix(
                "odornet-molecule-"
            )
        )

        if edge.source_id != expected_annotation_id:
            incoming_query_errors.append(
                f"{molecule.id}: "
                f"expected incoming source "
                f"{expected_annotation_id!r}, "
                f"actual {edge.source_id!r}"
            )

    molecule_incoming_seconds = (
        perf_counter()
        - incoming_start
    )

    annotation_incoming_start = perf_counter()

    annotation_incoming_count = 0

    for annotation in annotations:
        annotation_incoming_count += len(
            index.references_to(
                annotation.id
            )
        )

    annotation_incoming_seconds = (
        perf_counter()
        - annotation_incoming_start
    )

    unique_edge_pairs = {
        (
            edge.source_id,
            edge.target_id,
        )
        for edge in discovered
    }

    resolved_pairs = {
        (
            edge.source_id,
            edge.target_id,
        )
        for edge in resolved
    }

    unresolved_pairs = {
        (
            edge.source_id,
            edge.target_id,
        )
        for edge in unresolved
    }

    semantic_state_count = sum(
        len(
            annotation_states(
                annotation
            )
        )
        for annotation in annotations
    )

    false_edge_count = (
        len(edge_errors)
        + len(unexpected_edge_sources)
        + len(outgoing_query_errors)
        + len(molecule_outgoing_errors)
        + len(incoming_query_errors)
        + annotation_incoming_count
    )

    total_seconds = (
        perf_counter()
        - total_start
    )

    print()
    print(
        "ODORNET INDEXED STRUCTURAL REFERENCE DISCOVERY VALIDATION"
    )
    print(
        "---------------------------------------------------------"
    )

    print(
        f"Dataset rows:                  "
        f"{len(molecules):,}"
    )
    print(
        f"Molecule resources:            "
        f"{len(molecules):,}"
    )
    print(
        f"Annotation resources:          "
        f"{len(annotations):,}"
    )
    print(
        f"Total graph resources:         "
        f"{len(graph.resources):,}"
    )
    print(
        f"Semantic annotation states:    "
        f"{semantic_state_count:,}"
    )
    print(
        f"Discovered references:         "
        f"{len(discovered):,}"
    )
    print(
        f"Unique source-target pairs:    "
        f"{len(unique_edge_pairs):,}"
    )
    print(
        f"Resolved references:           "
        f"{len(resolved):,}"
    )
    print(
        f"Unresolved references:         "
        f"{len(unresolved):,}"
    )
    print(
        f"Annotation sources discovered: "
        f"{len(seen_sources):,}"
    )
    print(
        f"Missing Annotation edges:      "
        f"{len(missing_annotation_edges):,}"
    )
    print(
        f"Unexpected edge sources:       "
        f"{len(unexpected_edge_sources):,}"
    )
    print(
        f"Molecule outgoing errors:      "
        f"{len(molecule_outgoing_errors):,}"
    )
    print(
        f"Annotation incoming edges:     "
        f"{annotation_incoming_count:,}"
    )
    print(
        f"False-edge/error count:        "
        f"{false_edge_count:,}"
    )

    print()
    print(
        "PERFORMANCE"
    )
    print(
        "---------------------------------------------------------"
    )
    print(
        f"Graph construction:            "
        f"{graph_seconds:.6f} s"
    )
    print(
        f"ReferenceIndex construction:   "
        f"{index_seconds:.6f} s"
    )
    print(
        f"Edge validation:               "
        f"{edge_validation_seconds:.6f} s"
    )
    print(
        f"8,892 Annotation outgoing:     "
        f"{annotation_outgoing_seconds:.6f} s"
    )
    print(
        f"8,892 Molecule outgoing:       "
        f"{molecule_outgoing_seconds:.6f} s"
    )
    print(
        f"8,892 Molecule incoming:       "
        f"{molecule_incoming_seconds:.6f} s"
    )
    print(
        f"8,892 Annotation incoming:     "
        f"{annotation_incoming_seconds:.6f} s"
    )
    print(
        f"Total validation runtime:      "
        f"{total_seconds:.6f} s"
    )

    failures = (
        len(index)
        != EXPECTED_STRUCTURAL_REFERENCE_COUNT
        or len(discovered)
        != EXPECTED_STRUCTURAL_REFERENCE_COUNT
        or len(unique_edge_pairs)
        != EXPECTED_STRUCTURAL_REFERENCE_COUNT
        or len(resolved)
        != EXPECTED_STRUCTURAL_REFERENCE_COUNT
        or bool(unresolved)
        or len(seen_sources)
        != EXPECTED_ROW_COUNT
        or bool(missing_annotation_edges)
        or bool(unexpected_edge_sources)
        or bool(edge_errors)
        or bool(outgoing_query_errors)
        or bool(molecule_outgoing_errors)
        or bool(incoming_query_errors)
        or annotation_incoming_count != 0
        or semantic_state_count
        != EXPECTED_ANNOTATION_COUNT
        or resolved_pairs
        != unique_edge_pairs
        or bool(unresolved_pairs)
    )

    if failures:
        print()

        categories = [
            (
                "Edge validation errors",
                edge_errors,
            ),
            (
                "Missing Annotation edges",
                missing_annotation_edges,
            ),
            (
                "Unexpected edge sources",
                unexpected_edge_sources,
            ),
            (
                "Outgoing Annotation query errors",
                outgoing_query_errors,
            ),
            (
                "Molecule outgoing errors",
                molecule_outgoing_errors,
            ),
            (
                "Incoming Molecule query errors",
                incoming_query_errors,
            ),
        ]

        for title, errors in categories:
            if not errors:
                continue

            print(
                f"{title}:"
            )

            for error in errors[:20]:
                print(
                    f"  {error}"
                )

            print()

        if annotation_incoming_count:
            print(
                "Unexpected incoming references to "
                "Annotation resources: "
                f"{annotation_incoming_count:,}"
            )
            print()

        raise SystemExit(1)

    print()
    print(
        "SUCCESS: the indexed structural reference discovery "
        "found exactly one Annotation-to-Molecule relationship "
        "for every OdorNet row, resolved all discovered "
        "references, did not interpret the 106,704 "
        "scheme-defined semantic annotation states as graph "
        "relationships, and served repeated incoming/outgoing "
        "queries without rescanning the graph."
    )


if __name__ == "__main__":
    main()