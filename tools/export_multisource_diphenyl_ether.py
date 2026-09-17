"""Reproduce the second real Local Explorer example from local source files.

Only the selected records and their source-file fingerprints are published.
No network or hardware access is used. The existing beta-pinene graph assembly,
SDK adapters, resource identifiers and provenance models are reused unchanged.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
from io import BytesIO
import json
from pathlib import Path

import pandas as pd

from opensmell.adapters.keller_vosshall import DESCRIPTOR_COLUMNS, GLOBAL_RATINGS
from opensmell.experimental.generic_graph import generic_graph_dumps
from opensmell.experimental.provenance import SourceIdentifier, provenance_from_dict, provenance_to_dict
from tools.export_multisource_beta_pinene import build_graph, clean
from tools.multisource_demo import create_registry


ROOT = Path(__file__).resolve().parents[1]
CID = "7583"
INCHIKEY = "USIUVYZYUHIAEV-UHFFFAOYSA-N"
ODORNET_ROW = 6065
KELLER_ROW = 34028
METHOD = "tools.export_multisource_diphenyl_ether.build_example"


def build_example(keller, odornet, cache, source_files, *,
                  odornet_row=ODORNET_ROW, keller_row=KELLER_ROW):
    """Assemble one selected observation, refusing identity ambiguity."""
    identity = cache.get(f"cid:{CID}")
    if (not isinstance(identity, dict) or identity.get("status") != "resolved"
            or str(identity.get("cid")) != CID or identity.get("inchikey") != INCHIKEY):
        raise ValueError("The selected CID must resolve to the complete expected InChIKey.")
    identity_keys = [key for key, value in cache.items()
                     if isinstance(value, dict) and value.get("status") == "resolved"
                     and value.get("inchikey") == INCHIKEY]
    if identity_keys != [f"cid:{CID}"]:
        raise ValueError("Ambiguous identity cache: multiple source keys match this InChIKey.")
    matches = odornet[odornet["PubChem_InChIKey"] == INCHIKEY]
    if len(matches) != 1 or matches.index[0] != odornet_row:
        raise ValueError("Expected one exact OdorNet match at the explicitly selected row.")
    if matches.iloc[0]["PubChem_Status"] != "resolved":
        raise ValueError("The selected OdorNet identity must be resolved.")
    if keller_row not in keller.index or not keller.index.is_unique:
        raise ValueError("The selected Keller row must exist and be unambiguous.")

    graph = build_graph(keller, odornet, cache, pubchem_cid=CID,
                        keller_row_index=keller_row, example_name="diphenyl ether",
                        derivation_method=METHOD)
    molecule, annotation, _, _, observation = graph.resources
    odornet_record = {key: clean(value) for key, value in matches.iloc[0].items()}
    keller_record = {key: clean(value) for key, value in keller.loc[keller_row].items()}

    # Keep source identity separate from file location and derivation metadata.
    for resource, source, location in (
        (molecule, "odornet", {"row_index": odornet_row, "indexing": "zero-based data records, header excluded"}),
        (annotation, "odornet", {"row_index": odornet_row, "indexing": "zero-based data records, header excluded"}),
        (observation, "keller", {"worksheet": "data", "header_row": 3,
                                "row_index": keller_row, "worksheet_row": keller_row + 4,
                                "indexing": "zero-based data rows after the third worksheet row"}),
    ):
        provenance = provenance_from_dict(resource.extra["provenance"])
        resource.extra["provenance"] = provenance_to_dict(replace(
            provenance,
            source=replace(provenance.source,
                           identifier=SourceIdentifier(scheme="sha256", value=source_files[source]["sha256"]),
                           extra={"file_name": source_files[source]["file_name"]}),
            record=replace(provenance.record, extra=location),
        ))

    observation.context["source_metadata"] = {
        key: value for key, value in keller_record.items()
        if key not in GLOBAL_RATINGS and key not in DESCRIPTOR_COLUMNS
    }
    graph.extra["export"] = {
        "method": METHOD,
        "source_files": source_files,
        "selection": {"pubchem_cid": CID, "inchikey": INCHIKEY,
                      "odornet_row_index": odornet_row, "keller_row_index": keller_row,
                      "identity_cache_key": f"cid:{CID}", "aggregation": "none"},
        "selected_records": {"odornet": odornet_record, "keller": keller_record,
                             "identity_cache": identity},
        "missing_cells": "Empty/NaN source cells are recorded as JSON null, never as zero.",
    }
    return graph


def export(odornet_path: Path, keller_path: Path, cache_path: Path, output_path: Path,
           *, odornet_row=ODORNET_ROW, keller_row=KELLER_ROW):
    """Hash the exact bytes read, then produce deterministic UTF-8/LF output."""
    raw = {}
    sources = {}
    for key, path in (("odornet", odornet_path), ("keller", keller_path), ("identity_cache", cache_path)):
        raw[key] = path.read_bytes()
        sources[key] = {"file_name": path.name, "sha256": hashlib.sha256(raw[key]).hexdigest(),
                        "byte_length": len(raw[key])}
    odornet = pd.read_csv(BytesIO(raw["odornet"]))
    keller = pd.read_excel(BytesIO(raw["keller"]), sheet_name="data", header=2)
    keller.columns = [str(column).strip() for column in keller.columns]
    cache = json.loads(raw["identity_cache"].decode("utf-8"))
    if not isinstance(cache, dict):
        raise ValueError("The identity cache must be a JSON object.")
    graph = build_example(keller, odornet, cache, sources,
                          odornet_row=odornet_row, keller_row=keller_row)
    output_path.write_bytes((generic_graph_dumps(graph, registry=create_registry(), indent=2) + "\n").encode("utf-8"))
    return graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--odornet", type=Path, default=ROOT / "examples/odornet_enriched.csv")
    parser.add_argument("--keller", type=Path, default=ROOT / "examples/keller_vosshall.xlsx")
    parser.add_argument("--identity-cache", type=Path, default=ROOT / "examples/keller_pubchem_identity_cache.json")
    parser.add_argument("--odornet-row", type=int, default=ODORNET_ROW)
    parser.add_argument("--keller-row", type=int, default=KELLER_ROW)
    parser.add_argument("--output", type=Path, default=ROOT / "examples/multisource_diphenyl_ether.osmell")
    args = parser.parse_args()
    export(args.odornet, args.keller, args.identity_cache, args.output,
           odornet_row=args.odornet_row, keller_row=args.keller_row)
    print(f"Written: {args.output}")


if __name__ == "__main__":
    main()
