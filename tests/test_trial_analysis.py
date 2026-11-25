"""Explicit passive observation joins; no inference from execution completion."""
import base64
from copy import deepcopy
import csv
import io
import json
import shutil
import subprocess
import sys

import pytest
from opensmell.experimental.experiment import prepare_experiment
from opensmell.experimental.experiment_run import run_prepared_experiment
from opensmell.experimental.trial_analysis import analyze_experiment, write_analysis_directory
from test_experiment import TABLE, GRAPH, PROFILE
from test_transport_sequence import Transport, ID


def encode(obj):return (json.dumps(obj,ensure_ascii=True)+'\n').encode()

@pytest.fixture
def inputs(tmp_path):
    dossier=tmp_path/'dossier';prepare_experiment(TABLE,GRAPH,PROFILE,dossier)
    report=run_prepared_experiment(dossier,lambda:Transport(),expected_device_id=ID)
    graph=json.loads(GRAPH);graph['analysis_fixture']='Declared synthetic join example, not a measured device outcome'
    obs=next(r for r in graph['resources'] if r['type']=='observation');obs['id']='observation-A'
    obs['results']=[{'scheme':{'id':'org.opensmell.perceptual.measurements','version':'0.1'},
                    'data':{'measurements':[{'property':'zero','value':0,'scale':{'min':0,'max':100},'unit':'rating','future':{'keep':2**70}},
                                             {'property':'missing-unit','value':3,'scale':{'min':0,'max':5}},
                                             {'property':'null-unit','value':4,'scale':{'min':0,'max':10},'unit':None}]}}]
    other=deepcopy(obs);other['id']='observation-B';graph['resources'].append(other)
    bindings=b'trial_id,observation_id,note\r\nfirst,observation-A,"quoted, opaque"\r\nsecond,observation-B,caller\r\n'
    return dossier,report,graph,bindings


def analyze(inputs):
    d,r,g,b=inputs;return analyze_experiment(d,encode(r),encode(g),b)


def test_join_exact_inputs_order_unknown_units_and_csv(inputs,tmp_path,monkeypatch):
    # Analysis must not even construct a transport; report is already supplied.
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('Passive analysis launched a process'))
    result=analyze(inputs)
    assert result['status']=='joined' and result['execution']=='not_attempted' and not result['physical_validation']
    assert [t['trial_id'] for t in result['tables']['trials']]==['first','second']
    rows=result['tables']['measurements'];assert len(rows)==6
    assert [(m['unit_presence'],m['value']) for m in rows[:3]]==[('value',0),('missing',3),('null',4)]
    assert rows[0]['binding_record']['note']=='quoted, opaque'
    assert base64.b64decode(result['inputs']['observations']['data'])==encode(inputs[2])
    assert base64.b64decode(result['inputs']['execution_report']['data'])==encode(inputs[1])
    assert result['observation_projection']['context']['analysis_fixture']==inputs[2]['analysis_fixture']
    out=tmp_path/'tables';write_analysis_directory(result,out)
    csvrows=list(csv.DictReader(io.StringIO((out/'measurements.csv').read_text())))
    assert csvrows[0]['value']=='0' and csvrows[1]['unit_presence']=='missing' and csvrows[2]['unit_presence']=='null'
    before=(out/'analysis.json').read_bytes()
    with pytest.raises(FileExistsError):write_analysis_directory(result,out)
    assert (out/'analysis.json').read_bytes()==before


@pytest.mark.parametrize('mode,state',[('lost','unknown'),('refused','rejected')])
def test_uncertain_refused_receipts_do_not_become_measurements(inputs,mode,state):
    d,r,g,b=inputs
    r=run_prepared_experiment(d,lambda:Transport(mode),expected_device_id=ID)
    result=analyze((d,r,g,b))
    assert result['status']=='partial'
    assert [t['receipt_state'] for t in result['tables']['trials']]==['completed',state]
    assert len(result['tables']['measurements'])==6  # caller observations retained, not generated/dropped by receipt
    assert not result['physical_validation']


