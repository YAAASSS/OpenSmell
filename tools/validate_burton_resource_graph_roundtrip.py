"""Validate Burton 2022 ResourceGraph JSON round-trip preservation."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from opensmell.experimental.graph import ResourceGraph
from opensmell.experimental.graph_serialization import dumps, loads
from opensmell.experimental.resources import (
    Observation,
    ObservationTarget,
    Result,
    Stimulus,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_TOOL_PATH = PROJECT_ROOT / "tools" / "analyze_burton_resource_graph.py"

EXPECTED_STIMULI = 227
EXPECTED_TARGETS = 1_008
EXPECTED_OBSERVATIONS = 187_748
EXPECTED_RESULTS = 187_748
EXPECTED_GRAPH_RESOURCES = (
    EXPECTED_STIMULI
    + EXPECTED_TARGETS
    + EXPECTED_OBSERVATIONS
)
EXPECTED_MOLECULE_REFERENCE_IDS = 186
EXPECTED_ZERO_DELTA_F = 184_356
EXPECTED_NONZERO_DELTA_F = 3_392
EXPECTED_RESULT_SCHEME_ID = (
    "org.opensmell.experimental.biological.measurements"
)
EXPECTED_RESULT_SCHEME_VERSION = "0.1"


def fail(message: str) -> None:
    raise AssertionError(message)


def load_source_tool() -> ModuleType:
    if not SOURCE_TOOL_PATH.exists():
        raise FileNotFoundError(
            f"Source tool not found: {SOURCE_TOOL_PATH}"
        )

    module_name = "_opensmell_burton_resource_graph_source"
    spec = importlib.util.spec_from_file_location(
        module_name,
        SOURCE_TOOL_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Could not load source tool: {SOURCE_TOOL_PATH}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def build_source_graph(
    source_tool: ModuleType,
) -> ResourceGraph:
    builder = getattr(
        source_tool,
        "build_resource_graph",
        None,
    )
    if not callable(builder):
        fail(
            "tools/analyze_burton_resource_graph.py must expose "
            "build_resource_graph()."
        )

    graph = builder()
    if not isinstance(graph, ResourceGraph):
        fail(
            "build_resource_graph() did not return a ResourceGraph."
        )

    return graph


def stimuli(graph: ResourceGraph) -> list[Stimulus]:
    return [
        resource
        for resource in graph
        if isinstance(resource, Stimulus)
    ]


def targets(graph: ResourceGraph) -> list[ObservationTarget]:
    return [
        resource
        for resource in graph
        if isinstance(resource, ObservationTarget)
    ]


def observations(graph: ResourceGraph) -> list[Observation]:
    return [
        resource
        for resource in graph
        if isinstance(resource, Observation)
    ]


def results(graph: ResourceGraph) -> list[Result]:
    return [
        result
        for observation in observations(graph)
        for result in observation.results
    ]


def same_number(before: float, after: float) -> bool:
    if before != after:
        return False

    if before == 0.0:
        return math.copysign(1.0, before) == math.copysign(
            1.0,
            after,
        )

    return True


def delta_f_values(
    source_tool: ModuleType,
    graph: ResourceGraph,
) -> list[float]:
    extractor = getattr(
        source_tool,
        "get_delta_f_from_observation",
        None,
    )
    if not callable(extractor):
        fail(
            "Source tool must expose "
            "get_delta_f_from_observation()."
        )

    return [
        extractor(observation)
        for observation in observations(graph)
    ]


def validate_expected_shape(
    source_tool: ModuleType,
    graph: ResourceGraph,
    *,
    label: str,
) -> None:
    if len(graph) != EXPECTED_GRAPH_RESOURCES:
        fail(
            f"{label}: expected {EXPECTED_GRAPH_RESOURCES:,} "
            f"materialized resources, found {len(graph):,}."
        )

    stimulus_count = len(stimuli(graph))
    target_count = len(targets(graph))
    observation_count = len(observations(graph))
    result_count = len(results(graph))

    if stimulus_count != EXPECTED_STIMULI:
        fail(
            f"{label}: expected {EXPECTED_STIMULI:,} Stimuli, "
            f"found {stimulus_count:,}."
        )

    if target_count != EXPECTED_TARGETS:
        fail(
            f"{label}: expected {EXPECTED_TARGETS:,} targets, "
            f"found {target_count:,}."
        )

    if observation_count != EXPECTED_OBSERVATIONS:
        fail(
            f"{label}: expected {EXPECTED_OBSERVATIONS:,} "
            f"Observations, found {observation_count:,}."
        )

    if result_count != EXPECTED_RESULTS:
        fail(
            f"{label}: expected {EXPECTED_RESULTS:,} Results, "
            f"found {result_count:,}."
        )

    unresolved = set(graph.unresolved_reference_ids())
    if len(unresolved) != EXPECTED_MOLECULE_REFERENCE_IDS:
        fail(
            f"{label}: expected "
            f"{EXPECTED_MOLECULE_REFERENCE_IDS:,} distinct unresolved "
            f"molecule Resource IDs, found {len(unresolved):,}."
        )

    for result in results(graph):
        if result.scheme.id != EXPECTED_RESULT_SCHEME_ID:
            fail(
                f"{label}: unexpected Result scheme ID "
                f"{result.scheme.id!r}."
            )
        if result.scheme.version != EXPECTED_RESULT_SCHEME_VERSION:
            fail(
                f"{label}: unexpected Result scheme version "
                f"{result.scheme.version!r}."
            )

    values = delta_f_values(
        source_tool,
        graph,
    )

    zero_count = sum(
        value == 0.0
        for value in values
    )
    nonzero_count = len(values) - zero_count

    if zero_count != EXPECTED_ZERO_DELTA_F:
        fail(
            f"{label}: expected {EXPECTED_ZERO_DELTA_F:,} zero "
            f"DeltaF values, found {zero_count:,}."
        )

    if nonzero_count != EXPECTED_NONZERO_DELTA_F:
        fail(
            f"{label}: expected {EXPECTED_NONZERO_DELTA_F:,} non-zero "
            f"DeltaF values, found {nonzero_count:,}."
        )


def compare_resource_order(
    before: ResourceGraph,
    after: ResourceGraph,
) -> None:
    before_ids = [resource.id for resource in before]
    after_ids = [resource.id for resource in after]

    if before_ids != after_ids:
        fail(
            "Resource order or Resource IDs changed during JSON "
            "round-trip."
        )


def structural_reference_snapshot(
    graph: ResourceGraph,
) -> list[tuple[str, str, str]]:
    """Return structural references without depending on graph.references() shape."""

    snapshot: list[tuple[str, str, str]] = []

    for resource in graph:
        if isinstance(resource, Stimulus):
            if resource.source is not None:
                snapshot.append(
                    (
                        resource.id,
                        "source",
                        resource.source.resource_id,
                    )
                )
            continue

        if isinstance(resource, Observation):
            snapshot.append(
                (
                    resource.id,
                    "stimulus",
                    resource.stimulus.resource_id,
                )
            )

            if resource.target is not None:
                snapshot.append(
                    (
                        resource.id,
                        "target",
                        resource.target.resource_id,
                    )
                )

    return snapshot


def compare_structural_references(
    before: ResourceGraph,
    after: ResourceGraph,
) -> None:
    before_refs = structural_reference_snapshot(before)
    after_refs = structural_reference_snapshot(after)

    if before_refs != after_refs:
        fail(
            "Structural references changed during JSON round-trip."
        )

    before_unresolved = set(
        before.unresolved_reference_ids()
    )
    after_unresolved = set(
        after.unresolved_reference_ids()
    )

    if before_unresolved != after_unresolved:
        fail(
            "Unresolved ResourceGraph references changed during JSON "
            "round-trip."
        )

def compare_complete_model_content(
    before: ResourceGraph,
    after: ResourceGraph,
) -> None:
    if before != after:
        fail(
            "ResourceGraph dataclass content changed during JSON "
            "round-trip."
        )


def compare_delta_f_values(
    source_tool: ModuleType,
    before: ResourceGraph,
    after: ResourceGraph,
) -> int:
    before_values = delta_f_values(
        source_tool,
        before,
    )
    after_values = delta_f_values(
        source_tool,
        after,
    )

    if len(before_values) != len(after_values):
        fail(
            "DeltaF value count changed during JSON round-trip."
        )

    for index, (before_value, after_value) in enumerate(
        zip(
            before_values,
            after_values,
            strict=True,
        )
    ):
        if not same_number(
            before_value,
            after_value,
        ):
            fail(
                "DeltaF value changed during JSON round-trip at "
                f"observation index {index}: "
                f"{before_value!r} -> {after_value!r}."
            )

    return len(before_values)


def compare_results(
    before: ResourceGraph,
    after: ResourceGraph,
) -> None:
    before_observations = observations(before)
    after_observations = observations(after)

    for index, (
        before_observation,
        after_observation,
    ) in enumerate(
        zip(
            before_observations,
            after_observations,
            strict=True,
        )
    ):
        if (
            len(before_observation.results)
            != len(after_observation.results)
        ):
            fail(
                f"Result count changed at observation index {index}."
            )

        for result_index, (
            before_result,
            after_result,
        ) in enumerate(
            zip(
                before_observation.results,
                after_observation.results,
                strict=True,
            )
        ):
            if before_result.scheme != after_result.scheme:
                fail(
                    "Result scheme changed at observation index "
                    f"{index}, Result index {result_index}."
                )

            if before_result.data != after_result.data:
                fail(
                    "Result data changed at observation index "
                    f"{index}, Result index {result_index}."
                )

            if before_result.extra != after_result.extra:
                fail(
                    "Result extensions changed at observation index "
                    f"{index}, Result index {result_index}."
                )


def count_source_less_stimuli(
    graph: ResourceGraph,
) -> int:
    return sum(
        stimulus.source is None
        for stimulus in stimuli(graph)
    )


def count_stimuli_without_conditions(
    graph: ResourceGraph,
) -> int:
    return sum(
        not stimulus.conditions
        for stimulus in stimuli(graph)
    )


def main() -> None:
    print(
        "Loading Burton 2022 ResourceGraph source tool..."
    )
    source_tool = load_source_tool()

    print(
        "Building Burton 2022 physiological ResourceGraph..."
    )
    before = build_source_graph(
        source_tool
    )

    print(
        f"Built {len(before):,} materialized resources."
    )

    print(
        "Validating source ResourceGraph..."
    )
    validate_expected_shape(
        source_tool,
        before,
        label="Source graph",
    )

    print(
        "Serializing compact JSON..."
    )
    serialized = dumps(
        before,
        indent=None,
    )
    serialized_bytes = len(
        serialized.encode("utf-8")
    )

    print(
        "Parsing JSON back to ResourceGraph..."
    )
    after = loads(
        serialized
    )

    print(
        "Validating parsed ResourceGraph..."
    )
    validate_expected_shape(
        source_tool,
        after,
        label="Parsed graph",
    )

    print(
        "Comparing complete graph content..."
    )
    compare_resource_order(
        before,
        after,
    )
    compare_structural_references(
        before,
        after,
    )
    compare_complete_model_content(
        before,
        after,
    )
    compare_results(
        before,
        after,
    )
    delta_f_count = compare_delta_f_values(
        source_tool,
        before,
        after,
    )

    print(
        "Checking serialization stability..."
    )
    serialized_again = dumps(
        after,
        indent=None,
    )
    if serialized_again != serialized:
        fail(
            "Compact JSON changed after parse and re-serialization."
        )

    zero_count = sum(
        value == 0.0
        for value in delta_f_values(
            source_tool,
            after,
        )
    )
    nonzero_count = (
        delta_f_count
        - zero_count
    )

    print()
    print(
        "OpenSmell Burton 2022 ResourceGraph JSON round-trip validation"
    )
    print("=" * 76)

    print()
    print("ResourceGraph")
    print("-" * 76)
    print(
        f"Resources                   : {len(after):>12,}"
    )
    print(
        f"Stimulus resources          : {len(stimuli(after)):>12,}"
    )
    print(
        f"Observation targets         : {len(targets(after)):>12,}"
    )
    print(
        f"Observations                : {len(observations(after)):>12,}"
    )
    print(
        f"Result objects              : {len(results(after)):>12,}"
    )

    print()
    print("Reference resolution")
    print("-" * 76)
    print(
        "Unresolved ResourceGraph IDs: "
        f"{len(set(after.unresolved_reference_ids())):>12,}"
    )
    print(
        "Expected unresolved kind    : molecule identities"
    )
    print(
        "Materialized Chemical type  : none invented"
    )
    print(
        f"Source-less stimuli         : "
        f"{count_source_less_stimuli(after):>12,}"
    )
    print(
        f"Stimuli without conditions  : "
        f"{count_stimuli_without_conditions(after):>12,}"
    )

    print()
    print("Scientific values")
    print("-" * 76)
    print(
        f"DeltaF values compared      : {delta_f_count:>12,}"
    )
    print(
        f"Zero DeltaF                 : {zero_count:>12,}"
    )
    print(
        f"Non-zero DeltaF             : {nonzero_count:>12,}"
    )
    print(
        f"Result scheme ID            : {EXPECTED_RESULT_SCHEME_ID}"
    )
    print(
        f"Result scheme version       : "
        f"{EXPECTED_RESULT_SCHEME_VERSION}"
    )

    print()
    print("JSON")
    print("-" * 76)
    print(
        f"Serialized characters       : {len(serialized):>12,}"
    )
    print(
        f"Serialized UTF-8 bytes      : {serialized_bytes:>12,}"
    )
    print(
        "Serialization mode          : compact"
    )

    print()
    print("Round-trip checks")
    print("-" * 76)
    print(
        "Resource count preserved    : True"
    )
    print(
        "Resource order preserved    : True"
    )
    print(
        "Structural refs preserved   : True"
    )
    print(
        "Unresolved refs preserved   : True"
    )
    print(
        "Result schemes preserved    : True"
    )
    print(
        "Result data preserved       : True"
    )
    print(
        "DeltaF values preserved     : True"
    )
    print(
        "Second serialization stable : True"
    )

    print()
    print("Result")
    print("=" * 76)
    print("SUCCESS")
    print(
        "The complete Burton 2022 experimental physiological "
        "ResourceGraph survived ResourceGraph -> JSON -> ResourceGraph "
        "without resource, reference, Result, or DeltaF loss."
    )


if __name__ == "__main__":
    main()
