"""Offline checks for the second real fixture, independent of full datasets."""

from copy import deepcopy
import http.client
import json
from pathlib import Path
import shutil
import subprocess
import threading

import pandas as pd
import pytest

from apps.local_demo.__main__ import create_server
from apps.local_demo.hardware import HardwareService
from apps.local_demo.service import preview
from opensmell.adapters.keller_vosshall import DESCRIPTOR_COLUMNS, GLOBAL_RATINGS
from opensmell.experimental.generic_graph import generic_graph_dumps, generic_graph_loads, generic_graph_to_dict
from opensmell.experimental.provenance import provenance_from_dict, provenance_to_dict
from opensmell.experimental.reference_discovery import unresolved_graph_references
from tools.export_multisource_beta_pinene import build_graph
from tools.export_multisource_diphenyl_ether import build_example
from tools.multisource_demo import create_registry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/multisource_diphenyl_ether.osmell"
BETA = ROOT / "examples/multisource_beta_pinene.osmell"
KEY = "USIUVYZYUHIAEV-UHFFFAOYSA-N"
# Independently transcribed from source row 6065; no mapper is the oracle.
STATES = {"animalic&ambery": "absent", "sweety&gourmand": "unknown",
          "floral": "present", "fruity&vegetable": "absent",
          "pungent&disagreeable": "unknown", "green&herbal": "present",
          "nutty": "absent", "woody&mossy": "absent", "resinous&balsamic": "absent",
          "cooked": "absent", "odorless": "absent", "spice": "absent"}
# Row 34028: every nonempty rating, including values unused by the mapper.
RATINGS = {"intensity": 95, "pleasantness": 2, "familiarity": 0,
           "wood": 15, "grass": 18, "flower": 47, "chemical": 1}
HASHES = {"odornet": "f0248b02c34fa58ddc38760e8454bf75dca6ca9764c27577401060a1d2f8bf3a",
          "keller": "efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62",
          "identity_cache": "a0580274144b994871f15b58275e0df5032383697570a33c2e54e2a5feadefec"}


@pytest.fixture
def document():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def selected_frames(document):
    records = document["export"]["selected_records"]
    # Recreate pandas missing cells as read from the actual CSV, not just None.
    odornet_record = {key: float("nan") if value is None else value
                      for key, value in records["odornet"].items()}
    return (pd.DataFrame([records["keller"]], index=[34028]),
            pd.DataFrame([odornet_record], index=[6065]),
            {"cid:7583": deepcopy(records["identity_cache"])})


def test_identity_references_and_source_context(document):
    graph = generic_graph_loads(json.dumps(document), registry=create_registry())
    assert len(graph) == 5
    assert not graph.unknown_resources(registry=create_registry())
    assert not unresolved_graph_references(graph)
    molecule, annotation, stimulus, target, observation = document["resources"]
    assert molecule["smiles"] == "c1ccc(Oc2ccccc2)cc1"
    assert molecule["identifiers"] == [{"scheme": "pubchem.inchikey", "value": KEY}]
    assert document["shared_inchikey"] == KEY
    assert annotation["subject"]["resource_id"] == stimulus["source"]["resource_id"] == molecule["id"]
    assert observation["stimulus"]["resource_id"] == stimulus["id"]
    assert observation["target"]["resource_id"] == target["id"]
    assert stimulus["conditions"] == [{"property": "dilution", "value": "1/1,000"}]
    assert stimulus["identifiers"] == [{"scheme": "cas", "value": "101-84-8"}]
    assert target["identifiers"] == [{"scheme": "keller_vosshall.subject_this_study", "value": "35"}]
    assert observation["context"]["source_row"] == 34028
    metadata = observation["context"]["source_metadata"]
    assert metadata["CID"] == 7583 and metadata["VIAL #"] == 590
    assert metadata["Subject # (DREAM challenge)"] is None
    assert metadata["CAN OR CAN'T SMELL"] == "I smell something"
    assert metadata["KNOW OR DON'T KNOW THE SMELL"] == "I don't know what the odor is"
    assert metadata["THE ODOR IS:"] == "No Answer"


