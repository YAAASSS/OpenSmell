"""Tests for experimental OpenSmell resource models.

These tests cover experimental resource-oriented concepts that are not part
of the OpenSmell 0.1 Core specification.

The experimental API may change before any future normative specification.
"""

import pytest

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def example_result_scheme(
    *,
    scheme_id: str = "org.opensmell.example",
    version: str = "0.1",
) -> ResultScheme:
    """Create a reusable experimental ResultScheme for tests."""

    return ResultScheme(
        id=scheme_id,
        version=version,
    )


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------


def test_reference_accepts_resource_id():
    reference = Reference(
        resource_id="resource-123"
    )

    assert reference.resource_id == "resource-123"


def test_reference_rejects_empty_resource_id():
    with pytest.raises(ValueError):
        Reference(
            resource_id=""
        )


def test_reference_rejects_non_string_resource_id():
    with pytest.raises(TypeError):
        Reference(
            resource_id=123,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# ExternalIdentifier
# ---------------------------------------------------------------------------


def test_external_identifier_accepts_scheme_and_value():
    identifier = ExternalIdentifier(
        scheme="pubchem.cid",
        value="240",
    )

    assert identifier.scheme == "pubchem.cid"
    assert identifier.value == "240"


def test_external_identifier_rejects_empty_scheme():
    with pytest.raises(ValueError):
        ExternalIdentifier(
            scheme="",
            value="240",
        )


def test_external_identifier_rejects_empty_value():
    with pytest.raises(ValueError):
        ExternalIdentifier(
            scheme="pubchem.cid",
            value="",
        )


def test_external_identifier_rejects_non_string_scheme():
    with pytest.raises(TypeError):
        ExternalIdentifier(
            scheme=123,  # type: ignore[arg-type]
            value="240",
        )


def test_external_identifier_rejects_non_string_value():
    with pytest.raises(TypeError):
        ExternalIdentifier(
            scheme="pubchem.cid",
            value=240,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Condition
# ---------------------------------------------------------------------------


def test_condition_accepts_property_and_value():
    condition = Condition(
        property="dilution",
        value="1/1000",
    )

    assert condition.property == "dilution"
    assert condition.value == "1/1000"
    assert condition.unit is None
    assert condition.extra == {}


def test_condition_accepts_numeric_value_and_unit():
    condition = Condition(
        property="concentration",
        value=0.001,
        unit="mol/L",
    )

    assert condition.property == "concentration"
    assert condition.value == 0.001
    assert condition.unit == "mol/L"


def test_condition_preserves_zero():
    condition = Condition(
        property="concentration",
        value=0.0,
        unit="mol/L",
    )

    assert condition.value == 0.0


def test_condition_accepts_arbitrary_value():
    condition = Condition(
        property="delivery",
        value={
            "method": "headspace",
            "flow": 2.5,
        },
    )

    assert condition.value == {
        "method": "headspace",
        "flow": 2.5,
    }


def test_condition_accepts_extra_data():
    condition = Condition(
        property="temperature",
        value=25.0,
        unit="C",
        extra={
            "method": "measured",
        },
    )

    assert condition.extra == {
        "method": "measured",
    }


def test_condition_rejects_empty_property():
    with pytest.raises(ValueError):
        Condition(
            property="",
            value=1,
        )


def test_condition_rejects_non_string_property():
    with pytest.raises(TypeError):
        Condition(
            property=123,  # type: ignore[arg-type]
            value=1,
        )


def test_condition_rejects_empty_unit():
    with pytest.raises(ValueError):
        Condition(
            property="temperature",
            value=25,
            unit="",
        )


def test_condition_rejects_non_dictionary_extra():
    with pytest.raises(TypeError):
        Condition(
            property="temperature",
            value=25,
            extra=[],  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# ResultScheme
# ---------------------------------------------------------------------------


def test_result_scheme_accepts_id_and_version():
    scheme = ResultScheme(
        id="org.opensmell.example",
        version="0.1",
    )

    assert scheme.id == "org.opensmell.example"
    assert scheme.version == "0.1"
    assert scheme.extra == {}


def test_result_scheme_accepts_extra_data():
    scheme = ResultScheme(
        id="org.opensmell.example",
        version="0.1",
        extra={
            "status": "experimental",
        },
    )

    assert scheme.extra == {
        "status": "experimental",
    }


def test_result_scheme_rejects_empty_id():
    with pytest.raises(ValueError):
        ResultScheme(
            id="",
            version="0.1",
        )


def test_result_scheme_rejects_non_string_id():
    with pytest.raises(TypeError):
        ResultScheme(
            id=123,  # type: ignore[arg-type]
            version="0.1",
        )


def test_result_scheme_rejects_empty_version():
    with pytest.raises(ValueError):
        ResultScheme(
            id="org.opensmell.example",
            version="",
        )


def test_result_scheme_rejects_non_string_version():
    with pytest.raises(TypeError):
        ResultScheme(
            id="org.opensmell.example",
            version=1,  # type: ignore[arg-type]
        )


def test_result_scheme_rejects_non_dictionary_extra():
    with pytest.raises(TypeError):
        ResultScheme(
            id="org.opensmell.example",
            version="0.1",
            extra=[],  # type: ignore[arg-type]
        )


def test_result_scheme_versions_are_distinct():
    version_01 = ResultScheme(
        id="org.opensmell.example",
        version="0.1",
    )

    version_02 = ResultScheme(
        id="org.opensmell.example",
        version="0.2",
    )

    assert version_01 != version_02
    assert version_01.id == version_02.id
    assert version_01.version != version_02.version


def test_unknown_result_scheme_is_representable():
    scheme = ResultScheme(
        id="vendor.example.future-result",
        version="9.7",
        extra={
            "vendor_extension": True,
        },
    )

    assert scheme.id == "vendor.example.future-result"
    assert scheme.version == "9.7"
    assert scheme.extra == {
        "vendor_extension": True,
    }


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


def test_result_accepts_scheme_defined_data():
    scheme = example_result_scheme()

    result = Result(
        scheme=scheme,
        data={
            "value": 42.0,
            "state": "detected",
        },
    )

    assert result.scheme == scheme
    assert result.scheme.id == "org.opensmell.example"
    assert result.scheme.version == "0.1"

    assert result.data == {
        "value": 42.0,
        "state": "detected",
    }


def test_result_allows_empty_data():
    result = Result(
        scheme=example_result_scheme(),
    )

    assert result.data == {}
    assert result.extra == {}


def test_result_accepts_arbitrary_nested_data():
    result = Result(
        scheme=example_result_scheme(),
        data={
            "measurements": [
                {
                    "property": "intensity",
                    "value": 42.0,
                    "scale": {
                        "min": 0,
                        "max": 100,
                    },
                }
            ],
            "metadata": {
                "source": "example",
            },
        },
    )

    assert (
        result.data["measurements"][0]["property"]
        == "intensity"
    )

    assert result.data["metadata"] == {
        "source": "example",
    }


def test_result_preserves_numeric_zero():
    result = Result(
        scheme=example_result_scheme(),
        data={
            "value": 0.0,
        },
    )

    assert result.data["value"] == 0.0


def test_result_preserves_negative_zero():
    result = Result(
        scheme=example_result_scheme(),
        data={
            "value": -0.0,
        },
    )

    assert result.data["value"] == -0.0


def test_result_accepts_extra_data():
    result = Result(
        scheme=example_result_scheme(),
        data={
            "value": 42.0,
        },
        extra={
            "future": True,
        },
    )

    assert result.extra == {
        "future": True,
    }


def test_result_rejects_string_scheme():
    with pytest.raises(TypeError):
        Result(
            scheme="org.opensmell.example",  # type: ignore[arg-type]
        )


def test_result_rejects_non_result_scheme():
    with pytest.raises(TypeError):
        Result(
            scheme=123,  # type: ignore[arg-type]
        )


def test_result_rejects_non_dictionary_data():
    with pytest.raises(TypeError):
        Result(
            scheme=example_result_scheme(),
            data=[],  # type: ignore[arg-type]
        )


def test_result_rejects_non_dictionary_extra():
    with pytest.raises(TypeError):
        Result(
            scheme=example_result_scheme(),
            extra=[],  # type: ignore[arg-type]
        )


def test_unknown_result_scheme_is_preserved():
    scheme = ResultScheme(
        id="example.future.unknown.scheme",
        version="3.4",
    )

    result = Result(
        scheme=scheme,
        data={
            "arbitrary": {
                "future": True,
            }
        },
    )

    assert result.scheme == scheme
    assert result.scheme.id == "example.future.unknown.scheme"
    assert result.scheme.version == "3.4"

    assert result.data == {
        "arbitrary": {
            "future": True,
        }
    }


# ---------------------------------------------------------------------------
# Stimulus
# ---------------------------------------------------------------------------


def test_stimulus_accepts_minimal_resource():
    stimulus = Stimulus(
        id="stimulus-1"
    )

    assert stimulus.id == "stimulus-1"
    assert stimulus.source is None
    assert stimulus.identifiers == []
    assert stimulus.conditions == []
    assert stimulus.extra == {}


def test_stimulus_accepts_source_reference():
    source = Reference(
        resource_id="molecule-1"
    )

    stimulus = Stimulus(
        id="stimulus-1",
        source=source,
    )

    assert stimulus.source == source


def test_stimulus_accepts_external_identifiers():
    identifier = ExternalIdentifier(
        scheme="dataset.stimulus",
        value="stimulus-A",
    )

    stimulus = Stimulus(
        id="stimulus-1",
        identifiers=[
            identifier
        ],
    )

    assert stimulus.identifiers == [
        identifier
    ]


def test_stimulus_accepts_conditions():
    condition = Condition(
        property="concentration",
        value=1e-6,
        unit="mol/L",
    )

    stimulus = Stimulus(
        id="stimulus-1",
        conditions=[
            condition
        ],
    )

    assert stimulus.conditions == [
        condition
    ]


def test_stimulus_can_have_no_source_and_no_conditions():
    stimulus = Stimulus(
        id="stimulus-empty"
    )

    assert stimulus.source is None
    assert stimulus.conditions == []


def test_stimulus_accepts_extra_data():
    stimulus = Stimulus(
        id="stimulus-1",
        extra={
            "source_note": "experimental",
        },
    )

    assert stimulus.extra == {
        "source_note": "experimental",
    }


def test_stimulus_rejects_empty_id():
    with pytest.raises(ValueError):
        Stimulus(
            id=""
        )


def test_stimulus_rejects_non_string_id():
    with pytest.raises(TypeError):
        Stimulus(
            id=123,  # type: ignore[arg-type]
        )


def test_stimulus_rejects_invalid_source():
    with pytest.raises(TypeError):
        Stimulus(
            id="stimulus-1",
            source="molecule-1",  # type: ignore[arg-type]
        )


def test_stimulus_rejects_non_list_identifiers():
    with pytest.raises(TypeError):
        Stimulus(
            id="stimulus-1",
            identifiers={},  # type: ignore[arg-type]
        )


def test_stimulus_rejects_non_list_conditions():
    with pytest.raises(TypeError):
        Stimulus(
            id="stimulus-1",
            conditions={},  # type: ignore[arg-type]
        )


def test_stimulus_rejects_non_dictionary_extra():
    with pytest.raises(TypeError):
        Stimulus(
            id="stimulus-1",
            extra=[],  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# ObservationTarget
# ---------------------------------------------------------------------------


def test_observation_target_accepts_minimal_resource():
    target = ObservationTarget(
        id="target-1"
    )

    assert target.id == "target-1"
    assert target.identifiers == []
    assert target.extra == {}


def test_observation_target_accepts_external_identifier():
    identifier = ExternalIdentifier(
        scheme="burton.roi",
        value="113L_038",
    )

    target = ObservationTarget(
        id="target-1",
        identifiers=[
            identifier
        ],
    )

    assert target.identifiers == [
        identifier
    ]


def test_observation_target_accepts_extra_data():
    target = ObservationTarget(
        id="target-1",
        extra={
            "kind": "roi",
        },
    )

    assert target.extra == {
        "kind": "roi",
    }


def test_observation_target_can_represent_composite_sensor_array():
    target = ObservationTarget(
        id="sensor-array-1",
        extra={
            "kind": "electronic_sensor_array",
            "sensor_count": 16,
        },
    )

    assert target.extra["kind"] == "electronic_sensor_array"
    assert target.extra["sensor_count"] == 16


def test_observation_target_rejects_empty_id():
    with pytest.raises(ValueError):
        ObservationTarget(
            id=""
        )


def test_observation_target_rejects_non_string_id():
    with pytest.raises(TypeError):
        ObservationTarget(
            id=123,  # type: ignore[arg-type]
        )


def test_observation_target_rejects_non_list_identifiers():
    with pytest.raises(TypeError):
        ObservationTarget(
            id="target-1",
            identifiers={},  # type: ignore[arg-type]
        )


def test_observation_target_rejects_non_dictionary_extra():
    with pytest.raises(TypeError):
        ObservationTarget(
            id="target-1",
            extra=[],  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------


def test_observation_accepts_minimal_resource():
    stimulus_reference = Reference(
        resource_id="stimulus-1"
    )

    observation = Observation(
        id="observation-1",
        stimulus=stimulus_reference,
    )

    assert observation.id == "observation-1"
    assert observation.stimulus == stimulus_reference
    assert observation.target is None
    assert observation.results == []
    assert observation.context == {}
    assert observation.identifiers == []
    assert observation.extra == {}


def test_observation_accepts_target_reference():
    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        target=Reference(
            resource_id="target-1"
        ),
    )

    assert observation.target == Reference(
        resource_id="target-1"
    )


def test_observation_accepts_single_result():
    result = Result(
        scheme=example_result_scheme(),
        data={
            "value": 42.0,
        },
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        results=[
            result
        ],
    )

    assert observation.results == [
        result
    ]


def test_observation_accepts_multiple_result_schemes():
    categorical = Result(
        scheme=ResultScheme(
            id="org.opensmell.example.categories",
            version="0.1",
        ),
        data={
            "detection": "detected",
        },
    )

    perceptual = Result(
        scheme=ResultScheme(
            id="org.opensmell.example.perceptual",
            version="0.1",
        ),
        data={
            "measurements": [
                {
                    "property": "intensity",
                    "value": 42.0,
                }
            ]
        },
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        results=[
            categorical,
            perceptual,
        ],
    )

    assert len(
        observation.results
    ) == 2

    assert (
        observation.results[0].scheme.id
        == "org.opensmell.example.categories"
    )

    assert (
        observation.results[0].scheme.version
        == "0.1"
    )

    assert (
        observation.results[1].scheme.id
        == "org.opensmell.example.perceptual"
    )

    assert (
        observation.results[1].scheme.version
        == "0.1"
    )


def test_observation_accepts_same_scheme_with_different_versions():
    version_01 = Result(
        scheme=ResultScheme(
            id="org.opensmell.example",
            version="0.1",
        ),
        data={
            "value": 1,
        },
    )

    version_02 = Result(
        scheme=ResultScheme(
            id="org.opensmell.example",
            version="0.2",
        ),
        data={
            "value": 2,
        },
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        results=[
            version_01,
            version_02,
        ],
    )

    assert (
        observation.results[0].scheme.id
        == observation.results[1].scheme.id
    )

    assert (
        observation.results[0].scheme.version
        != observation.results[1].scheme.version
    )


def test_observation_preserves_zero_inside_result():
    result = Result(
        scheme=example_result_scheme(),
        data={
            "measurements": [
                {
                    "property": "delta_f",
                    "value": 0.0,
                }
            ]
        },
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        results=[
            result
        ],
    )

    assert (
        observation.results[0]
        .data["measurements"][0]["value"]
        == 0.0
    )


def test_observation_accepts_context():
    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        context={
            "measurement_domain": "physiological",
        },
    )

    assert observation.context == {
        "measurement_domain": "physiological",
    }


def test_observation_accepts_external_identifier():
    identifier = ExternalIdentifier(
        scheme="dataset.observation",
        value="observation-A",
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        identifiers=[
            identifier
        ],
    )

    assert observation.identifiers == [
        identifier
    ]


def test_observation_accepts_extra_data():
    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        extra={
            "future": True,
        },
    )

    assert observation.extra == {
        "future": True,
    }


def test_observation_preserves_unresolved_reference():
    """Structural models must not require graph resolution."""

    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="missing-stimulus"
        ),
        target=Reference(
            resource_id="missing-target"
        ),
    )

    assert (
        observation.stimulus.resource_id
        == "missing-stimulus"
    )

    assert observation.target is not None

    assert (
        observation.target.resource_id
        == "missing-target"
    )


