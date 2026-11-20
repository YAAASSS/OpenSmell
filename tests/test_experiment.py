import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from opensmell.experimental.experiment import prepare_experiment
from opensmell.experimental.software_sequence import prepare_steps

ROOT = Path(__file__).resolve().parents[1]
RID = '219ef28c-9b58-52f2-93a7-0807f5897857'
GRAPH = (ROOT/'examples/multisource_diphenyl_ether.osmell').read_bytes()
PROFILE = (ROOT/'examples/offline_perceptual_profile.json').read_bytes()
TABLE = f'trial_id,resource_id,duration,note\r\nfirst,{RID},.1,"quoted, annotation"\r\nsecond,{RID},.2,caller-design\r\n'.encode()


def test_portable_table_order_exact_unknown_bytes_and_normal_sequence_preflight(tmp_path):
    obj = json.loads(GRAPH); obj['future'] = {'opaque':[None, 2**65]}
    raw = json.dumps(obj, indent=3).encode()
    target = tmp_path/'experiment'
    report = prepare_experiment(TABLE, raw, PROFILE, target)
    assert json.loads((target/'experiment.json').read_bytes()) == report
    assert report['execution'] == 'not_attempted' and not report['physical_validation']
    assert [r['trial_id'] for r in report['trials']] == ['first','second']
    assert (target/'source.osmell').read_bytes() == raw
    assert (target/'trials.csv').read_bytes() == TABLE
    assert (target/'profile.json').read_bytes() == PROFILE
    for name, entry in report['files'].items():
        content = (target/name).read_bytes()
        assert entry == {'sha256':hashlib.sha256(content).hexdigest(),'byte_count':len(content)}
    steps = prepare_steps([(target/r['plan_file']).read_bytes() for r in report['trials']])
    assert [s.plan.duration for s in steps] == [.1,.2]
    assert steps[0].context['request']['resource_id'] == RID
    assert json.loads((target/'plan-001.json').read_bytes())['org.opensmell.experimental.trial']['record']['note'] == 'quoted, annotation'
    with pytest.raises(FileExistsError): prepare_experiment(TABLE, raw, PROFILE, target)
    assert (target/'trials.csv').read_bytes() == TABLE


@pytest.mark.parametrize('table', [b'',b'trial_id,resource_id\na,b\n',b'trial_id,resource_id,duration,duration\na,b,1,1\n',
    b'trial_id,resource_id,duration\n',b'trial_id,resource_id,duration\na,b,1\n',
    TABLE+f'second,{RID},.1,note\n'.encode(), TABLE+b'\n',TABLE+b'short,row\n',
    TABLE+f'bad,{RID},nan,note\n'.encode(), TABLE+f'bad,{RID},31,note\n'.encode(),
    TABLE+f'bad,{RID},0,note\n'.encode(),TABLE+b'bad,missing,.1,note\n',b'x'*65537,
    b'trial_id,resource_id,duration\n'+b''.join(f'{i},{RID},.1\n'.encode() for i in range(17)),
    b'trial_id,resource_id,duration\n'+b''.join(f'{i},{RID},30\n'.encode() for i in range(5)),
    b'trial_id,resource_id,duration\n"unfinished'])
def test_any_bad_row_refuses_whole_experiment_before_output(tmp_path,table):
    out = tmp_path/'no-output'
    with pytest.raises((ValueError,TypeError,csv.Error)): prepare_experiment(table,GRAPH,PROFILE,out)
    assert not out.exists()


def test_trial_id_is_metadata_never_filename(tmp_path):
    report = prepare_experiment(TABLE.replace(b'first,',b'../../outside,'),GRAPH,PROFILE,tmp_path/'safe')
    assert report['trials'][0]['plan_file'] == 'plan-001.json'
    assert not (tmp_path/'outside').exists()


def test_cli_normal_entry_and_collision(tmp_path):
    table=tmp_path/'input.csv';table.write_bytes(TABLE)
    out=tmp_path/'bundle'
    command=[sys.executable,'-m','opensmell','prepare-experiment',str(table),'--graph',str(ROOT/'examples/multisource_diphenyl_ether.osmell'),
             '--profile',str(ROOT/'examples/offline_perceptual_profile.json'),'--output-directory',str(out)]
    result=subprocess.run(command,capture_output=True)
    assert result.returncode==0,result.stdout
    report=json.loads(result.stdout)
    assert report['status']=='prepared' and report['execution']=='not_attempted'
    again=subprocess.run(command,capture_output=True)
    assert again.returncode==2
    assert json.loads((out/'experiment.json').read_bytes())==report
