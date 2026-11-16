"""Normal extracted-entry checks using actual CLI and reader, no endpoint by default."""
import base64
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest
from tools.build_developer_kit import PAYLOADS, make_archive

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def kit(tmp_path):
    target = tmp_path / 'kit'
    payload = {n:(ROOT/p).read_bytes() for n,p in PAYLOADS.items()}
    with zipfile.ZipFile(io.BytesIO(make_archive(payload, {'test':True}))) as z:
        z.extractall(target)
    shutil.copytree(ROOT/'packages/javascript', target/'node_modules/@opensmell/graph-reader')
    return target


def invoke(kit, tmp_path, *, rid='e6ad8ce3-dc6e-5d94-9287-57665d48fc0b', mapper='semantic', extra=(), graph=None):
    path=tmp_path/'input.osmell'
    path.write_bytes(graph if graph is not None else (ROOT/'examples/multisource_diphenyl_ether.osmell').read_bytes())
    args=[sys.executable,kit/'try_kit.py','--graph',path,'--resource-id',rid,'--profile',kit/f'profiles/{mapper}.json','--report',tmp_path/'report.json',*extra]
    return subprocess.run(list(map(str,args)),cwd=tmp_path,capture_output=True,text=True,timeout=30)


@pytest.mark.parametrize('mapper,rid,expected',[
    ('semantic','e6ad8ce3-dc6e-5d94-9287-57665d48fc0b',{0:.25,1:.6}),
    ('perceptual','219ef28c-9b58-52f2-93a7-0807f5897857',{0:.47,1:.18,2:.15})])
def test_passive_original_bytes_unknowns_and_profile(kit,tmp_path,mapper,rid,expected):
    graph=json.loads((ROOT/'examples/multisource_diphenyl_ether.osmell').read_bytes())
    graph['future']={'keep':[None,'unknown']}
    raw=(json.dumps(graph,indent=3)+'\n').encode()
    r=invoke(kit,tmp_path,mapper=mapper,rid=rid,graph=raw)
    assert r.returncode==0,r.stderr
    report=json.loads(r.stdout)
    assert report['result']=='planned' and report['execution']=='not_attempted'
    assert report['transfer_byte_identity'] is True and 'software_observations' not in report
    assert base64.b64decode(report['inputs']['graph']['data'])==raw
    assert {c['channel']:c['intensity'] for c in report['plan']['plan']['commands']}==expected
    assert report['plan']['source']['document']['future']==graph['future']


@pytest.mark.parametrize('options,phase',[({'rid':'absent'},'planning'),({'graph':b'{bad'},'validation'),
    ({'extra':('--simulate','--duration','1')},'simulation_preflight')])
def test_refusals_retained_before_simulation(kit,tmp_path,options,phase):
    r=invoke(kit,tmp_path,**options)
    assert r.returncode==3,(r.stdout,r.stderr)
    report=json.loads((tmp_path/'report.json').read_bytes())
    assert report['result']=='rejected' and report['error']['phase']==phase
    assert report['execution']=='not_attempted' and 'software_observations' not in report


def test_report_collision_and_bad_manifest_block_work(kit,tmp_path):
    (tmp_path/'report.json').write_text('original')
    r=invoke(kit,tmp_path)
    assert r.returncode==2 and (tmp_path/'report.json').read_text()=='original'
    (kit/'graph_trial.py').write_text('raise Exception("must not execute")')
    r=invoke(kit,tmp_path)
    assert r.returncode!=0 and 'Kit bytes differ from manifest' in r.stderr
    assert (tmp_path/'report.json').read_text()=='original'
