"""Explicit trial policies, compatibility and source-bound dossier execution."""
from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import shutil
import pytest
from opensmell.experimental.experiment import prepare_experiment, prepare_experiment_profiles, TRIAL_PROFILES_FORMAT
from opensmell.experimental.experiment_run import load_prepared_experiment, run_prepared_experiment
from opensmell.experimental.perceptual_cohort import import_keller_cohort, COHORT_KEY
from test_transport_sequence import Transport, ID

ROOT=Path(__file__).resolve().parents[1]
enc=lambda value:json.dumps(value,indent=3).encode()+b'\r\n'

@pytest.fixture
def inputs():
    graph=import_keller_cohort((ROOT/'examples/synthetic_keller.csv').read_bytes(),rows=[1,2],source=json.loads((ROOT/'examples/synthetic_keller_source.json').read_bytes()))
    ids=[r['observation_id'] for r in json.loads(graph)[COHORT_KEY]['results']]
    table=f'trial_id,resource_id,duration,profile_id\r\nfirst,{ids[0]},.1,opaque\r\nsecond,{ids[1]},.2,also-opaque\r\n'.encode()
    profile=json.loads((ROOT/'examples/offline_perceptual_profile.json').read_bytes());profile['future']={'huge':2**70,'null':None}
    other=deepcopy(profile);other['bindings']=other['bindings'][:2]
    other['bindings'][0]['channel']=1;other['bindings'][1]['channel']=0
    bundle={'format':TRIAL_PROFILES_FORMAT,'version':'0.1','profiles':{'first':profile,'second':other},'future':{'opaque':[2**70,None]}}
    return table,graph,bundle

def test_relocated_policy_dossier_exact_sources_distinct_commands_and_receipts(tmp_path,inputs):
    table,graph,b=inputs;raw=enc(b);out=tmp_path/'a'
    m=prepare_experiment_profiles(table,graph,raw,out);assert m['version']=='0.2'
    assert (out/'profiles.json').read_bytes()==raw and not (out/'profile.json').exists()
    moved=tmp_path/'moved';shutil.move(out,moved)
    plans,context=load_prepared_experiment(moved)
    assert base64.b64decode(context['retained_inputs']['profiles.json']['data'])==raw
    assert [{c['channel']:c['intensity'] for c in json.loads(p)['plan']['commands']} for p in plans]==[{0:.26,1:0,2:.89},{0:.2,1:.8}]
    for p,key in zip(plans,['first','second']):
        d=json.loads(p);assert d['profile']['document']==b['profiles'][key]
        canonical=json.dumps(b['profiles'][key],sort_keys=True,separators=(',', ':'),ensure_ascii=True,allow_nan=False).encode()
        assert d['profile']['sha256']==hashlib.sha256(canonical).hexdigest()
    t=Transport()
    def factory():shutil.rmtree(moved);return t
    r=run_prepared_experiment(moved,factory,expected_device_id=ID)
    assert r['status']=='completed' and [s['trial_id'] for s in r['sequence']['steps']]==['first','second']
    assert [q['duration'] for q in t.requests if q['type']=='render']==[.1,.2]

@pytest.mark.parametrize('change',[
 lambda b:b.update(format='unknown'),lambda b:b.update(version='9'),
 lambda b:b.update(profiles=[]),lambda b:b['profiles'].pop('second'),
 lambda b:b['profiles'].update(unused=deepcopy(b['profiles']['first'])),
 lambda b:b['profiles'].update(second=None),
 lambda b:b['profiles']['second']['bindings'][0].update(channel=99),
 lambda b:b['profiles']['second'].update(mapper='unknown'),
 lambda b:b['profiles']['second'].update(capabilities={}),
])
def test_bad_last_policy_or_ambiguous_map_creates_no_output(tmp_path,inputs,change):
    table,g,b=inputs;change(b);out=tmp_path/'no'
    with pytest.raises((ValueError,TypeError,KeyError)):prepare_experiment_profiles(table,g,enc(b),out)
    assert not out.exists()

def test_bundle_bound_and_collision(tmp_path,inputs):
    table,g,b=inputs;out=tmp_path/'out'
    with pytest.raises(ValueError):prepare_experiment_profiles(table,g,b' '*(1048576+1),out)
    assert not out.exists()
    prepare_experiment_profiles(table,g,enc(b),out);before=(out/'profiles.json').read_bytes()
    with pytest.raises(FileExistsError):prepare_experiment_profiles(table,g,enc(b),out)
    assert (out/'profiles.json').read_bytes()==before

@pytest.mark.parametrize('kind',['profile','plan','version','symlink','inventory'])
def test_hash_consistent_stale_policy_refuses_before_connection(tmp_path,inputs,kind):
    table,g,b=inputs;out=tmp_path/'out';m=prepare_experiment_profiles(table,g,enc(b),out)
    if kind=='profile':
        b['profiles']['second']['bindings'].reverse();raw=enc(b);(out/'profiles.json').write_bytes(raw)
        m['files']['profiles.json']={'sha256':hashlib.sha256(raw).hexdigest(),'byte_count':len(raw)}
    if kind=='plan':
        p=json.loads((out/'plan-002.json').read_bytes());p['profile']['document']=b['profiles']['first'];raw=enc(p);(out/'plan-002.json').write_bytes(raw)
        m['files']['plan-002.json']={'sha256':hashlib.sha256(raw).hexdigest(),'byte_count':len(raw)}
    if kind=='version':m['version']='9'
    if kind=='inventory':m['files']['../outside']={}
    if kind=='symlink':
        p=out/'profiles.json';raw=p.read_bytes();p.unlink();other=tmp_path/'other';other.write_bytes(raw);p.symlink_to(other)
    (out/'experiment.json').write_bytes(enc(m));opened=[]
    with pytest.raises((ValueError,OSError)):run_prepared_experiment(out,lambda:opened.append(True),expected_device_id=ID)
    assert opened==[]

@pytest.mark.parametrize('mode,state',[('lost','unknown'),('refused','rejected')])
def test_distinct_policy_failure_preserves_first_receipt(tmp_path,inputs,mode,state):
    table,g,b=inputs;out=tmp_path/'out';prepare_experiment_profiles(table,g,enc(b),out)
    t=Transport(mode);r=run_prepared_experiment(out,lambda:t,expected_device_id=ID)
    assert [s['state'] for s in r['sequence']['steps']]==['completed',state]
    assert t.closed==1

def test_legacy_single_profile_annotations_stay_opaque(tmp_path,inputs):
    table,g,b=inputs;table=table.splitlines()[0]+b'\n'+table.splitlines()[1]+b'\n'
    out=tmp_path/'legacy';m=prepare_experiment(table,g,enc(b['profiles']['first']),out)
    assert m['version']=='0.1' and (out/'profile.json').exists()
    assert m['trials'][0]['record']['profile_id']=='opaque'
    assert len(load_prepared_experiment(out)[0])==1
