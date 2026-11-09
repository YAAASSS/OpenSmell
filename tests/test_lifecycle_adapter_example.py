import json
import shutil
import sys

import pytest
from apps.local_demo.process_transport import ProcessTransport, node_transport, NODE_DEVICE_ID
from apps.local_demo.simulator import SimulatedEndpoint, SIMULATOR_ID
from tools.verify_lifecycle_adapter import verify


def test_python_reference_cases():
    report = verify(lambda _: SimulatedEndpoint(), SIMULATOR_ID)
    assert report['passed'], report
    assert len(report['cases']) == 10


@pytest.mark.skipif(not shutil.which('node'), reason='Node.js example requires Node.js')
def test_independent_node_reference_cases():
    report = verify(node_transport, NODE_DEVICE_ID)
    assert report['passed'], report
    assert len(report['cases']) == 10
    assert any(e.get('response', {}).get('state') == 'completed' for e in report['exchanges'])


@pytest.mark.parametrize('program', [
    'import time; time.sleep(10)',
    'print("not json", flush=True)',
    'print("x" * 65537, flush=True)',
    'pass',
])
def test_broken_process_is_closed_and_never_reused(program):
    transport = ProcessTransport([sys.executable, '-u', '-c', program], timeout=0.2)
    with pytest.raises(Exception):
        transport.exchange('{"type":"hello"}')
    assert transport.process.poll() is not None
    with pytest.raises(OSError, match='closed'):
        transport.exchange('{"type":"hello"}')
    transport.close()


@pytest.mark.skipif(not shutil.which('node'), reason='Node.js example requires Node.js')
def test_node_rejects_invalid_plans_and_recovers():
    transport = node_transport('SIMULATED')
    try:
        for duration, commands in [(31,[{'channel':0,'intensity':0.5}]),
                                   (5,[{'channel':0,'intensity':True}]),
                                   (5,[{'channel':0,'intensity':0.5}]*2)]:
            reply = json.loads(transport.exchange(json.dumps({'protocol_version':'0.1','type':'render',
                                                              'duration':duration,'commands':commands})))
            assert reply['type'] == 'error'
        assert json.loads(transport.exchange('{"protocol_version":"0.1","type":"hello"}'))['device_id'] == NODE_DEVICE_ID
    finally:
        transport.close()


def test_reference_runner_detects_broken_stop():
    class BrokenStop(SimulatedEndpoint):
        def exchange(self, text):
            request = json.loads(text)
            if request['type'] == 'stop' and request.get('profile') == 'local-simulator-lifecycle-v1' and self.execution and request.get('execution_id') == self.execution['execution_id']:
                request['type'] = 'execution_status'
            return super().exchange(json.dumps(request))
    report = verify(lambda _: BrokenStop(), SIMULATOR_ID)
    assert not report['passed']
    assert 'Stop not confirmed' in report['error']


