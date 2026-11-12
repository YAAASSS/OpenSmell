"""Source-preserving installed Core interoperability, including failure cases."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from opensmell.exceptions import OpenSmellError
from opensmell.experimental.core_interchange import (
    IMPORT_KEY, bridge_core_bytes, extract_core_bytes, interchange_registry,
)
from opensmell.experimental.generic_graph import generic_graph_to_dict
from opensmell.experimental.planning import plan_with_profile
from opensmell.experimental.rendering import RenderRequest

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "examples/geraniol.osmell").read_bytes()


def encoded(result):
    return json.dumps(generic_graph_to_dict(result.graph, registry=interchange_registry())).encode()


def cli(*args, data=None):
    return subprocess.run([sys.executable, "-m", "opensmell", *map(str, args)],
                          input=data, capture_output=True, check=False)


def test_real_core_to_graph_to_plan_and_exact_source():
    result = bridge_core_bytes(RAW)
    graph_bytes = encoded(result)
    assert extract_core_bytes(graph_bytes) == RAW
    profile = json.loads((ROOT / "examples/offline_semantic_profile.json").read_bytes())
    plan = plan_with_profile(result.graph, RenderRequest(result.primary_resource_id, 5), profile)
    assert [(c.channel, c.intensity) for c in plan.commands] == [(0, 0.25)]
    assert encoded(bridge_core_bytes(RAW)) == graph_bytes


def test_unknown_content_and_whitespace_are_recoverable_at_every_level():
    source = json.loads(RAW)
    source["future"] = {"anything": ["é", 1, None]}
    source["odor"]["extra_future"] = {"x": False}
    source["odor"]["metadata"]["future"] = "preserve"
    chemical = source["odor"]["representations"][0]
    chemical["scheme"]["future"] = {"v": 8}
    chemical["data"]["future"] = "not projected"
    chemical["future"] = 42
    source["odor"]["representations"].append({
        "type": "future", "scheme": {"id": "example.unknown", "version": "9",
                                    "future": "scheme extension"},
        "data": {"vector": [1, 2, 3]}, "future": {"a": True},
        "core_representation_type": "collision preserved in original",
    })
    raw = (" \n" + json.dumps(source, ensure_ascii=False, indent=3) + "\n\n").encode()
    result = bridge_core_bytes(raw)
    assert extract_core_bytes(encoded(result)) == raw
    assert result.graph.resources[-1].scheme.id == "example.unknown"
    # Extraction is original-source recovery, never a reverse application of graph edits.
    result.graph.resources[0].smiles = "CCO"
    assert extract_core_bytes(encoded(result)) == raw
    assert source["odor"]["representations"][-1]["core_representation_type"].startswith("collision")


@pytest.mark.parametrize("mutation", ["checksum", "count", "encoding", "data", "odor_id", "version"])
def test_snapshot_corruption_fails(mutation):
    result = bridge_core_bytes(RAW)
    snapshot = result.graph.extra[IMPORT_KEY]
    source = snapshot["source"]
    if mutation == "checksum":
        source["sha256"] = "0" * 64
    elif mutation == "count":
        source["byte_count"] = True
    elif mutation == "encoding":
        source["encoding"] = "text"
    elif mutation == "data":
        source["data"] = "bad!"
    elif mutation == "odor_id":
        source["odor_id"] = "wrong"
    else:
        snapshot["version"] = "9"
    with pytest.raises(ValueError):
        extract_core_bytes(encoded(result))


@pytest.mark.parametrize("raw", [
    b'{"opensmell":"0.1","opensmell":"0.1"}',
    b'{"opensmell":"0.1","odor":null}',
    b'{"format":"other","opensmell":"0.1"}',
    b'{"extra":NaN}', b'{"extra":1e9999}', b"\xff", b"[]",
])
def test_invalid_or_ambiguous_source_is_refused(raw):
    with pytest.raises((OpenSmellError, ValueError, TypeError)):
        bridge_core_bytes(raw)


@pytest.mark.parametrize("kind", ["missing", "multiple", "unsupported"])
def test_unsupported_chemical_source_refused(kind):
    source = json.loads(RAW)
    if kind == "missing":
        source["odor"]["representations"] = source["odor"]["representations"][1:]
    elif kind == "multiple":
        source["odor"]["representations"].append(deepcopy(source["odor"]["representations"][0]))
    else:
        source["odor"]["representations"][0]["scheme"]["version"] = "99"
    with pytest.raises(ValueError):
        bridge_core_bytes(json.dumps(source).encode())


def test_tampered_embedded_document_is_still_validated():
    result = bridge_core_bytes(RAW)
    source = result.graph.extra[IMPORT_KEY]["source"]
    raw = b'{"opensmell":"0.1","odor":{}}'
    source.update(data=base64.b64encode(raw).decode(), byte_count=len(raw),
                  sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises((OpenSmellError, ValueError, TypeError)):
        extract_core_bytes(encoded(result))


def test_cli_file_stdin_roundtrip_and_no_overwrite(tmp_path):
    source = tmp_path / "source.osmell"
    source.write_bytes(RAW)
    target = tmp_path / "graph.osmell"
    run = cli("bridge-core", source, "--output", target)
    assert run.returncode == 0 and run.stdout == run.stderr == b""
    graph_before = target.read_bytes()
    assert cli("validate", target, "--json").returncode == 0
    recovered = cli("extract-core", "-", data=graph_before)
    assert recovered.returncode == 0 and recovered.stdout == RAW
    assert cli("bridge-core", source, "--output", source).returncode == 2
    assert source.read_bytes() == RAW
    assert cli("bridge-core", source, "--output", target).returncode == 2
    assert target.read_bytes() == graph_before
    assert cli("bridge-core", "-", data=RAW).returncode == 0


def test_cli_errors_never_create_output(tmp_path):
    output = tmp_path / "not-created"
    result = cli("bridge-core", "-", "--output", output, data=b"{}")
    assert result.returncode == 1 and not output.exists()
    assert result.stdout == b"" and json.loads(result.stderr)["status"] == "invalid"
    assert cli("bridge-core", tmp_path / "missing").returncode == 2
    assert cli("extract-core", "-", data=RAW).returncode == 1
