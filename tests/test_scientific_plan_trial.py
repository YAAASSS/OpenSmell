import importlib.util
import json
from pathlib import Path
import pytest
from opensmell.experimental.frame_export import encode_plan_frame
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scientific_trial',ROOT/'examples/rdkit_molecule/science_to_plan.py')
trial=importlib.util.module_from_spec(spec);spec.loader.exec_module(trial)
RAW=(ROOT/'examples/multisource_diphenyl_ether.osmell').read_bytes()
MOL='e6ad8ce3-dc6e-5d94-9287-57665d48fc0b';OBS='219ef28c-9b58-52f2-93a7-0807f5897857'


def run(raw,profile,path,resource=OBS,molecule=MOL):
    return trial.export_experiment(raw,profile,molecule_id=molecule,observation_id=OBS,resource_id=resource,duration=5,directory=path)


@pytest.mark.parametrize('mapper,resource,commands',[
 ('semantic',MOL,[{'channel':0,'intensity':.25},{'channel':1,'intensity':.6}]),
 ('perceptual',OBS,[{'channel':0,'intensity':.47},{'channel':1,'intensity':.18},{'channel':2,'intensity':.15}])])
def test_linked_installed_sdk_plan_is_reusable(tmp_path,mapper,resource,commands):
    pytest.importorskip('rdkit')
    profile=(ROOT/f'examples/offline_{mapper}_profile.json').read_bytes();out=tmp_path/'new'
    result=run(RAW,profile,out,resource)
    assert result['status']=='prepared' and result['execution']=='not_attempted'
    assert sorted(result['plan']['commands'],key=lambda c:c['channel'])==commands
    frame=encode_plan_frame((out/'plan.json').read_bytes(),json.dumps(json.loads(profile)['capabilities']).encode())
    assert json.loads(frame['frame']['line'])['commands']==result['plan']['commands']
    assert (out/'source.osmell').read_bytes()==RAW and (out/'profile.json').read_bytes()==profile
    with pytest.raises(FileExistsError):run(RAW,profile,out,resource)


@pytest.mark.parametrize('change',['molecule','stimulus','mapping','profile'])
def test_mismatch_or_missing_mapping_refuses_before_any_output(tmp_path,change):
    doc=json.loads(RAW);profile=json.loads((ROOT/'examples/offline_perceptual_profile.json').read_bytes())
    resource=OBS;molecule=MOL
    if change=='molecule':molecule='other'
    elif change=='stimulus':next(r for r in doc['resources'] if r['type']=='observation')['stimulus']['resource_id']='missing'
    elif change=='mapping':resource='another'
    else:profile['bindings']=[{'property':'absent','channel':0}]
    with pytest.raises(ValueError):run(json.dumps(doc).encode(),json.dumps(profile).encode(),tmp_path/'no',resource,molecule)
    assert not (tmp_path/'no').exists()
