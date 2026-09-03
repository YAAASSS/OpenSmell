"""Experimental JSON serialization for OpenSmell resource graphs.

This module defines the experimental exchange representation for the
RFC-0007 resource graph model.

It is intentionally separate from the OpenSmell 0.1 Core parser and
serializer.

Experimental document envelope:

{
    "format": "org.opensmell.experimental.resource-graph",
    "version": "0.1",
    "resources": [...]
}

Unknown fields are preserved through each model object's ``extra`` mapping.

Unresolved references are preserved and do not cause parsing failure.
"""

from __future__ import annotations

import json
from typing import Any

from .graph import Resource, ResourceGraph
from .resources import (
    Condition,
    ExternalIdentifier,
    Observation,
    ObservationTarget,
    Reference,
    Result,
    ResultScheme,
    Stimulus,
)


RESOURCE_GRAPH_FORMAT = "org.opensmell.experimental.resource-graph"
RESOURCE_GRAPH_VERSION = "0.1"


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")

    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a list")

    return value


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")

    if not value:
        raise ValueError(f"{name} must not be empty")

    return value


def _split_known_fields(
    value: dict[str, Any],
    known_fields: set[str],
) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key not in known_fields
    }


def _merge_extra(
    extra: dict[str, Any],
    official: dict[str, Any],
) -> dict[str, Any]:
    """Merge extension fields with official fields.

    Official fields always win over extension data.
    """

    result = dict(extra)
    result.update(official)
    return result


def reference_to_dict(reference: Reference) -> dict[str, Any]:
    if not isinstance(reference, Reference):
        raise TypeError("reference must be a Reference")

    return {
        "resource_id": reference.resource_id,
    }


def reference_from_dict(value: Any) -> Reference:
    obj = _require_dict(value, "reference")

    resource_id = _require_string(
        obj.get("resource_id"),
        "reference.resource_id",
    )

    return Reference(resource_id=resource_id)


def external_identifier_to_dict(
    identifier: ExternalIdentifier,
) -> dict[str, Any]:
    if not isinstance(identifier, ExternalIdentifier):
        raise TypeError(
            "identifier must be an ExternalIdentifier"
        )

    return {
        "scheme": identifier.scheme,
        "value": identifier.value,
    }


def external_identifier_from_dict(
    value: Any,
) -> ExternalIdentifier:
    obj = _require_dict(value, "external identifier")

    scheme = _require_string(
        obj.get("scheme"),
        "external identifier.scheme",
    )

    identifier_value = _require_string(
        obj.get("value"),
        "external identifier.value",
    )

    return ExternalIdentifier(
        scheme=scheme,
        value=identifier_value,
    )


def condition_to_dict(condition: Condition) -> dict[str, Any]:
    if not isinstance(condition, Condition):
        raise TypeError("condition must be a Condition")

    official: dict[str, Any] = {
        "property": condition.property,
        "value": condition.value,
    }

    if condition.unit is not None:
        official["unit"] = condition.unit

    return _merge_extra(
        condition.extra,
        official,
    )


def condition_from_dict(value: Any) -> Condition:
    obj = _require_dict(value, "condition")

    property_name = _require_string(
        obj.get("property"),
        "condition.property",
    )

    if "value" not in obj:
        raise ValueError("condition.value is required")

    unit = obj.get("unit")

    if unit is not None:
        unit = _require_string(
            unit,
            "condition.unit",
        )

    extra = _split_known_fields(
        obj,
        {
            "property",
            "value",
            "unit",
        },
    )

    return Condition(
        property=property_name,
        value=obj["value"],
        unit=unit,
        extra=extra,
    )


def result_scheme_to_dict(
    scheme: ResultScheme,
) -> dict[str, Any]:
    if not isinstance(scheme, ResultScheme):
        raise TypeError("scheme must be a ResultScheme")

    return _merge_extra(
        scheme.extra,
        {
            "id": scheme.id,
            "version": scheme.version,
        },
    )


def result_scheme_from_dict(value: Any) -> ResultScheme:
    obj = _require_dict(value, "result scheme")

    scheme_id = _require_string(
        obj.get("id"),
        "result scheme.id",
    )

    version = _require_string(
        obj.get("version"),
        "result scheme.version",
    )

    extra = _split_known_fields(
        obj,
        {
            "id",
            "version",
        },
    )

    return ResultScheme(
        id=scheme_id,
        version=version,
        extra=extra,
    )