def test_all_states_values_missing_cells_and_zero_are_preserved(document):
    records = document["export"]["selected_records"]
    annotation, observation = document["resources"][1], document["resources"][4]
    assert {item["value"]: item["state"] for item in annotation["data"]["annotations"]} == STATES
    assert len(annotation["data"]["annotations"]) == 12
    for label, state in STATES.items():
        assert records["odornet"][label] == {"present": 1, "absent": 0, "unknown": None}[state]
    measurements = observation["results"][0]["data"]["measurements"]
    assert {item["property"]: item["value"] for item in measurements} == RATINGS
    for item in measurements:
        assert item["scale"] == {"min": 0, "max": 100}
        assert "unit" not in item  # Source ratings are not chemical concentrations.
    expected_fields = {**GLOBAL_RATINGS, **{name: name.lower() for name in DESCRIPTOR_COLUMNS}}
    for field, property_name in expected_fields.items():
        assert records["keller"][field] == RATINGS.get(property_name)
    assert records["keller"]["HOW FAMILIAR IS THE SMELL?"] == 0
    assert records["keller"]["EDIBLE"] is None


def test_file_fingerprints_record_identity_and_provenance_roundtrip(document):
    export = document["export"]
    assert export["selection"] == {"pubchem_cid": "7583", "inchikey": KEY,
                                   "odornet_row_index": 6065, "keller_row_index": 34028,
                                   "identity_cache_key": "cid:7583", "aggregation": "none"}
    assert {key: value["sha256"] for key, value in export["source_files"].items()} == HASHES
    assert export["selected_records"]["identity_cache"]["inchikey"] == KEY
    for index, source in ((0, "odornet"), (1, "odornet"), (4, "keller")):
        raw = document["resources"][index]["provenance"]
        assert provenance_to_dict(provenance_from_dict(raw)) == raw
        assert raw["source"]["name"] == {"odornet": "OdorNet", "keller": "Keller/Vosshall"}[source]
        assert raw["source"]["identifier"] == {"scheme": "sha256", "value": HASHES[source]}
    assert document["resources"][0]["provenance"]["record"]["identity"] == {"smiles": "c1ccc(Oc2ccccc2)cc1"}
    record = document["resources"][4]["provenance"]["record"]
    assert record["identity"] == {"source_row": 34028}
    assert record["worksheet"] == "data" and record["worksheet_row"] == 34032


def test_rebuild_from_published_records_is_exact_without_external_files(document):
    graph = build_example(*selected_frames(document), document["export"]["source_files"])
    assert generic_graph_to_dict(graph, registry=create_registry()) == document
    assert generic_graph_dumps(graph, registry=create_registry(), indent=2) + "\n" == FIXTURE.read_text(encoding="utf-8")


def test_roundtrip_preserves_all_extensions_and_raw_source_records(document):
    registry = create_registry()
    graph = generic_graph_loads(json.dumps(document), registry=registry)
    assert json.loads(generic_graph_dumps(graph, registry=registry)) == document


@pytest.mark.parametrize("case", ["fragment", "other_stereochemistry", "wrong_cid", "unresolved",
                                   "duplicate_cache", "duplicate_odornet", "wrong_odornet_row",
                                   "wrong_keller_cid", "duplicate_keller_row"])
def test_export_rejects_ambiguous_or_inconsistent_identity(document, case):
    keller, odornet, cache = selected_frames(document)
    if case == "fragment":
        cache["cid:7583"]["inchikey"] = KEY[:14]
    elif case == "other_stereochemistry":
        cache["cid:7583"]["inchikey"] = KEY[:15] + "IUCAKERBSA-N"
    elif case == "wrong_cid":
        cache["cid:7583"]["cid"] = "999"
    elif case == "unresolved":
        odornet.loc[6065, "PubChem_Status"] = "unresolved"
    elif case == "duplicate_cache":
        cache["cas:101-84-8"] = dict(cache["cid:7583"])
    elif case == "duplicate_odornet":
        odornet = pd.concat([odornet, odornet.rename(index={6065: 6066})])
    elif case == "wrong_odornet_row":
        odornet = odornet.rename(index={6065: 6066})
    elif case == "wrong_keller_cid":
        keller.loc[34028, "CID"] = 440967
    else:
        keller = pd.concat([keller, keller])
    with pytest.raises((ValueError, RuntimeError)):
        build_example(keller, odornet, cache, document["export"]["source_files"])


