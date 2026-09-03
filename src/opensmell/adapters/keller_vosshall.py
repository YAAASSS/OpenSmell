"""Adapter for Keller/Vosshall psychophysical olfaction records."""

from typing import Any

from ..models import Representation, Scheme


SCHEME_ID = "org.opensmell.perceptual.measurements"
SCHEME_VERSION = "0.1"

GLOBAL_RATINGS = {
    "HOW STRONG IS THE SMELL?": "intensity",
    "HOW PLEASANT IS THE SMELL?": "pleasantness",
    "HOW FAMILIAR IS THE SMELL?": "familiarity",
}

DESCRIPTOR_COLUMNS = (
    "EDIBLE",
    "BAKERY",
    "SWEET",
    "FRUIT",
    "FISH",
    "GARLIC",
    "SPICES",
    "COLD",
    "SOUR",
    "BURNT",
    "ACID",
    "WARM",
    "MUSKY",
    "SWEATY",
    "AMMONIA/URINOUS",
    "DECAYED",
    "WOOD",
    "GRASS",
    "FLOWER",
    "CHEMICAL",
)


def _is_missing(value: Any) -> bool:
    """Return True for source values treated as missing."""

    if value is None:
        return True

    try:
        return value != value
    except (TypeError, ValueError):
        return False


def _numeric_value(value: Any, *, field: str) -> int | float:
    """Return a validated numeric psychophysical value."""

    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")

    if isinstance(value, (int, float)):
        numeric = value
    else:
        try:
            numeric = float(str(value).strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{field} must be numeric"
            ) from error

    if not 0 <= numeric <= 100:
        raise ValueError(
            f"{field} must be between 0 and 100"
        )

    if isinstance(numeric, float) and numeric.is_integer():
        return int(numeric)

    return numeric


def _measurement(
    property_name: str,
    value: Any,
    *,
    source_field: str,
) -> dict[str, Any]:
    """Build one Keller/Vosshall perceptual measurement."""

    return {
        "property": property_name,
        "value": _numeric_value(
            value,
            field=source_field,
        ),
        "scale": {
            "min": 0,
            "max": 100,
        },
    }


def measurements_from_record(
    record: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract explicit perceptual measurements from a source row.

    Missing source values are omitted. This function does not infer zero
    values from missing descriptor cells.
    """

    measurements: list[dict[str, Any]] = []

    for source_field, property_name in GLOBAL_RATINGS.items():
        value = record.get(source_field)

        if _is_missing(value):
            continue

        measurements.append(
            _measurement(
                property_name,
                value,
                source_field=source_field,
            )
        )

    for source_field in DESCRIPTOR_COLUMNS:
        value = record.get(source_field)

        if _is_missing(value):
            continue

        measurements.append(
            _measurement(
                source_field.lower(),
                value,
                source_field=source_field,
            )
        )

    return measurements


def representation_from_record(
    record: dict[str, Any],
) -> Representation | None:
    """Convert one source row into a perceptual representation.

    Rows without explicit perceptual measurements return None rather than
    inventing numerical values.
    """

    measurements = measurements_from_record(record)

    if not measurements:
        return None

    representation = Representation(
        type="perceptual",
        scheme=Scheme(
            id=SCHEME_ID,
            version=SCHEME_VERSION,
        ),
        data={
            "measurements": measurements,
        },
    )

    representation.extra["provenance"] = {
        "source": "Keller/Vosshall",
    }

    return representation