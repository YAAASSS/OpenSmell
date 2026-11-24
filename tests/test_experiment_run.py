"""Dossier consistency before any connection and reusable SDK lifecycle behavior."""
import base64
import hashlib
import json
import shutil
import subprocess
import sys

import pytest
from opensmell.experimental.experiment import prepare_experiment
from opensmell.experimental.experiment_run import load_prepared_experiment, run_prepared_experiment
from test_experiment import TABLE, GRAPH, PROFILE
from test_transport_sequence import Transport, ID

@pytest.fixture
def dossier(tmp_path):
    original=tmp_path/'original'
    prepare_experiment(TABLE, GRAPH, PROFILE, original)
    moved=tmp_path/'moved space';shutil.move(original,moved)
    return moved


def test_order_snapshots_unknown_and_no_reread_after_factory(dossier):
    manifest=json.loads((dossier/'experiment.json').read_bytes())
    manifest['future']={'opaque':[2**70,None]}
    raw=json.dumps(manifest).encode();(dossier/'experiment.json').write_bytes(raw)
    transport=Transport()
    def factory():
        shutil.rmtree(dossier)
        return transport
    r=run_prepared_experiment(dossier,factory,expected_device_id=ID)
    assert r['status']=='completed' and transport.closed==1
    assert [s['trial_id'] for s in r['sequence']['steps']]==['first','second']
    assert base64.b64decode(r['prepared_experiment']['manifest']['data'])==raw
    assert base64.b64decode(r['prepared_experiment']['retained_inputs']['trials.csv']['data'])==TABLE
    assert [q['duration'] for q in transport.requests if q['type']=='render']==[.1,.2]


@pytest.mark.parametrize('bad',['hash','table','order','id','path','inventory','missing','symlink','plan_binding','manifest_type','plan_type'])
def test_invalid_dossier_never_calls_factory(dossier,bad):
    manifest=json.loads((dossier/'experiment.json').read_bytes())
    if bad=='hash':manifest['files']['plan-002.json']['sha256']='0'*64
    if bad=='table':(dossier/'trials.csv').write_bytes(TABLE.replace(b'caller-design',b'changed'))
    if bad=='order':manifest['trials'].reverse()
    if bad=='id':manifest['trials'][1]['trial_id']='first'
    if bad=='path':manifest['trials'][1]['plan_file']='../outside'
    if bad=='inventory':manifest['files']['../outside']={}
    if bad=='missing':(dossier/'plan-002.json').unlink()
    if bad=='symlink':
        p=dossier/'plan-002.json';value=p.read_bytes();p.unlink();other=dossier.parent/'outside';other.write_bytes(value);p.symlink_to(other)
    if bad in {'plan_binding','plan_type'}:
        p=dossier/'plan-002.json';obj=json.loads(p.read_bytes())
        if bad=='plan_binding':obj['org.opensmell.experimental.trial']['record']['note']='edited'
        else:obj=[]
        value=json.dumps(obj).encode();p.write_bytes(value)
        manifest['files'][p.name]={'sha256':hashlib.sha256(value).hexdigest(),'byte_count':len(value)}
    if bad=='manifest_type':manifest=[]
    (dossier/'experiment.json').write_text(json.dumps(manifest))
    opened=[]
    with pytest.raises((ValueError,OSError)):
        run_prepared_experiment(dossier,lambda:opened.append(True),expected_device_id=ID)
    assert opened==[]


@pytest.mark.parametrize('mode,state',[('lost','unknown'),('refused','rejected')])
def test_second_failure_preserves_trial_receipts_and_halts(tmp_path,mode,state):
    table=TABLE+TABLE.splitlines()[-1].replace(b'second,',b'third,')+b'\n'
    dossier=tmp_path/'d';prepare_experiment(table,GRAPH,PROFILE,dossier)
    t=Transport(mode);r=run_prepared_experiment(dossier,lambda:t,expected_device_id=ID)
    assert [s['state'] for s in r['sequence']['steps']]==['completed',state,'not_attempted']
    assert [s['trial_id'] for s in r['sequence']['steps']]==['first','second','third']
    assert t.renders==2 and t.closed==1


def test_stop_and_callback_failure_close(dossier):
    t=Transport();stop=[False]
    def progress(r):
        if r['sequence'] and any(s['state']=='accepted' for s in r['sequence']['steps']):stop[0]=True
    r=run_prepared_experiment(dossier,lambda:t,expected_device_id=ID,on_progress=progress,stop_requested=lambda:stop[0])
    assert r['status']=='stopped' and t.renders==1 and t.closed==1
    t=Transport()
    def broken(r):
        if any(json.loads(e['request_line'])['type']=='render' for e in r['transcript']):raise OSError('storage failed')
    with pytest.raises(OSError):run_prepared_experiment(dossier,lambda:t,expected_device_id=ID,on_progress=broken)
    assert t.closed==1 and t.renders==0


def test_normal_cli_and_collision_before_launch(dossier,tmp_path):
    out=tmp_path/'report.json'
    cmd=[sys.executable,'-m','opensmell','run-experiment',str(dossier),'--software-command-json',json.dumps([sys.executable,'-m','opensmell','simulate-device']),
         '--expected-device-id',ID,'--action','complete','--output',str(out)]
    r=subprocess.run(cmd,capture_output=True);assert r.returncode==0,r.stderr
    assert json.loads(out.read_bytes())['status']=='completed'
    before=out.read_bytes();cmd[cmd.index('--software-command-json')+1]='["definitely-missing-executable"]'
    r=subprocess.run(cmd,capture_output=True);assert r.returncode==2
    assert out.read_bytes()==before
