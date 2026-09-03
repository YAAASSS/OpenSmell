"""Experimental OpenSmell resource models.

These models are intentionally outside the OpenSmell 0.1 Core specification.

They are used to explore resource-oriented concepts such as:

- references;
- external identifiers;
- stimuli;
- observation targets;
- observations;
- scheme-defined observation results.

Nothing in this module is normative.

The experimental models may change incompatibly before being promoted into
a future OpenSmell specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _require_nonempty_string(
    value: Any,
    *,
    field_name: str,
) -> str:
    """Validate a required non-empty string."""

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string."
        )

    if not value:
        raise ValueError(
            f"{field_name} must not be empty."
        )

    return value


def _validate_optional_unit(
    unit: str | None,
) -> None:
    """Validate an optional unit string."""

    if unit is None:
        return

    _require_nonempty_string(
        unit,
        field_name="unit",
    )


# ---------------------------------------------------------------------------
# References and external identifiers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Reference:
    """Reference to another OpenSmell resource.

    Resource ID syntax is deliberately not coupled to RFC-0006 here.

    RFC-0006 is still experimental, so this model only requires a non-empty
    string. A future normative resource model may impose stronger Resource ID
    requirements.
    """

    resource_id: str

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.resource_id,
            field_name="resource_id",
        )


@dataclass(frozen=True)
class ExternalIdentifier:
    """Identifier assigned by an external dataset or system."""

    scheme: str
    value: str

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.scheme,
            field_name="scheme",
        )

        _require_nonempty_string(
            self.value,
            field_name="value",
        )


# ---------------------------------------------------------------------------
# Stimulus conditions
# ---------------------------------------------------------------------------


@dataclass
class Condition:
    """Condition under which a resource is presented or applied.

    The value is intentionally open-ended.

    Examples include concentration, dilution, temperature, duration,
    carrier, flow, or another dataset-specific condition.

    The generic resource model does not define a normative unit system.
    """

    property: str
    value: Any
    unit: str | None = None
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.property,
            field_name="property",
        )

        _validate_optional_unit(
            self.unit
        )

        if not isinstance(
            self.extra,
            dict,
        ):
            raise TypeError(
                "extra must be a dictionary."
            )


# ---------------------------------------------------------------------------
# Scheme-defined observation results
# ---------------------------------------------------------------------------


@dataclass
class Result:
    """Scheme-defined result attached to an Observation.

    Observation itself does not interpret the contents of ``data``.

    The ``scheme`` identifies the rules required to interpret those data.

    This allows categorical, perceptual, physiological, sensor, model, and
    future result types to coexist without forcing them into one universal
    measurement structure.

    Unknown schemes are intentionally representable.

    Scheme-specific validation belongs outside this generic resource model.
    """

    scheme: str
    data: dict[str, Any] = field(
        default_factory=dict
    )
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.scheme,
            field_name="scheme",
        )

        if not isinstance(
            self.data,
            dict,
        ):
            raise TypeError(
                "data must be a dictionary."
            )

        if not isinstance(
            self.extra,
            dict,
        ):
            raise TypeError(
                "extra must be a dictionary."
            )


# ---------------------------------------------------------------------------
# Stimulus resources
# ---------------------------------------------------------------------------


@dataclass
class Stimulus:
    """Something presented to or applied to an observation target.

    A Stimulus is not the same thing as an Odor or molecule.

    ``source`` may reference an odor, molecule, mixture, or another resource
    describing what was presented.

    ``conditions`` describe presentation conditions such as concentration,
    dilution, temperature, duration, carrier, or flow.

    A source or condition may legitimately be unknown.
    """

    id: str
    source: Reference | None = None
    identifiers: list[
        ExternalIdentifier
    ] = field(
        default_factory=list
    )
    conditions: list[
        Condition
    ] = field(
        default_factory=list
    )
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.id,
            field_name="id",
        )

        if (
            self.source is not None
            and not isinstance(
                self.source,
                Reference,
            )
        ):
            raise TypeError(
                "source must be a Reference or None."
            )

        if not isinstance(
            self.identifiers,
            list,
        ):
            raise TypeError(
                "identifiers must be a list."
            )

        if not isinstance(
            self.conditions,
            list,
        ):
            raise TypeError(
                "conditions must be a list."
            )

        if not isinstance(
            self.extra,
            dict,
        ):
            raise TypeError(
                "extra must be a dictionary."
            )


# ---------------------------------------------------------------------------
# Observation targets
# ---------------------------------------------------------------------------


@dataclass
class ObservationTarget:
    """Target with respect to which an observation is made.

    The term ``target`` is deliberately generic.

    A target may represent, for example:

    - a human participant;
    - an animal;
    - a receptor;
    - a glomerulus or ROI;
    - a physical sensor;
    - a computational model.

    Domain-specific meaning belongs in identifiers, extensions, or
    scheme-defined data rather than in the generic resource graph.
    """

    id: str
    identifiers: list[
        ExternalIdentifier
    ] = field(
        default_factory=list
    )
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.id,
            field_name="id",
        )

        if not isinstance(
            self.identifiers,
            list,
        ):
            raise TypeError(
                "identifiers must be a list."
            )

        if not isinstance(
            self.extra,
            dict,
        ):
            raise TypeError(
                "extra must be a dictionary."
            )


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------


@dataclass
class Observation:
    """Observation associated with a Stimulus and optional target.

    ``stimulus`` is required because the observation must identify what was
    presented or applied.

    ``target`` remains optional because some observation sources may not
    expose or define a target.

    ``results`` contains scheme-defined payloads.

    The Observation resource deliberately does not define a universal
    Measurement object. Interpretation and validation of result data belong
    to the scheme identified by each Result.
    """

    id: str
    stimulus: Reference
    target: Reference | None = None

    results: list[
        Result
    ] = field(
        default_factory=list
    )

    context: dict[str, Any] = field(
        default_factory=dict
    )

    identifiers: list[
        ExternalIdentifier
    ] = field(
        default_factory=list
    )

    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.id,
            field_name="id",
        )

        if not isinstance(
            self.stimulus,
            Reference,
        ):
            raise TypeError(
                "stimulus must be a Reference."
            )

        if (
            self.target is not None
            and not isinstance(
                self.target,
                Reference,
            )
        ):
            raise TypeError(
                "target must be a Reference or None."
            )

        if not isinstance(
            self.results,
            list,
        ):
            raise TypeError(
                "results must be a list."
            )

        if not isinstance(
            self.context,
            dict,
        ):
            raise TypeError(
                "context must be a dictionary."
            )

        if not isinstance(
            self.identifiers,
            list,
        ):
            raise TypeError(
                "identifiers must be a list."
            )

        if not isinstance(
            self.extra,
            dict,
        ):
            raise TypeError(
                "extra must be a dictionary."
            )