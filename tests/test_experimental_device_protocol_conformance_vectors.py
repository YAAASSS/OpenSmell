"""Portable conformance vectors for experimental Device Protocol 0.1.

Portable semantic conformance intentionally compares JSON data-model values,
not host-language numeric implementation types. In particular, JSON `1` and
`1.0` may become indistinguishable after parsing in JavaScript.

The Python reference implementation is allowed to be stricter at its API
boundary. Such host-language-specific behavior is tested by Python unit tests,
not by the cross-language semantic conformance corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opensmell.experimental.device_protocol import (
    DeviceProtocolError,
    dumps_message,
    loads_message,
    parse_capabilities_response,
    parse_hello_response,
    parse_render_request,
    require_ok_response,
)

VECTORS_PATH = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "device_protocol_conformance_vectors.json"
)


def _vectors() -> dict:
    return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def _validate(kind: str, message: dict) -> None:
    if kind == "hello_request":
        assert message.get("protocol_version") == "0.1"
        assert message.get("type") == "hello"
        return

    if kind == "capabilities_request":
        assert message.get("protocol_version") == "0.1"
        assert message.get("type") == "get_capabilities"
        return

    if kind == "hello_response":
        parse_hello_response(message)
        return

    if kind == "capabilities_response":
        parse_capabilities_response(message)
        return

    if kind == "render_request":
        parse_render_request(message)
        return

    if kind == "ok_response":
        require_ok_response(message)
        return

    if kind == "error_response":
        require_ok_response(message)
        return

    raise AssertionError(f"unknown vector kind: {kind}")


def test_conformance_metadata() -> None:
    vectors = _vectors()
    assert vectors["protocol_version"] == "0.1"
    assert (
        vectors["suite"]
        == "org.opensmell.experimental.device-protocol-conformance"
    )
    assert vectors["suite_version"] == "0.1"


@pytest.mark.parametrize(
    "vector",
    _vectors()["valid"],
    ids=lambda vector: vector["id"],
)
def test_valid_protocol_vectors(vector: dict) -> None:
    if vector["kind"] == "error_response":
        with pytest.raises(DeviceProtocolError, match="device error"):
            _validate(vector["kind"], vector["message"])
        return

    _validate(vector["kind"], vector["message"])


@pytest.mark.parametrize(
    "vector",
    _vectors()["invalid"],
    ids=lambda vector: vector["id"],
)
def test_invalid_protocol_vectors(vector: dict) -> None:
    with pytest.raises((DeviceProtocolError, TypeError, ValueError)):
        _validate(vector["kind"], vector["message"])


@pytest.mark.parametrize(
    "vector",
    _vectors()["strict_json_invalid_text"],
    ids=lambda vector: vector["id"],
)
def test_invalid_strict_json_vectors(vector: dict) -> None:
    with pytest.raises((DeviceProtocolError, TypeError, ValueError)):
        loads_message(vector["text"])


@pytest.mark.parametrize(
    "vector",
    _vectors()["valid"],
    ids=lambda vector: vector["id"],
)
def test_valid_vectors_survive_strict_json_roundtrip(vector: dict) -> None:
    encoded = dumps_message(vector["message"])
    decoded = loads_message(encoded)
    assert decoded == vector["message"]


def test_python_reference_is_stricter_for_decimal_channel_lexeme() -> None:
    """Document a Python-specific boundary that is not portable JS semantics."""

    vector = _vectors()["lexical_json"][0]
    message = loads_message(vector["text"])

    with pytest.raises(DeviceProtocolError):
        parse_render_request(message)
