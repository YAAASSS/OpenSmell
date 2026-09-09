"""Experimental scientific provenance model for OpenSmell.

This module defines small generic structures for describing where imported
information came from, which source record was used, and how it was derived
into an OpenSmell resource.

The model deliberately does not define citation, licensing, scientific trust,
or dataset-specific semantics.

This model is experimental and non-normative.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


def _require_nonempty_string(
    value: Any,
    name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be a string"
        )

    if not value:
        raise ValueError(
            f"{name} must be non-empty"
        )

    return value


def _require_dict(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(
            f"{name} must be a dict"
        )

    return value


def _copy_json_value(
    value: Any,
) -> Any:
    """Recursively copy a strict JSON-compatible value."""

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                "JSON numeric values must be finite"
            )

        return value

    if isinstance(value, list):
        return [
            _copy_json_value(item)
            for item in value
        ]

    if isinstance(value, dict):
        result: dict[str, Any] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "provenance object keys must be strings"
                )

            result[key] = _copy_json_value(
                item
            )

        return result

    raise TypeError(
        "provenance values must contain only "
        "JSON-compatible values"
    )


@dataclass(frozen=True)
class SourceIdentifier:
    """Persistent or external identifier for a provenance source."""

    scheme: str
    value: str
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.scheme,
            "SourceIdentifier.scheme",
        )
        _require_nonempty_string(
            self.value,
            "SourceIdentifier.value",
        )
        _require_dict(
            self.extra,
            "SourceIdentifier.extra",
        )

        object.__setattr__(
            self,
            "extra",
            _copy_json_value(
                self.extra
            ),
        )


@dataclass(frozen=True)
class ProvenanceSource:
    """Dataset, publication, archive, or other source of imported data."""

    name: str
    version: str | None = None
    identifier: SourceIdentifier | None = None
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.name,
            "ProvenanceSource.name",
        )

        if self.version is not None:
            _require_nonempty_string(
                self.version,
                "ProvenanceSource.version",
            )

        if (
            self.identifier is not None
            and not isinstance(
                self.identifier,
                SourceIdentifier,
            )
        ):
            raise TypeError(
                "ProvenanceSource.identifier must be "
                "a SourceIdentifier or None"
            )

        _require_dict(
            self.extra,
            "ProvenanceSource.extra",
        )

        object.__setattr__(
            self,
            "extra",
            _copy_json_value(
                self.extra
            ),
        )


@dataclass(frozen=True)
class ProvenanceRecord:
    """Identity of the record within the declared provenance source."""

    identity: dict[str, Any]
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_dict(
            self.identity,
            "ProvenanceRecord.identity",
        )

        if not self.identity:
            raise ValueError(
                "ProvenanceRecord.identity must be non-empty"
            )

        _require_dict(
            self.extra,
            "ProvenanceRecord.extra",
        )

        object.__setattr__(
            self,
            "identity",
            _copy_json_value(
                self.identity
            ),
        )
        object.__setattr__(
            self,
            "extra",
            _copy_json_value(
                self.extra
            ),
        )


@dataclass(frozen=True)
class ProvenanceDerivation:
    """Description of the import or derivation operation."""

    method: str
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.method,
            "ProvenanceDerivation.method",
        )
        _require_dict(
            self.extra,
            "ProvenanceDerivation.extra",
        )

        object.__setattr__(
            self,
            "extra",
            _copy_json_value(
                self.extra
            ),
        )


@dataclass(frozen=True)
class Provenance:
    """Generic experimental provenance attached to imported information."""

    source: ProvenanceSource
    record: ProvenanceRecord | None = None
    derivation: ProvenanceDerivation | None = None
    extra: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ProvenanceSource,
        ):
            raise TypeError(
                "Provenance.source must be a ProvenanceSource"
            )

        if (
            self.record is not None
            and not isinstance(
                self.record,
                ProvenanceRecord,
            )
        ):
            raise TypeError(
                "Provenance.record must be "
                "a ProvenanceRecord or None"
            )

        if (
            self.derivation is not None
            and not isinstance(
                self.derivation,
                ProvenanceDerivation,
            )
        ):
            raise TypeError(
                "Provenance.derivation must be "
                "a ProvenanceDerivation or None"
            )

        _require_dict(
            self.extra,
            "Provenance.extra",
        )

        object.__setattr__(
            self,
            "extra",
            _copy_json_value(
                self.extra
            ),
        )


def _source_identifier_to_dict(
    identifier: SourceIdentifier,
) -> dict[str, Any]:
    document = _copy_json_value(
        identifier.extra
    )
    document.update(
        {
            "scheme": identifier.scheme,
            "value": identifier.value,
        }
    )
    return document


def _source_identifier_from_dict(
    value: Any,
) -> SourceIdentifier:
    obj = _require_dict(
        value,
        "provenance.source.identifier",
    )

    scheme = _require_nonempty_string(
        obj.get("scheme"),
        "provenance.source.identifier.scheme",
    )
    identifier_value = _require_nonempty_string(
        obj.get("value"),
        "provenance.source.identifier.value",
    )

    extra = {
        key: _copy_json_value(item)
        for key, item in obj.items()
        if key not in {
            "scheme",
            "value",
        }
    }

    return SourceIdentifier(
        scheme=scheme,
        value=identifier_value,
        extra=extra,
    )


def provenance_to_dict(
    provenance: Provenance,
) -> dict[str, Any]:
    """Serialize experimental provenance to a strict JSON-compatible dict."""

    if not isinstance(
        provenance,
        Provenance,
    ):
        raise TypeError(
            "provenance must be a Provenance"
        )

    source = _copy_json_value(
        provenance.source.extra
    )
    source["name"] = provenance.source.name

    if provenance.source.version is not None:
        source["version"] = provenance.source.version

    if provenance.source.identifier is not None:
        source["identifier"] = _source_identifier_to_dict(
            provenance.source.identifier
        )

    document = _copy_json_value(
        provenance.extra
    )
    document["source"] = source

    if provenance.record is not None:
        record = _copy_json_value(
            provenance.record.extra
        )
        record["identity"] = _copy_json_value(
            provenance.record.identity
        )
        document["record"] = record

    if provenance.derivation is not None:
        derivation = _copy_json_value(
            provenance.derivation.extra
        )
        derivation["method"] = provenance.derivation.method
        document["derivation"] = derivation

    return document


def provenance_from_dict(
    value: Any,
) -> Provenance:
    """Parse experimental provenance from a JSON-compatible dict."""

    obj = _require_dict(
        value,
        "provenance",
    )

    source_obj = _require_dict(
        obj.get("source"),
        "provenance.source",
    )

    source_name = _require_nonempty_string(
        source_obj.get("name"),
        "provenance.source.name",
    )

    source_version = source_obj.get(
        "version"
    )
    if source_version is not None:
        _require_nonempty_string(
            source_version,
            "provenance.source.version",
        )

    identifier = None
    if "identifier" in source_obj:
        identifier = _source_identifier_from_dict(
            source_obj["identifier"]
        )

    source_extra = {
        key: _copy_json_value(item)
        for key, item in source_obj.items()
        if key not in {
            "name",
            "version",
            "identifier",
        }
    }

    record = None
    if "record" in obj:
        record_obj = _require_dict(
            obj["record"],
            "provenance.record",
        )
        identity = _require_dict(
            record_obj.get("identity"),
            "provenance.record.identity",
        )
        record_extra = {
            key: _copy_json_value(item)
            for key, item in record_obj.items()
            if key != "identity"
        }
        record = ProvenanceRecord(
            identity=identity,
            extra=record_extra,
        )

    derivation = None
    if "derivation" in obj:
        derivation_obj = _require_dict(
            obj["derivation"],
            "provenance.derivation",
        )
        method = _require_nonempty_string(
            derivation_obj.get("method"),
            "provenance.derivation.method",
        )
        derivation_extra = {
            key: _copy_json_value(item)
            for key, item in derivation_obj.items()
            if key != "method"
        }
        derivation = ProvenanceDerivation(
            method=method,
            extra=derivation_extra,
        )

    extra = {
        key: _copy_json_value(item)
        for key, item in obj.items()
        if key not in {
            "source",
            "record",
            "derivation",
        }
    }

    return Provenance(
        source=ProvenanceSource(
            name=source_name,
            version=source_version,
            identifier=identifier,
            extra=source_extra,
        ),
        record=record,
        derivation=derivation,
        extra=extra,
    )
