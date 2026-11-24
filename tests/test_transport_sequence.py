"""Lazy transport ownership, full preflight and one-shot correlated sequencing."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from opensmell.experimental.lifecycle_simulator import SimulatedEndpoint
from opensmell.experimental.transport_sequence import run_transport_sequence
from opensmell.experimental.serial_sequence import run_serial_sequence

ROOT=Path(__file__).resolve().parents[1]
ID='opensmell-local-simulator-001'

@pytest.fixture(scope='module')
def inputs():
    result=[]
    for profile,rid in [('semantic','e6ad8ce3-dc6e-5d94-9287-57665d48fc0b'),('perceptual','219ef28c-9b58-52f2-93a7-0807f5897857')]:
        result.append(subprocess.check_output([sys.executable,'-m','opensmell','plan',str(ROOT/'examples/multisource_diphenyl_ether.osmell'),'--profile',str(ROOT/f'examples/offline_{profile}_profile.json'),'--resource-id',rid,'--duration','.1']))
    return result

class Transport:
    def __init__(self, mode='normal'):
        self.now=0;self.endpoint=SimulatedEndpoint(lambda:self.now)
        self.requests=[];self.closed=0;self.mode=mode;self.renders=0
    def exchange(self,text):
        req=json.loads(text);self.requests.append(req)
        if req['type']=='execution_status': self.now+=1
        if req['type']=='render':
            self.renders+=1
            if self.renders==2 and self.mode=='lost':raise OSError('Lost second reply')
            if self.renders==2 and self.mode=='refused':return json.dumps({'protocol_version':'0.1','type':'error','code':'busy','message':'Explicit refusal'})
        reply=json.loads(self.endpoint.exchange(text))
        if self.mode=='caps' and req['type']=='get_capabilities':reply['channels']=[c for c in reply['channels'] if c['channel']!=2]
        return json.dumps(reply)
    def close(self):self.closed+=1


def test_transport_without_diagnostics_owned_once(inputs):
    t=Transport();context={'opaque':{'count':2**70}}
    r=run_transport_sequence(inputs,lambda:t,expected_device_id=ID,transport_context=context)
    assert r['status']=='completed' and t.renders==2 and t.closed==1
    assert r['transport_context']==context
    assert [s['state'] for s in r['sequence']['steps']]==['completed','completed']

@pytest.mark.parametrize('bad',['last_plan','factory','identity','context','stop'])
def test_preflight_does_not_open_transport(inputs,bad):
    opened=[];factory=lambda:opened.append(True)
    raw=list(inputs);identity=ID;context={};stop=None
    if bad=='last_plan':raw[-1]=b'{}'
    if bad=='factory':factory=object()
    if bad=='identity':identity=''
    if bad=='context':context={'bad':float('nan')}
    if bad=='stop':stop=True
    r=run_transport_sequence(raw,factory,expected_device_id=identity,transport_context=context,stop_requested=stop)
    assert r['status']=='invalid' and not opened


def test_late_live_caps_before_first_send(inputs):
    t=Transport('caps');r=run_transport_sequence(inputs,lambda:t,expected_device_id=ID)
    assert r['status']=='invalid' and not t.renders and t.closed==1

@pytest.mark.parametrize('mode,status',[('lost','unknown'),('refused','rejected')])
def test_second_failure_keeps_first_and_prevents_third(inputs,mode,status):
    t=Transport(mode);r=run_transport_sequence([*inputs,inputs[0]],lambda:t,expected_device_id=ID)
    assert [s['state'] for s in r['sequence']['steps']]==['completed',status,'not_attempted']
    assert t.renders==2 and t.closed==1
    assert r['status']==status


def test_cooperative_stop_after_acceptance(inputs):
    t=Transport();stop=[False]
    def progress(r):
        if r['sequence'] and any(s['state']=='accepted' for s in r['sequence']['steps']):stop[0]=True
    r=run_transport_sequence(inputs,lambda:t,expected_device_id=ID,on_progress=progress,stop_requested=lambda:stop[0])
    assert r['status']=='stopped' and t.renders==1 and t.closed==1
    assert r['sequence']['steps'][1]['state']=='not_attempted'
    assert any(q['type']=='stop' for q in t.requests)


def test_checkpoint_failure_after_reply_preserves_intent(inputs):
    t=Transport();snapshots=[]
    def progress(r):
        if r['transcript'] and json.loads(r['transcript'][-1]['request_line'])['type']=='render' and 'response_line' in r['transcript'][-1]:raise OSError('Disk failure')
        snapshots.append(deepcopy(r))
    with pytest.raises(OSError):run_transport_sequence(inputs,lambda:t,expected_device_id=ID,on_progress=progress)
    assert t.renders==1 and t.closed==1
    assert snapshots[-1]['sequence']['steps'][0]['state']=='unknown'


def test_invalid_serial_input_never_opens_port(inputs,monkeypatch):
    import opensmell.experimental.serial_sequence as module
    opened=[];monkeypatch.setattr(module,'SerialDeviceTransport',lambda *a,**k:opened.append(True))
    r=run_serial_sequence([inputs[0],b'{}'],'owned-test-port',expected_device_id=ID)
    assert r['status']=='invalid' and not opened


def test_software_command_snapshot_matches_actual_connection(inputs,monkeypatch):
    import opensmell.experimental.software_sequence as module
    command=['explicit-original','argument'];seen=[];t=Transport()
    def factory(args,**kwargs):seen.append(args);return t
    monkeypatch.setattr(module,'ProcessTransport',factory)
    def progress(r):
        if r['phase']=='connect':command[:]=['changed-after-validation']
    report=module.run_software_sequence(inputs,command,expected_device_id=ID,on_progress=progress)
    assert report['status']=='completed'
    assert seen==[['explicit-original','argument']]
    assert report['command']==seen[0]
