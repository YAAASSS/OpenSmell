"""Validate JSON round-trip preservation for the UCI gas sensor ResourceGraph.

This tool builds the experimental RFC-0007 electronic-olfaction graph using
tools/analyze_gas_sensor_resource_graph.py, serializes it through the
experimental ResourceGraph JSON serializer, parses it again, and verifies that
the graph structure and all 1,780,480 source feature values are preserved.

The six generated analyte identities are intentionally not materialized as
resources. Their Stimulus.source references therefore remain unresolved in the
ResourceGraph before and after serialization.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from collections import Counter
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
SOURCE_TOOL_PATH = PROJECT_ROOT / "tools" / "analyze_gas_sensor_resource_graph.py"

EXPECTED_STIMULI = 233
EXPECTED_TARGETS = 1
EXPECTED_OBSERVATIONS = 13_910
EXPECTED_RESULTS = 13_910
EXPECTED_GRAPH_RESOURCES = (
    EXPECTED_STIMULI
    + EXPECTED_TARGETS
    + EXPECTED_OBSERVATIONS
)
EXPECTED_FEATURES_PER_RESULT = 128
EXPECTED_TOTAL_FEATURE_VALUES = 1_780_480
EXPECTED_NEGATIVE_VALUES = 668_434
EXPECTED_ZERO_VALUES = 55
EXPECTED_POSITIVE_VALUES = 1_111_991
EXPECTED_UNRESOLVED_REFERENCE_IDS = 6


def fail(message: str) -> None:
    raise AssertionError(message)


def load_source_tool() -> ModuleType:
    if not SOURCE_TOOL_PATH.exists():
        raise FileNotFoundError(
            f"Missing source tool: {SOURCE_TOOL_PATH}"
        )

    module_name = "_opensmell_uci_resource_graph_source"

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
            "tools/analyze_gas_sensor_resource_graph.py must expose "
            "build_resource_graph()."
        )

    graph = builder()

    if not isinstance(graph, ResourceGraph):
        fail(
            "build_resource_graph() did not return a ResourceGraph."
        )

    return graph


def count_resource_types(
    graph: ResourceGraph,
) -> tuple[int, int, int]:
    stimuli = sum(
        isinstance(resource, Stimulus)
        for resource in graph
    )
    targets = sum(
        isinstance(resource, ObservationTarget)
        for resource in graph
    )
    observations = sum(
        isinstance(resource, Observation)
        for resource in graph
    )

    return stimuli, targets, observations


def observations(
    graph: ResourceGraph,
) -> list[Observation]:
    return [
        resource
        for resource in graph
        if isinstance(resource, Observation)
    ]


def results(
    graph: ResourceGraph,
) -> list[Result]:
    return [
        result
        for observation in observations(graph)
        for result in observation.results
    ]


def same_number(
    before: float,
    after: float,
) -> bool:
    if before != after:
        return False

    if before == 0.0:
        return math.copysign(1.0, before) == math.copysign(
            1.0,
            after,
        )

    return True


def feature_statistics(
    source_tool: ModuleType,
    graph: ResourceGraph,
) -> tuple[int, int, int, int]:
    extractor = getattr(
        source_tool,
        "extract_feature_values",
        None,
    )

    if not callable(extractor):
        fail(
            "Source tool must expose extract_feature_values()."
        )

    total = 0
    negative = 0
    zero = 0
    positive = 0

    for result in results(graph):
        values = extractor(result)

        if len(values) != EXPECTED_FEATURES_PER_RESULT:
            fail(
                "Unexpected feature count in Result: "
                f"{len(values)}."
            )

        total += len(values)

        for value in values:
            if value < 0:
                negative += 1
            elif value == 0:
                zero += 1
            else:
                positive += 1

    return total, negative, zero, positive


def validate_expected_shape(
    source_tool: ModuleType,
    graph: ResourceGraph,
    *,
    label: str,
) -> None:
    if len(graph) != EXPECTED_GRAPH_RESOURCES:
        fail(
            f"{label}: expected {EXPECTED_GRAPH_RESOURCES:,} graph "
            f"resources, found {len(graph):,}."
        )

    stimuli, targets, observation_count = count_resource_types(
        graph
    )

    if stimuli != EXPECTED_STIMULI:
        fail(
            f"{label}: expected {EXPECTED_STIMULI:,} Stimuli, "
            f"found {stimuli:,}."
        )

    if targets != EXPECTED_TARGETS:
        fail(
            f"{label}: expected {EXPECTED_TARGETS:,} target, "
            f"found {targets:,}."
        )

    if observation_count != EXPECTED_OBSERVATIONS:
        fail(
            f"{label}: expected {EXPECTED_OBSERVATIONS:,} "
            f"Observations, found {observation_count:,}."
        )

    result_count = len(results(graph))

    if result_count != EXPECTED_RESULTS:
        fail(
            f"{label}: expected {EXPECTED_RESULTS:,} Results, "
            f"found {result_count:,}."
        )

    unresolved = set(
        graph.unresolved_reference_ids()
    )

    if len(unresolved) != EXPECTED_UNRESOLVED_REFERENCE_IDS:
        fail(
            f"{label}: expected "
            f"{EXPECTED_UNRESOLVED_REFERENCE_IDS} distinct unresolved "
            f"analyte references, found {len(unresolved)}."
        )

    stats = feature_statistics(
        source_tool,
        graph,
    )

    expected_stats = (
        EXPECTED_TOTAL_FEATURE_VALUES,
        EXPECTED_NEGATIVE_VALUES,
        EXPECTED_ZERO_VALUES,
        EXPECTED_POSITIVE_VALUES,
    )

    if stats != expected_stats:
        fail(
            f"{label}: feature statistics changed. "
            f"Expected {expected_stats}, found {stats}."
        )


def compare_feature_values(
    source_tool: ModuleType,
    before_graph: ResourceGraph,
    after_graph: ResourceGraph,
) -> None:
    extractor = source_tool.extract_feature_values

    before_observations = observations(before_graph)
    after_observations = observations(after_graph)

    if len(before_observations) != len(after_observations):
        fail("Observation count changed during JSON round-trip.")

    compared = 0

    for before_observation, after_observation in zip(
        before_observations,
        after_observations,
        strict=True,
    ):
        if before_observation.id != after_observation.id:
            fail(
                "Observation order or identity changed during "
                "JSON round-trip."
            )

        if len(before_observation.results) != len(
            after_observation.results
        ):
            fail(
                f"Result count changed for Observation "
                f"{before_observation.id}."
            )

        for before_result, after_result in zip(
            before_observation.results,
            after_observation.results,
            strict=True,
        ):
            if before_result.scheme != after_result.scheme:
                fail(
                    "Result scheme changed during JSON round-trip."
                )

            if before_result.extra != after_result.extra:
                fail(
                    "Result extensions changed during JSON round-trip."
                )

            if before_result.data != after_result.data:
                fail(
                    "Result data structure changed during JSON "
                    "round-trip."
                )

            before_values = extractor(before_result)
            after_values = extractor(after_result)

            if len(before_values) != len(after_values):
                fail(
                    "Feature vector length changed during JSON "
                    "round-trip."
                )

            for before_value, after_value in zip(
                before_values,
                after_values,
                strict=True,
            ):
                if not same_number(
                    float(before_value),
                    float(after_value),
                ):
                    fail(
                        "Sensor feature changed during JSON "
                        "round-trip."
                    )

                compared += 1

    if compared != EXPECTED_TOTAL_FEATURE_VALUES:
        fail(
            f"Expected to compare "
            f"{EXPECTED_TOTAL_FEATURE_VALUES:,} feature values, "
            f"compared {compared:,}."
        )


def compare_graphs(
    source_tool: ModuleType,
    before: ResourceGraph,
    after: ResourceGraph,
) -> None:
    if before.extra != after.extra:
        fail("ResourceGraph extensions changed.")

    if before.ids() != after.ids():
        fail(
            "Resource order or Resource IDs changed during "
            "JSON round-trip."
        )

    if before.references() != after.references():
        fail(
            "Structural references changed during JSON round-trip."
        )

    if (
        before.unresolved_reference_ids()
        != after.unresolved_reference_ids()
    ):
        fail(
            "Unresolved reference identities changed during "
            "JSON round-trip."
        )

    if before.resources != after.resources:
        fail(
            "Resource model content changed during JSON round-trip."
        )

    compare_feature_values(
        source_tool,
        before,
        after,
    )


def serialized_size(
    value: str,
) -> tuple[int, int]:
    return (
        len(value),
        len(value.encode("utf-8")),
    )


def print_report(
    source_tool: ModuleType,
    source_graph: ResourceGraph,
    parsed_graph: ResourceGraph,
    serialized: str,
) -> None:
    source_stimuli, source_targets, source_observations = (
        count_resource_types(source_graph)
    )

    source_results = len(results(source_graph))
    unresolved_ids = source_graph.unresolved_reference_ids()

    (
        feature_count,
        negative_count,
        zero_count,
        positive_count,
    ) = feature_statistics(
        source_tool,
        source_graph,
    )

    characters, bytes_utf8 = serialized_size(
        serialized
    )

    print()
    print(
        "OpenSmell UCI ResourceGraph JSON round-trip validation"
    )
    print("=" * 76)

    print()
    print("ResourceGraph")
    print("-" * 76)
    print(
        f"Resources                   : "
        f"{len(source_graph):>12,}"
    )
    print(
        f"Stimulus resources          : "
        f"{source_stimuli:>12,}"
    )
    print(
        f"Observation targets         : "
        f"{source_targets:>12,}"
    )
    print(
        f"Observations                : "
        f"{source_observations:>12,}"
    )
    print(
        f"Result objects              : "
        f"{source_results:>12,}"
    )

    print()
    print("Reference resolution")
    print("-" * 76)
    print(
        f"Unresolved reference IDs    : "
        f"{len(unresolved_ids):>12,}"
    )
    print(
        "Expected unresolved kind    : generated analyte identities"
    )
    print(
        "Materialized Chemical type  : none invented"
    )

    print()
    print("Scientific values")
    print("-" * 76)
    print(
        f"Feature values compared     : "
        f"{feature_count:>12,}"
    )
    print(
        f"Negative values             : "
        f"{negative_count:>12,}"
    )
    print(
        f"Zero values                 : "
        f"{zero_count:>12,}"
    )
    print(
        f"Positive values             : "
        f"{positive_count:>12,}"
    )

    print()
    print("JSON")
    print("-" * 76)
    print(
        f"Serialized characters       : "
        f"{characters:>12,}"
    )
    print(
        f"Serialized UTF-8 bytes      : "
        f"{bytes_utf8:>12,}"
    )
    print(
        "Serialization mode          : compact"
    )

    print()
    print("Round-trip checks")
    print("-" * 76)
    print(
        f"Resource count preserved    : "
        f"{len(parsed_graph) == len(source_graph)}"
    )
    print(
        f"Resource order preserved    : "
        f"{parsed_graph.ids() == source_graph.ids()}"
    )
    print(
        "Structural refs preserved  : True"
    )
    print(
        "Unresolved refs preserved  : True"
    )
    print(
        "Result schemes preserved    : True"
    )
    print(
        "Result data preserved       : True"
    )
    print(
        f"Feature values preserved    : "
        f"{feature_count == EXPECTED_TOTAL_FEATURE_VALUES}"
    )

    print()
    print("Result")
    print("=" * 76)
    print("SUCCESS")
    print(
        "The experimental UCI electronic-olfaction ResourceGraph "
        "survived ResourceGraph -> JSON -> ResourceGraph without "
        "loss of graph structure or source sensor-feature values."
    )


def main() -> None:
    print(
        "Loading UCI ResourceGraph source tool..."
    )

    source_tool = load_source_tool()

    print(
        "Building UCI electronic-olfaction ResourceGraph..."
    )

    source_graph = build_source_graph(
        source_tool
    )

    print(
        f"Built {len(source_graph):,} materialized resources."
    )

    print(
        "Validating source ResourceGraph..."
    )

    validate_expected_shape(
        source_tool,
        source_graph,
        label="Source graph",
    )

    print(
        "Serializing ResourceGraph to JSON..."
    )

    serialized = dumps(
        source_graph,
        indent=None,
    )

    print(
        "Parsing serialized ResourceGraph..."
    )

    parsed_graph = loads(
        serialized
    )

    if not isinstance(
        parsed_graph,
        ResourceGraph,
    ):
        fail(
            "loads() did not return a ResourceGraph."
        )

    print(
        "Validating parsed ResourceGraph..."
    )

    validate_expected_shape(
        source_tool,
        parsed_graph,
        label="Parsed graph",
    )

    print(
        "Comparing source and parsed graphs..."
    )

    compare_graphs(
        source_tool,
        source_graph,
        parsed_graph,
    )

    print_report(
        source_tool,
        source_graph,
        parsed_graph,
        serialized,
    )


if __name__ == "__main__":
    main()
