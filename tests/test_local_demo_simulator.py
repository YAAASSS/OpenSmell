"""Lifecycle evidence through the normal HTTP preview/connect/send/stop routes."""
import http.client
import json
import threading

import pytest
from apps.local_demo.__main__ import create_server
from apps.local_demo.simulator import SimulatedEndpoint, SimulatedHardwareService


class Clock:
    now = 100.0
    def __call__(self):
        return self.now


@pytest.fixture
def api():
    clock = Clock()
    endpoint = SimulatedEndpoint(clock)
    hardware = SimulatedHardwareService(clock=clock, factory=lambda _: endpoint)
    server = create_server(0, hardware=hardware)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    def request(route, data=None, expected=200):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET" if data is None else "POST", "/api/" + route,
                     body=None if data is None else json.dumps(data),
                     headers={} if data is None else {"Content-Type": "application/json"})
        response = conn.getresponse()
        result = json.loads(response.read())
        conn.close()
        assert response.status == expected, result
        return result
    yield request, clock, endpoint
    server.shutdown()
    thread.join()
    server.server_close()


def send(request, revision=1, duration=5):
    result = request("preview", {"client_id": "simulated-browser", "revision": revision,
                                "duration": duration, "policy": "semantic"})
    ticket = result["preview_ticket"]
    request("hardware/check", ticket)
    return request("hardware/send", ticket), ticket


def test_complete_stop_and_stale_stop_via_http(api):
    request, clock, endpoint = api
    assert request("hardware/status")["simulated"] is True
    connected = request("hardware/connect", {"port": "SIMULATED"})
    assert connected["device_id"] == "opensmell-local-simulator-001"
    assert connected["lifecycle_capabilities"]["stop"] is True
    first, ticket = send(request)
    first_id = first["execution"]["execution_id"]
    assert first["execution"]["state"] == "running"
    request("hardware/send", ticket, expected=409)
    clock.now += 5
    completed = request("hardware/status")["execution"]
    assert completed["state"] == "completed"
    assert completed["observation"]["execution_id"] == first_id
    second, _ = send(request, 2)
    second_id = second["execution"]["execution_id"]
    assert second_id != first_id
    request("hardware/stop", {"execution_id": first_id}, expected=409)
    assert endpoint.execution["state"] == "running"
    stopped = request("hardware/stop", {"execution_id": second_id})
    assert stopped["execution"]["state"] == "stopped"
    assert stopped["execution"]["observation"]["execution_id"] == second_id
    assert request("hardware/stop", {"execution_id": second_id})["execution"]["state"] == "stopped"
    clock.now += 10
    assert request("hardware/status")["execution"]["state"] == "stopped"


@pytest.mark.parametrize("disconnect", [True, False])
def test_link_loss_never_invents_completion(api, disconnect):
    request, clock, endpoint = api
    request("hardware/connect", {"port": "SIMULATED"})
    send(request)
    if disconnect:
        request("hardware/disconnect", {})
    else:
        endpoint.close()
    assert request("hardware/status")["execution"]["state"] == "unknown"
    clock.now += 20
    assert request("hardware/status")["execution"]["state"] == "unknown"


def test_wrong_execution_reply_is_unknown(api):
    request, _, endpoint = api
    request("hardware/connect", {"port": "SIMULATED"})
    send(request)
    original = endpoint.exchange
    def wrong(message):
        reply = json.loads(original(message))
        reply["execution_id"] = "unrelated"
        return json.dumps(reply)
    endpoint.exchange = wrong
    assert request("hardware/status")["execution"]["state"] == "unknown"


def test_simulator_rejects_physical_ports_and_duration(api):
    request, _, endpoint = api
    request("hardware/connect", {"port": "COM8"}, expected=400)
    request("hardware/connect", {"port": "SIMULATED"})
    result = request("preview", {"client_id": "simulated-browser", "revision": 1, "duration": 31})
    request("hardware/send", result["preview_ticket"], expected=409)
    assert endpoint.execution is None
    request("hardware/stop", {}, expected=400)


def test_device_rejection_is_exportable_and_connection_recovers(api):
    request, _, endpoint = api
    request('hardware/connect', {'port': 'SIMULATED'})
    # Another software client owns the endpoint's run; the app has no local run.
    external = json.loads(endpoint.exchange(json.dumps({
        'type': 'render', 'protocol_version': '0.1', 'duration': 5,
        'commands': [{'channel': 0, 'intensity': 0.5}],
    })))
    p = request('preview', {'client_id': 'simulated-browser', 'revision': 1, 'duration': 5})
    request('hardware/send', p['preview_ticket'], expected=502)
    state = request('hardware/status')
    assert state['connection'] == 'connected'
    assert state['execution']['state'] == 'rejected'
    assert state['execution']['response']['code'] == 'busy'
    evidence = request('hardware/evidence?report_id=' + state['evidence_id'])
    assert json.loads(evidence['exchanges'][-1]['response_text'])['code'] == 'busy'
    endpoint.exchange(json.dumps({'type': 'stop', 'profile': 'local-simulator-lifecycle-v1',
                                 'execution_id': external['execution_id']}))
    fresh, _ = send(request, revision=2)
    assert fresh['execution']['state'] == 'running'
    assert request('hardware/stop', {'execution_id': fresh['execution']['execution_id']})['execution']['state'] == 'stopped'


@pytest.mark.parametrize('advertised', [None, 'future-errors'])
def test_error_capability_migration(advertised):
    class Endpoint(SimulatedEndpoint):
        def _handle(self, request):
            reply = super()._handle(request)
            if request.get('type') == 'lifecycle_capabilities':
                if advertised is None:
                    reply.pop('errors')
                else:
                    reply['errors'] = advertised
            return reply
    hardware = SimulatedHardwareService(factory=lambda _: Endpoint())
    try:
        if advertised is None:
            assert hardware.connect('SIMULATED')['connection'] == 'connected'
        else:
            from apps.local_demo.hardware import HardwareError
            with pytest.raises(HardwareError, match='Unsupported lifecycle capabilities'):
                hardware.connect('SIMULATED')
            assert hardware.status()['connection'] == 'disconnected'
    finally:
        hardware.close()
