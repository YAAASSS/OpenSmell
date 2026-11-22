import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

import pytest
from opensmell.experimental.starter import init_workspace
from opensmell.experimental.stdio_simulator import serve
from opensmell.experimental.lifecycle_adapter import LifecycleAdapter
from opensmell.experimental.lifecycle_simulator import SIMULATOR_ID
from opensmell.experimental.process_transport import ProcessTransport
from opensmell.experimental.rendering import RenderingPlan,DeviceCommand


def test_passive_installed_resources_validate_and_never_launch(tmp_path,monkeypatch):
    def forbidden(*a,**k):raise AssertionError('No child allowed during workspace creation')
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    directory=tmp_path/'workspace';report=init_workspace(directory)
    assert report['execution']=='not_attempted' and not report['physical_validation']
    assert set(p.name for p in directory.iterdir())=={'README.md','sample.osmell','profile.json','workspace.json'}
    for name,metadata in report['files'].items():
        raw=(directory/name).read_bytes()
        assert metadata=={'sha256':hashlib.sha256(raw).hexdigest(),'byte_count':len(raw)}
    from opensmell.experimental.core_planning import plan_core_bytes
    artifact=plan_core_bytes((directory/'sample.osmell').read_bytes(),(directory/'profile.json').read_bytes(),representation_index=0,duration=.1)
    assert artifact['plan']['commands']==[{'channel':0,'intensity':.25}]
    before={p.name:p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(FileExistsError):init_workspace(directory)
    assert {p.name:p.read_bytes() for p in directory.iterdir()}==before


@pytest.mark.parametrize('wire',[b'{}',b' '*65537+b'\n',b'{"type":"hello"}'])
def test_bad_framing_fails_closed_without_response(wire):
    output=io.StringIO();error=io.StringIO()
    assert serve(io.BytesIO(wire),output,error)==1
    assert not output.getvalue() and 'framing' in error.getvalue()


@pytest.mark.parametrize('wire',[b'{\n',b'{"x":1,"x":2}\n',b'{"x":NaN}\n',b'\xff\n',b'\xef\xbb\xbf{}\n',b'[]\n'])
def test_complete_invalid_request_refuses_then_next_hello_works(wire):
    output=io.StringIO();error=io.StringIO()
    hello=b'{"type":"hello","protocol_version":"0.1"}\n'
    assert serve(io.BytesIO(wire+hello),output,error)==0
    replies=[json.loads(line) for line in output.getvalue().splitlines()]
    assert replies[0]['type']=='error' and replies[0]['code']=='invalid_request'
    assert replies[1]['device_id']==SIMULATOR_ID and not error.getvalue()


def test_installed_simulator_identity_stop_duration_and_stale_ids():
    transport=ProcessTransport([sys.executable,'-I','-m','opensmell','simulate-device'])
    client=LifecycleAdapter(transport,expected_device_id=SIMULATOR_ID)
    plan=RenderingPlan([DeviceCommand(0,.25)],5)
    try:
        first=client.render(plan,request_id='first')
        assert first['state']=='accepted'
        with pytest.raises(ValueError,match='Stale'):client.stop('not-current')
        with pytest.raises(ValueError,match='consumed'):client.render(plan,request_id='first')
        assert client.stop(first['execution_id'])['state']=='stopped'
        with pytest.raises(ValueError):client.render(RenderingPlan(plan.commands,31),request_id='duration')
        next_run=client.render(plan,request_id='second')
        assert next_run['state']=='accepted'
        client.close()
        assert client.execution['state']=='unknown'
    finally:client.close()


def test_simulator_wire_refusal_is_protocol_json_without_banner():
    messages=[{'type':'render','protocol_version':'0.1','duration':31,'commands':[{'channel':0,'intensity':.25}]},
              {'type':'render','protocol_version':'0.1','duration':5,'commands':[{'channel':0,'intensity':.25}]},
              {'type':'render','protocol_version':'0.1','duration':5,'commands':[{'channel':1,'intensity':.1}]}]
    result=subprocess.run([sys.executable,'-I','-m','opensmell','simulate-device'],input=('\n'.join(map(json.dumps,messages))+'\n').encode(),capture_output=True)
    assert result.returncode==0 and not result.stderr
    replies=[json.loads(line) for line in result.stdout.splitlines()]
    assert [r['type'] for r in replies]==['error','ok','error'] and replies[-1]['code']=='busy'


def test_cli_workspace_creation_and_collision(tmp_path):
    cmd=[sys.executable,'-m','opensmell','init-workspace',str(tmp_path/'start')]
    first=subprocess.run(cmd,capture_output=True);assert first.returncode==0
    assert json.loads(first.stdout)['execution']=='not_attempted'
    second=subprocess.run(cmd,capture_output=True);assert second.returncode==2
