"""Tests for experimental OpenSmell ResourceGraph JSON serialization."""

import json
import math

import pytest

from opensmell.experimental.graph import ResourceGraph
from opensmell.experimental.graph_serialization import (
    RESOURCE_GRAPH_FORMAT,
    RESOURCE_GRAPH_VERSION,
    condition_from_dict,
    condition_to_dict,
    dumps,
    external_identifier_from_dict,
    external_identifier_to_dict,
    graph_from_dict,
    graph_to_dict,
    loads,
    observation_from_dict,
    observation_target_from_dict,
    observation_target_to_dict,
    observation_to_dict,
    reference_from_dict,
    reference_to_dict,
    resource_from_dict,
    resource_to_dict,
    result_from_dict,
    result_scheme_from_dict,
    result_scheme_to_dict,
    result_to_dict,
    stimulus_from_dict,
    stimulus_to_dict,
)
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


def make_scheme(
    scheme_id: str = "org.opensmell.experimental.test",
    version: str = "0.1",
) -> ResultScheme:
    return ResultScheme(
        id=scheme_id,
        version=version,
    )


def make_result(
    scheme_id: str = "org.opensmell.experimental.test",
    version: str = "0.1",
    value=1.0,
) -> Result:
    return Result(
        scheme=make_scheme(
            scheme_id,
            version,
        ),
        data={
            "value": value,
        },
    )


def make_graph() -> ResourceGraph:
    source = Stimulus(
        id="source-1",
        extra={
            "source_extension": "preserved",
        },
    )

    stimulus = Stimulus(
        id="stimulus-1",
        source=Reference("source-1"),
        identifiers=[
            ExternalIdentifier(
                scheme="example.stimulus",
                value="S-001",
            )
        ],
        conditions=[
            Condition(
                property="concentration",
                value=10.0,
                unit="ppmv",
                extra={
                    "condition_extension": True,
                },
            )
        ],
        extra={
            "stimulus_extension": {
                "hello": "world",
            }
        },
    )

    target = ObservationTarget(
        id="target-1",
        identifiers=[
            ExternalIdentifier(
                scheme="example.target",
                value="T-001",
            )
        ],
        extra={
            "target_extension": [
                1,
                2,
                3,
            ]
        },
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference("stimulus-1"),
        target=Reference("target-1"),
        results=[
            Result(
                scheme=ResultScheme(
                    id="org.opensmell.experimental.test",
                    version="0.1",
                    extra={
                        "scheme_extension": "yes",
                    },
                ),
                data={
                    "value": -0.0,
                    "nested": {
                        "values": [
                            1,
                            2,
                            3,
                        ]
                    },
                },
                extra={
                    "result_extension": {
                        "x": 1,
                    }
                },
            ),
            Result(
                scheme=ResultScheme(
                    id="vendor.example.future-result",
                    version="999.42",
                ),
                data={
                    "label": "unknown scheme survives",
                },
            ),
        ],
        context={
            "experiment": "example",
            "unicode": "café — запах",
        },
        identifiers=[
            ExternalIdentifier(
                scheme="example.observation",
                value="O-001",
            )
        ],
        extra={
            "observation_extension": False,
        },
    )

    unresolved_observation = Observation(
        id="observation-2",
        stimulus=Reference("missing-stimulus"),
        target=Reference("missing-target"),
        results=[
            make_result(
                scheme_id="vendor.example.unknown",
                version="7.5",
                value=0.0,
            )
        ],
    )

    return ResourceGraph(
        resources=[
            source,
            stimulus,
            target,
            observation,
            unresolved_observation,
        ],
        extra={
            "document_extension": {
                "future": True,
            }
        },
    )


def test_constants():
    assert (
        RESOURCE_GRAPH_FORMAT
        == "org.opensmell.experimental.resource-graph"
    )
    assert RESOURCE_GRAPH_VERSION == "0.1"


