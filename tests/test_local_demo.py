"""Application integration tests: real mappings, diagnostics and no hardware."""

from copy import deepcopy
import http.client
import json
import subprocess
import sys
import threading

import pytest

from apps.local_demo.__main__ import MAX_BODY, create_server
from apps.local_demo.service import FIXTURE, PreviewError, preview
from tools import multisource_demo as demo


@pytest.fixture
def document():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def calculate(document, **kwargs):
    return preview(json.dumps(document), **kwargs)


def commands(result, policy):
    return {item["channel"]: item["intensity"] for item in result["plans"][policy]["commands"]}


@pytest.mark.parametrize("policy", ["semantic", "perceptual"])
def test_fixture_uses_real_mappers_and_duration(document, monkeypatch, policy):
    calls = []
    for mapper_type in (demo.SemanticChannelMapper, demo.PerceptualChannelMapper):
        original = mapper_type.map

        def spy(self, graph, request, original=original):
            calls.append((type(self).__name__, request.duration))
            return original(self, graph, request)

        monkeypatch.setattr(mapper_type, "map", spy)
    result = calculate(document, policy=policy, duration=7.5)
    assert result["policy"] == policy
    assert commands(result, "semantic") == {1: 0.60, 2: 1.00}
    assert commands(result, "perceptual") == {0: 0.01, 1: 0.86, 2: 0.97}
    assert all(plan["duration"] == 7.5 for plan in result["plans"].values())
    assert calls == [("SemanticChannelMapper", 7.5), ("PerceptualChannelMapper", 7.5)]
    assert result["molecule"]["provenance"] == document["resources"][0]["provenance"]
    assert result["observation"]["provenance"] == document["resources"][4]["provenance"]


def test_changed_data_changes_plans_without_conflating_zero_missing_unknown(document):
    annotations = document["resources"][1]["data"]["annotations"]
    next(item for item in annotations if item["value"] == "floral")["state"] = "present"
    next(item for item in annotations if item["value"] == "green&herbal")["state"] = "unknown"
    del next(item for item in annotations if item["value"] == "woody&mossy")["state"]
    measurements = document["resources"][4]["results"][0]["data"]["measurements"]
    next(item for item in measurements if item["property"] == "wood")["value"] = 0
    del next(item for item in measurements if item["property"] == "grass")["value"]
    document["resources"][0].pop("provenance")
    document["resources"][4]["provenance"]["record"] = None
    result = calculate(document)
    assert commands(result, "semantic") == {0: 0.25}
    assert commands(result, "perceptual") == {0: 0.01, 2: 0.0}
    assert result["annotations"][0]["data"]["annotations"] == annotations
    assert result["observation"]["results"][0]["data"]["measurements"] == measurements
    assert "provenance" not in result["molecule"]
    assert result["observation"]["provenance"]["record"] is None


def test_all_absent_annotations_produce_empty_semantic_plan(document):
    for item in document["resources"][1]["data"]["annotations"]:
        item["state"] = "absent"
    assert commands(calculate(document), "semantic") == {}


@pytest.mark.parametrize("text", ["not json", "{}", "[]", '{"opensmell":"0.1","odor":{}}', '{"format":NaN}'])
def test_bad_files_are_diagnosed(text):
    with pytest.raises(PreviewError, match="Invalid file"):
        preview(text)


def test_duplicate_resource_id_is_invalid(document):
    document["resources"].append(deepcopy(document["resources"][0]))
    with pytest.raises(PreviewError, match="duplicate Resource ID"):
        calculate(document)


@pytest.mark.parametrize("missing", [0, 1, 2, 3, 4])
def test_missing_required_or_referenced_resource_is_diagnosed(document, missing):
    document["resources"].pop(missing)
    with pytest.raises(PreviewError, match="[Ii]ncompatible"):
        calculate(document)


def test_unlinked_stimulus_is_diagnosed(document):
    document["resources"][2].pop("source")
    with pytest.raises(PreviewError, match="stimulus"):
        calculate(document)


def test_optional_target_is_not_invented(document):
    document["resources"][4].pop("target")
    assert calculate(document)["target"] is None


def test_second_molecule_is_diagnosed(document):
    other = deepcopy(document["resources"][0])
    other["id"] = "another-molecule"
    document["resources"].append(other)
    with pytest.raises(PreviewError, match="exactly one molecule"):
        calculate(document)


