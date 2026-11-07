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
    assert len(report['cases']) == 5


@pytest.mark.skipif(not shutil.which('node'), reason='Node.js example requires Node.js')
def test_independent_node_reference_cases():
    report = verify(node_transport, NODE_DEVICE_ID)
    assert report['passed'], report
    assert len(report['cases']) == 5
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
            if request['type'] == 'stop' and self.execution and request.get('execution_id') == self.execution['execution_id']:
                request['type'] = 'execution_status'
            return super().exchange(json.dumps(request))
    report = verify(lambda _: BrokenStop(), SIMULATOR_ID)
    assert not report['passed']
    assert 'Stop not confirmed' in report['error']


@pytest.mark.skipif(not shutil.which('node'), reason='Node.js example requires Node.js')
def test_normal_cli_node_mode_http_flow():
    import http.client
    import subprocess
    import time
    from urllib.parse import urlsplit
    server = subprocess.Popen([sys.executable, '-m', 'apps.local_demo', '--simulate-node', '--no-browser', '--port', '0'],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    port = None
    try:
        assert 'OpenSmell' in server.stdout.readline()
        port = urlsplit(server.stdout.readline().strip()).port
        def call(route, data=None):
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
            connection.request('GET' if data is None else 'POST', '/api/' + route,
                               body=None if data is None else json.dumps(data), headers={'Content-Type':'application/json'})
            response = connection.getresponse()
            result = json.loads(response.read())
            connection.close()
            assert response.status == 200, result
            return result
        assert call('hardware/connect', {'port':'SIMULATED'})['device_id'] == NODE_DEVICE_ID
        ids = []
        for revision, duration in [(1,0.1),(2,5),(3,5)]:
            p = call('preview', {'client_id':'node-http-reference-client','revision':revision,'duration':duration})
            execution = call('hardware/send', p['preview_ticket'])['execution']
            ids.append(execution['execution_id'])
            if revision == 1:
                time.sleep(0.15)
                assert call('hardware/status')['execution']['state'] == 'completed'
            elif revision == 2:
                assert call('hardware/stop', {'execution_id':ids[-1]})['execution']['state'] == 'stopped'
            else:
                assert call('hardware/disconnect', {})['execution']['state'] == 'unknown'
            report = call('hardware/evidence?report_id=' + execution['report_id'])
            assert report['execution']['state'] == {1:'completed', 2:'stopped', 3:'unknown'}[revision]
            assert report['device_id'] == NODE_DEVICE_ID
            assert report['source']['document']['resources']
        assert len(set(ids)) == 3
    finally:
        if port:
            try:
                call('hardware/disconnect', {})
            except Exception:
                pass
        server.terminate()
        server.wait(timeout=5)