def test_reference_round_trip():
    reference = Reference("resource-123")

    encoded = reference_to_dict(reference)
    decoded = reference_from_dict(encoded)

    assert encoded == {
        "resource_id": "resource-123",
    }
    assert decoded == reference


def test_reference_rejects_missing_resource_id():
    with pytest.raises((TypeError, ValueError)):
        reference_from_dict({})


def test_reference_rejects_empty_resource_id():
    with pytest.raises(ValueError):
        reference_from_dict(
            {
                "resource_id": "",
            }
        )


def test_external_identifier_round_trip():
    identifier = ExternalIdentifier(
        scheme="pubchem.cid",
        value="240",
    )

    encoded = external_identifier_to_dict(
        identifier
    )
    decoded = external_identifier_from_dict(
        encoded
    )

    assert encoded == {
        "scheme": "pubchem.cid",
        "value": "240",
    }
    assert decoded == identifier


def test_external_identifier_rejects_missing_scheme():
    with pytest.raises((TypeError, ValueError)):
        external_identifier_from_dict(
            {
                "value": "240",
            }
        )


def test_external_identifier_rejects_missing_value():
    with pytest.raises((TypeError, ValueError)):
        external_identifier_from_dict(
            {
                "scheme": "pubchem.cid",
            }
        )


def test_condition_round_trip():
    condition = Condition(
        property="concentration",
        value=10.0,
        unit="ppmv",
        extra={
            "vendor.example": {
                "x": 1,
            }
        },
    )

    encoded = condition_to_dict(condition)
    decoded = condition_from_dict(encoded)

    assert decoded.property == "concentration"
    assert decoded.value == 10.0
    assert decoded.unit == "ppmv"
    assert decoded.extra == {
        "vendor.example": {
            "x": 1,
        }
    }


def test_condition_without_unit_round_trip():
    condition = Condition(
        property="temperature",
        value=25,
    )

    encoded = condition_to_dict(condition)
    decoded = condition_from_dict(encoded)

    assert "unit" not in encoded
    assert decoded.unit is None


def test_condition_requires_value():
    with pytest.raises(ValueError):
        condition_from_dict(
            {
                "property": "concentration",
            }
        )


def test_condition_preserves_null_value():
    condition = condition_from_dict(
        {
            "property": "unknown-condition",
            "value": None,
        }
    )

    assert condition.value is None


def test_result_scheme_round_trip():
    scheme = ResultScheme(
        id="vendor.example.scheme",
        version="42.1",
        extra={
            "vendor": "extension",
        },
    )

    encoded = result_scheme_to_dict(scheme)
    decoded = result_scheme_from_dict(encoded)

    assert decoded.id == "vendor.example.scheme"
    assert decoded.version == "42.1"
    assert decoded.extra == {
        "vendor": "extension",
    }


def test_unknown_result_scheme_is_accepted():
    scheme = result_scheme_from_dict(
        {
            "id": "completely.unknown.scheme",
            "version": "9999",
        }
    )

    assert scheme.id == "completely.unknown.scheme"
    assert scheme.version == "9999"


def test_result_scheme_requires_version():
    with pytest.raises((TypeError, ValueError)):
        result_scheme_from_dict(
            {
                "id": "example.scheme",
            }
        )


def test_result_round_trip():
    result = Result(
        scheme=make_scheme(),
        data={
            "value": 123,
        },
        extra={
            "future": True,
        },
    )

    encoded = result_to_dict(result)
    decoded = result_from_dict(encoded)

    assert decoded.scheme.id == (
        "org.opensmell.experimental.test"
    )
    assert decoded.scheme.version == "0.1"
    assert decoded.data == {
        "value": 123,
    }
    assert decoded.extra == {
        "future": True,
    }


def test_result_requires_scheme():
    with pytest.raises(ValueError):
        result_from_dict(
            {
                "data": {},
            }
        )


