"""Marker projection without making pylsl a mandatory SDK dependency."""
import importlib.util
import json
from pathlib import Path
import pytest
from opensmell.experimental.lifecycle_adapter import LifecycleAdapter
from opensmell.experimental.lifecycle_simulator import SimulatedEndpoint,SIMULATOR_ID
from opensmell.experimental.rendering import RenderingPlan,DeviceCommand
from opensmell.experimental.sequence import SequenceRunner,SequenceStep

spec=importlib.util.spec_from_file_location('lsl_example',Path(__file__).resolve().parents[1]/'examples/lsl_markers/bridge.py')
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)


class Outlet:
    def __init__(self):self.samples=[]
    def push_sample(self,sample,*,timestamp):self.samples.append((json.loads(sample[0]),timestamp))


@pytest.mark.parametrize('mode',['completed','stopped','unknown','rejected'])
def test_real_sdk_snapshots_project_without_conflating_intent_or_terminal(mode):
    clock=[0];endpoint=SimulatedEndpoint(lambda:clock[0]);original=endpoint.exchange
    def exchange(text):
        message=json.loads(text)
        if message['type']=='execution_status':clock[0]+=10
        if message['type']=='render' and mode=='unknown':raise EOFError('Lost reply')
        if message['type']=='render' and mode=='rejected':return '{"type":"error","protocol_version":"0.1","code":"busy","message":"Busy"}'
        return original(text)
    endpoint.exchange=exchange
    client=LifecycleAdapter(endpoint,expected_device_id=SIMULATOR_ID);outlet=Outlet();relay=bridge.MarkerRelay(outlet,lambda:12.5)
    def progress(report):
        relay(report)
        if mode=='stopped' and report['steps'][0]['state']=='accepted':runner.request_stop()
    plan=RenderingPlan([DeviceCommand(0,.25)],.1)
    runner=SequenceRunner(client,[SequenceStep('first',plan),SequenceStep('second',plan)],on_progress=progress)
    report=runner.run();relay.finish(report)
    assert report['status']==mode
    assert outlet.samples[-1][0]['kind']=='run_finished' and outlet.samples[-1][0]['status']==mode
    assert [x[0]['event_index'] for x in outlet.samples]==list(range(len(outlet.samples)))
    before=len(outlet.samples);relay(report);assert len(outlet.samples)==before
    assert all(x[1]==12.5 and not x[0]['physical_validation'] for x in outlet.samples)
    snapshots=[x[0] for x in outlet.samples if x[0]['kind']=='step_snapshot']
    assert any(x['state']=='unknown' and x['execution_id'] is None for x in snapshots)
    assert not any(x['trial_id']=='second' and x['state']=='accepted' for x in snapshots) if mode!='completed' else True


def test_failing_marker_sink_aborts_before_next_send():
    endpoint=SimulatedEndpoint();client=LifecycleAdapter(endpoint,expected_device_id=SIMULATOR_ID)
    class Fail:
        def push_sample(self,*a,**k):raise OSError('LSL push failed')
    relay=bridge.MarkerRelay(Fail(),lambda:1)
    plan=RenderingPlan([DeviceCommand(0,.25)],.1)
    report=SequenceRunner(client,[SequenceStep('first',plan)],on_progress=relay).run()
    assert report['status']=='invalid' and endpoint.execution is None and endpoint.closed
    assert not relay.events


def test_marker_failure_after_acceptance_closes_unknown_and_never_starts_second():
    endpoint=SimulatedEndpoint();original=endpoint.exchange;renders=[]
    def exchange(text):
        if json.loads(text)['type']=='render':renders.append(text)
        return original(text)
    endpoint.exchange=exchange
    class FailAccepted(Outlet):
        def push_sample(self,sample,*,timestamp):
            if json.loads(sample[0]).get('state')=='accepted':raise OSError('Marker push uncertain')
            super().push_sample(sample,timestamp=timestamp)
    relay=bridge.MarkerRelay(FailAccepted(),lambda:1)
    client=LifecycleAdapter(endpoint,expected_device_id=SIMULATOR_ID)
    plan=RenderingPlan([DeviceCommand(0,.25)],5)
    report=SequenceRunner(client,[SequenceStep('a',plan),SequenceStep('b',plan)],on_progress=relay).run()
    assert report['status']=='unknown' and endpoint.closed and len(renders)==1
    assert report['steps'][1]['state']=='not_attempted'