@pytest.mark.skipif(not shutil.which('node'), reason='Node.js example requires Node.js')
@pytest.mark.parametrize('custom', [False, True], ids=['builtin-node', 'custom-command'])
def test_normal_cli_node_mode_http_flow(custom, tmp_path):
    import http.client
    import subprocess
    import time
    from urllib.parse import urlsplit
    device_id = NODE_DEVICE_ID
    endpoint_port = 'SIMULATED'
    options = ['--simulate-node']
    if custom:
        from apps.local_demo.process_transport import EXAMPLE
        device_id = 'my-independent-software-adapter'
        endpoint_port = 'SOFTWARE'
        script = tmp_path / 'my adapter with spaces.cjs'
        script.write_text(EXAMPLE.read_text().replace(NODE_DEVICE_ID, device_id))
        options = ['--software-device-id', device_id, '--software-command', 'node', str(script)]
    server = subprocess.Popen([sys.executable, '-m', 'apps.local_demo', '--no-browser', '--port', '0', *options],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    port = None
    try:
        assert 'OpenSmell' in server.stdout.readline()
        port = urlsplit(server.stdout.readline().strip()).port
        def call(route, data=None, expected_status=200):
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
            connection.request('GET' if data is None else 'POST', '/api/' + route,
                               body=None if data is None else json.dumps(data), headers={'Content-Type':'application/json'})
            response = connection.getresponse()
            result = json.loads(response.read())
            connection.close()
            assert response.status == expected_status, result
            return result
        initial = call('hardware/status')
        assert initial['connection'] == 'disconnected'
        if custom:
            assert initial['software_adapter']['expected_device_id'] == device_id
            call('hardware/connect', {'port': endpoint_port, 'command': ['unexpected']}, expected_status=400)
        assert call('hardware/connect', {'port':endpoint_port})['device_id'] == device_id
        ids = []
        for revision, duration in [(1,5 if custom else 0.1),(2,5),(3,5)]:
            p = call('preview', {'client_id':'node-http-reference-client','revision':revision,'duration':duration})
            execution = call('hardware/send', p['preview_ticket'])['execution']
            ids.append(execution['execution_id'])
            if revision == 1:
                time.sleep(duration + 0.05)
                assert call('hardware/status')['execution']['state'] == 'completed'
            elif revision == 2:
                assert call('hardware/stop', {'execution_id':ids[-1]})['execution']['state'] == 'stopped'
            else:
                assert call('hardware/disconnect', {})['execution']['state'] == 'unknown'
            report = call('hardware/evidence?report_id=' + execution['report_id'])
            assert report['execution']['state'] == {1:'completed', 2:'stopped', 3:'unknown'}[revision]
            assert report['device_id'] == device_id
            if custom:
                assert report['software_adapter']['expected_device_id'] == device_id
            assert report['source']['document']['resources']
        assert len(set(ids)) == 3
        old_report = report
        time.sleep(5)  # Retain the app's duration guard; no inferred completion.
        assert call('hardware/connect', {'port':endpoint_port})['execution']['state'] == 'unknown'
        reconnected_report = call('hardware/evidence?report_id=' + execution['report_id'])
        assert reconnected_report['execution'] == old_report['execution']
        assert reconnected_report['exchanges'] == old_report['exchanges']
        p = call('preview', {'client_id':'node-http-reference-client','revision':4,'duration':5})
        fresh = call('hardware/send', p['preview_ticket'])['execution']
        assert fresh['execution_id'] not in ids
        call('hardware/stop', {'execution_id':ids[-1]}, expected_status=409)
        assert call('hardware/status')['execution']['state'] == 'running'
        assert call('hardware/stop', {'execution_id':fresh['execution_id']})['execution']['state'] == 'stopped'
        fresh_report = call('hardware/evidence?report_id=' + fresh['report_id'])
        assert ids[-1] not in json.dumps(fresh_report)

    finally:
        if port:
            try:
                call('hardware/disconnect', {})
            except Exception:
                pass
        server.terminate()
        server.wait(timeout=5)


def test_reference_runner_detects_ids_reused_after_restart():
    class ReusedId(SimulatedEndpoint):
        def __init__(self):
            super().__init__()
            self.counter = 0

        def exchange(self, text):
            reply = json.loads(super().exchange(text))
            if json.loads(text)['type'] == 'render' and reply.get('type') == 'ok':
                self.counter += 1
                self.execution['execution_id'] = str(self.counter)
                reply['execution_id'] = str(self.counter)
            return json.dumps(reply)
    report = verify(lambda _: ReusedId(), SIMULATOR_ID)
    assert not report['passed']
    assert 'Restart reused an execution ID' in report['error']


@pytest.mark.parametrize('factory', [lambda _: SimulatedEndpoint(), node_transport], ids=['python', 'node'])
def test_error_envelopes_and_connection_recovery(factory):
    if factory is node_transport and not shutil.which('node'):
        pytest.skip('Node.js required')
    transport = factory('SIMULATED')
    try:
        cases = [
            ('[]', 'invalid_request'),
            ('{"type":"unrecognized"}', 'unsupported_request'),
            ('{"type":"hello","protocol_version":"9"}', 'invalid_request'),
            ('{"type":"stop","profile":"wrong","execution_id":"old"}', 'unsupported_profile'),
            ('{"type":"stop","profile":"local-simulator-lifecycle-v1","execution_id":"old"}', 'unknown_execution'),
        ]
        for text, code in cases:
            reply = json.loads(transport.exchange(text))
            assert reply['type'] == 'error'
            assert reply['code'] == code
            assert reply['error_profile'] == 'local-simulator-errors-v1'
            assert isinstance(reply['message'], str) and reply['message']
            assert 'state' not in reply
            if '"old"' in text:
                assert reply['execution_id'] == 'old'
                assert reply['request_type'] == 'stop'
            assert json.loads(transport.exchange('{"type":"hello","protocol_version":"0.1"}'))['type'] == 'hello_response'
    finally:
        transport.close()


def test_malformed_json_recovery_on_both_wire_endpoints():
    endpoint = SimulatedEndpoint()
    assert json.loads(endpoint.exchange('{'))['code'] == 'invalid_request'
    assert json.loads(endpoint.exchange('{"type":"hello","protocol_version":"0.1"}'))['type'] == 'hello_response'
    if not shutil.which('node'):
        pytest.skip('Node.js required')
    import subprocess
    from apps.local_demo.process_transport import EXAMPLE
    result = subprocess.run(['node', str(EXAMPLE)],
        input='{\n{"type":"hello","protocol_version":"0.1"}\n',
        text=True, capture_output=True, timeout=5, check=True)
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    assert replies[0]['code'] == 'invalid_request'
    assert replies[1]['type'] == 'hello_response'
