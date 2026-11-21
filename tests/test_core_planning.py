import base64
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from opensmell.experimental.core_planning import plan_core_bytes, project_core_selection, SELECTION_KEY
from opensmell.experimental.frame_export import encode_plan_frame
from opensmell.experimental.software_sequence import prepare_steps

ROOT=Path(__file__).resolve().parents[1]
PROFILE=(ROOT/'examples/offline_semantic_profile.json').read_bytes()
CORE=(ROOT/'examples/geraniol.osmell').read_bytes()
TARGET=json.dumps(json.loads(PROFILE)['capabilities']).encode()


def raw_core():
    obj=json.loads(CORE)
    # Caller has semantic data only; no chemical identity required or invented.
    obj['odor']['representations']=[obj['odor']['representations'][1],
        {'type':'semantic','scheme':{'id':'caller.future','version':'9'},'data':{'opaque':[None,2**65]}}]
    obj['future']={'retain':'verbatim'}
    return (json.dumps(obj,indent=3)+'\r\n').encode()


def test_semantic_only_core_normal_frame_and_sequence_input_preserve_all_bytes():
    raw=raw_core();artifact=plan_core_bytes(raw,PROFILE,representation_index=0,duration=.1)
    assert artifact['execution']=='not_attempted'
    assert artifact['plan']['commands']==[{'channel':0,'intensity':.25}]
    projection=artifact['source']['document']
    assert base64.b64decode(projection[SELECTION_KEY]['source']['data'])==raw
    assert not any(r['type']=='org.opensmell.molecule' for r in projection['resources'])
    encoded=json.dumps(artifact).encode()
    frame=encode_plan_frame(encoded,TARGET)
    assert json.loads(frame['frame']['line'])['commands']==artifact['plan']['commands']
    assert frame['transport']=='not_opened'
    assert prepare_steps([encoded])[0].plan.duration==.1


def test_selects_only_one_representation_with_other_known_representations_retained():
    obj=json.loads(raw_core());second=deepcopy(obj['odor']['representations'][0])
    second['data']['annotations']=[{'value':'green&herbal','language':'en','state':'present'}]
    obj['odor']['representations'].append(second);raw=json.dumps(obj).encode()
    first=plan_core_bytes(raw,PROFILE,representation_index=0,duration=1)
    third=plan_core_bytes(raw,PROFILE,representation_index=2,duration=1)
    assert first['plan']['commands']==[{'channel':0,'intensity':.25}]
    assert third['plan']['commands']==[{'channel':1,'intensity':.6}]
    assert first['request']['resource_id']!=third['request']['resource_id']


@pytest.mark.parametrize('index',[None,True,-1,99,1,'0'])
def test_unknown_missing_or_invalid_explicit_selection_refuses(index):
    with pytest.raises((ValueError,TypeError)):
        plan_core_bytes(raw_core(),PROFILE,representation_index=index,duration=1)


@pytest.mark.parametrize('change',['annotation','index','hash','count','snapshot','root_bool','version','remove_annotation'])
def test_stale_projection_refused_by_normal_export_and_sequence_preflight(change):
    artifact=plan_core_bytes(raw_core(),PROFILE,representation_index=0,duration=.1)
    doc=artifact['source']['document'];selection=doc[SELECTION_KEY]
    if change=='annotation':doc['resources'][1]['data']['annotations'][2]['state']='absent'
    if change=='index':selection['representation_index']=1
    if change=='hash':selection['source']['sha256']='0'*64
    if change=='count':selection['source']['byte_count']+=1
    if change=='snapshot':selection['source']['data']='!invalid'
    if change=='root_bool':doc['resources'][0]['representation_index']=False
    if change=='version':selection['version']='9'
    if change=='remove_annotation':doc['resources'].pop()
    encoded=json.dumps(artifact).encode()
    with pytest.raises(ValueError):encode_plan_frame(encoded,TARGET)
    with pytest.raises(ValueError):prepare_steps([encoded])


@pytest.mark.parametrize('bad',['empty','no_binding','perceptual','duration','known_invalid','chemical','ambiguous_envelope','oversize'])
def test_refusal_boundaries(bad):
    raw=raw_core();profile=json.loads(PROFILE);duration=.1;index=0
    if bad=='empty':raw=b'{}'
    if bad=='no_binding':profile['bindings'][0]['descriptor']='not-in-data'
    if bad=='perceptual':profile['mapper']='perceptual'
    if bad=='duration':duration=31
    if bad=='known_invalid':
        obj=json.loads(raw);obj['odor']['representations'][0]['data']={'annotations':'bad'};raw=json.dumps(obj).encode()
    if bad=='chemical':raw=CORE
    if bad=='ambiguous_envelope':
        obj=json.loads(raw);obj['format']='caller';raw=json.dumps(obj).encode()
    if bad=='oversize':raw=b' '*(4*1048576+1)
    with pytest.raises((ValueError,TypeError)):
        plan_core_bytes(raw,json.dumps(profile).encode(),representation_index=index,duration=duration)


def test_normal_cli_stdin_and_exclusive_output(tmp_path):
    output=tmp_path/'plan.json'
    command=[sys.executable,'-m','opensmell','plan-core','-','--representation-index','0',
             '--profile',str(ROOT/'examples/offline_semantic_profile.json'),'--duration','.1','--output',str(output)]
    result=subprocess.run(command,input=raw_core(),capture_output=True)
    assert result.returncode==0,result.stderr
    before=output.read_bytes();assert json.loads(before)['status']=='planned'
    assert subprocess.run(command,input=raw_core(),capture_output=True).returncode==2
    assert output.read_bytes()==before
    refused=command.copy();refused[refused.index('0')]='1';refused[-1]=str(tmp_path/'no-output')
    assert subprocess.run(refused,input=raw_core(),capture_output=True).returncode==1
    assert not (tmp_path/'no-output').exists()


def test_matching_edited_graph_and_plan_still_cannot_replace_original_core_selection():
    artifact=plan_core_bytes(raw_core(),PROFILE,representation_index=0,duration=.1)
    artifact['source']['document']['resources'][1]['data']['annotations']=[{'value':'green&herbal','language':'en','state':'present'}]
    artifact['plan']['commands']=[{'channel':1,'intensity':.6}]
    with pytest.raises(ValueError,match='Core projection'):
        encode_plan_frame(json.dumps(artifact).encode(),TARGET)
