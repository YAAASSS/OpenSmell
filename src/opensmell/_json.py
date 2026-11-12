"""Strict UTF-8 JSON byte boundary shared by installed tools."""
import json


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def decode_bytes(raw):
    if not isinstance(raw, bytes):
        raise TypeError("input must be bytes")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                       parse_constant=reject_constant)
    # Reject overflowed exponents as well as explicit NaN/Infinity.
    json.dumps(value, allow_nan=False)
    return value
