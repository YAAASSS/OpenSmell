"""Regression tests for strict JSON numeric boundaries in experimental models."""

from __future__ import annotations

import math

import pytest

from opensmell.experimental.annotation import Annotation
from opensmell.experimental.odor_graph_bridge import (
    _copy_json_value as bridge_copy_json_value,
)
from opensmell.experimental.resources import Reference
from opensmell.experimental.scheme import Scheme


NON_FINITE_VALUES = (
    float("nan"),
    float("inf"),
    float("-inf"),
)


@pytest.mark.parametrize("value", NON_FINITE_VALUES)
def test_experimental_scheme_rejects_non_finite_extra(
    value: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="JSON numeric values must be finite",
    ):
        Scheme(
            id="org.example.scheme",
            version="0.1",
            extra={
                "nested": {
                    "value": value,
                }
            },
        )


@pytest.mark.parametrize("value", NON_FINITE_VALUES)
def test_experimental_annotation_rejects_non_finite_data(
    value: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="JSON numeric values must be finite",
    ):
        Annotation(
            id="annotation-1",
            subject=Reference(
                resource_id="molecule-1",
            ),
            scheme=Scheme(
                id="org.example.scheme",
                version="0.1",
            ),
            data={
                "nested": [
                    value,
                ]
            },
        )


@pytest.mark.parametrize("value", NON_FINITE_VALUES)
def test_odor_graph_bridge_copy_rejects_non_finite_values(
    value: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="JSON numeric values must be finite",
    ):
        bridge_copy_json_value(
            {
                "nested": [
                    value,
                ]
            }
        )


def test_experimental_json_boundaries_still_accept_finite_numbers() -> None:
    values = [
        -1.5,
        0.0,
        2.5,
        1e308,
    ]

    scheme = Scheme(
        id="org.example.scheme",
        version="0.1",
        extra={
            "values": values,
        },
    )

    annotation = Annotation(
        id="annotation-1",
        subject=Reference(
            resource_id="molecule-1",
        ),
        scheme=scheme,
        data={
            "values": values,
        },
    )

    copied = bridge_copy_json_value(
        {
            "values": values,
        }
    )

    assert all(
        math.isfinite(value)
        for value in scheme.extra["values"]
    )
    assert annotation.data["values"] == values
    assert copied["values"] == values
