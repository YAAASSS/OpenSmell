"""Selected Core quantitative data, explicit unit/scale policy, no invented experiment."""
import base64
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from opensmell.exceptions import OpenSmellError
from opensmell.experimental.core_planning import plan_core_bytes, validate_core_projection
from opensmell.experimental.core_perceptual import POLICY_KEY, SELECTION_KEY
from opensmell.experimental.core_interchange import interchange_registry
from opensmell.experimental.generic_graph import generic_graph_from_dict
from opensmell.experimental.planning import plan_with_profile
from opensmell.experimental.rendering import RenderRequest
from opensmell.experimental.frame_export import encode_plan_frame
from opensmell.experimental.transport_sequence import prepare_steps, run_transport_sequence
from test_transport_sequence import Transport, ID

ROOT=Path(__file__).resolve().parents[1]
CORE=(ROOT/'examples/core_perceptual_only.osmell').read_bytes()
PROFILE=(ROOT/'examples/offline_core_perceptual_profile.json').read_bytes()
TARGET=json.dumps(json.loads(PROFILE)['capabilities']).encode()


def encoded(obj):return json.dumps(obj,indent=3).encode()+b'\r\n'


def test_selected_representations_normal_frame_sdk_and_no_fabricated_observation():
    plans=[]
    for index,flower in [(0,.25),(1,.75)]:
        artifact=plan_core_bytes(CORE,PROFILE,representation_index=index,duration=.1)
        assert artifact['plan']['commands']==[{'channel':0,'intensity':flower},{'channel':1,'intensity':.5},{'channel':2,'intensity':1}]
        doc=artifact['source']['document'];assert base64.b64decode(doc[SELECTION_KEY]['source']['data'])==CORE
        assert len(doc['resources'])==1 and doc['resources'][0]['type']=='org.opensmell.experimental.core-perceptual-representation'
        assert not any(r['type'] in {'observation','stimulus','org.opensmell.molecule'} for r in doc['resources'])
        raw=encoded(artifact);plans.append(raw)
        assert json.loads(encode_plan_frame(raw,TARGET)['frame']['line'])['commands']==artifact['plan']['commands']
    t=Transport();report=run_transport_sequence(plans,lambda:t,expected_device_id=ID)
    assert report['status']=='completed' and t.renders==2 and t.closed==1
    assert [s.plan.commands[0].intensity for s in prepare_steps(plans)]==[.25,.75]


@pytest.mark.parametrize('bad',['no_policy','version','normalization','unit','missing_unit','null_unit','scale','extra_policy_property',
    'duplicate_policy_property','missing_policy_property','policy_bool','policy_unit_object','policy_scale_overflow','profile_mapper',
    'source_duplicate','source_missing','source_invalid','source_unknown_scheme','source_unknown_version','index','no_bindings','duration'])
def test_refused_inputs_never_choose_fallback(bad):
    core=json.loads(CORE);profile=json.loads(PROFILE);index=0;duration=.1
    policy=profile[POLICY_KEY];source=core['odor']['representations'][0]['data']['measurements']
    if bad=='no_policy':profile.pop(POLICY_KEY)
    if bad=='version':policy['version']='9'
    if bad=='normalization':policy['normalization']='infer'
    if bad=='unit':policy['measurements'][0]['unit']='percent'
    if bad=='missing_unit':policy['measurements'][0].pop('unit')
    if bad=='null_unit':policy['measurements'][2]['unit']=None
    if bad=='scale':policy['measurements'][0]['scale']['max']=100
    if bad=='extra_policy_property':policy['measurements'].append({'property':'extra','scale':{'min':0,'max':1}})
    if bad=='duplicate_policy_property':policy['measurements'].append(deepcopy(policy['measurements'][0]))
    if bad=='missing_policy_property':policy['measurements'].pop()
    if bad=='policy_bool':policy['measurements'][0]['scale']['min']=False
    if bad=='policy_unit_object':policy['measurements'][0]['unit']={}
    if bad=='policy_scale_overflow':policy['measurements'][0]['scale']['max']=10**400
    if bad=='profile_mapper':profile['mapper']='semantic'
    if bad=='source_duplicate':source.append(deepcopy(source[0]))
    if bad=='source_missing':source.pop()
    if bad=='source_invalid':source[0]['value']=1000
    if bad=='source_unknown_scheme':core['odor']['representations'][0]['scheme']['id']='caller.future'
    if bad=='source_unknown_version':core['odor']['representations'][0]['scheme']['version']='9'
    if bad=='index':index=2
    if bad=='no_bindings':profile['bindings']=[]
    if bad=='duration':duration=31
    with pytest.raises((OpenSmellError,ValueError,TypeError)):
        plan_core_bytes(encoded(core),encoded(profile),representation_index=index,duration=duration)


@pytest.mark.parametrize('bad',['value','unit','scale','index','snapshot','both','policy','request'])
def test_stale_projection_and_inconsistent_policy_refused_at_existing_normal_boundaries(bad):
    artifact=plan_core_bytes(CORE,PROFILE,representation_index=0,duration=.1)
    doc=artifact['source']['document'];m=doc['resources'][0]['data']['measurements'][0]
    if bad=='value':
        m['value']=7.5;artifact['plan']['commands'][0]['intensity']=.75
    if bad=='unit':m['unit']='percent'
    if bad=='scale':m['scale']['max']=100
    if bad=='index':doc[SELECTION_KEY]['representation_index']=1
    if bad=='snapshot':doc[SELECTION_KEY]['source']['sha256']='0'*64
    if bad=='both':doc['org.opensmell.experimental.core-semantic-selection']=deepcopy(doc[SELECTION_KEY])
    if bad=='policy':artifact['profile']['document'][POLICY_KEY]['measurements'][0]['unit']='other'
    if bad=='request':artifact['request']['resource_id']='another'
    with pytest.raises(ValueError):encode_plan_frame(encoded(artifact),TARGET)
    opened=[];r=run_transport_sequence([encoded(artifact)],lambda:opened.append(True),expected_device_id=ID)
    assert r['status']=='invalid' and opened==[]


def test_direct_graph_plan_obeys_same_projection_and_policy_guard():
    artifact=plan_core_bytes(CORE,PROFILE,representation_index=0,duration=.1)
    doc=artifact['source']['document'];doc['resources'][0]['data']['measurements'][0]['value']=7.5
    graph=generic_graph_from_dict(doc,registry=interchange_registry())
    with pytest.raises(ValueError):plan_with_profile(graph,RenderRequest(artifact['request']['resource_id'],.1),json.loads(PROFILE))


def test_normal_cli_exclusive_output_and_no_profile_auto_selection(tmp_path):
    output=tmp_path/'plan.json'
    cmd=[sys.executable,'-m','opensmell','plan-core','-','--representation-index','0','--profile',str(ROOT/'examples/offline_core_perceptual_profile.json'),'--duration','.1','--output',str(output)]
    r=subprocess.run(cmd,input=CORE,capture_output=True);assert r.returncode==0,r.stderr
    before=output.read_bytes();assert subprocess.run(cmd,input=CORE,capture_output=True).returncode==2
    assert output.read_bytes()==before
    cmd[cmd.index('--representation-index')+1]='2';cmd[-1]=str(tmp_path/'refused.json')
    assert subprocess.run(cmd,input=CORE,capture_output=True).returncode==1 and not (tmp_path/'refused.json').exists()