def test_observation_with_unknown_result_scheme():
    result = Result(
        scheme=ResultScheme(
            id="vendor.example.future-result",
            version="4.2",
        ),
        data={
            "something": 123,
        },
    )

    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
        results=[
            result
        ],
    )

    assert (
        observation.results[0].scheme.id
        == "vendor.example.future-result"
    )

    assert (
        observation.results[0].scheme.version
        == "4.2"
    )

    assert observation.results[0].data == {
        "something": 123,
    }


def test_observation_can_have_no_results():
    observation = Observation(
        id="observation-1",
        stimulus=Reference(
            resource_id="stimulus-1"
        ),
    )

    assert observation.results == []


def test_observation_rejects_empty_id():
    with pytest.raises(ValueError):
        Observation(
            id="",
            stimulus=Reference(
                resource_id="stimulus-1"
            ),
        )


def test_observation_rejects_invalid_stimulus():
    with pytest.raises(TypeError):
        Observation(
            id="observation-1",
            stimulus="stimulus-1",  # type: ignore[arg-type]
        )


def test_observation_rejects_invalid_target():
    with pytest.raises(TypeError):
        Observation(
            id="observation-1",
            stimulus=Reference(
                resource_id="stimulus-1"
            ),
            target="target-1",  # type: ignore[arg-type]
        )


def test_observation_rejects_non_list_results():
    with pytest.raises(TypeError):
        Observation(
            id="observation-1",
            stimulus=Reference(
                resource_id="stimulus-1"
            ),
            results={},  # type: ignore[arg-type]
        )


def test_observation_rejects_non_dictionary_context():
    with pytest.raises(TypeError):
        Observation(
            id="observation-1",
            stimulus=Reference(
                resource_id="stimulus-1"
            ),
            context=[],  # type: ignore[arg-type]
        )


def test_observation_rejects_non_list_identifiers():
    with pytest.raises(TypeError):
        Observation(
            id="observation-1",
            stimulus=Reference(
                resource_id="stimulus-1"
            ),
            identifiers={},  # type: ignore[arg-type]
        )


def test_observation_rejects_non_dictionary_extra():
    with pytest.raises(TypeError):
        Observation(
            id="observation-1",
            stimulus=Reference(
                resource_id="stimulus-1"
            ),
            extra=[],  # type: ignore[arg-type]
        )