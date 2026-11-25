"""Installed quantitative Core -> explicit policy -> frame -> Python/Node/native."""
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel',type=Path);parser.add_argument('--host',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();wheel=args.wheel.resolve(strict=True)
    host=args.host.resolve(strict=True) if args.host else None
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    result={'result':'incomplete','physical_validation':False,'source_kind':'declared synthetic Core','cases':[]}
    def save():(output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-installed-core-perceptual-') as tmp:
        work=Path(tmp);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        def run(command,code=0):
            r=subprocess.run(list(map(str,command)),cwd=work,env=env,capture_output=True,timeout=60)
            assert r.returncode==code,(command,r.returncode,r.stdout[-1000:],r.stderr[-1000:])
            return r.stdout
        cli=[python,'-I','-m','opensmell']
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        location=run([python,'-I','-c','import opensmell;print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv');result['installed_outside_checkout']=True
        result['dependency_scope']='Installed wheel with inherited build dependencies; no clean offline or physical proof'
        raw=(root/'examples/core_perceptual_only.osmell').read_bytes().replace(b'\n',b'\r\n')
        profile=(root/'examples/offline_core_perceptual_profile.json').read_bytes()
        source=work/'caller.osmell';source.write_bytes(raw)
        supplied=work/'profile.json';supplied.write_bytes(profile)
        target=work/'target.json';target.write_text(json.dumps(json.loads(profile)['capabilities']))
        plans=[]
        for index in (0,1):
            path=work/f'plan-{index}.json'
            cmd=[*cli,'plan-core',source,'--representation-index',str(index),'--profile',supplied,'--duration','.1','--output',path]
            run(cmd);artifact=json.loads(path.read_bytes());doc=artifact['source']['document']
            assert len(doc['resources'])==1 and doc['resources'][0]['type']=='org.opensmell.experimental.core-perceptual-representation'
            snapshot=doc['org.opensmell.experimental.core-perceptual-selection']['source']
            assert base64.b64decode(snapshot['data'])==raw and snapshot['sha256']==hashlib.sha256(raw).hexdigest()
            assert [c['intensity'] for c in artifact['plan']['commands']]==[.25 if index==0 else .75,.5,1]
            before=path.read_bytes();run(cmd,2);assert path.read_bytes()==before
            shutil.copyfile(path,output/path.name);plans.append(path)
        # Wrong unit, scale, policy and unknown index must refuse before output.
        policy='org.opensmell.experimental.core-perceptual-policy'
        for kind in ('unit','scale','normalization','missing-policy','unknown-index'):
            p=json.loads(profile);index=0
            if kind=='unit':p[policy]['measurements'][0]['unit']='percent'
            if kind=='scale':p[policy]['measurements'][0]['scale']['max']=100
            if kind=='normalization':p[policy]['normalization']='guess'
            if kind=='missing-policy':p.pop(policy)
            if kind=='unknown-index':index=2
            bad_profile=work/(kind+'.json');bad_profile.write_text(json.dumps(p))
            absent=work/(kind+'-must-not-exist')
            run([*cli,'plan-core',source,'--representation-index',str(index),'--profile',bad_profile,'--duration','.1','--output',absent],1)
            assert not absent.exists()
        source.unlink();supplied.unlink()
        for path in plans:
            frame=json.loads(run([*cli,'encode-frame',path,'--capabilities',target]))
            assert frame['transport']=='not_opened'
            (output/(path.stem+'-frame.json')).write_text(json.dumps(frame,indent=2))
        shutil.copyfile(root/'examples/lifecycle_adapter/python_device.py',work/'device.py')
        shutil.copyfile(root/'examples/lifecycle_adapter/device.cjs',work/'device.cjs')
        endpoints=[('python',[str(python),'-I',str(work/'device.py')],'opensmell-local-simulator-001'),
                   ('node',['node',str(work/'device.cjs')],'opensmell-node-simulator-001')]
        if host:endpoints.append(('native',[str(host),'--realtime'],'opensmell-esp32-lifecycle-led-001'))
        for name,command,identity in endpoints:
            receipt=output/(name+'-receipt.json')
            report=json.loads(run([*cli,'run-sequence',*plans,'--software-command-json',json.dumps(command),
                                  '--expected-device-id',identity,'--output',receipt]))
            assert report['status']=='completed' and [s['state'] for s in report['sequence']['steps']]==['completed','completed']
            assert [[c['intensity'] for c in s['plan']['commands']] for s in report['sequence']['steps']]==[[.25,.5,1],[.75,.5,1]]
            result['cases'].append({'endpoint':name,'states':['completed','completed']});save()
        # A matching edited graph/plan cannot replace the original retained Core.
        changed=json.loads(plans[0].read_bytes());changed['source']['document']['resources'][0]['data']['measurements'][0]['value']=7.5
        changed['plan']['commands'][0]['intensity']=.75
        stale=work/'stale.json';stale.write_text(json.dumps(changed))
        flag=work/'must-not-launch';command=[str(python),'-c',f"from pathlib import Path;Path({str(flag)!r}).write_text('launched')"]
        refusal=json.loads(run([*cli,'run-sequence',stale,'--software-command-json',json.dumps(command),
                               '--expected-device-id','opensmell-local-simulator-001','--output',output/'stale-refusal.json'],1))
        assert refusal['status']=='invalid' and not flag.exists() and refusal['transcript']==[]
        result.update(result='passed',exact_core_preserved=True,original_preparation_paths_deleted=True,
                      no_invented_observation=True,explicit_unit_scale_policy_refusals=True,
                      stale_projection_no_process=True,collision_preserved=True)
        save()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
