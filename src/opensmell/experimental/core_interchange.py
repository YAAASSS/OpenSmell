"""Explicit Core-to-graph projection with recoverable original source bytes.

Experimental, unauthenticated source snapshot. Extraction recovers the embedded
Core source, not edits made to the projected graph. No device access.
"""
import base64
import hashlib
from .._json import decode_bytes
from ..parser import _parse_document
from ..validation import validate_document
from .annotation import register_annotation_resource_type
from .molecule import register_molecule_resource_type
from .generic_graph import create_default_resource_type_registry, generic_graph_from_dict
from .odor_graph_bridge import bridge_odor_to_resource_graph

IMPORT_KEY = "org.opensmell.experimental.core-import"
PROJECTION = "core-odor-smiles-annotations-v1"


def interchange_registry():
    registry = create_default_resource_type_registry()
    register_annotation_resource_type(registry)
    register_molecule_resource_type(registry)
    return registry


def _core_document(raw):
    document = decode_bytes(raw)
    if not isinstance(document, dict) or "format" in document or document.get("opensmell") != "0.1":
        raise ValueError("Expected an unambiguous Core 0.1 document")
    validate_document(document)
    return document


def bridge_core_bytes(raw):
    """Project one validated Core document and retain every original byte.

    Exactly one supported chemical SMILES representation is required. Existing
    odor bridge IDs and mapping semantics are unchanged. Unknown content is
    preserved exactly in the snapshot; projection is deliberately partial.
    """
    document = _core_document(raw)
    result = bridge_odor_to_resource_graph(_parse_document(document).odor)
    result.graph.extra[IMPORT_KEY] = {
        "version": "0.1", "projection": PROJECTION,
        "primary_resource_id": result.primary_resource_id,
        "annotation_ids": list(result.annotation_ids),
        "source": {"encoding": "base64", "data": base64.b64encode(raw).decode("ascii"),
                   "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw),
                   "odor_id": document["odor"]["id"]},
        "limitations": [
            "Projection is partial; the embedded original preserves all source fields and bytes.",
            "Extracting the original does not apply edits made to graph resources.",
            "Source provenance is supplied, not authenticated. SMILES is not a measured odor outcome.",
        ],
    }
    return result


def extract_core_bytes(raw):
    """Validate a graph and recover its integrity-checked original Core bytes."""
    graph = generic_graph_from_dict(decode_bytes(raw), registry=interchange_registry())
    snapshot = graph.extra.get(IMPORT_KEY)
    if (not isinstance(snapshot, dict) or snapshot.get("version") != "0.1"
            or snapshot.get("projection") != PROJECTION):
        raise ValueError("No supported Core import snapshot")
    source = snapshot.get("source")
    if not isinstance(source, dict) or source.get("encoding") != "base64":
        raise ValueError("Unsupported Core source encoding")
    data = source.get("data")
    if not isinstance(data, str):
        raise ValueError("Missing Core source bytes")
    try:
        original = base64.b64decode(data, validate=True)
    except (ValueError, UnicodeError) as error:
        raise ValueError("Invalid base64 Core source") from error
    if (type(source.get("byte_count")) is not int or source["byte_count"] != len(original)
            or source.get("sha256") != hashlib.sha256(original).hexdigest()):
        raise ValueError("Core source integrity mismatch")
    document = _core_document(original)
    if source.get("odor_id") != document["odor"]["id"]:
        raise ValueError("Core source identity mismatch")
    return original
