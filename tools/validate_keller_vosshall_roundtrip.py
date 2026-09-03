"""Validate full JSON round-trip of the Keller/Vosshall ResourceGraph."""
from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any

from opensmell.experimental.graph import ResourceGraph
from opensmell.experimental.graph_serialization import dumps, loads
from opensmell.experimental.resources import Observation, ObservationTarget, Result, Stimulus

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_TOOL_PATH = PROJECT_ROOT / "tools" / "analyze_keller_vosshall_resource_graph.py"

EXPECTED_GRAPH_RESOURCES = 56_015
EXPECTED_STIMULI = 960
EXPECTED_TARGETS = 55
EXPECTED_OBSERVATIONS = 55_000
EXPECTED_CATEGORICAL_RESULTS = 55_000
EXPECTED_PERCEPTUAL_RESULTS = 41_289
EXPECTED_RESULTS = 96_289
EXPECTED_MEASUREMENTS = 263_683
EXPECTED_DETECTED = 41_289
EXPECTED_NOT_DETECTED = 13_711
EXPECTED_UNKNOWN = 0
EXPECTED_UNRESOLVED_REFERENCE_IDS = 480


def fail(message: str) -> None:
    raise AssertionError(message)


def load_source_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "_opensmell_keller_resource_graph_source", SOURCE_TOOL_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load source tool: {SOURCE_TOOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_source_graph(source_tool: ModuleType) -> ResourceGraph:
    builder = getattr(source_tool, "build_resource_graph", None)
    if not callable(builder):
        fail("tools/analyze_keller_vosshall_resource_graph.py must expose build_resource_graph().")
    graph = builder()
    if not isinstance(graph, ResourceGraph):
        fail("build_resource_graph() did not return a ResourceGraph.")
    return graph


def observations(graph: ResourceGraph) -> list[Observation]:
    return [r for r in graph if isinstance(r, Observation)]


def result_statistics(source_tool: ModuleType, graph: ResourceGraph) -> dict[str, Any]:
    categorical = 0
    perceptual = 0
    measurements = 0
    recognition = 0
    detection: Counter[str] = Counter()

    for observation in observations(graph):
        categorical_result = source_tool.get_categorical_result(observation)
        categorical += 1
        detection[categorical_result.data["detection"]] += 1
        if "recognition" in categorical_result.data:
            recognition += 1

        perceptual_result = source_tool.get_perceptual_result(observation)
        if perceptual_result is not None:
            perceptual += 1
            values = source_tool.get_perceptual_measurements(observation)
            measurements += len(values)

    return {
        "categorical": categorical,
        "perceptual": perceptual,
        "results": categorical + perceptual,
        "measurements": measurements,
        "recognition": recognition,
        "detected": detection["detected"],
        "not_detected": detection["not_detected"],
        "unknown": detection["unknown"],
    }


def validate_expected_shape(source_tool: ModuleType, graph: ResourceGraph, *, label: str) -> None:
    if len(graph) != EXPECTED_GRAPH_RESOURCES:
        fail(f"{label}: expected {EXPECTED_GRAPH_RESOURCES:,} resources, found {len(graph):,}.")

    stimuli = sum(isinstance(r, Stimulus) for r in graph)
    targets = sum(isinstance(r, ObservationTarget) for r in graph)
    obs = sum(isinstance(r, Observation) for r in graph)
    if (stimuli, targets, obs) != (EXPECTED_STIMULI, EXPECTED_TARGETS, EXPECTED_OBSERVATIONS):
        fail(f"{label}: resource type counts changed: {(stimuli, targets, obs)}")

    unresolved = set(graph.unresolved_reference_ids())
    if len(unresolved) != EXPECTED_UNRESOLVED_REFERENCE_IDS:
        fail(f"{label}: expected {EXPECTED_UNRESOLVED_REFERENCE_IDS} unresolved molecule IDs, found {len(unresolved)}.")

    stats = result_statistics(source_tool, graph)
    expected = {
        "categorical": EXPECTED_CATEGORICAL_RESULTS,
        "perceptual": EXPECTED_PERCEPTUAL_RESULTS,
        "results": EXPECTED_RESULTS,
        "measurements": EXPECTED_MEASUREMENTS,
        "recognition": EXPECTED_DETECTED,
        "detected": EXPECTED_DETECTED,
        "not_detected": EXPECTED_NOT_DETECTED,
        "unknown": EXPECTED_UNKNOWN,
    }
    if stats != expected:
        fail(f"{label}: scientific/result statistics changed. Expected {expected}, found {stats}.")


def compare_graphs(before: ResourceGraph, after: ResourceGraph) -> None:
    if len(before) != len(after):
        fail("Resource count changed during JSON round-trip.")

    if before.ids() != after.ids():
        fail("Resource IDs or resource order changed during JSON round-trip.")

    if before.unresolved_reference_ids() != after.unresolved_reference_ids():
        fail("Unresolved references changed during JSON round-trip.")

    compared_results = 0
    compared_measurements = 0

    for left, right in zip(before, after, strict=True):
        if type(left) is not type(right):
            fail(f"Resource type changed for {left.id}.")
        if left != right:
            fail(f"Resource content changed during JSON round-trip: {left.id}")

        if isinstance(left, Observation):
            compared_results += len(left.results)
            for result in left.results:
                if result.scheme.id == "org.opensmell.perceptual.measurements":
                    values = result.data.get("measurements", [])
                    if not isinstance(values, list):
                        fail("Perceptual measurements changed type.")
                    compared_measurements += len(values)

    if compared_results != EXPECTED_RESULTS:
        fail(f"Expected to compare {EXPECTED_RESULTS:,} Results, compared {compared_results:,}.")
    if compared_measurements != EXPECTED_MEASUREMENTS:
        fail(f"Expected to compare {EXPECTED_MEASUREMENTS:,} measurements, compared {compared_measurements:,}.")


def main() -> None:
    print("Building Keller/Vosshall psychophysical ResourceGraph...")
    source_tool = load_source_tool()
    before = build_source_graph(source_tool)
    validate_expected_shape(source_tool, before, label="Before JSON")

    print(f"Graph resources              : {len(before):>10,}")
    print(f"Unresolved molecule IDs      : {len(set(before.unresolved_reference_ids())):>10,}")
    print("Serializing compact JSON...")
    payload = dumps(before, indent=None)
    payload_bytes = len(payload.encode("utf-8"))
    print(f"Serialized JSON bytes        : {payload_bytes:>10,}")

    print("Parsing JSON back to ResourceGraph...")
    after = loads(payload)
    validate_expected_shape(source_tool, after, label="After JSON")

    print("Comparing complete graph content...")
    compare_graphs(before, after)

    stable = dumps(after, indent=None)
    if payload != stable:
        fail("Compact JSON serialization is not stable after one round-trip.")

    stats = result_statistics(source_tool, after)
    print(f"Stimulus resources           : {EXPECTED_STIMULI:>10,}")
    print(f"Observation targets          : {EXPECTED_TARGETS:>10,}")
    print(f"Observations                 : {EXPECTED_OBSERVATIONS:>10,}")
    print(f"Categorical Results          : {stats['categorical']:>10,}")
    print(f"Perceptual Results           : {stats['perceptual']:>10,}")
    print(f"Total Result objects         : {stats['results']:>10,}")
    print(f"Numeric measurements         : {stats['measurements']:>10,}")
    print(f"Detected                     : {stats['detected']:>10,}")
    print(f"Not detected                 : {stats['not_detected']:>10,}")
    print()
    print("SUCCESS")
    print("The complete Keller/Vosshall experimental ResourceGraph survived JSON round-trip without resource, reference, Result, or psychophysical measurement loss.")


if __name__ == "__main__":
    main()