@pytest.mark.parametrize("path,semantic,perceptual", [
    (FIXTURE, {0: 0.25, 1: 0.60}, {0: 47 / 100, 1: 18 / 100, 2: 15 / 100}),
    (BETA, {1: 0.60, 2: 1.00}, {0: 1 / 100, 1: 86 / 100, 2: 97 / 100}),
])
def test_service_and_http_import_match_independent_five_second_expectations(path, semantic, perceptual):
    text = path.read_text(encoding="utf-8")
    for policy in ("semantic", "perceptual"):
        result = preview(text, policy=policy, duration=5)
        for name, expected in (("semantic", semantic), ("perceptual", perceptual)):
            plan = result["plans"][name]
            assert plan["duration"] == 5
            assert {item["channel"]: item["intensity"] for item in plan["commands"]} == expected

    def forbidden(*args, **kwargs):
        pytest.fail("Offline fixture import attempted serial access")

    server = create_server(0, hardware=HardwareService(available=lambda: False, factory=forbidden, ports=forbidden))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request("POST", "/api/preview", json.dumps({"source": "file", "text": text,
                           "client_id": "second-example-test", "revision": 1}),
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        assert response.status == 200
        result = json.loads(response.read())
        assert result["document"] == json.loads(text)
        with server.previews.current(result["preview_ticket"]) as entry:
            assert {item.channel: item.intensity for item in entry["plan"].commands} == semantic
        assert server.hardware.status()["connection"] == "disconnected"
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(5)


def test_historical_beta_export_defaults_reproduce_the_published_graph():
    document = json.loads(BETA.read_text(encoding="utf-8"))
    molecule, annotation, stimulus, target, observation = document["resources"]
    record = {item["value"]: {"present": 1, "absent": 0, "unknown": None}[item["state"]]
              for item in annotation["data"]["annotations"]}
    record.update(SMILES=molecule["smiles"], PubChem_Status="resolved",
                  PubChem_Title=molecule["pubchem"]["title"],
                  PubChem_IUPACName=molecule["pubchem"]["iupac_name"],
                  PubChem_CanonicalSMILES=molecule["pubchem"]["canonical_smiles"],
                  PubChem_InChIKey=document["shared_inchikey"])
    fields = {**GLOBAL_RATINGS, **{name: name.lower() for name in DESCRIPTOR_COLUMNS}}
    values = {item["property"]: item["value"] for item in observation["results"][0]["data"]["measurements"]}
    keller = {field: values.get(name) for field, name in fields.items()}
    keller.update({"CID": 440967, "C.A.S.": "18172-67-3", "Odor": "(-)-beta-Pinene",
                   "Odor dilution": "1/10", "Subject # (this study)": 47})
    graph = build_graph(pd.DataFrame([keller], index=[46426]), pd.DataFrame([record]),
                        {"cid:440967": {"status": "resolved", "inchikey": document["shared_inchikey"]}})
    assert generic_graph_to_dict(graph, registry=create_registry()) == document


def test_javascript_roundtrip_is_lossless(tmp_path, document):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not available")
    output = tmp_path / "second-example-js.json"
    subprocess.run([node, "-e", "const fs=require('fs'); const d=JSON.parse(fs.readFileSync(process.argv[1],'utf8')); fs.writeFileSync(process.argv[2],JSON.stringify(d));",
                    str(FIXTURE), str(output)], check=True, timeout=15)
    roundtrip = generic_graph_loads(output.read_text(encoding="utf-8"), registry=create_registry())
    assert generic_graph_to_dict(roundtrip, registry=create_registry()) == document
