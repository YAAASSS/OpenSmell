import json
import math
import sys
import pytest
from opensmell.experimental.lifecycle_adapter import LifecycleAdapter
from opensmell.experimental.lifecycle_simulator import SimulatedEndpoint, SIMULATOR_ID
from opensmell.experimental.process_transport import ProcessTransport
from opensmell.experimental.rendering import RenderingPlan, DeviceCommand

def plan(duration=5):
    return RenderingPlan([DeviceCommand(0, 0.25)], duration)

def test_complete_stop_unknown_and_snapshots():
    now = [0]
    endpoint = SimulatedEndpoint(lambda: now[0])
    client = LifecycleAdapter(endpoint, expected_device_id=SIMULATOR_ID)
    accepted = client.render(plan(), request_id="one")
    eid = accepted["execution_id"]
    assert accepted["state"] == "accepted"
    with pytest.raises(ValueError, match="active"):
        client.render(plan(), request_id="two")
    with pytest.raises(ValueError, match="Stale"):
        client.stop("stale")
    now[0] = 5
    assert client.status(eid)["state"] == "completed"
    assert client.stop(eid)["state"] == "completed"
    assert accepted["state"] == "accepted"
    with pytest.raises(ValueError, match="consumed"):
        client.render(plan(), request_id="one")
    run = client.render(plan(), request_id="two")
    assert client.stop(run["execution_id"])["state"] == "stopped"
    run = client.render(plan(), request_id="three")
    client.close()
    assert client.execution["state"] == "unknown"
    assert client.status(run["execution_id"])["state"] == "unknown"
    with pytest.raises(ValueError, match="closed"):
        client.render(plan(), request_id="four")

@pytest.mark.parametrize("fault", ["eof", "malformed", "wrong_id", "missing_id", "reused_id"])
def test_ambiguous_exchange_closes_without_retry(fault):
    endpoint = SimulatedEndpoint()
    original = endpoint.exchange
    calls = []
    def exchange(message):
        request = json.loads(message)
        calls.append(request["type"])
        if request["type"] == "render" and fault in {"eof", "malformed", "missing_id"}:
            if fault == "eof":
                raise OSError("EOF")
            return "{" if fault == "malformed" else '{"type":"ok","protocol_version":"0.1"}'
        if request["type"] == "execution_status" and fault == "wrong_id":
            return '{"profile":"local-simulator-lifecycle-v1","execution_id":"wrong","state":"completed"}'
        response = original(message)
        if request["type"] == "render" and fault == "reused_id":
            data = json.loads(response)
            data["execution_id"] = "reused"
            return json.dumps(data)
        return response
    endpoint.exchange = exchange
    client = LifecycleAdapter(endpoint, expected_device_id=SIMULATOR_ID)
    if fault == "reused_id":
        client._execution_ids.add("reused")
    run = client.render(plan(), request_id="one")
    if fault == "wrong_id":
        run = client.status(run["execution_id"])
    assert run["state"] == "unknown"
    assert endpoint.closed
    assert calls.count("render") == 1

def test_refusal_preserves_connection_and_local_validation():
    endpoint = SimulatedEndpoint()
    client = LifecycleAdapter(endpoint, expected_device_id=SIMULATOR_ID)
    with pytest.raises(ValueError):
        client.render(plan(31), request_id="valid-later")
    assert endpoint.execution is None
    endpoint.exchange(json.dumps({"type":"render","protocol_version":"0.1",
                                  "duration":5,"commands":[{"channel":0,"intensity":0.2}]}))
    run = client.render(plan(), request_id="valid-later")
    assert run["state"] == "rejected"
    assert not endpoint.closed
    with pytest.raises(ValueError, match="consumed"):
        client.render(plan(), request_id="valid-later")
    client.close()

def test_identity_failure_closes():
    endpoint = SimulatedEndpoint()
    with pytest.raises(ValueError, match="identity"):
        LifecycleAdapter(endpoint, expected_device_id="wrong")
    assert endpoint.closed

@pytest.mark.parametrize("timeout", [0, -1, math.inf, math.nan, True])
def test_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        ProcessTransport([sys.executable], timeout=timeout)

def test_process_timeout_closes():
    transport = ProcessTransport([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.05)
    with pytest.raises(TimeoutError):
        transport.exchange('{}')
    assert transport.process.poll() is not None
