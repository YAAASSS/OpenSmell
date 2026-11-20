"""Normal installed CLI boundary and software-only transcript preservation."""
import base64
import json
from pathlib import Path
import subprocess
import sys

import pytest

from opensmell.experimental.software_sequence import prepare_steps, run_software_sequence

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = "opensmell-local-simulator-001"


@pytest.fixture(scope="module")
def artifacts():
    result = []
    for profile, resource in [("semantic", "e6ad8ce3-dc6e-5d94-9287-57665d48fc0b"),
                              ("perceptual", "219ef28c-9b58-52f2-93a7-0807f5897857")]:
        result.append(subprocess.run([sys.executable, "-m", "opensmell", "plan",
            str(ROOT / "examples/multisource_diphenyl_ether.osmell"), "--profile",
            str(ROOT / f"examples/offline_{profile}_profile.json"), "--resource-id", resource,
            "--duration", ".1"], capture_output=True, check=True).stdout)
    return result


@pytest.fixture
def endpoint(tmp_path):
    def make(mode="normal"):
        path = tmp_path / "device.py"
        path.write_text(f'''
import json,sys
from pathlib import Path
from opensmell.experimental.lifecycle_simulator import SimulatedEndpoint
from opensmell.experimental.device_protocol import error_response
Path({str(tmp_path / 'launched')!r}).write_text('yes')
now=[0]
endpoint=SimulatedEndpoint(lambda:now[0]); count=0
for line in sys.stdin:
 request=json.loads(line)
 with Path({str(tmp_path / 'requests')!r}).open('a') as log:log.write(line)
 if request['type']=='render':
  count+=1
  if {mode!r}=='lost' and count==2:sys.exit(1)
  if {mode!r}=='rejected' and count==2:
   print(json.dumps(error_response('busy','Explicit refusal')),flush=True);continue
 if request['type']=='execution_status':now[0]+=30
 response=json.loads(endpoint.exchange(line))
 if {mode!r}=='caps' and request['type']=='get_capabilities':response['channels']=[0]
 if {mode!r}=='wrong' and request['type']=='execution_status' and count==2:response['execution_id']='stale'
 print(json.dumps(response),flush=True)
''')
        return [sys.executable, "-I", "-u", str(path)]
    return make


def test_normal_cli_and_preserved_unknown_input(artifacts, endpoint, tmp_path):
    first = json.loads(artifacts[0]); first["future"] = {"opaque": [None, 2**65]}
    inputs = [json.dumps(first, indent=3).encode(), artifacts[1]]
    files = []
    for i, raw in enumerate(inputs):
        path = tmp_path / f"{i}.json"; path.write_bytes(raw); files.append(str(path))
    output = tmp_path / "report.json"
    result = subprocess.run([sys.executable, "-m", "opensmell", "run-sequence", *files,
        "--software-command-json", json.dumps(endpoint()), "--expected-device-id", IDENTITY,
        "--output", str(output)], capture_output=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_bytes())
    assert json.loads(result.stdout) == report and report["status"] == "completed"
    steps = report["sequence"]["steps"]
    assert [s["state"] for s in steps] == ["completed", "completed"]
    for step, raw in zip(steps, inputs):
        assert base64.b64decode(step["context"]["input"]["data"]) == raw
        assert step["context"]["request"] == json.loads(raw)["request"]
    assert steps[0]["plan"]["commands"] != steps[1]["plan"]["commands"]
    assert [json.loads(e["request_line"])["type"] for e in report["transcript"]][3:] == ["render", "execution_status", "render", "execution_status"]
    assert all(e["response_line"].endswith("\n") for e in report["transcript"])
    # Collision must fail before launching a second process or changing evidence.
    before = (tmp_path / "requests").read_bytes(); saved = output.read_bytes()
    again = subprocess.run(result.args, capture_output=True)
    assert again.returncode == 2 and output.read_bytes() == saved
    assert (tmp_path / "requests").read_bytes() == before


@pytest.mark.parametrize("mode,status", [("rejected", "rejected"), ("lost", "unknown"), ("wrong", "unknown")])
def test_failure_at_second_step_keeps_first_receipt(artifacts, endpoint, mode, status):
    report = run_software_sequence([*artifacts, artifacts[0]], endpoint(mode), expected_device_id=IDENTITY)
    assert report["status"] == status
    assert [s["state"] for s in report["sequence"]["steps"]] == ["completed", status, "not_attempted"]
    assert sum(json.loads(e["request_line"])["type"] == "render" for e in report["transcript"]) == 2
    if mode == "lost": assert "diagnostic" in report["transcript"][-1]


@pytest.mark.parametrize("change", ["tamper", "duplicate_json", "long", "missing", "bad_command", "too_many", "identity"])
def test_preflight_failure_does_not_launch(artifacts, endpoint, tmp_path, change):
    inputs = list(artifacts); command = endpoint(); identity = IDENTITY
    if change == "tamper":
        obj = json.loads(inputs[1]); obj["plan"]["commands"][0]["intensity"] = .99
        inputs[1] = json.dumps(obj).encode()
    if change == "duplicate_json": inputs[1] = b'{"format":0,"format":1}'
    if change == "long": inputs[1] = b" " * (8 * 1048576 + 1)
    if change == "missing": inputs[1] = b"{}"
    if change == "bad_command": command = "python"
    if change == "too_many": inputs *= 9
    if change == "identity": identity = ""
    report = run_software_sequence(inputs, command, expected_device_id=identity)
    assert report["status"] == "invalid" and not report["transcript"]
    assert not (tmp_path / "launched").exists()


def test_wrong_identity_cannot_render(artifacts, endpoint):
    report = run_software_sequence(artifacts, endpoint(), expected_device_id="other")
    assert report["status"] == "incompatible"
    assert not any(json.loads(e["request_line"])["type"] == "render" for e in report["transcript"])


def test_checkpoint_failure_cannot_start_process(artifacts, endpoint, tmp_path):
    def fail(_): raise OSError("Storage failed")
    with pytest.raises(OSError): run_software_sequence(artifacts, endpoint(), expected_device_id=IDENTITY, on_progress=fail)
    assert not (tmp_path / "launched").exists()


def test_duration_total_refused_before_launch(artifacts, endpoint, tmp_path):
    obj = json.loads(artifacts[0]); obj["plan"]["duration"] = obj["request"]["duration"] = 30
    raw = json.dumps(obj).encode()
    report = run_software_sequence([raw] * 5, endpoint(), expected_device_id=IDENTITY)
    assert report["status"] == "invalid" and "120" in report["detail"]
    assert not (tmp_path / "launched").exists()
