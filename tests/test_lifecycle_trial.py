"""Installed-entry trial behavior, including failures that must never resend."""
import base64
import json
from pathlib import Path
import subprocess
import sys

import pytest

from opensmell.experimental.lifecycle_trial import lifecycle_trial

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = "opensmell-local-simulator-001"


@pytest.fixture(scope="module")
def plan_bytes():
    return subprocess.run([sys.executable, "-m", "opensmell", "plan",
                           str(ROOT / "examples/multisource_diphenyl_ether.osmell"),
                           "--profile", str(ROOT / "examples/offline_perceptual_profile.json"),
                           "--resource-id", "219ef28c-9b58-52f2-93a7-0807f5897857", "--duration", "5"],
                          capture_output=True, check=True).stdout


@pytest.fixture
def endpoint(tmp_path):
    def make(mode="normal"):
        path = tmp_path / "endpoint.py"
        path.write_text(f'''
import json,sys
from pathlib import Path
from opensmell.experimental.lifecycle_simulator import SimulatedEndpoint
from opensmell.experimental.device_protocol import error_response
mode={mode!r}
Path({str(tmp_path / 'launched')!r}).write_text('yes')
endpoint=SimulatedEndpoint((lambda:0) if mode=='never_completed' else __import__('time').monotonic)
for line in sys.stdin:
 request=json.loads(line)
 with Path({str(tmp_path / 'requests')!r}).open('a') as log:log.write(line)
 if request['type']=='render':
  if mode=='lost':sys.exit(1)
  if mode=='malformed':print('{{',flush=True);continue
  if mode=='rejected':print(json.dumps(error_response('busy','Already active')),flush=True);continue
 response=json.loads(endpoint.exchange(line))
 if mode=='duration' and request['type']=='get_capabilities':response['min_duration']=1
 if mode=='wrong_status' and request['type']=='execution_status':response['execution_id']='other'
 print(json.dumps(response),flush=True)
''')
        return [sys.executable, "-I", "-u", str(path)]
    return make


def renders(tmp_path):
    path = tmp_path / "requests"
    return [r for line in path.read_text().splitlines() if (r := json.loads(line))["type"] == "render"] if path.exists() else []


def test_trial_complete_stop_unknown_preserves_exact_input(plan_bytes, endpoint, tmp_path):
    source = json.loads(plan_bytes); source["future"] = {"unrecognized": [None, 2**64 + 1]}
    raw = json.dumps(source).encode()
    checkpoints = []
    report = lifecycle_trial(raw, endpoint(), expected_device_id=IDENTITY, on_progress=checkpoints.append)
    assert report["status"] == "passed"
    assert base64.b64decode(report["input"]["data"]) == raw
    assert [report["results"][phase]["state"] for phase in ("completion", "stop", "disconnect")] == ["completed", "stopped", "unknown"]
    assert [r["duration"] for r in renders(tmp_path)] == [.1, 5, 5]
    assert report["duplicate_request_refused_before_io"]
    assert report["execution"]["state"] == "unknown" and report["physical_validation"] is False
    assert checkpoints[0]["acceptance"] == "not_attempted" and not checkpoints[0]["transcript"]
    assert any(c["acceptance"] == "unknown" and c["transcript"][-1].get("response_line") is None for c in checkpoints if c["transcript"])
    assert report["context"]["request"] == source["request"]


@pytest.mark.parametrize("mode,status", [("rejected", "rejected"), ("lost", "unknown"),
                                        ("malformed", "unknown"), ("wrong_status", "unknown"),
                                        ("never_completed", "unknown")])
def test_refusal_or_uncertainty_stops_trial_without_resend(plan_bytes, endpoint, tmp_path, mode, status):
    report = lifecycle_trial(plan_bytes, endpoint(mode), expected_device_id=IDENTITY)
    assert report["status"] == status
    assert len(renders(tmp_path)) == 1
    assert report["phase"] == "completion" and "stop" not in report["results"]
    assert report["execution"]["state"] == status
    assert report["acceptance"] == ("rejected" if mode == "rejected" else "unknown" if mode in {"lost", "malformed"} else "accepted")


@pytest.mark.parametrize("mode,identity", [("duration", IDENTITY), ("normal", "wrong-device")])
def test_identity_or_duration_preflight_never_renders(plan_bytes, endpoint, tmp_path, mode, identity):
    report = lifecycle_trial(plan_bytes, endpoint(mode), expected_device_id=identity)
    assert report["status"] == "incompatible" and report["acceptance"] == "not_attempted"
    assert not renders(tmp_path)


@pytest.mark.parametrize("change", ["altered_plan", "unsupported_duration", "invalid_graph", "duplicate_json", "command"])
def test_invalid_input_does_not_launch(plan_bytes, endpoint, tmp_path, change):
    source = json.loads(plan_bytes)
    command = endpoint()
    if change == "altered_plan":
        source["plan"]["commands"][0]["intensity"] = .123
    elif change == "unsupported_duration":
        source["request"]["duration"] = source["plan"]["duration"] = 1
    elif change == "invalid_graph":
        source["source"]["document"]["resources"] = "invalid"
    elif change == "command":
        command = "implicit-shell-command"
    raw = b'{"a":1,"a":2}' if change == "duplicate_json" else json.dumps(source).encode()
    report = lifecycle_trial(raw, command, expected_device_id=IDENTITY)
    assert report["status"] == "invalid" and report["acceptance"] == "not_attempted"
    assert not (tmp_path / "launched").exists()


def test_cli_new_report_and_collision_before_launch(plan_bytes, endpoint, tmp_path):
    command = endpoint()
    source, output = tmp_path / "plan.json", tmp_path / "report.json"
    source.write_bytes(plan_bytes)
    args = [sys.executable, "-m", "opensmell", "lifecycle-trial", str(source),
            "--software-command-json", json.dumps(command), "--expected-device-id", IDENTITY, "--output", str(output)]
    result = subprocess.run(args, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_bytes()) == json.loads(result.stdout)
    before = output.read_bytes()
    (tmp_path / "launched").unlink()
    assert subprocess.run(args, capture_output=True).returncode == 2
    assert output.read_bytes() == before and not (tmp_path / "launched").exists()


def test_cli_lost_reply_keeps_unknown_report(plan_bytes, endpoint, tmp_path):
    output = tmp_path / "unknown.json"
    result = subprocess.run([sys.executable, "-m", "opensmell", "lifecycle-trial", "-",
                             "--software-command-json", json.dumps(endpoint("lost")),
                             "--expected-device-id", IDENTITY, "--output", str(output)],
                            input=plan_bytes, capture_output=True)
    assert result.returncode == 1
    report = json.loads(output.read_bytes())
    assert report["status"] == "unknown" and report["execution"]["state"] == "unknown"
    assert len(renders(tmp_path)) == 1 and "error" in report["transcript"][-1]
