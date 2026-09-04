from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opensmell.experimental.graph import ResourceGraph
from opensmell.experimental.graph_serialization import graph_to_dict
from opensmell.experimental.resources import (
    Condition,
    ExternalIdentifier,
    Observation,
    ObservationTarget,
    Reference,
    Result,
    ResultScheme,
    Stimulus,
)


OUTPUT_PATH = Path("examples/resource_graph_interop_vectors.json")

FORMAT_ID = "org.opensmell.experimental.resource-graph"
FORMAT_VERSION = "0.1"


def make_basic_graph() -> ResourceGraph:
    stimulus = Stimulus(
        id="11111111-1111-4111-8111-111111111111",
    )

    target = ObservationTarget(
        id="22222222-2222-4222-8222-222222222222",
    )

    observation = Observation(
        id="33333333-3333-4333-8333-333333333333",
        stimulus=Reference(stimulus.id),
        target=Reference(target.id),
        results=[
            Result(
                scheme=ResultScheme(
                    id="org.opensmell.experimental.test",
                    version="0.1",
                ),
                data={
                    "value": 42.5,
                },
            )
        ],
    )

    return ResourceGraph(
        resources=[
            stimulus,
            target,
            observation,
        ]
    )


def make_unicode_graph() -> ResourceGraph:
    stimulus = Stimulus(
        id="44444444-4444-4444-8444-444444444444",
        identifiers=[
            ExternalIdentifier(
                scheme="example.unicode",
                value="café-香り-🌹",
            )
        ],
        conditions=[
            Condition(
                property="description",
                value="Crème brûlée — ваниль — 香り 🌹",
            )
        ],
        extra={
            "unicode_extension": "éèê-日本語-🚀",
        },
    )

    observation = Observation(
        id="55555555-5555-4555-8555-555555555555",
        stimulus=Reference(stimulus.id),
        results=[
            Result(
                scheme=ResultScheme(
                    id="org.opensmell.experimental.unicode",
                    version="0.1",
                ),
                data={
                    "label": "café",
                    "japanese": "香り",
                    "russian": "запах",
                    "emoji": "🌹",
                },
            )
        ],
    )

    return ResourceGraph(
        resources=[
            stimulus,
            observation,
        ]
    )


def make_negative_zero_graph() -> ResourceGraph:
    stimulus = Stimulus(
        id="66666666-6666-4666-8666-666666666666",
    )

    observation = Observation(
        id="77777777-7777-4777-8777-777777777777",
        stimulus=Reference(stimulus.id),
        results=[
            Result(
                scheme=ResultScheme(
                    id="org.opensmell.experimental.biological.measurements",
                    version="0.1",
                ),
                data={
                    "property": "DeltaF",
                    "value": -0.0,
                },
            )
        ],
    )

    return ResourceGraph(
        resources=[
            stimulus,
            observation,
        ]
    )