def result_to_dict(result: Result) -> dict[str, Any]:
    if not isinstance(result, Result):
        raise TypeError("result must be a Result")

    return _merge_extra(
        result.extra,
        {
            "scheme": result_scheme_to_dict(
                result.scheme
            ),
            "data": result.data,
        },
    )


def result_from_dict(value: Any) -> Result:
    obj = _require_dict(value, "result")

    if "scheme" not in obj:
        raise ValueError("result.scheme is required")

    if "data" not in obj:
        raise ValueError("result.data is required")

    data = _require_dict(
        obj["data"],
        "result.data",
    )

    extra = _split_known_fields(
        obj,
        {
            "scheme",
            "data",
        },
    )

    return Result(
        scheme=result_scheme_from_dict(
            obj["scheme"]
        ),
        data=data,
        extra=extra,
    )


def stimulus_to_dict(stimulus: Stimulus) -> dict[str, Any]:
    if not isinstance(stimulus, Stimulus):
        raise TypeError("stimulus must be a Stimulus")

    official: dict[str, Any] = {
        "type": "stimulus",
        "id": stimulus.id,
    }

    if stimulus.source is not None:
        official["source"] = reference_to_dict(
            stimulus.source
        )

    if stimulus.identifiers:
        official["identifiers"] = [
            external_identifier_to_dict(identifier)
            for identifier in stimulus.identifiers
        ]

    if stimulus.conditions:
        official["conditions"] = [
            condition_to_dict(condition)
            for condition in stimulus.conditions
        ]

    return _merge_extra(
        stimulus.extra,
        official,
    )


def stimulus_from_dict(value: Any) -> Stimulus:
    obj = _require_dict(value, "stimulus")

    resource_id = _require_string(
        obj.get("id"),
        "stimulus.id",
    )

    source = None

    if "source" in obj and obj["source"] is not None:
        source = reference_from_dict(
            obj["source"]
        )

    identifiers: list[ExternalIdentifier] = []

    if "identifiers" in obj:
        identifiers = [
            external_identifier_from_dict(item)
            for item in _require_list(
                obj["identifiers"],
                "stimulus.identifiers",
            )
        ]

    conditions: list[Condition] = []

    if "conditions" in obj:
        conditions = [
            condition_from_dict(item)
            for item in _require_list(
                obj["conditions"],
                "stimulus.conditions",
            )
        ]

    extra = _split_known_fields(
        obj,
        {
            "type",
            "id",
            "source",
            "identifiers",
            "conditions",
        },
    )

    return Stimulus(
        id=resource_id,
        source=source,
        identifiers=identifiers,
        conditions=conditions,
        extra=extra,
    )


def observation_target_to_dict(
    target: ObservationTarget,
) -> dict[str, Any]:
    if not isinstance(target, ObservationTarget):
        raise TypeError(
            "target must be an ObservationTarget"
        )

    official: dict[str, Any] = {
        "type": "observation_target",
        "id": target.id,
    }

    if target.identifiers:
        official["identifiers"] = [
            external_identifier_to_dict(identifier)
            for identifier in target.identifiers
        ]

    return _merge_extra(
        target.extra,
        official,
    )


def observation_target_from_dict(
    value: Any,
) -> ObservationTarget:
    obj = _require_dict(
        value,
        "observation target",
    )

    resource_id = _require_string(
        obj.get("id"),
        "observation target.id",
    )

    identifiers: list[ExternalIdentifier] = []

    if "identifiers" in obj:
        identifiers = [
            external_identifier_from_dict(item)
            for item in _require_list(
                obj["identifiers"],
                "observation target.identifiers",
            )
        ]

    extra = _split_known_fields(
        obj,
        {
            "type",
            "id",
            "identifiers",
        },
    )

    return ObservationTarget(
        id=resource_id,
        identifiers=identifiers,
        extra=extra,
    )


def observation_to_dict(
    observation: Observation,
) -> dict[str, Any]:
    if not isinstance(observation, Observation):
        raise TypeError(
            "observation must be an Observation"
        )

    official: dict[str, Any] = {
        "type": "observation",
        "id": observation.id,
        "stimulus": reference_to_dict(
            observation.stimulus
        ),
    }

    if observation.target is not None:
        official["target"] = reference_to_dict(
            observation.target
        )

    if observation.results:
        official["results"] = [
            result_to_dict(result)
            for result in observation.results
        ]

    if observation.context:
        official["context"] = observation.context

    if observation.identifiers:
        official["identifiers"] = [
            external_identifier_to_dict(identifier)
            for identifier in observation.identifiers
        ]

    return _merge_extra(
        observation.extra,
        official,
    )


