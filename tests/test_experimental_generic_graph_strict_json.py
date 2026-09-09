"""Strict-JSON regression tests for the experimental GenericResourceGraph."""

import pytest

from opensmell.experimental.generic_graph import (
    GenericResource,
    generic_graph_loads,
)


def test_generic_resource_rejects_non_finite_float() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        GenericResource(
            id="future-1",
            type="future.resource",
            data={"value": float("inf")},
        )


@pytest.mark.parametrize(
    "numeric_text",
    [
        "1e400",
        "-1e400",
    ],
)
def test_generic_graph_loads_rejects_finite_json_number_that_overflows_python_float(
    numeric_text: str,
) -> None:
    document = (
        '{"format":"org.opensmell.experimental.generic-resource-graph",'
        '"version":"0.1",'
        '"resources":['
        '{"type":"future.resource","id":"future-1",'
        f'"value":{numeric_text}'
        "}]}"
    )

    with pytest.raises(ValueError, match="must be finite"):
        generic_graph_loads(document)


@pytest.mark.parametrize(
    "numeric_text",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_generic_graph_loads_still_rejects_nonstandard_json_numeric_constants(
    numeric_text: str,
) -> None:
    document = (
        '{"format":"org.opensmell.experimental.generic-resource-graph",'
        '"version":"0.1",'
        '"resources":['
        '{"type":"future.resource","id":"future-1",'
        f'"value":{numeric_text}'
        "}]}"
    )

    with pytest.raises(
        ValueError,
        match="non-standard JSON numeric constant",
    ):
        generic_graph_loads(document)