def test_result_requires_data():
    with pytest.raises(ValueError):
        result_from_dict(
            {
                "scheme": {
                    "id": "example",
                    "version": "0.1",
                }
            }
        )


def test_result_data_must_be_object():
    with pytest.raises(TypeError):
        result_from_dict(
            {
                "scheme": {
                    "id": "example",
                    "version": "0.1",
                },
                "data": [],
            }
        )


def test_negative_zero_survives_result_round_trip():
    result = Result(
        scheme=make_scheme(),
        data={
            "value": -0.0,
        },
    )

    encoded = result_to_dict(result)
    decoded = result_from_dict(encoded)

    value = decoded.data["value"]

    assert value == 0.0
    assert math.copysign(1.0, value) == -1.0


def test_stimulus_round_trip():
    stimulus = Stimulus(
        id="stimulus-1",
        source=Reference("source-1"),
        identifiers=[
            ExternalIdentifier(
                scheme="example",
                value="123",
            )
        ],
        conditions=[
            Condition(
                property="concentration",
                value=5,
                unit="ppmv",
            )
        ],
        extra={
            "future": "field",
        },
    )

    encoded = stimulus_to_dict(stimulus)
    decoded = stimulus_from_dict(encoded)

    assert encoded["type"] == "stimulus"
    assert decoded.id == "stimulus-1"
    assert decoded.source == Reference("source-1")
    assert decoded.identifiers[0].value == "123"
    assert decoded.conditions[0].value == 5
    assert decoded.extra == {
        "future": "field",
    }


def test_stimulus_without_optional_fields():
    stimulus = Stimulus(
        id="stimulus-1",
    )

    encoded = stimulus_to_dict(stimulus)
    decoded = stimulus_from_dict(encoded)

    assert encoded == {
        "type": "stimulus",
        "id": "stimulus-1",
    }

    assert decoded.source is None
    assert decoded.identifiers == []
    assert decoded.conditions == []


def test_stimulus_unknown_fields_are_preserved():
    stimulus = stimulus_from_dict(
        {
            "type": "stimulus",
            "id": "stimulus-1",
            "vendor.future": {
                "hello": "world",
            },
        }
    )

    assert stimulus.extra == {
        "vendor.future": {
            "hello": "world",
        }
    }


def test_observation_target_round_trip():
    target = ObservationTarget(
        id="target-1",
        identifiers=[
            ExternalIdentifier(
                scheme="example.target",
                value="42",
            )
        ],
        extra={
            "kind": "sensor-array",
        },
    )

    encoded = observation_target_to_dict(
        target
    )
    decoded = observation_target_from_dict(
        encoded
    )

    assert encoded["type"] == (
        "observation_target"
    )
    assert decoded.id == "target-1"
    assert decoded.identifiers[0].value == "42"
    assert decoded.extra == {
        "kind": "sensor-array",
    }


def test_observation_round_trip():
    observation = Observation(
        id="observation-1",
        stimulus=Reference("stimulus-1"),
        target=Reference("target-1"),
        results=[
            make_result(),
        ],
        context={
            "experiment": "test",
        },
        identifiers=[
            ExternalIdentifier(
                scheme="example",
                value="O1",
            )
        ],
        extra={
            "future": True,
        },
    )

    encoded = observation_to_dict(
        observation
    )
    decoded = observation_from_dict(
        encoded
    )

    assert encoded["type"] == "observation"
    assert decoded.id == "observation-1"
    assert decoded.stimulus == Reference(
        "stimulus-1"
    )
    assert decoded.target == Reference(
        "target-1"
    )
    assert len(decoded.results) == 1
    assert decoded.context == {
        "experiment": "test",
    }
    assert decoded.identifiers[0].value == "O1"
    assert decoded.extra == {
        "future": True,
    }


def test_observation_requires_stimulus():
    with pytest.raises(ValueError):
        observation_from_dict(
            {
                "type": "observation",
                "id": "observation-1",
            }
        )


