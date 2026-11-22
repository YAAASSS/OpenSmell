"""Clean wheel-only starter: no checkout data, inherited site packages or Node."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import venv
import tempfile

from .offline_dependencies import load_wheelhouse, require_target, TARGET, PINS


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('wheel',type=Path);p.add_argument('--dependency-directory',type=Path,required=True)
    p.add_argument('--evidence-directory',type=Path,required=True)
    a=p.parse_args();require_target();wheel=a.wheel.resolve(strict=True)
    dependencies=a.dependency_directory.resolve(strict=True);load_wheelhouse(dependencies)
    evidence=a.evidence_directory.resolve();evidence.mkdir(parents=True,exist_ok=False)
    result={'result':'incomplete','physical_validation':False,'target':TARGET,'dependency_pins':PINS,
            'scope':'Clean venv; only SDK and verified normal dependency wheels; PATH excludes Node; no checkout resources copied'}
    def save():(evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-clean-starter-') as directory:
        work=Path(directory);venv.EnvBuilder(with_pip=True,system_site_packages=False).create(work/'venv')
        python=work/'venv'/'bin/python'
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        env['PATH']=str(python.parent)
        def run(command,expected=0):
            r=subprocess.run([str(x) for x in command],cwd=work,env=env,capture_output=True,timeout=60)
            if r.returncode!=expected:raise RuntimeError(f'{command}: {r.returncode} {r.stdout!r} {r.stderr!r}')
            return r.stdout
        run([python,'-I','-m','pip','install','--no-index','--no-deps',wheel,*sorted(dependencies.glob('*.whl'))])
        runtime=json.loads(run([python,'-I','-c',
            'import importlib.util as u,importlib.metadata as m,json,opensmell,sys,site,shutil;print(json.dumps({"sdk":opensmell.__file__,"prefix":sys.prefix,"user_site":site.ENABLE_USER_SITE,"optional":{x:u.find_spec(x) is not None for x in ("pandas","numpy","networkx","rdkit","serial","pylsl")},"node":shutil.which("node"),"versions":{d.metadata["Name"]:d.version for d in m.distributions()}}))']))
        assert Path(runtime['sdk']).is_relative_to(work/'venv') and not runtime['user_site']
        assert not any(runtime['optional'].values()) and runtime['node'] is None
        result['runtime']=runtime;save()
        cli=[python,'-I','-m','opensmell']
        workspace=work/'my-workspace'
        created=json.loads(run([python.parent/'opensmell','init-workspace',workspace]))
        assert created['execution']=='not_attempted' and created['status']=='created'
        assert set(x.name for x in workspace.iterdir())=={'README.md','sample.osmell','profile.json','workspace.json'}
        for name,entry in created['files'].items():
            raw=(workspace/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==entry['sha256'] and len(raw)==entry['byte_count']
        original={p.name:p.read_bytes() for p in workspace.iterdir()}
        run([python.parent/'opensmell','init-workspace',workspace],expected=2)
        assert {p.name:p.read_bytes() for p in workspace.iterdir()}==original
        run([*cli,'validate',workspace/'sample.osmell'])
        inspection=json.loads(run([*cli,'inspect',workspace/'sample.osmell','--json']))
        (evidence/'inspection.json').write_text(json.dumps(inspection,indent=2))
        sample=workspace/'sample.osmell';profile=workspace/'profile.json';plan=workspace/'plan.json'
        plan_command=[*cli,'plan-core',sample,'--representation-index','0','--profile',profile,'--duration','.1','--output',plan]
        run(plan_command);artifact=json.loads(plan.read_bytes())
        assert artifact['plan']['commands']==[{'channel':0,'intensity':.25}] and artifact['execution']=='not_attempted'
        snapshot=artifact['source']['document']['org.opensmell.experimental.core-semantic-selection']['source']
        assert base64.b64decode(snapshot['data'])==sample.read_bytes()
        # Caller edits produce a new explicitly selected plan; no template reset or guessing.
        caller=json.loads(sample.read_bytes())
        caller['odor']['representations'][0]['data']['annotations']=[{'value':'green&herbal','language':'en','state':'present'}]
        caller['caller_future']={'keep':[None,2**65]}
        caller_source=workspace/'caller.osmell';caller_source.write_text(json.dumps(caller,indent=3))
        caller_plan=workspace/'caller-plan.json'
        run([*cli,'plan-core',caller_source,'--representation-index','0','--profile',profile,'--duration','.1','--output',caller_plan])
        assert json.loads(caller_plan.read_bytes())['plan']['commands']==[{'channel':1,'intensity':.6}]
        command=[str(python),'-I','-m','opensmell','simulate-device'];identity='opensmell-local-simulator-001'
        receipt=json.loads(run([*cli,'run-sequence',plan,caller_plan,'--software-command-json',json.dumps(command),
                               '--expected-device-id',identity,'--output',workspace/'receipt.json']))
        assert receipt['status']=='completed' and [s['state'] for s in receipt['sequence']['steps']]==['completed']*2
        trial_plan=workspace/'trial-plan.json'
        run([*cli,'plan-core',sample,'--representation-index','0','--profile',profile,'--duration','5','--output',trial_plan])
        trial=json.loads(run([*cli,'lifecycle-trial',trial_plan,'--software-command-json',json.dumps(command),
                             '--expected-device-id',identity,'--output',workspace/'trial.json']))
        assert trial['status']=='passed' and trial['duplicate_request_refused_before_io']
        assert [trial['results'][k]['state'] for k in ('completion','stop','disconnect')]==['completed','stopped','unknown']
        run(plan_command,expected=2)
        for selection,duration,label in ((1,'.1','opaque'),(0,'31','duration')):
            output=workspace/f'refused-{label}.json'
            run([*cli,'plan-core',sample,'--representation-index',str(selection),'--profile',profile,'--duration',duration,'--output',output],expected=1)
            assert not output.exists()
        wrong=json.loads(run([*cli,'run-sequence',plan,'--software-command-json',json.dumps(command),
                             '--expected-device-id','wrong-identity','--output',workspace/'wrong.json'],expected=3))
        assert wrong['status']=='incompatible' and not any(json.loads(t['request_line'])['type']=='render' for t in wrong['transcript'])
        shutil.copytree(workspace,evidence/'workspace')
        result.update(result='passed',clean_environment=True,no_optional_dependencies=True,no_node_on_path=True,
                      passive_workspace=True,exact_template_hashes=True,workspace_collision_refused=True,
                      caller_plans='two distinct selected synthetic Core plans completed',
                      lifecycle=['completed','stopped','unknown'],duplicate_request_refused=True,
                      unknown_selection_and_duration_refused=True,wrong_identity_no_render=True)
        save();print(json.dumps(result))


if __name__=='__main__':main()