def observation_from_dict(value: Any) -> Observation:
    obj = _require_dict(value, "observation")

    resource_id = _require_string(
        obj.get("id"),
        "observation.id",
    )

    if "stimulus" not in obj:
        raise ValueError(
            "observation.stimulus is required"
        )

    stimulus = reference_from_dict(
        obj["stimulus"]
    )

    target = None

    if "target" in obj and obj["target"] is not None:
        target = reference_from_dict(
            obj["target"]
        )

    results: list[Result] = []

    if "results" in obj:
        results = [
            result_from_dict(item)
            for item in _require_list(
                obj["results"],
                "observation.results",
            )
        ]

    context: dict[str, Any] = {}

    if "context" in obj:
        context = _require_dict(
            obj["context"],
            "observation.context",
        )

    identifiers: list[ExternalIdentifier] = []

    if "identifiers" in obj:
        identifiers = [
            external_identifier_from_dict(item)
            for item in _require_list(
                obj["identifiers"],
                "observation.identifiers",
            )
        ]

    extra = _split_known_fields(
        obj,
        {
            "type",
            "id",
            "stimulus",
            "target",
            "results",
            "context",
            "identifiers",
        },
    )

    return Observation(
        id=resource_id,
        stimulus=stimulus,
        target=target,
        results=results,
        context=context,
        identifiers=identifiers,
        extra=extra,
    )


def resource_to_dict(
    resource: Resource,
) -> dict[str, Any]:
    if isinstance(resource, Stimulus):
        return stimulus_to_dict(resource)

    if isinstance(resource, ObservationTarget):
        return observation_target_to_dict(
            resource
        )

    if isinstance(resource, Observation):
        return observation_to_dict(resource)

    raise TypeError(
        "unsupported resource type"
    )


def resource_from_dict(value: Any) -> Resource:
    obj = _require_dict(value, "resource")

    resource_type = _require_string(
        obj.get("type"),
        "resource.type",
    )

    if resource_type == "stimulus":
        return stimulus_from_dict(obj)

    if resource_type == "observation_target":
        return observation_target_from_dict(
            obj
        )

    if resource_type == "observation":
        return observation_from_dict(obj)

    raise ValueError(
        f"unknown resource type: {resource_type!r}"
    )


def graph_to_dict(
    graph: ResourceGraph,
) -> dict[str, Any]:
    if not isinstance(graph, ResourceGraph):
        raise TypeError(
            "graph must be a ResourceGraph"
        )

    return _merge_extra(
        graph.extra,
        {
            "format": RESOURCE_GRAPH_FORMAT,
            "version": RESOURCE_GRAPH_VERSION,
            "resources": [
                resource_to_dict(resource)
                for resource in graph.resources
            ],
        },
    )


def graph_from_dict(value: Any) -> ResourceGraph:
    obj = _require_dict(
        value,
        "resource graph document",
    )

    document_format = _require_string(
        obj.get("format"),
        "resource graph format",
    )

    if document_format != RESOURCE_GRAPH_FORMAT:
        raise ValueError(
            "unsupported resource graph format: "
            f"{document_format!r}"
        )

    version = _require_string(
        obj.get("version"),
        "resource graph version",
    )

    if version != RESOURCE_GRAPH_VERSION:
        raise ValueError(
            "unsupported resource graph version: "
            f"{version!r}"
        )

    if "resources" not in obj:
        raise ValueError(
            "resource graph resources are required"
        )

    resources = [
        resource_from_dict(item)
        for item in _require_list(
            obj["resources"],
            "resource graph resources",
        )
    ]

    extra = _split_known_fields(
        obj,
        {
            "format",
            "version",
            "resources",
        },
    )

    return ResourceGraph(
        resources=resources,
        extra=extra,
    )


def dumps(
    graph: ResourceGraph,
    *,
    indent: int | None = 2,
) -> str:
    """Serialize a ResourceGraph to JSON text."""

    return json.dumps(
        graph_to_dict(graph),
        ensure_ascii=False,
        indent=indent,
        allow_nan=False,
    )


def _reject_nonstandard_json_constant(value: str) -> Any:
    """Reject NaN and Infinity tokens accepted by Python's JSON decoder."""

    raise ValueError(
        f"non-standard JSON numeric constant is not allowed: {value}"
    )


def loads(value: str) -> ResourceGraph:
    """Parse a ResourceGraph from JSON text."""

    if not isinstance(value, str):
        raise TypeError(
            "value must be a string"
        )

    parsed = json.loads(
        value,
        parse_constant=_reject_nonstandard_json_constant,
    )

    return graph_from_dict(parsed)