def test_observation_without_optional_fields():
    observation = Observation(
        id="observation-1",
        stimulus=Reference("stimulus-1"),
    )

    encoded = observation_to_dict(
        observation
    )

    assert encoded == {
        "type": "observation",
        "id": "observation-1",
        "stimulus": {
            "resource_id": "stimulus-1",
        },
    }


def test_resource_dispatch_stimulus():
    resource = resource_from_dict(
        {
            "type": "stimulus",
            "id": "stimulus-1",
        }
    )

    assert isinstance(resource, Stimulus)


def test_resource_dispatch_target():
    resource = resource_from_dict(
        {
            "type": "observation_target",
            "id": "target-1",
        }
    )

    assert isinstance(
        resource,
        ObservationTarget,
    )


def test_resource_dispatch_observation():
    resource = resource_from_dict(
        {
            "type": "observation",
            "id": "observation-1",
            "stimulus": {
                "resource_id": "stimulus-1",
            },
        }
    )

    assert isinstance(resource, Observation)


def test_unknown_resource_type_is_rejected():
    with pytest.raises(ValueError):
        resource_from_dict(
            {
                "type": "future-resource",
                "id": "resource-1",
            }
        )


def test_resource_to_dict_rejects_unknown_object():
    with pytest.raises(TypeError):
        resource_to_dict(object())


def test_graph_to_dict_envelope():
    graph = ResourceGraph()

    encoded = graph_to_dict(graph)

    assert encoded == {
        "format": RESOURCE_GRAPH_FORMAT,
        "version": RESOURCE_GRAPH_VERSION,
        "resources": [],
    }


def test_graph_round_trip():
    graph = make_graph()

    encoded = graph_to_dict(graph)
    decoded = graph_from_dict(encoded)

    assert len(decoded.resources) == 5

    assert [
        resource.id
        for resource in decoded.resources
    ] == [
        "source-1",
        "stimulus-1",
        "target-1",
        "observation-1",
        "observation-2",
    ]


def test_graph_resource_order_is_preserved():
    graph = make_graph()

    decoded = graph_from_dict(
        graph_to_dict(graph)
    )

    assert [
        resource.id
        for resource in decoded
    ] == [
        resource.id
        for resource in graph
    ]


def test_graph_extra_is_preserved():
    graph = make_graph()

    decoded = graph_from_dict(
        graph_to_dict(graph)
    )

    assert decoded.extra == {
        "document_extension": {
            "future": True,
        }
    }


def test_unknown_graph_fields_are_preserved():
    graph = graph_from_dict(
        {
            "format": RESOURCE_GRAPH_FORMAT,
            "version": RESOURCE_GRAPH_VERSION,
            "resources": [],
            "vendor.example": {
                "future": 123,
            },
        }
    )

    assert graph.extra == {
        "vendor.example": {
            "future": 123,
        }
    }


def test_unknown_graph_format_is_rejected():
    with pytest.raises(ValueError):
        graph_from_dict(
            {
                "format": "vendor.other-format",
                "version": "0.1",
                "resources": [],
            }
        )


def test_unknown_graph_version_is_rejected():
    with pytest.raises(ValueError):
        graph_from_dict(
            {
                "format": RESOURCE_GRAPH_FORMAT,
                "version": "999",
                "resources": [],
            }
        )


def test_graph_requires_resources():
    with pytest.raises(ValueError):
        graph_from_dict(
            {
                "format": RESOURCE_GRAPH_FORMAT,
                "version": RESOURCE_GRAPH_VERSION,
            }
        )


def test_duplicate_resource_ids_are_rejected_after_parse():
    with pytest.raises(ValueError):
        graph_from_dict(
            {
                "format": RESOURCE_GRAPH_FORMAT,
                "version": RESOURCE_GRAPH_VERSION,
                "resources": [
                    {
                        "type": "stimulus",
                        "id": "duplicate",
                    },
                    {
                        "type": "observation_target",
                        "id": "duplicate",
                    },
                ],
            }
        )


