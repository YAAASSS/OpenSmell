"""Selected-result export, exact context recovery and downstream source bindings."""
import base64
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from opensmell.exceptions import OpenSmellError
from opensmell.experimental.observation_core import export_observation_core, extract_observation_source, EXPORT_KEY
from opensmell.experimental.core_planning import plan_core_bytes
from opensmell.experimental.core_perceptual import POLICY_KEY, SELECTION_KEY
from opensmell.experimental.frame_export import encode_plan_frame
from opensmell.experimental.transport_sequence import run_transport_sequence
from test_transport_sequence import Transport, ID

ROOT=Path(__file__).resolve().parents[1]
GRAPH=(ROOT/'examples/multisource_diphenyl_ether.osmell').read_bytes()
RID='219ef28c-9b58-52f2-93a7-0807f5897857'
ODOR='urn:caller:selected-odor'


def encode(v):return json.dumps(v,ensure_ascii=True,indent=3).encode()+b'\r\n'

def obs(doc):return next(r for r in doc['resources'] if r['id']==RID)

def export(raw=GRAPH,index=0,oid=ODOR):
    return export_observation_core(raw,observation_id=RID,result_index=index,odor_id=oid)


def profile(doc):
    p=json.loads((ROOT/'examples/offline_perceptual_profile.json').read_bytes())
    source=obs(doc)['results'][0]['data']['measurements']
    p[POLICY_KEY]={'version':'0.1','normalization':'value-minus-min-over-range','measurements':[
        {k:deepcopy(v) for k,v in m.items() if k in {'property','scale','unit'}} for m in source
        if m['property'] in {b['property'] for b in p['bindings']}]}
    return encode(p)


def test_selected_result_context_roundtrip_and_normal_plan_frame_sequence():
    doc=json.loads(GRAPH);doc['future']={'retain':[None,2**70]}
    obs(doc)['results'][0]['future_result']={'uninterpreted':['keep',None]}
    raw=encode(doc);core=export(raw);parsed=json.loads(core)
    assert parsed['odor']['id']==ODOR
    assert len(parsed['odor']['representations'])==1
    rep=parsed['odor']['representations'][0]
    assert rep['type']=='perceptual' and rep['data']==obs(doc)['results'][0]['data']
    assert extract_observation_source(core)==raw
    assert base64.b64decode(parsed[EXPORT_KEY]['source']['data'])==raw
    assert rep['org.opensmell.experimental.observation-result-context']['future_result']=={'uninterpreted':['keep',None]}
    artifact=plan_core_bytes(core,profile(doc),representation_index=0,duration=.1)
    assert [c['intensity'] for c in artifact['plan']['commands']]==[.47,.18,.15]
    encoded=encode(artifact);target=json.dumps(json.loads(profile(doc))['capabilities']).encode()
    assert encode_plan_frame(encoded,target)['transport']=='not_opened'
    t=Transport();report=run_transport_sequence([encoded],lambda:t,expected_device_id=ID)
    assert report['status']=='completed' and t.closed==1


@pytest.mark.parametrize('bad',['missing_id','wrong_resource','blank_odor','no_odor','bool_index','negative_index','unknown_index',
    'category','unknown_scheme','unknown_version','no_measurements','invalid_value','invalid_unit','ambiguous','oversize','invalid_json'])
def test_invalid_selection_refuses_without_fallback(bad):
    doc=json.loads(GRAPH);rid=RID;oid=ODOR;index=0;raw=None
    if bad=='missing_id':rid='absent'
    if bad=='wrong_resource':rid=next(r['id'] for r in doc['resources'] if r['type']!='observation')
    if bad=='blank_odor':oid=' '
    if bad=='no_odor':oid=None
    if bad=='bool_index':index=True
    if bad=='negative_index':index=-1
    if bad=='unknown_index':index=99
    if bad=='category':index=1
    if bad=='unknown_scheme':obs(doc)['results'][0]['scheme']['id']='caller.future'
    if bad=='unknown_version':obs(doc)['results'][0]['scheme']['version']='9'
    if bad=='no_measurements':obs(doc)['results'][0]['data']={'measurements':[]}
    if bad=='invalid_value':obs(doc)['results'][0]['data']['measurements'][0]['value']=10000
    if bad=='invalid_unit':obs(doc)['results'][0]['data']['measurements'][0]['unit']={}
    if bad=='ambiguous':doc['opensmell']='0.1'
    if bad=='oversize':raw=b' '*(2*1048576+1)
    if bad=='invalid_json':raw=b'{"a":1,"a":2}'
    with pytest.raises((OpenSmellError,ValueError,TypeError)):
        export_observation_core(raw if raw is not None else encode(doc),observation_id=rid,result_index=index,odor_id=oid)


