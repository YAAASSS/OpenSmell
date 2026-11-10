"""Exercise the installed CLI contract through its module entry point."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def run_cli(*arguments, data=None):
    return subprocess.run(
        [sys.executable, "-m", "opensmell", *map(str, arguments)],
        input=data, capture_output=True, check=False,
    )


def report(result):
    assert result.stderr == b""
    return json.loads(result.stdout)["results"]


@pytest.mark.parametrize("command", ["validate", "inspect"])
@pytest.mark.parametrize("name", ["geraniol.osmell", "multisource_beta_pinene.osmell", "multisource_diphenyl_ether.osmell"])
def test_real_files_pass_with_exact_byte_identity(command, name):
    path = EXAMPLES / name
    before = path.read_bytes()
    result = run_cli(command, path, "--json")
    assert result.returncode == 0
    item = report(result)[0]
    assert item["status"] == "valid"
    assert item["sha256"] == hashlib.sha256(before).hexdigest()
    assert item["byte_count"] == len(before)
    assert path.read_bytes() == before
    if name == "geraniol.osmell":
        assert item["metadata"]["labels"]["en"] == "Geraniol"
        assert item["representations"][0]["provenance"]["source"] == "OdorNet"
        assert item["warnings"][0]["code"] == "unknown_scheme"
    else:
        assert item["resource_count"] > 1
        assert item["known_reference_count"] > 0
        assert item["unresolved_references"] == []
        assert any(resource["provenance"] for resource in item["resources"])


def test_stdin_and_file_in_one_report():
    result = run_cli("validate", "-", EXAMPLES / "geraniol.osmell", "--json",
                     data=(EXAMPLES / "multisource_beta_pinene.osmell").read_bytes())
    assert result.returncode == 0
    assert [item["input"] for item in report(result)] == ["-", str(EXAMPLES / "geraniol.osmell")]


@pytest.mark.parametrize("raw", [
    b"[]", b"{", b"null", b'{}', b'{"opensmell":"9.0","odor":{}}',
    b'{"opensmell":"0.1","opensmell":"0.1"}',
    b'{"extension":{"x":1,"\\u0078":2}}',
    b'{"x":NaN}', b'{"x":Infinity}', b'\xff',
    b'{"format":"org.opensmell.experimental.generic-resource-graph","version":"99","resources":[]}',
])
def test_invalid_text_fails_without_traceback(raw):
    result = run_cli("validate", "-", "--json", data=raw)
    assert result.returncode == 1
    assert report(result)[0]["status"] == "invalid"


def test_rejects_nonfinite_extension_and_invalid_known_scheme():
    doc = json.loads((EXAMPLES / "geraniol.osmell").read_bytes())
    doc["odor"]["representations"][0]["data"]["smiles"] = 5
    result = run_cli("validate", "-", "--json", data=json.dumps(doc).encode())
    assert result.returncode == 1
    doc = json.loads((EXAMPLES / "geraniol.osmell").read_bytes())
    doc["extension"] = "OVERFLOW"
    raw = json.dumps(doc).replace('"OVERFLOW"', "1e400").encode()
    assert run_cli("validate", "-", "--json", data=raw).returncode == 1


def test_unknown_resource_and_unresolved_reference_are_explicit():
    doc = json.loads((EXAMPLES / "multisource_beta_pinene.osmell").read_bytes())
    # Keep a known annotation, remove its target and add opaque future data.
    doc["resources"] = [r for r in doc["resources"] if r["type"] == "org.opensmell.annotation"][:1]
    doc["resources"].append({"id": "future", "type": "vendor.future", "type_version": "2",
                             "opaque": {"resource_id": "not-a-known-reference"}})
    result = run_cli("inspect", "-", "--json", data=json.dumps(doc).encode())
    assert result.returncode == 0
    item = report(result)[0]
    assert {w["code"] for w in item["warnings"]} == {"unknown_resource_type", "unresolved_references"}
    assert item["known_reference_count"] == 1
    assert len(item["unresolved_references"]) == 1
    assert item["resources"][1]["type_validation"] == "unknown"


def test_duplicate_resource_ids_and_invalid_known_resources_fail():
    doc = json.loads((EXAMPLES / "multisource_beta_pinene.osmell").read_bytes())
    doc["resources"].append(doc["resources"][0])
    assert run_cli("validate", "-", "--json", data=json.dumps(doc).encode()).returncode == 1
    doc["resources"].pop()
    doc["resources"][0]["smiles"] = 4
    assert run_cli("validate", "-", "--json", data=json.dumps(doc).encode()).returncode == 1


def test_batch_continues_after_invalid_and_missing_file(tmp_path):
    result = run_cli("validate", EXAMPLES / "invalid.osmell", tmp_path / "missing.osmell",
                     EXAMPLES / "geraniol.osmell", "--json")
    assert result.returncode == 2
    assert [item["status"] for item in report(result)] == ["invalid", "error", "valid"]


def test_text_inspection_exposes_provenance_and_escapes_terminal_control():
    doc = json.loads((EXAMPLES / "geraniol.osmell").read_bytes())
    doc["odor"]["id"] = "test\x1b[31m"
    result = run_cli("inspect", "-", data=json.dumps(doc).encode())
    assert result.returncode == 0
    assert b"OdorNet" in result.stdout
    assert b"\x1b" not in result.stdout
    assert b"\\u001b" in result.stdout


def test_help_version_and_usage_errors():
    assert run_cli("--help").returncode == 0
    assert b"OpenSmell" in run_cli("--version").stdout
    assert run_cli("validate").returncode == 2
    assert run_cli("inspect", "-", "-").returncode == 2


@pytest.mark.parametrize("mapper,resource_id,expected", [
    ("semantic", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b", [(0, 0.25), (1, 0.60)]),
    ("perceptual", "219ef28c-9b58-52f2-93a7-0807f5897857", [(0, 0.47), (1, 0.18), (2, 0.15)]),
])
def test_offline_plan_preserves_source_and_explicit_profile(mapper, resource_id, expected):
    source = EXAMPLES / "multisource_diphenyl_ether.osmell"
    profile = EXAMPLES / f"offline_{mapper}_profile.json"
    result = run_cli("plan", source, "--profile", profile,
                     "--resource-id", resource_id, "--duration", "5")
    assert result.returncode == 0, result.stdout
    assert result.stderr == b""
    output = json.loads(result.stdout)
    assert output["execution"] == "not_attempted"
    assert output["capability_basis"] == "supplied_profile_not_live_device"
    assert output["source"]["document"] == json.loads(source.read_bytes())
    assert output["profile"]["document"] == json.loads(profile.read_bytes())
    assert output["plan"]["duration"] == 5.0
    assert sorted((c["channel"], c["intensity"]) for c in output["plan"]["commands"]) == expected
    assert output["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert output["profile"]["sha256"] == hashlib.sha256(profile.read_bytes()).hexdigest()


@pytest.mark.parametrize("duration", ["31", "0", "nan", "inf", "-1", "0.01"])
def test_offline_plan_rejects_invalid_or_unsupported_duration(duration):
    result = run_cli("plan", EXAMPLES / "multisource_diphenyl_ether.osmell",
                     "--profile", EXAMPLES / "offline_semantic_profile.json",
                     "--resource-id", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b",
                     "--duration", duration)
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "invalid"
    assert b"Traceback" not in result.stderr


@pytest.mark.parametrize("change", ["channel", "intensity", "empty", "duplicate", "version", "mapper", "no_matches"])
def test_offline_plan_refuses_bad_mapping_or_capabilities(tmp_path, change):
    profile = json.loads((EXAMPLES / "offline_semantic_profile.json").read_bytes())
    if change == "channel":
        profile["bindings"][0]["channel"] = 9
    elif change == "intensity":
        profile["capabilities"]["channels"][0]["max_intensity"] = 0.1
    elif change == "empty":
        profile["bindings"] = []
    elif change == "duplicate":
        profile["bindings"].append(profile["bindings"][0])
    elif change == "no_matches":
        profile["bindings"] = [{"descriptor": "does-not-exist", "channel": 0, "intensity": 0.2}]
    else:
        profile[change] = "unsupported"
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile))
    result = run_cli("plan", EXAMPLES / "multisource_diphenyl_ether.osmell",
                     "--profile", path, "--resource-id", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b",
                     "--duration", "5")
    assert result.returncode == 1
    assert json.loads(result.stdout)["status"] == "invalid"


def test_plan_requires_graph_and_explicit_existing_resource(tmp_path):
    base = ["--profile", EXAMPLES / "offline_semantic_profile.json", "--resource-id", "absent", "--duration", "5"]
    assert run_cli("plan", EXAMPLES / "geraniol.osmell", *base).returncode == 1
    assert run_cli("plan", EXAMPLES / "multisource_diphenyl_ether.osmell", *base).returncode == 1
    assert run_cli("plan", tmp_path / "missing", *base).returncode == 2


def test_profile_ambiguity_and_nonfinite_extensions_rejected(tmp_path):
    profile = (EXAMPLES / "offline_semantic_profile.json").read_text()
    for raw in ['{"mapper":"semantic","mapper":"perceptual"}',
                profile.replace('"version": "0.1"', '"version": "0.1", "future": 1e400')]:
        path = tmp_path / "profile.json"
        path.write_text(raw)
        result = run_cli("plan", "-", "--profile", path,
                         "--resource-id", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b", "--duration", "5",
                         data=(EXAMPLES / "multisource_diphenyl_ether.osmell").read_bytes())
        assert result.returncode == 1


def test_sdk_planning_has_no_application_dependency():
    from opensmell.experimental.generic_graph import create_default_resource_type_registry, generic_graph_loads
    from opensmell.experimental.molecule import register_molecule_resource_type
    from opensmell.experimental.annotation import register_annotation_resource_type
    from opensmell.experimental.planning import plan_with_profile
    from opensmell.experimental.rendering import RenderRequest

    registry = create_default_resource_type_registry()
    register_molecule_resource_type(registry)
    register_annotation_resource_type(registry)
    graph = generic_graph_loads((EXAMPLES / "multisource_diphenyl_ether.osmell").read_text(), registry=registry)
    profile = json.loads((EXAMPLES / "offline_semantic_profile.json").read_bytes())
    plan = plan_with_profile(graph, RenderRequest("e6ad8ce3-dc6e-5d94-9287-57665d48fc0b", 5), profile)
    assert [command.channel for command in plan.commands] == [0, 1]
