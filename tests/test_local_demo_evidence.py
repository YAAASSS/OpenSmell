"""Evidence is a passive, correlated snapshot of the normal HTTP send flow."""
import json

import pytest
from test_local_demo_simulator import api, send
from test_local_demo_hardware import setup_hardware, FakeTransport, make_preview
from apps.local_demo.hardware import HardwareError
from apps.local_demo.preview_store import PreviewStore
from apps.local_demo.evidence import ExecutionEvidence, MAX_EVENTS, MAX_TEXT
from opensmell.experimental.device_protocol import hello_response, capabilities_response, error_response
from test_local_demo_hardware import capabilities, EXPECTED_DEVICE_ID


def evidence(request, state, expected=200):
    return request('hardware/evidence?report_id=' + state['evidence_id'], expected=expected)


def test_http_completed_export_preserves_source_plan_and_raw_messages(api):
    request, clock, endpoint = api
    request('hardware/connect', {'port':'SIMULATED'})
    state, _ = send(request)
    report_id = state['evidence_id']
    clock.now += 5
    state = request('hardware/status')
    # If export polls the endpoint, this replacement makes it fail.
    endpoint.exchange = lambda _: pytest.fail('Export performed device I/O')
    report = evidence(request, state)
    assert report['report_id'] == report_id
    assert report['execution']['state'] == 'completed'
    assert report['source']['document']['resources']
    assert report['source']['policy'] == 'semantic'
    assert report['source']['bindings']
    assert report['plan']['duration'] == 5
    assert report['simulated'] is True
    assert report['measured_olfactory_result'] is None
    messages = [json.loads(e['request_text']) for e in report['exchanges']]
    assert messages[0]['type'] == 'render'
    assert messages[0]['commands'] == report['plan']['commands']
    last = json.loads(report['exchanges'][-1]['response_text'])
    assert last['state'] == 'completed'
    assert last['execution_id'] == report['execution']['execution_id']
    request('hardware/disconnect', {})
    assert evidence(request, state)['execution']['state'] == 'completed'


def test_stopped_then_unknown_exports_never_mix_executions(api):
    request, _, _ = api
    request('hardware/connect', {'port':'SIMULATED'})
    first, _ = send(request)
    stopped = request('hardware/stop', {'execution_id':first['execution']['execution_id']})
    report = evidence(request, stopped)
    assert report['execution']['state'] == 'stopped'
    assert json.loads(report['exchanges'][-1]['request_text'])['type'] == 'stop'
    second, _ = send(request, 2)
    assert second['evidence_id'] != first['evidence_id']
    evidence(request, first, expected=409)
    unknown = request('hardware/disconnect', {})
    report = evidence(request, unknown)
    assert report['execution']['state'] == 'unknown'
    assert all(json.loads(e['request_text'])['type'] != 'stop' for e in report['exchanges'])
    assert report['execution']['execution_id'] == second['execution']['execution_id']


def test_evidence_query_requires_exact_identifier(api):
    request, _, _ = api
    request('hardware/evidence', expected=400)
    request('hardware/evidence?report_id=x&report_id=y', expected=400)
    request('hardware/evidence?report_id=missing', expected=409)


def test_rejection_export_is_not_acceptance():
    transport = FakeTransport([hello_response(EXPECTED_DEVICE_ID), capabilities_response(capabilities()),
                               error_response('rejected', 'Software refusal')])
    hardware, _, _ = setup_hardware(transport)
    hardware.connect('SIMULATED')
    store = PreviewStore()
    ticket, result = make_preview(store)
    with pytest.raises(HardwareError):
        hardware.send(store, ticket)
    report = hardware.evidence(hardware.status()['evidence_id'])
    assert report['execution']['state'] == 'rejected'
    assert json.loads(report['exchanges'][0]['response_text'])['type'] == 'error'
    assert report['source']['document'] == result['document']
    report['source']['document'].clear()
    assert hardware.evidence(report['report_id'])['source']['document'] == result['document']


def test_timeout_export_preserves_uncertainty_and_transport_error():
    hardware, _, _ = setup_hardware(FakeTransport([hello_response(EXPECTED_DEVICE_ID),
                                                  capabilities_response(capabilities()), TimeoutError('No reply')]))
    hardware.connect('SIMULATED')
    store = PreviewStore()
    ticket, _ = make_preview(store)
    with pytest.raises(HardwareError):
        hardware.send(store, ticket)
    report = hardware.evidence(hardware.status()['evidence_id'])
    assert report['execution']['state'] == 'uncertain'
    assert 'TimeoutError' in report['exchanges'][0]['transport_error']
    assert 'response_text' not in report['exchanges'][0]


def test_bounded_trace_discloses_omissions_and_truncation():
    log = ExecutionEvidence()
    log.begin(plan={}, source={}, device_id='test', capabilities={}, simulated=True)
    log.record('x' * (MAX_TEXT + 1), response='raw response')
    for _ in range(MAX_EVENTS + 10):
        log.record('{}', response='{}')
    report = log.snapshot({})
    assert len(report['exchanges']) == MAX_EVENTS
    assert report['exchanges'][0]['text_truncated'] is True
    assert report['omitted_events'] == 11
