"""Validation for quantitative perceptual measurements."""

from typing import Any

from ..exceptions import SchemeValidationError


SCHEME_ID = "org.opensmell.perceptual.measurements"
SCHEME_VERSION = "0.1"


def validate(data: dict[str, Any]) -> None:
    """Validate perceptual measurement scheme data."""

    measurements = data.get("measurements")

    if not isinstance(measurements, list) or not measurements:
        raise SchemeValidationError(
            "perceptual measurements must contain "
            "a non-empty measurements array"
        )

    for index, measurement in enumerate(measurements):
        if not isinstance(measurement, dict):
            raise SchemeValidationError(
                f"measurement {index} must be an object"
            )

        property_name = measurement.get("property")

        if (
            not isinstance(property_name, str)
            or not property_name.strip()
        ):
            raise SchemeValidationError(
                f"measurement {index} property "
                "must be a non-empty string"
            )

        value = measurement.get("value")

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            raise SchemeValidationError(
                f"measurement {index} value must be numeric"
            )

        scale = measurement.get("scale")

        if not isinstance(scale, dict):
            raise SchemeValidationError(
                f"measurement {index} scale must be an object"
            )

        minimum = scale.get("min")
        maximum = scale.get("max")

        if (
            isinstance(minimum, bool)
            or not isinstance(minimum, (int, float))
            or isinstance(maximum, bool)
            or not isinstance(maximum, (int, float))
        ):
            raise SchemeValidationError(
                f"measurement {index} scale boundaries "
                "must be numeric"
            )

        if minimum >= maximum:
            raise SchemeValidationError(
                f"measurement {index} scale min "
                "must be less than max"
            )

        if not minimum <= value <= maximum:
            raise SchemeValidationError(
                f"measurement {index} value "
                "must lie within its scale"
            )