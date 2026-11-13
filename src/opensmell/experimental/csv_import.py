"""Explicit selected-record import of OdorNet-shaped CSV, without data fetching."""
import csv
from copy import deepcopy
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


def _prepare(raw, source):
    if not isinstance(raw, bytes):
        raise TypeError("CSV input must be bytes")
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
    csv_hash = hashlib.sha256(raw).hexdigest()
    source_hash = hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
    return reader, headers, source, csv_hash, source_hash


def _make_document(raw, row, source, headers, selected, csv_hash, source_hash):
    if len(selected) != len(headers):
        raise ValueError("Selected record field count does not match header")
    original = dict(zip(headers, selected))
    record = dict(original)
    for label in ODORNET_LABELS:
        token = original[label].strip()
        if token not in {"", "0", "0.0", "1", "1.0"}:
            raise ValueError(f"Unsupported semantic value for {label}: {original[label]!r}")
        record[label] = None if token == "" else int(float(token))
    odor_id = "urn:uuid:" + str(uuid5(NAMESPACE, f"{csv_hash}\n{row}\n{source_hash}"))
    odor = from_record_with_annotations(record, odor_id=odor_id)
    provenance = {"source": source["name"], "url": source["url"], "license": source["license"],
                  "kind": source["kind"], "csv_sha256": csv_hash, "data_record": row,
                  "adapter": "odornet-shaped-csv-v1"}
    for representation in odor.representations:
        representation.extra["provenance"] = dict(provenance)
    document = Document(odor=odor, version="0.1", extra={IMPORT_KEY: {
        "version": "0.1", "adapter": "odornet-shaped-csv-v1", "source": deepcopy(source),
        "source_manifest_sha256": source_hash, "csv_sha256": csv_hash,
        "csv_byte_count": len(raw), "data_record": row,
        "headers": list(headers), "raw_record": original,
        "limitations": ["Only the selected record is imported; unknown columns are not interpreted.",
                        "Source/license are supplied declarations, not authenticated facts.",
                        "Blank semantic cells are unknown; no chemical or perceptual validation is implied."],
    }})
    validate_document(_document_to_dict(document))
    return document


def import_odornet_csv(raw, *, row, source):
    """Import one selected logical data record (one-based, excluding header)."""
    if type(row) is not int or row < 1:
        raise ValueError("row must be a positive one-based data-record index")
    reader, headers, source, csv_hash, source_hash = _prepare(raw, source)
    for index, cells in enumerate(reader, 1):
        if index == row:
            return _make_document(raw, row, source, headers, cells, csv_hash, source_hash)
    raise ValueError("Selected CSV data record does not exist")


BATCH_FORMAT = "org.opensmell.experimental.csv-import-batch"
MAX_BATCH_RECORDS = 1000


def _rows(rows):
    if (not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= MAX_BATCH_RECORDS
            or any(type(row) is not int or row < 1 for row in rows)
            or len(set(rows)) != len(rows)):
        raise ValueError("Select 1–1000 unique positive one-based record indexes")
    return list(rows)


def _document_hash(document):
    return hashlib.sha256(json.dumps(document, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def import_odornet_csv_batch(raw, *, rows, source):
    """Parse once through the last selected record; retain per-record refusals."""
    from ..exceptions import OpenSmellError
    rows = _rows(rows)
    reader, headers, source, csv_hash, source_hash = _prepare(raw, source)
    requested = set(rows)
    found = {}
    last = max(requested)
    for index, cells in enumerate(reader, 1):
        if index in requested:
            entry = {"data_record": index, "raw_cells": cells}
            try:
                document = _make_document(raw, index, source, headers, cells, csv_hash, source_hash)
            except (ValueError, TypeError, OpenSmellError) as error:
                entry.update(status="rejected", error={"code": "invalid_record", "message": str(error)})
            else:
                value = _document_to_dict(document)
                entry.update(status="accepted", document=value, document_sha256=_document_hash(value))
            found[index] = entry
        if index >= last:
            break
    results = [found.get(row, {"data_record": row, "status": "rejected",
                              "error": {"code": "missing_record", "message": "Selected record does not exist"}})
               for row in rows]
    accepted = sum(entry["status"] == "accepted" for entry in results)
    return {
        "format": BATCH_FORMAT, "version": "0.1", "experimental": True,
        "status": "accepted" if accepted == len(rows) else "partial" if accepted else "rejected",
        "source": source, "source_manifest_sha256": source_hash,
        "csv_sha256": csv_hash, "csv_byte_count": len(raw), "headers": headers,
        "requested_records": rows, "counts": {"accepted": accepted, "rejected": len(rows) - accepted},
        "results": results,
        "limitations": ["Only selected records are semantically validated.",
                        "Declared source and content hashes are not authenticated.",
                        "No planning, device commands or physical validation occur during import."],
    }


def extract_batch_record(raw, *, row):
    """Extract one accepted Core document with checked hash and import context."""
    if type(row) is not int or row < 1:
        raise ValueError("row must be a positive one-based index")
    batch = decode_bytes(raw)
    if (not isinstance(batch, dict) or batch.get("format") != BATCH_FORMAT
            or batch.get("version") != "0.1"):
        raise ValueError("Unsupported CSV batch envelope")
    requested = _rows(batch.get("requested_records"))
    entries = batch.get("results")
    if (not isinstance(entries, list) or len(entries) != len(requested)
            or any(not isinstance(entry, dict) or type(entry.get("data_record")) is not int
                   or entry["data_record"] != index for entry, index in zip(entries, requested))):
        raise ValueError("Batch entries do not match requested records")
    if any(entry.get("status") not in {"accepted", "rejected"} for entry in entries):
        raise ValueError("Unsupported batch record status")
    accepted = sum(entry["status"] == "accepted" for entry in entries)
    counts = batch.get("counts")
    expected_status = "accepted" if accepted == len(entries) else "partial" if accepted else "rejected"
    if (not isinstance(counts, dict) or any(type(counts.get(k)) is not int for k in ("accepted", "rejected"))
            or counts != {"accepted": accepted, "rejected": len(entries) - accepted}
            or batch.get("status") != expected_status):
        raise ValueError("Batch summary contradicts record statuses")
    if row not in requested:
        raise ValueError("Record was not selected in this batch")
    entry = entries[requested.index(row)]
    if entry.get("status") != "accepted":
        raise ValueError("Selected record was rejected; no Core document is available")
    document = entry.get("document")
    if not isinstance(document, dict) or entry.get("document_sha256") != _document_hash(document):
        raise ValueError("Core document integrity mismatch")
    validate_document(document)
    context = document.get(IMPORT_KEY)
    if (not isinstance(context, dict) or context.get("data_record") != row
            or any(context.get(key) != batch.get(key) for key in
                   ("source", "source_manifest_sha256", "csv_sha256", "csv_byte_count", "headers"))):
        raise ValueError("Core document source context does not match batch")
    source_hash = hashlib.sha256(json.dumps(batch["source"], sort_keys=True, ensure_ascii=True,
                                           separators=(",", ":")).encode()).hexdigest()
    expected_id = "urn:uuid:" + str(uuid5(NAMESPACE, '\n'.join((batch["csv_sha256"], str(row), source_hash))))
    if source_hash != batch["source_manifest_sha256"] or document["odor"]["id"] != expected_id:
        raise ValueError("Core import identity mismatch")
    return (json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode()