def test_unresolved_references_survive_round_trip():
    graph = make_graph()

    decoded = graph_from_dict(
        graph_to_dict(graph)
    )

    assert decoded.unresolved_reference_ids() == {
        "missing-stimulus",
        "missing-target",
    }


def test_unknown_result_scheme_survives_graph_round_trip():
    graph = make_graph()

    decoded = graph_from_dict(
        graph_to_dict(graph)
    )

    observation = decoded.require(
        "observation-1"
    )

    assert isinstance(
        observation,
        Observation,
    )

    unknown = observation.results[1]

    assert unknown.scheme.id == (
        "vendor.example.future-result"
    )
    assert unknown.scheme.version == "999.42"


def test_negative_zero_survives_graph_dict_round_trip():
    graph = make_graph()

    decoded = graph_from_dict(
        graph_to_dict(graph)
    )

    observation = decoded.require(
        "observation-1"
    )

    assert isinstance(
        observation,
        Observation,
    )

    value = observation.results[0].data[
        "value"
    ]

    assert value == 0.0
    assert math.copysign(1.0, value) == -1.0


def test_negative_zero_survives_json_text_round_trip():
    graph = make_graph()

    text = dumps(graph)
    decoded = loads(text)

    observation = decoded.require(
        "observation-1"
    )

    assert isinstance(
        observation,
        Observation,
    )

    value = observation.results[0].data[
        "value"
    ]

    assert value == 0.0
    assert math.copysign(1.0, value) == -1.0


def test_unicode_survives_json_round_trip():
    graph = make_graph()

    text = dumps(graph)

    assert "café" in text
    assert "запах" in text

    decoded = loads(text)

    observation = decoded.require(
        "observation-1"
    )

    assert isinstance(
        observation,
        Observation,
    )

    assert observation.context["unicode"] == (
        "café — запах"
    )


def test_dumps_produces_valid_json():
    text = dumps(
        make_graph()
    )

    parsed = json.loads(text)

    assert parsed["format"] == (
        RESOURCE_GRAPH_FORMAT
    )
    assert parsed["version"] == (
        RESOURCE_GRAPH_VERSION
    )


def test_dumps_compact_mode():
    text = dumps(
        ResourceGraph(),
        indent=None,
    )

    parsed = json.loads(text)

    assert parsed["resources"] == []


def test_loads_rejects_non_string():
    with pytest.raises(TypeError):
        loads(
            {
                "format": RESOURCE_GRAPH_FORMAT,
            }
        )


def test_invalid_json_is_rejected():
    with pytest.raises(
        json.JSONDecodeError
    ):
        loads("{not-json}")


