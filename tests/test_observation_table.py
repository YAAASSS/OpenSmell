import base64
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from opensmell.experimental.observation_table import observation_table, MAX_BYTES
from opensmell.experimental.perceptual_import import import_keller_csv
from opensmell.experimental.generic_graph import generic_graph_to_dict
from opensmell.experimental.core_interchange import interchange_registry

ROOT=Path(__file__).resolve().parents[1]
RAW=(ROOT/'examples/multisource_diphenyl_ether.osmell').read_bytes()


def graph():
    return json.loads(RAW)


def export(doc):
    return observation_table(json.dumps(doc).encode())


def observation(doc):
    return next(r for r in doc['resources'] if r['type']=='observation')


def test_real_graph_values_categories_and_exact_original():
    result=observation_table(RAW)
    assert result['status']=='projected'
    assert base64.b64decode(result['source']['data'])==RAW
    rows=result['tables']['measurements']
    values={r['property']:r for r in rows}
    assert values['familiarity']['value']==0 and values['flower']['value']==47
    assert values['flower']['unit'] is None and values['flower']['unit_presence']=='missing'
    assert len(result['tables']['categorical'])==1
    assert result['tables']['categorical'][0]['data']['annotations'][1]['state']=='unknown'
    stimulus=next(r for r in result['context']['resources'] if r['id']==values['flower']['stimulus_id'])
    assert stimulus['conditions']
    assert result['execution']=='not_attempted' and not result['physical_validation']


def test_synthetic_import_missing_zero_scale_and_unknown_fields():
    raw=(ROOT/'examples/synthetic_keller.csv').read_bytes()
    source=json.loads((ROOT/'examples/synthetic_keller_source.json').read_bytes())
    g=import_keller_csv(raw,row=1,source=source)
    doc=generic_graph_to_dict(g,registry=interchange_registry());doc['future']={'keep':[None,True]}
    result=export(doc)
    values={r['property']:r for r in result['tables']['measurements']}
    assert values['grass']['value']==0 and 'pleasantness' not in values
    assert values['flower']['unit']=='rating' and values['flower']['scale_max']==100
    assert result['context']['future']==doc['future']
    g=import_keller_csv(raw,row=3,source=source)
    empty=export(generic_graph_to_dict(g,registry=interchange_registry()))
    assert empty['tables']['measurements']==[] and empty['tables']['observations'][0]['measurement_count']==0
    assert len(empty['tables']['categorical'])==1


@pytest.mark.parametrize('measurement',[
    {'property':'x','value':None,'scale':{'min':0,'max':100}},
    {'property':'x','value':True,'scale':{'min':0,'max':100}},
    {'property':'x','value':101,'scale':{'min':0,'max':100}},
    {'property':'x','value':0,'scale':{'min':0,'max':0}},
    {'property':'','value':0,'scale':{'min':0,'max':1}},
    {'property':'x','value':0,'scale':{'min':0,'max':1},'unit':{'unknown':1}},
    'opaque',
])
def test_invalid_measurement_partial_not_coerced(measurement):
    doc=graph();m=observation(doc)['results'][0]['data']['measurements'];m.append(measurement)
    result=export(doc)
    assert result['status']=='partial' and result['coverage']['issues'][-1]['code']=='invalid_measurement'
    assert result['context']==doc and len(result['tables']['measurements'])==len(m)-1


def test_unknown_contract_and_empty_results_preserved():
    doc=graph();obs=observation(doc)
    obs['results'].append({'scheme':{'id':'org.example.future','version':'9'},'data':{'opaque':[1,None]}})
    obs['target']=None
    doc['resources'].append({'type':'org.example.future','type_version':'1','id':'unknown','data':{'keep':True}})
    result=export(doc)
    assert result['status']=='partial' and {i['code'] for i in result['coverage']['issues']}=={'uninterpreted_result','uninterpreted_resource'}
    assert all(r['target_id'] is None for r in result['tables']['measurements'])
    obs.pop('results');result=export(doc)
    assert result['tables']['measurements']==[]


@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'NaN',b'{}',b'\xff',b' '*(MAX_BYTES+1)])
def test_invalid_input(raw):
    with pytest.raises((ValueError,TypeError)):
        observation_table(raw)


def test_cli_stdin_partial_and_collision(tmp_path):
    def cli(raw):
        return subprocess.run([sys.executable,'-m','opensmell','observation-table','-','--output',str(tmp_path/'table.json')],input=raw,capture_output=True,timeout=15)
    doc=graph();observation(doc)['results'][0]['scheme']['version']='future'
    assert cli(json.dumps(doc).encode()).returncode==3
    saved=(tmp_path/'table.json').read_bytes()
    assert cli(RAW).returncode==2 and (tmp_path/'table.json').read_bytes()==saved


def test_nonstandard_scale_unit_and_unresolved_context_are_not_normalized():
    doc=graph();obs=observation(doc)
    obs['stimulus']['resource_id']='external-stimulus'
    obs['results'][0]['data']['measurements']=[{'property':'declared','value':-5,'scale':{'min':-10,'max':10},'unit':'source-unit','future':{'retain':True}}]
    result=export(doc)
    row,=result['tables']['measurements']
    assert (row['value'],row['scale_min'],row['scale_max'],row['unit'])==(-5,-10,10,'source-unit')
    assert result['status']=='partial' and result['coverage']['issues'][0]['code']=='unresolved_context_reference'
    assert result['context']==doc


@pytest.mark.parametrize('raw',[b'{',b'{"format":"x","format":"y"}',b'{"x":NaN}',b'{}',b'x'*(MAX_BYTES+1)])
def test_structural_or_strict_input_refused(raw):
    with pytest.raises((ValueError,TypeError)):
        observation_table(raw)
