"""Cross the independent JS reader/byte transfer with the real Python loader/app."""

import hashlib
import http.client
import json
from pathlib import Path
import shutil
import subprocess
import threading

import pytest

from apps.local_demo.__main__ import create_server
from apps.local_demo.hardware import HardwareService
from opensmell.experimental.generic_graph import generic_graph_loads, generic_graph_to_dict
from opensmell.experimental.reference_discovery import discover_graph_references
from tools.multisource_demo import create_registry


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name,key,semantic,perceptual", [
    ("beta_pinene", "WTARULDDTDQWMU-IUCAKERBSA-N", {1: 0.60, 2: 1.00}, {0: 0.01, 1: 0.86, 2: 0.97}),
    ("diphenyl_ether", "USIUVYZYUHIAEV-UHFFFAOYSA-N", {0: 0.25, 1: 0.60}, {0: 0.47, 1: 0.18, 2: 0.15}),
])
@pytest.mark.parametrize("bom", [False, True])
def test_js_interpretation_and_byte_transfer_into_python(tmp_path, name, key, semantic, perceptual, bom):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js required for cross-language exchange; mandatory in interoperability CI")
    original = (ROOT / f"examples/multisource_{name}.osmell").read_bytes()
    if bom:
        original = b"\xef\xbb\xbf" + original
    source, copied, report_path = (tmp_path / name for name in ("input.osmell", "copy.osmell", "inspection.json"))
    source.write_bytes(original)
    subprocess.run([node, str(ROOT / "apps/graph_viewer_js/inspect.cjs"), str(source), str(copied), str(report_path)],
                   check=True, capture_output=True, text=True, timeout=15)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert copied.read_bytes() == original
    assert report["file"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert report["file"]["byte_length"] == len(original)
    assert report["file"]["utf8_bom"] is bom

    # Compare independently interpreted content, separately from file identity.
    registry = create_registry()
    graph = generic_graph_loads(copied.read_text(encoding="utf-8-sig"), registry=registry)
    parsed = generic_graph_to_dict(graph, registry=registry)
    molecule, annotation, _, _, observation = parsed["resources"]
    assert report["molecules"][0]["identifiers"] == molecule["identifiers"] == [{"scheme": "pubchem.inchikey", "value": key}]
    assert {item["value"]: item["state"] for item in report["annotations"][0]["entries"]} == {
        item["value"]: item["state"] for item in annotation["data"]["annotations"]}
    expected_measurements = observation["results"][0]["data"]["measurements"]
    actual_measurements = report["observations"][0]["groups"][0]["entries"]
    assert {item["property"]: item["value"]["text"] for item in actual_measurements} == {
        item["property"]: str(item["value"]) for item in expected_measurements}
    assert {(item["source_id"], item["target_id"]) for item in report["references"]} == {
        (item.source_id, item.target_id) for item in discover_graph_references(graph)}
    for branch, resource in ((report["annotations"][0], annotation), (report["observations"][0], observation)):
        assert json.loads(branch["source"]["provenance_json"]) == resource["provenance"]

    def forbidden(*args, **kwargs):
        pytest.fail("JS/Python exchange must never open or enumerate serial ports")

    server = create_server(0, hardware=HardwareService(available=lambda: False, factory=forbidden, ports=forbidden))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        for revision, policy in enumerate(("semantic", "perceptual"), 1):
            connection.request("POST", "/api/preview", json.dumps({
                "source": "file", "text": copied.read_bytes().decode("utf-8"), "duration": 5,
                "policy": policy, "client_id": "js-python-exchange", "revision": revision,
            }), {"Content-Type": "application/json"})
            response = connection.getresponse()
            result = json.loads(response.read())
            assert response.status == 200, result
            for name, expected in (("semantic", semantic), ("perceptual", perceptual)):
                plan = result["plans"][name]
                assert plan["duration"] == 5
                assert {item["channel"]: item["intensity"] for item in plan["commands"]} == expected
            with server.previews.current(result["preview_ticket"]) as entry:
                assert {item.channel: item.intensity for item in entry["plan"].commands} == {
                    "semantic": semantic, "perceptual": perceptual}[policy]
        assert server.hardware.status()["connection"] == "disconnected"
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(5)