@pytest.mark.parametrize(
    "constant",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_nonstandard_numeric_constants_are_rejected_during_parsing(
    constant: str,
):
    text = (
        '{"format":"'
        + RESOURCE_GRAPH_FORMAT
        + '","version":"'
        + RESOURCE_GRAPH_VERSION
        + '","resources":[],"vendor.value":'
        + constant
        + "}"
    )

    with pytest.raises(
        ValueError,
        match="non-standard JSON numeric constant",
    ):
        loads(text)


@pytest.mark.parametrize(
    "constant",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_nonstandard_numeric_constants_are_rejected_when_nested(
    constant: str,
):
    text = (
        '{"format":"'
        + RESOURCE_GRAPH_FORMAT
        + '","version":"'
        + RESOURCE_GRAPH_VERSION
        + '","resources":[{"type":"observation",'
        + '"id":"observation-1",'
        + '"stimulus":{"resource_id":"stimulus-1"},'
        + '"results":[{"scheme":{"id":"example","version":"0.1"},'
        + '"data":{"value":'
        + constant
        + "}}]}]}"
    )

    with pytest.raises(
        ValueError,
        match="non-standard JSON numeric constant",
    ):
        loads(text)


def test_nan_is_rejected_during_serialization():
    graph = ResourceGraph(
        resources=[
            Stimulus(
                id="stimulus-1",
            ),
            Observation(
                id="observation-1",
                stimulus=Reference(
                    "stimulus-1"
                ),
                results=[
                    Result(
                        scheme=make_scheme(),
                        data={
                            "value": float("nan"),
                        },
                    )
                ],
            ),
        ]
    )

    with pytest.raises(ValueError):
        dumps(graph)


def test_positive_infinity_is_rejected_during_serialization():
    graph = ResourceGraph(
        resources=[
            Stimulus(
                id="stimulus-1",
            ),
            Observation(
                id="observation-1",
                stimulus=Reference(
                    "stimulus-1"
                ),
                results=[
                    Result(
                        scheme=make_scheme(),
                        data={
                            "value": float("inf"),
                        },
                    )
                ],
            ),
        ]
    )

    with pytest.raises(ValueError):
        dumps(graph)


def test_official_stimulus_fields_override_extra():
    stimulus = Stimulus(
        id="real-id",
        extra={
            "id": "wrong-id",
            "type": "observation",
        },
    )

    encoded = stimulus_to_dict(
        stimulus
    )

    assert encoded["id"] == "real-id"
    assert encoded["type"] == "stimulus"


def test_official_result_scheme_fields_override_extra():
    scheme = ResultScheme(
        id="real.scheme",
        version="0.1",
        extra={
            "id": "wrong.scheme",
            "version": "999",
        },
    )

    encoded = result_scheme_to_dict(
        scheme
    )

    assert encoded["id"] == "real.scheme"
    assert encoded["version"] == "0.1"


def test_official_graph_fields_override_extra():
    graph = ResourceGraph(
        extra={
            "format": "wrong",
            "version": "999",
            "resources": [
                {
                    "bad": True,
                }
            ],
        }
    )

    encoded = graph_to_dict(graph)

    assert encoded["format"] == (
        RESOURCE_GRAPH_FORMAT
    )
    assert encoded["version"] == (
        RESOURCE_GRAPH_VERSION
    )
    assert encoded["resources"] == []


def test_nested_extensions_survive_round_trip():
    graph = make_graph()

    decoded = loads(
        dumps(graph)
    )

    stimulus = decoded.require(
        "stimulus-1"
    )

    target = decoded.require(
        "target-1"
    )

    observation = decoded.require(
        "observation-1"
    )

    assert isinstance(
        stimulus,
        Stimulus,
    )
    assert isinstance(
        target,
        ObservationTarget,
    )
    assert isinstance(
        observation,
        Observation,
    )

    assert stimulus.extra[
        "stimulus_extension"
    ] == {
        "hello": "world",
    }

    assert stimulus.conditions[0].extra[
        "condition_extension"
    ] is True

    assert target.extra[
        "target_extension"
    ] == [
        1,
        2,
        3,
    ]

    result = observation.results[0]

    assert result.scheme.extra[
        "scheme_extension"
    ] == "yes"

    assert result.extra[
        "result_extension"
    ] == {
        "x": 1,
    }


def test_double_serialization_is_stable():
    graph_1 = make_graph()

    json_1 = dumps(
        graph_1,
        indent=None,
    )

    graph_2 = loads(json_1)

    json_2 = dumps(
        graph_2,
        indent=None,
    )

    graph_3 = loads(json_2)

    json_3 = dumps(
        graph_3,
        indent=None,
    )

    assert json_2 == json_3


def test_dict_round_trip_is_stable():
    graph_1 = make_graph()

    dict_1 = graph_to_dict(
        graph_1
    )

    graph_2 = graph_from_dict(
        dict_1
    )

    dict_2 = graph_to_dict(
        graph_2
    )

    graph_3 = graph_from_dict(
        dict_2
    )

    dict_3 = graph_to_dict(
        graph_3
    )

    assert dict_2 == dict_3