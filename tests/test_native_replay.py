"""Normal installed CLI boundary and deterministic trusted-software failure cases."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from opensmell.experimental.frame_export import encode_plan_frame
from opensmell.experimental.native_replay import replay_frame, validate_frame_export

ROOT = Path(__file__).resolve().parents[1]
TARGET = (ROOT/'hardware/esp32/led_capabilities.json').read_bytes()


@pytest.fixture(scope='module')
def exported():
    result = subprocess.run([sys.executable,'-m','opensmell','plan',str(ROOT/'examples/multisource_diphenyl_ether.osmell'),
        '--profile',str(ROOT/'examples/offline_semantic_profile.json'),'--resource-id',
        'e6ad8ce3-dc6e-5d94-9287-57665d48fc0b','--duration','5'],capture_output=True,check=True)
    return json.dumps(encode_plan_frame(result.stdout,TARGET)).encode()


@pytest.fixture
def host(tmp_path):
    def make(mode='accepted'):
        script=tmp_path/'native-host'
        script.write_text('#!'+sys.executable+'\n'+f'''
import json,sys,time
from pathlib import Path
Path({str(tmp_path/'started')!r}).write_text('launched')
mode={mode!r}
if mode=='startup_exit':sys.exit(1)
caps=json.loads({TARGET.decode()!r})
if mode=='incompatible':caps['device_id']='other-device'
if mode=='wide':caps['max_duration']=60
pins=[0,0,0]
for line in sys.stdin:
 with Path({str(tmp_path/'requests')!r}).open('a') as log: log.write(line)
 if line=='!pins\\n':
  if mode=='lost_pins' and pins!=[0,0,0]:sys.exit(1)
  reply={{'host_pwm':pins}}
 elif line.startswith('!advance '): pins=[0,0,0];reply={{'host':'advanced'}}
 else:
  m=json.loads(line)
  if m['type']=='hello':reply={{'protocol_version':'0.1','type':'hello_response','device_id':caps['device_id']}}
  elif m['type']=='get_capabilities':reply=caps
  else:
   if mode=='timeout':time.sleep(60)
   if mode=='lost':sys.exit(1)
   if mode=='malformed':print('invalid json',flush=True);continue
   if m['duration']==31 or mode in ('rejected','mutated_refusal'):
    reply={{'protocol_version':'0.1','type':'error','code':'invalid_plan','message':'refused'}}
    if mode=='mutated_refusal':pins=[255,0,0]
   else: pins=[64,153,0];reply={{'protocol_version':'0.1','type':'ok'}}
 print(json.dumps(reply),flush=True)
''')
        script.chmod(0o755)
        return script
    return make


def test_accepted_transcript_and_exact_line(exported, host):
    path=host(); calls=[]
    report=replay_frame(exported,path,on_progress=lambda value:calls.append(value))
    assert report['status']==report['acceptance']=='accepted'
    assert report['execution']=='not_observed' and report['physical_validation'] is False
    assert base64.b64decode(report['input']['data'])==exported
    assert report['native_host']['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    selected=next(x for x in report['transcript'] if x['role']=='selected_frame')
    assert selected['request_line']==json.loads(exported)['frame']['line']
    assert report['fake_outputs']['after']==report['fake_outputs']['after_negative_control']==[64,153,0]
    assert report['fake_outputs']['after_duration']==[0,0,0]
    assert report['fake_clock_advance_ms']==5001
    assert any(x['acceptance']=='unknown' for x in calls)
    assert any(x['role']=='negative_control_duration_31' for x in report['transcript'])


@pytest.mark.parametrize('mode,status,acceptance', [('incompatible','incompatible','not_attempted'),
    ('rejected','rejected','rejected'),('lost','unknown','unknown'),('malformed','unknown','unknown'),
    ('mutated_refusal','unknown','rejected'),('lost_pins','unknown','accepted'),('timeout','unknown','unknown')])
def test_explicit_refusal_mismatch_and_lost_reply(exported,host,mode,status,acceptance):
    path=host(mode);report=replay_frame(exported,path)
    assert report['status']==status and report['acceptance']==acceptance
    requests=(path.parent/'requests').read_text().splitlines()
    render=[json.loads(x) for x in requests if x.startswith('{') and json.loads(x).get('type')=='render']
    assert len(render)==(0 if mode=='incompatible' else 1)
    if mode=='rejected':assert report['fake_outputs']['before']==report['fake_outputs']['after']
    if mode=='malformed':
        entry=report['transcript'][-1]
        assert entry['response_complete'] is True
        assert base64.b64decode(entry['response_bytes']['data'])==b'invalid json\n'


@pytest.mark.parametrize('field', ['frame','input','target','context','status'])
def test_altered_export_never_launches(exported,host,field):
    path=host();value=json.loads(exported)
    if field=='frame':
        value['frame']['line']=value['frame']['line'].replace('0.25','0.4')
        value['frame']['sha256']=hashlib.sha256(value['frame']['line'].encode()).hexdigest()
    elif field in ('input','target'):value[field]['sha256']='0'*64
    elif field=='context':value['context']['plan']['duration']=1
    else:value['status']='accepted'
    with pytest.raises(ValueError):replay_frame(json.dumps(value).encode(),path)
    assert not (path.parent/'started').exists()


def test_unknown_outer_extensions_preserved(exported):
    value=json.loads(exported);value['future']={'numbers':[123456789012345678901,None]}
    raw=json.dumps(value).encode()
    checked,_=validate_frame_export(raw)
    assert checked['future']==value['future']


def test_cli_reserved_output_and_progress(exported,host,tmp_path):
    executable=host();source=tmp_path/'frame.json';source.write_bytes(exported)
    output=tmp_path/'transcript.json'
    command=[sys.executable,'-m','opensmell','replay-frame',str(source),'--native-host',str(executable),'--output',str(output)]
    result=subprocess.run(command,capture_output=True)
    assert result.returncode==0,result.stderr
    assert json.loads(output.read_bytes())==json.loads(result.stdout)
    before=output.read_bytes();(tmp_path/'started').unlink()
    assert subprocess.run(command,capture_output=True).returncode==2
    assert output.read_bytes()==before and not (tmp_path/'started').exists()
    assert source.read_bytes()==exported


def test_cli_unknown_retained_without_retry(exported,host,tmp_path):
    executable=host('lost');source=tmp_path/'frame.json';source.write_bytes(exported)
    output=tmp_path/'unknown.json'
    result=subprocess.run([sys.executable,'-m','opensmell','replay-frame',str(source),'--native-host',str(executable),'--output',str(output)],capture_output=True)
    assert result.returncode==1
    report=json.loads(output.read_bytes())
    assert report['status']==report['acceptance']=='unknown'
    assert report['transcript'][-1]['role']=='selected_frame' and 'error' in report['transcript'][-1]


def test_native_exit_before_handshake_retains_no_attempt(exported,host):
    report=replay_frame(exported,host('startup_exit'))
    assert report['status']=='unknown' and report['acceptance']=='not_attempted'
    assert report['transcript'][0]['role']=='hello' and 'error' in report['transcript'][0]


def test_non_reference_control_profile_stops_before_send(exported,host):
    input_bytes=base64.b64decode(json.loads(exported)['input']['data'])
    target=json.loads(TARGET);target['max_duration']=60
    wider=json.dumps(encode_plan_frame(input_bytes,json.dumps(target).encode())).encode()
    path=host('wide');report=replay_frame(wider,path)
    assert report['status']=='incompatible' and report['acceptance']=='not_attempted'
    assert 'reference bounds' in report['detail']
    assert not any(x['role']=='selected_frame' for x in report['transcript'])
