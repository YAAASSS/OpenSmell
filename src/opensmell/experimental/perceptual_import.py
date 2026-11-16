"""Selected prepared Keller/Vosshall-shaped CSV observation; no fetching/joins.

The prepared contract is deliberately narrower than arbitrary spreadsheets.
Source/license, preparation and subjective rating units are caller declarations.
"""
import csv
import hashlib
import io
import json
import re
from uuid import UUID, uuid5

from .._json import decode_bytes
from ..adapters.keller_vosshall import DESCRIPTOR_COLUMNS, GLOBAL_RATINGS, measurements_from_record
from ..schemes.perceptual_measurements import validate as validate_measurements
from .core_interchange import interchange_registry
from .generic_graph import GenericResourceGraph, generic_graph_to_dict
from .molecule import Molecule
from .resources import Condition, ExternalIdentifier, Observation, ObservationTarget, Reference, Result, ResultScheme, Stimulus

IMPORT_KEY = "org.opensmell.experimental.perceptual-csv-import"
ADAPTER = "keller-vosshall-prepared-csv-v1"
MAX_CSV_BYTES = 8 * 1048576
MAX_SOURCE_BYTES = 1048576
NAMESPACE = UUID("cc218da5-ddc7-4ebc-8314-a781e812fa38")
IDENTITY_COLUMNS = ("CID", "Odor", "Odor dilution", "Subject # (this study)")
RATING_COLUMNS = (*GLOBAL_RATINGS, *DESCRIPTOR_COLUMNS)
CATEGORY_COLUMNS = ("CAN OR CAN'T SMELL", "KNOW OR DON'T KNOW THE SMELL")


def _source(source):
    encoded = json.dumps(source, allow_nan=False, ensure_ascii=True).encode()
    if len(encoded) > MAX_SOURCE_BYTES:
        raise ValueError("Source declaration exceeds 1 MiB")
    source = decode_bytes(encoded)  # copy unknown fields; no caller aliases
    if not isinstance(source, dict):
        raise ValueError("Source declaration must be an object")
    for key in ("name", "url", "license", "preparation"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise ValueError(f"Source declaration requires nonempty {key}")
    if source.get("kind") not in {"dataset", "synthetic"}:
        raise ValueError("Source kind must be dataset or synthetic")
    scale = source.get("rating_scale")
    if (not isinstance(scale, dict) or type(scale.get("min")) not in (int, float)
            or type(scale.get("max")) not in (int, float)
            or scale["min"] != 0 or scale["max"] != 100 or scale.get("unit") != "rating"):
        raise ValueError("Prepared contract requires rating_scale min=0, max=100, unit='rating'")
    digest = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    return source, digest


def import_keller_csv(raw, *, row, source):
    """Return a GenericResourceGraph for one one-based logical data record.

    Blank rating cells are omitted, explicit zero remains measured zero. Numeric
    cells use the existing Keller adapter's fixed 0..100 validation. All selected
    cells and unknown source fields survive in graph metadata; full CSV bytes do
    not. IDs identify this import occurrence, never chemical/person equivalence.
    """
    if not isinstance(raw, bytes):
        raise TypeError("CSV input must be bytes")
    if len(raw) > MAX_CSV_BYTES:
        raise ValueError("CSV exceeds 8 MiB; prepare a smaller explicit selection")
    if type(row) is not int or row < 1:
        raise ValueError("row must be a positive one-based logical data-record index")
    source, source_hash = _source(source)
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
    headers = next(reader, None)
    if (not headers or any(not h or h != h.strip() for h in headers)
            or len(headers) != len(set(headers))):
        raise ValueError("CSV headers must be nonempty, unique and unpadded")
    if any(h not in headers for h in IDENTITY_COLUMNS):
        raise ValueError("CSV requires columns: " + ", ".join(IDENTITY_COLUMNS))
    if not any(h in headers for h in RATING_COLUMNS):
        raise ValueError("CSV requires at least one supported rating column")
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
    if any(not original[h].strip() for h in IDENTITY_COLUMNS):
        raise ValueError("Selected record requires nonblank stimulus/subject identity and dilution")
    if not re.fullmatch(r"[1-9][0-9]*", original["CID"].strip()):
        raise ValueError("CID must be a positive decimal integer declaration")
    record = {h: (original[h].strip() or None) for h in RATING_COLUMNS if h in original}
    measurements = measurements_from_record(record)
    for measurement in measurements:
        measurement["unit"] = "rating"  # dimensionless subjective scale, not concentration
    if measurements:
        validate_measurements({"measurements": measurements})
    csv_hash = hashlib.sha256(raw).hexdigest()
    def rid(kind):
        return str(uuid5(NAMESPACE, f"{csv_hash}\n{row}\n{source_hash}\n{kind}"))
    provenance = {"source": {"name": source["name"], "url": source["url"], "license": source["license"],
                              "kind": source["kind"]},
                  "record": {"identity": {"data_record": row}, "csv_sha256": csv_hash},
                  "derivation": {"method": ADAPTER}}
    molecule = Molecule(id=rid("molecule"), identifiers=[ExternalIdentifier(scheme="pubchem.cid", value=original["CID"].strip())],
                        extra={"source_name": original["Odor"], "provenance": provenance})
    stimulus = Stimulus(id=rid("stimulus"), source=Reference(molecule.id),
                        conditions=[Condition(property="dilution", value=original["Odor dilution"])])
    target = ObservationTarget(id=rid("target"),
                              identifiers=[ExternalIdentifier(scheme="keller_vosshall.subject", value=original["Subject # (this study)"])],
                              extra={"kind": "human_subject", "source_kind": source["kind"]})
    results = []
    if any(h in original for h in CATEGORY_COLUMNS):
        # Retain source tokens without guessing detection from free-text substrings.
        categories = {"detection": "unknown", "source_fields": {h: original[h] for h in CATEGORY_COLUMNS if h in original}}
        results.append(Result(ResultScheme("org.opensmell.experimental.observation.categories", "0.1"), categories))
    if measurements:
        results.append(Result(ResultScheme("org.opensmell.perceptual.measurements", "0.1"), {"measurements": measurements}))
    observation = Observation(id=rid("observation"), stimulus=Reference(stimulus.id), target=Reference(target.id),
                              results=results, context={"measurement_domain": "psychophysical", "source_kind": source["kind"]},
                              extra={"provenance": provenance})
    graph = GenericResourceGraph(resources=[molecule, stimulus, target, observation], extra={IMPORT_KEY: {
        "version": "0.1", "adapter": ADAPTER, "primary_resource_id": observation.id,
        "source": source, "source_manifest_sha256": source_hash, "csv_sha256": csv_hash,
        "csv_byte_count": len(raw), "data_record": row, "headers": headers, "raw_record": original,
        "measurement_count": len(measurements),
        "omitted_rating_columns": [h for h in RATING_COLUMNS if h not in original or not original[h].strip()],
        "limitations": ["Only this selected record is interpreted; complete CSV bytes are not embedded.",
                        "Source, license, preparation, CID and subjective scale are supplied declarations, not authenticated facts.",
                        "Blank ratings are unmeasured; zero is measured zero. Free-text categorical fields are retained without inference.",
                        "IDs identify this import occurrence; no chemical/person join, unit/dilution conversion or aggregate is performed.",
                        "Rating unit is dimensionless subjective rating; no physical command or odor outcome is established."]}})
    # Exercise the same registered serialization boundary as installed consumers.
    generic_graph_to_dict(graph, registry=interchange_registry())
    return graph