def test_no_receipts_and_unfinished_snapshot(inputs):
    d,r,g,b=inputs;r['sequence']=None;r['phase']='connect';r['status']='incomplete'
    result=analyze((d,r,g,b));assert result['status']=='partial'
    assert all(t['receipt_state']=='unrecorded' for t in result['tables']['trials'])
    assert {'no_sequence_receipts','unfinished_report'} <= {i['code'] for i in result['coverage']['issues']}


@pytest.mark.parametrize('kind',['manifest','plan','trial','state','execution','format','length'])
def test_report_cannot_bind_to_another_dossier(inputs,kind):
    d,r,g,b=inputs
    if kind=='manifest':r['prepared_experiment']['manifest']['sha256']='0'*64
    if kind=='plan':r['sequence']['steps'][1]['context']['input']['data']=''
    if kind=='trial':r['sequence']['steps'][1]['trial_id']='first'
    if kind=='state':r['sequence']['steps'][0]['state']='unknown'
    if kind=='execution':r['sequence']['steps'][0]['execution']=None
    if kind=='format':r['format']='future'
    if kind=='length':r['sequence']['steps'].pop()
    with pytest.raises(ValueError):analyze((d,r,g,b))


@pytest.mark.parametrize('bindings,codes',[
    (b'trial_id,observation_id\nunknown,observation-A\n',{'unmatched_trial','trial_without_observation'}),
    (b'trial_id,observation_id\nfirst,absent\n',{'unmatched_observation'}),
    (b'trial_id,observation_id\nfirst,observation-A\nsecond,observation-A\n',{'ambiguous_observation_binding'}),
    (b'trial_id,observation_id\nfirst,observation-A\nfirst,observation-A\n',{'ambiguous_observation_binding'}),
    (b'trial_id,observation_id\n',{'trial_without_observation','observation_without_trial'})])
def test_unmatched_ambiguous_bindings_preserved_without_double_count(inputs,bindings,codes):
    d,r,g,b=inputs;result=analyze((d,r,g,bindings))
    assert result['status']=='partial' and result['tables']['measurements']==[]
    assert codes <= {i['code'] for i in result['coverage']['issues']}
    assert base64.b64decode(result['inputs']['bindings']['data'])==bindings


@pytest.mark.parametrize('bindings',[b'',b'trial_id,trial_id\nx,y\n',b'trial_id,observation_id\nx\n',
    b'trial_id,observation_id\n,observation-A\n',b'trial_id,observation_id\n\n',b'x'*65537])
def test_invalid_csv_not_silently_skipped(inputs,bindings):
    d,r,g,b=inputs
    with pytest.raises(ValueError):analyze((d,r,g,bindings))


def test_unknown_scheme_and_no_results_stay_partial(inputs):
    d,r,g,b=inputs;obs=next(o for o in g['resources'] if o['id']=='observation-A')
    obs['results'][0]['scheme']['version']='future'
    result=analyze(inputs)
    assert result['status']=='partial' and len(result['tables']['measurements'])==3
    assert any(i['code']=='observation_without_projected_results' for i in result['coverage']['issues'])
    assert result['observation_projection']['context']==g


def test_normal_cli_moved_dossier_collision_and_stale_report(inputs,tmp_path):
    d,r,g,b=inputs;moved=tmp_path/'moved';shutil.move(d,moved)
    for name,raw in [('report.json',encode(r)),('observations.osmell',encode(g)),('bindings.csv',b)]: (tmp_path/name).write_bytes(raw)
    out=tmp_path/'analysis';cmd=[sys.executable,'-m','opensmell','analyze-experiment',str(moved),'--report',str(tmp_path/'report.json'),
        '--observations',str(tmp_path/'observations.osmell'),'--bindings',str(tmp_path/'bindings.csv'),'--output-directory',str(out)]
    result=subprocess.run(cmd,capture_output=True);assert result.returncode==0,result.stderr
    original=(out/'analysis.json').read_bytes();assert subprocess.run(cmd,capture_output=True).returncode==2
    assert (out/'analysis.json').read_bytes()==original
    r['prepared_experiment']['trial_order'].reverse();(tmp_path/'report.json').write_bytes(encode(r))
    cmd[-1]=str(tmp_path/'refused')
    assert subprocess.run(cmd,capture_output=True).returncode==1 and not (tmp_path/'refused').exists()
