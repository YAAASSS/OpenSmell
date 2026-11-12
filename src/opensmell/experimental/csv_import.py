"""Explicit selected-record import of OdorNet-shaped CSV, without data fetching."""
import csv
import hashlib
import io
import json
from uuid import UUID, uuid5

from .._json import decode_bytes
from ..adapters.odornet import ODORNET_LABELS, from_record_with_annotations
from ..models import Document
from ..validation import validate_document
from ..serializer import _document_to_dict

IMPORT_KEY = "org.opensmell.experimental.csv-import"
NAMESPACE = UUID("e6e81508-d0f0-431e-87ad-882b2cd5503a")


def import_odornet_csv(raw, *, row, source):
    """Return one Core Document with a deterministic record ID and raw-row context.

    row is a one-based logical data-record index, excluding the header. Every
    label column is required; blank cells mean unknown, never absent. Unselected
    records are not semantically validated. Source declarations are not verified.
    """
    if not isinstance(raw, bytes):
        raise TypeError("CSV input must be bytes")
    if type(row) is not int or row < 1:
        raise ValueError("row must be a positive one-based data-record index")
    # Copy/validate JSON metadata without aliasing caller objects.
    source = decode_bytes(json.dumps(source, allow_nan=False).encode())
    if not isinstance(source, dict):
        raise ValueError("source manifest must be an object")
    for key in ("name", "url", "license"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise ValueError(f"source manifest requires nonempty {key}")
    if source.get("kind") not in {"dataset", "synthetic"}:
        raise ValueError("source kind must be dataset or synthetic")
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    try:
        headers = next(reader)
    except StopIteration as error:
        raise ValueError("CSV requires a header") from error
    if not headers or any(not h or h != h.strip() for h in headers) or len(headers) != len(set(headers)):
        raise ValueError("CSV headers must be nonempty, unique and unpadded")
    missing = [h for h in ("SMILES", *ODORNET_LABELS) if h not in headers]
    if missing:
        raise ValueError("Missing CSV columns: " + ", ".join(missing))
    selected = None
    for index, cells in enumerate(reader, 1):
        if index == row:
            selected = cells
            break
    if selected is None:
        raise ValueError("Selected CSV data record does not exist")
    if len(selected) != len(headers):
        raise ValueError("Selected record field count does not match header")
    original = dict(zip(headers, selected))
    record = dict(original)
    for label in ODORNET_LABELS:
        token = original[label].strip()
        if token not in {"", "0", "0.0", "1", "1.0"}:
            raise ValueError(f"Unsupported semantic value for {label}: {original[label]!r}")
        record[label] = None if token == "" else int(float(token))
    csv_hash = hashlib.sha256(raw).hexdigest()
    source_hash = hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=True,
                                           separators=(",", ":")).encode()).hexdigest()
    odor_id = "urn:uuid:" + str(uuid5(NAMESPACE, f"{csv_hash}\n{row}\n{source_hash}"))
    odor = from_record_with_annotations(record, odor_id=odor_id)
    provenance = {"source": source["name"], "url": source["url"], "license": source["license"],
                  "kind": source["kind"], "csv_sha256": csv_hash, "data_record": row,
                  "adapter": "odornet-shaped-csv-v1"}
    for representation in odor.representations:
        representation.extra["provenance"] = dict(provenance)
    document = Document(odor=odor, version="0.1", extra={IMPORT_KEY: {
        "version": "0.1", "adapter": "odornet-shaped-csv-v1", "source": source,
        "source_manifest_sha256": source_hash, "csv_sha256": csv_hash,
        "csv_byte_count": len(raw), "data_record": row,
        "headers": headers, "raw_record": original,
        "limitations": ["Only the selected record is imported; unknown columns are not interpreted.",
                        "Source/license are supplied declarations, not authenticated facts.",
                        "Blank semantic cells are unknown; no chemical or perceptual validation is implied."],
    }})
    validate_document(_document_to_dict(document))
    return document