def test_unsupported_perceptual_scheme_is_diagnosed(document):
    document["resources"][4]["results"][0]["scheme"]["version"] = "999"
    with pytest.raises(PreviewError, match="no usable"):
        calculate(document)


def test_nonmatching_measurements_are_diagnosed(document):
    document["resources"][4]["results"][0]["data"]["measurements"] = [
        {"property": "unmapped", "value": 0, "scale": {"min": 0, "max": 100}}
    ]
    with pytest.raises(PreviewError, match="no usable"):
        calculate(document)


@pytest.mark.parametrize("duration", [0, -1, None, True, "5", float("nan"), float("inf")])
def test_invalid_duration_is_diagnosed(document, duration):
    with pytest.raises(PreviewError, match="duration"):
        calculate(document, duration=duration)


def test_invalid_policy_is_diagnosed(document):
    with pytest.raises(PreviewError, match="Unknown policy"):
        calculate(document, policy="hardware")


def test_preview_never_imports_serial_or_opens_external_connections():
    # A fresh process avoids mistaking modules imported by other tests for
    # dependencies of the app. Fail even on importing a transport or PubChem.
    script = '''
import builtins
import socket
original = builtins.__import__
def guarded(name, *args, **kwargs):
    assert not any(part == "serial" or part.endswith("_transport") or "pubchem" in part or part == "protocol_device_adapter" for part in name.split(".")), name
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
class NoNetwork(socket.socket):
    def __init__(self, *args, **kwargs):
        raise AssertionError("Preview attempted to open a network socket")
socket.socket = NoNetwork
from apps.local_demo.service import FIXTURE, preview
for policy in ("semantic", "perceptual"):
    preview(FIXTURE.read_text(encoding="utf-8"), policy=policy)
'''
    subprocess.run([sys.executable, "-c", script], cwd=FIXTURE.parents[1], check=True, timeout=20)


@pytest.fixture
def server():
    httpd = create_server(0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)


def request(server, method, path, payload=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    try:
        connection.request(method, path, json.dumps(payload) if payload is not None else None,
                           headers=headers or {"Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, response.read(), dict(response.getheaders())
    finally:
        connection.close()


def test_http_fixture_import_and_errors(server, document):
    assert server.server_address[0] == "127.0.0.1"
    status, body, _ = request(server, "POST", "/api/preview", {"source": "fixture", "policy": "perceptual", "duration": 3})
    assert status == 200
    assert commands(json.loads(body), "perceptual") == {0: 0.01, 1: 0.86, 2: 0.97}
    status, body, _ = request(server, "POST", "/api/preview", {"source": "file", "text": json.dumps(document)})
    assert status == 200
    assert commands(json.loads(body), "semantic") == {1: 0.6, 2: 1.0}
    for payload in ({"source": "file", "text": "broken"}, {"duration": 0}, {"source": "some/path"}, []):
        status, body, _ = request(server, "POST", "/api/preview", payload)
        assert status == 400
        assert json.loads(body)["error"]


@pytest.mark.parametrize("path", ["/", "/app.js", "/hardware.js", "/app.css", "/logo-full.png", "/logo-small.png"])
def test_local_assets_are_served(server, path):
    status, body, headers = request(server, "GET", path)
    assert status == 200
    assert body
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    if path.startswith("/logo"):
        filename = "OpenSmell_Official_Logo_Full.png" if "full" in path else "OpenSmell_Official_Logo_Small.png"
        assert body == (FIXTURE.parents[1] / "docs/images" / filename).read_bytes()


def test_server_has_no_file_browsing_or_unrestricted_render_or_stop(server):
    for path in ("/../pyproject.toml", "/examples/multisource_beta_pinene.osmell", "/.git/config"):
        assert request(server, "GET", path)[0] == 404
    for path in ("/api/render", "/api/ports", "/api/connect", "/api/stop"):
        assert request(server, "POST", path, {})[0] == 404
    assert request(server, "POST", "/api/preview", {}, {"Content-Type": "text/plain"})[0] == 415
    assert request(server, "POST", "/api/preview", {}, {"Origin": "https://example.com"})[0] == 403
    assert request(server, "GET", "/", headers={"Host": "example.com"})[0] == 403
    assert request(server, "POST", "/api/preview", {}, {"Content-Type": "application/json", "Content-Length": str(MAX_BODY + 1)})[0] == 413