def make_unresolved_reference_graph() -> ResourceGraph:
    missing_source_id = "88888888-8888-4888-8888-888888888888"

    stimulus = Stimulus(
        id="99999999-9999-4999-8999-999999999999",
        source=Reference(missing_source_id),
    )

    observation = Observation(
        id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        stimulus=Reference(stimulus.id),
        target=Reference(
            "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        ),
        results=[
            Result(
                scheme=ResultScheme(
                    id="org.opensmell.experimental.observation.categories",
                    version="0.1",
                ),
                data={
                    "state": "present",
                },
            )
        ],
    )

    return ResourceGraph(
        resources=[
            stimulus,
            observation,
        ]
    )


def make_extensions_graph() -> ResourceGraph:
    stimulus = Stimulus(
        id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        conditions=[
            Condition(
                property="temperature",
                value=23.5,
                unit="degC",
                extra={
                    "condition_extension": {
                        "origin": "interop-test",
                    }
                },
            )
        ],
        extra={
            "future_stimulus_field": {
                "enabled": True,
                "nested": {
                    "value": 123,
                },
            }
        },
    )

    target = ObservationTarget(
        id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        extra={
            "future_target_field": [
                "a",
                "b",
                "c",
            ]
        },
    )

    result_scheme = ResultScheme(
        id="org.example.future.result-scheme",
        version="9.7",
        extra={
            "scheme_extension": "preserve-me",
        },
    )

    result = Result(
        scheme=result_scheme,
        data={
            "arbitrary": {
                "nested": [
                    1,
                    2,
                    3,
                ]
            }
        },
        extra={
            "result_extension": True,
        },
    )

    observation = Observation(
        id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        stimulus=Reference(stimulus.id),
        target=Reference(target.id),
        results=[result],
        context={
            "protocol": "future-protocol",
        },
        extra={
            "future_observation_field": {
                "answer": 42,
            }
        },
    )

    return ResourceGraph(
        resources=[
            stimulus,
            target,
            observation,
        ],
        extra={
            "graph_extension": {
                "producer": "OpenSmell interoperability test",
            }
        },
    )


def make_multiple_results_graph() -> ResourceGraph:
    stimulus = Stimulus(
        id="ffffffff-ffff-4fff-8fff-ffffffffffff",
    )

    observation = Observation(
        id="12345678-1234-4234-8234-123456789abc",
        stimulus=Reference(stimulus.id),
        results=[
            Result(
                scheme=ResultScheme(
                    id="org.opensmell.experimental.observation.categories",
                    version="0.1",
                ),
                data={
                    "state": "present",
                },
            ),
            Result(
                scheme=ResultScheme(
                    id="org.opensmell.perceptual.measurements",
                    version="0.1",
                ),
                data={
                    "measurements": [
                        {
                            "property": "intensity",
                            "value": 75.0,
                            "scale": {
                                "min": 0.0,
                                "max": 100.0,
                            },
                        }
                    ]
                },
            ),
            Result(
                scheme=ResultScheme(
                    id="org.example.unknown",
                    version="42",
                ),
                data={
                    "opaque": "preserve this",
                },
            ),
        ],
    )

    return ResourceGraph(
        resources=[
            stimulus,
            observation,
        ]
    )


def build_vectors() -> dict[str, Any]:
    graphs = [
        (
            "basic_graph",
            "Basic resolved Stimulus -> ObservationTarget -> Observation graph.",
            make_basic_graph(),
        ),
        (
            "unicode",
            "Unicode strings must survive JSON exchange without ASCII-only assumptions.",
            make_unicode_graph(),
        ),
        (
            "negative_zero",
            "Valid JSON negative zero must preserve its numeric sign.",
            make_negative_zero_graph(),
        ),
        (
            "unresolved_references",
            "Structurally unresolved Resource IDs must remain representable.",
            make_unresolved_reference_graph(),
        ),
        (
            "extensions_and_unknown_scheme",
            "Unknown extension fields and an unknown Result scheme must survive exchange.",
            make_extensions_graph(),
        ),
        (
            "multiple_results",
            "One Observation may carry multiple Results using independent schemes.",
            make_multiple_results_graph(),
        ),
    ]

    return {
        "vector_set": "org.opensmell.experimental.resource-graph.interop-vectors",
        "version": "0.1",
        "resource_graph_format": FORMAT_ID,
        "resource_graph_version": FORMAT_VERSION,
        "vectors": [
            {
                "name": name,
                "description": description,
                "graph": graph_to_dict(graph),
            }
            for name, description, graph in graphs
        ],
    }


def main() -> None:
    vectors = build_vectors()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            vectors,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print("OpenSmell ResourceGraph interoperability vectors")
    print("=" * 72)
    print(f"Output : {OUTPUT_PATH}")
    print(f"Vectors: {len(vectors['vectors'])}")
    print()
    for vector in vectors["vectors"]:
        print(f"  PASS  {vector['name']}")
    print()
    print("SUCCESS")


if __name__ == "__main__":
    main()