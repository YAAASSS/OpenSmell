"""Installed Core selection -> passive plan/frame -> explicit software receipts."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import venv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('wheel',type=Path);p.add_argument('--evidence-directory',type=Path,required=True)
    p.add_argument('--host',type=Path,help='Optional explicit trusted native lifecycle sketch executable')
    a=p.parse_args();root=Path(__file__).resolve().parents[1];wheel=a.wheel.resolve(strict=True)
    host=a.host.resolve(strict=True) if a.host else None
    evidence=a.evidence_directory.resolve();evidence.mkdir(parents=True,exist_ok=False)
    result={'result':'incomplete','experimental':True,'physical_validation':False,'cases':[],
            'scope':'Installed wheel outside checkout; inherited build dependencies, no clean/offline or physical claim'}
    def save():(evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-installed-core-plan-') as directory:
        work=Path(directory);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        def run(command,expected=0,raw=None):
            r=subprocess.run([str(x) for x in command],cwd=work,env=env,input=raw,capture_output=True,timeout=60)
            if r.returncode!=expected:raise RuntimeError(f'{command}: {r.returncode} {r.stdout!r} {r.stderr!r}')
            return r.stdout
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        location=run([python,'-I','-c','import opensmell;print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv')
        cli=[python,'-I','-m','opensmell']
        profile=(root/'examples/offline_semantic_profile.json').read_bytes()
        (work/'profile.json').write_bytes(profile)
        (work/'target.json').write_text(json.dumps(json.loads(profile)['capabilities']))
        original=(root/'examples/geraniol.osmell').read_bytes()
        obj=json.loads(original)
        semantic=obj['odor']['representations'][1]
        semantic['provenance']={'source':'Synthetic caller data for software interoperability; not a measured observation'}
        semantic['data']['annotations']=[{'value':'green&herbal','language':'en','state':'present'},
                                        {'value':'floral','language':'en','state':'unknown'}]
        obj['odor']['representations']=[semantic,{'type':'semantic','scheme':{'id':'caller.future','version':'9'},
                                                 'data':{'opaque':[None,2**65]}}]
        obj['caller_note']='Declared semantic-only caller fixture; no chemical identity inferred'
        custom=json.dumps(obj,indent=3).replace('\n','\r\n').encode()+b'\r\n'
        plans=[]
        for i,(raw,index) in enumerate(((original,1),(custom,0))):
            source=work/f'core-{i}.osmell';source.write_bytes(raw)
            output=work/f'plan-{i}.json'
            cmd=[*cli,'plan-core',source,'--representation-index',str(index),'--profile','profile.json','--duration','.1','--output',output]
            run(cmd);artifact=json.loads(output.read_bytes())
            snapshot=artifact['source']['document']['org.opensmell.experimental.core-semantic-selection']['source']
            assert base64.b64decode(snapshot['data'])==raw and snapshot['sha256']==hashlib.sha256(raw).hexdigest()
            assert artifact['plan']['commands']==[{'channel':i,'intensity':.25 if i==0 else .6}]
            before=output.read_bytes();run(cmd,expected=2);assert output.read_bytes()==before
            (evidence/f'core-{i}.osmell').write_bytes(raw)
            shutil.copyfile(output,evidence/f'plan-{i}.json');plans.append(output)
            source.unlink()
        (work/'profile.json').unlink()
        # All original preparation paths are gone: existing frame entry recomputes from snapshots.
        for path in plans:
            frame=json.loads(run([*cli,'encode-frame',path,'--capabilities','target.json']))
            assert frame['transport']=='not_opened'
            (evidence/(path.stem+'-frame.json')).write_text(json.dumps(frame,indent=2))
        endpoints=[('python',[str(python),'-I','-u',str(work/'device.py')],'opensmell-local-simulator-001'),
                   ('node',['node',str(work/'device.cjs')],'opensmell-node-simulator-001')]
        shutil.copyfile(root/'examples/lifecycle_adapter/python_device.py',work/'device.py')
        shutil.copyfile(root/'examples/lifecycle_adapter/device.cjs',work/'device.cjs')
        if host:endpoints.append(('native',[str(host),'--realtime'],'opensmell-esp32-lifecycle-led-001'))
        for label,command,identity in endpoints:
            receipt=json.loads(run([*cli,'run-sequence',*plans,'--software-command-json',json.dumps(command),
                                   '--expected-device-id',identity,'--output',work/f'{label}.json']))
            assert receipt['status']=='completed'
            assert [s['state'] for s in receipt['sequence']['steps']]==['completed','completed']
            (evidence/f'{label}-receipt.json').write_text(json.dumps(receipt,indent=2))
            result['cases'].append({'endpoint':label,'states':['completed','completed'],'selected_channels':[0,1]});save()
        # Make plan and edited graph agree: only Core-source recomputation detects this stale projection.
        tampered=json.loads(plans[0].read_bytes())
        tampered['source']['document']['resources'][1]['data']['annotations']=[{'value':'green&herbal','language':'en','state':'present'}]
        tampered['plan']['commands']=[{'channel':1,'intensity':.6}]
        changed=work/'stale.json';changed.write_text(json.dumps(tampered))
        flag=work/'must-not-launch'
        command=[str(python),'-c',f"from pathlib import Path;Path({str(flag)!r}).write_text('launched')"]
        refusal=json.loads(run([*cli,'run-sequence',changed,'--software-command-json',json.dumps(command),
                               '--expected-device-id','opensmell-local-simulator-001','--output',work/'refused.json'],expected=1))
        assert refusal['status']=='invalid' and not flag.exists() and not refusal['transcript']
        (evidence/'stale-refusal.json').write_text(json.dumps(refusal,indent=2))
        # Unsupported selection must not choose a different known representation.
        (work/'custom.osmell').write_bytes(custom);(work/'profile.json').write_bytes(profile)
        run([*cli,'plan-core','custom.osmell','--representation-index','1','--profile','profile.json','--duration','.1','--output',work/'must-not-exist'],expected=1)
        assert not (work/'must-not-exist').exists()
        result.update(result='passed',exact_core_preserved=True,original_inputs_deleted=True,
                      stale_projection_no_child=True,unknown_selection_no_output=True,collision_refused=True)
        save();print(json.dumps(result))


if __name__=='__main__':main()
