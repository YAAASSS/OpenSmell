"""Offline user entry against actual HTTP exports and deliberately altered evidence."""
from copy import deepcopy
import json
import subprocess
import sys

import pytest
from test_local_demo_simulator import api, send
from tools.diagnose_execution_evidence import diagnose, loads


def completed(request, clock):
    request('hardware/connect', {'port': 'SIMULATED'})
    state, _ = send(request)
    clock.now += 5
    request('hardware/status')
    return request('hardware/evidence?report_id=' + state['evidence_id'])


def test_real_exports_cli_and_passivity(api, tmp_path):
    request, clock, endpoint = api
    report = completed(request, clock)
    original = deepcopy(report)
    assert diagnose(report)['verdict'] == 'consistent'
    assert report == original
    state, _ = send(request, 2)
    request('hardware/stop', {'execution_id': state['execution']['execution_id']})
    bundle = request('hardware/evidence-history')
    endpoint.exchange = lambda _: pytest.fail('Diagnostics contacted endpoint')
    target = tmp_path / 'history.json'
    target.write_text(json.dumps(bundle))
    process = subprocess.run([sys.executable, '-m', 'tools.diagnose_execution_evidence', str(target), '--json'], capture_output=True, text=True)
    assert process.returncode == 0, process.stdout
    assert len(json.loads(process.stdout)['reports']) == 2


@pytest.mark.parametrize('mutation,code', [
    (lambda r: r['plan'].update(duration=99), 'plan_mismatch'),
    (lambda r: r['execution'].update(execution_id='other'), 'snapshot_mismatch'),
    (lambda r: r['execution'].update(state='stopped'), 'snapshot_mismatch'),
    (lambda r: r['execution'].update(report_id='other'), 'snapshot_identity'),
    (lambda r: r.update(exchanges=r['exchanges'][:1]), 'unsupported_state'),
])
def test_contradictions(api, mutation, code):
    request, clock, _ = api
    report = completed(request, clock)
    mutation(report)
    result = diagnose(report)
    assert result['verdict'] == 'inconsistent'
    assert code in [f['code'] for f in result['findings']]


def test_unknown_and_omissions_remain_incomplete(api):
    request, clock, _ = api
    report = completed(request, clock)
    report['exchanges'] = report['exchanges'][:1]
    report['omitted_events'] = 2
    assert diagnose(report)['verdict'] == 'incomplete'
    state, _ = send(request, 2)
    request('hardware/disconnect', {})
    report = request('hardware/evidence?report_id=' + state['evidence_id'])
    assert diagnose(report)['verdict'] == 'incomplete'


@pytest.mark.parametrize('text', ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_ambiguous_input(text):
    with pytest.raises(ValueError):
        loads(text)


@pytest.mark.parametrize('value', [None, [], {}, {'format':'future'}, {'format':'opensmell.local-execution-history.v1','reports':False}])
def test_bad_structure(value):
    assert diagnose(value)['verdict'] == 'inconsistent'


def test_invalid_cli(tmp_path):
    path = tmp_path / 'bad.json'
    path.write_text('{broken')
    result = subprocess.run([sys.executable, '-m', 'tools.diagnose_execution_evidence', str(path), '--json'], capture_output=True, text=True)
    assert result.returncode == 2
    assert json.loads(result.stdout)['verdict'] == 'invalid-input'


def test_duplicate_bundle_and_truncation(api):
    request, clock, _ = api
    report = completed(request, clock)
    bundle = {'format':'opensmell.local-execution-history.v1', 'reports':[report, report]}
    assert 'report_identity' in [f['code'] for f in diagnose(bundle)['findings']]
    report['exchanges'][-1]['text_truncated'] = True
    report['exchanges'][-1]['response_text'] = '{'
    assert diagnose(report)['verdict'] == 'incomplete'


def test_invalid_observation_does_not_establish_completion(api):
    request, clock, _ = api
    report = completed(request, clock)
    # Corrupt every lifecycle reply so no terminal evidence survives.
    for event in report['exchanges'][1:]:
        response = json.loads(event['response_text'])
        response['execution_id'] = 'foreign'
        event['response_text'] = json.dumps(response)
    assert diagnose(report)['verdict'] == 'inconsistent'
    report['execution']['state'] = 'unknown'
    assert diagnose(report)['verdict'] == 'incomplete'


def test_terminal_state_cannot_change(api):
    request, clock, _ = api
    report = completed(request, clock)
    event = deepcopy(report['exchanges'][-1])
    response = json.loads(event['response_text'])
    response['state'] = 'running'
    event['response_text'] = json.dumps(response)
    report['exchanges'].append(event)
    assert 'terminal_changed' in [f['code'] for f in diagnose(report)['findings']]


def test_overflow_is_not_finite():
    with pytest.raises(ValueError):
        loads('{"number":1e9999}')