@pytest.mark.parametrize('bad',['data','odor','index','identity','snapshot','hash','count','metadata','version'])
def test_tampered_export_refuses_extraction_planning_and_downstream(bad):
    core=json.loads(export());context=core[EXPORT_KEY]
    if bad=='data':core['odor']['representations'][0]['data']['measurements'][0]['value']=1
    if bad=='odor':core['odor']['id']='changed'
    if bad=='index':context['selection']['result_index']=1
    if bad=='identity':context['selection']['observation_id']='absent'
    if bad=='snapshot':context['source']['data']='!'
    if bad=='hash':context['source']['sha256']='0'*64
    if bad=='count':context['source']['byte_count']=False
    if bad=='metadata':core['odor']['metadata']['description']='stale'
    if bad=='version':context['version']='9'
    with pytest.raises((OpenSmellError,ValueError,TypeError)):extract_observation_source(encode(core))
    with pytest.raises((OpenSmellError,ValueError,TypeError)):plan_core_bytes(encode(core),profile(json.loads(GRAPH)),representation_index=0,duration=.1)


def test_changed_core_and_matching_plan_cannot_replace_retained_graph():
    artifact=plan_core_bytes(export(),profile(json.loads(GRAPH)),representation_index=0,duration=.1)
    projection=artifact['source']['document'];raw_core=json.loads(base64.b64decode(projection[SELECTION_KEY]['source']['data']))
    raw_core['odor']['representations'][0]['data']['measurements'][0]['value']=100
    # The nested Core itself is inconsistent with its graph snapshot, even when
    # the outer snapshot/hash and projected result are rebuilt by a hostile caller.
    changed=encode(raw_core);import hashlib
    projection[SELECTION_KEY]['source']={'encoding':'base64','data':base64.b64encode(changed).decode(),'sha256':hashlib.sha256(changed).hexdigest(),'byte_count':len(changed)}
    opened=[];r=run_transport_sequence([encode(artifact)],lambda:opened.append(True),expected_device_id=ID)
    assert r['status']=='invalid' and opened==[]


def test_select_one_result_other_results_retained_and_no_units_converted():
    doc=json.loads(GRAPH);copy=deepcopy(obs(doc)['results'][0]);copy['data']['measurements'][0]['unit']=None
    obs(doc)['results'].append(copy);raw=encode(doc)
    core=export(raw,index=len(obs(doc)['results'])-1)
    rep=json.loads(core)['odor']['representations'][0]
    assert rep['data']['measurements'][0]['unit'] is None
    assert rep['data']==copy['data'] and extract_observation_source(core)==raw


def test_cli_stdin_recovery_collision_and_invalid_before_output(tmp_path):
    out=tmp_path/'core.osmell';cmd=[sys.executable,'-m','opensmell','export-observation-core','-',
        '--observation-id',RID,'--result-index','0','--odor-id',ODOR,'--output',str(out)]
    r=subprocess.run(cmd,input=GRAPH,capture_output=True);assert r.returncode==0,r.stderr
    before=out.read_bytes();assert subprocess.run(cmd,input=GRAPH,capture_output=True).returncode==2
    assert out.read_bytes()==before
    recovered=subprocess.run([sys.executable,'-m','opensmell','extract-observation-source',str(out)],capture_output=True)
    assert recovered.returncode==0 and recovered.stdout==GRAPH
    cmd[cmd.index('--result-index')+1]='1';cmd[-1]=str(tmp_path/'refused')
    assert subprocess.run(cmd,input=GRAPH,capture_output=True).returncode==1 and not (tmp_path/'refused').exists()


def test_serialized_core_limit_refuses_without_truncating_source():
    doc=json.loads(GRAPH);obs(doc)['results'][0]['data']['opaque']='é'*600000
    raw=json.dumps(doc,ensure_ascii=False).encode()
    assert len(raw)<2*1048576
    with pytest.raises(ValueError,match='exceeds4MiB'):export(raw)
    assert json.loads(raw)['resources']==doc['resources']
