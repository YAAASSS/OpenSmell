"""Installed synthetic import -> selected Core export/recovery -> plans -> software."""
import argparse
import base64
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import venv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('wheel',type=Path);p.add_argument('--host',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();wheel=a.wheel.resolve(strict=True);host=a.host.resolve(strict=True) if a.host else None
    output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    result={'result':'incomplete','physical_validation':False,'source_kind':'declared synthetic CSV','cases':[]}
    def save():(output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-installed-observation-core-') as tmp:
        work=Path(tmp);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        def run(cmd,code=0):
            r=subprocess.run(list(map(str,cmd)),cwd=work,env=env,capture_output=True,timeout=60)
            assert r.returncode==code,(cmd,r.returncode,r.stdout[-1000:],r.stderr[-1000:])
            return r.stdout
        cli=[python,'-I','-m','opensmell']
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        location=run([python,'-I','-c','import opensmell;print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv');result['installed_outside_checkout']=True
        result['dependency_scope']='Inherited build dependencies, not clean offline closure or independent adoption'
        table=work/'caller.csv';table.write_bytes((root/'examples/synthetic_keller.csv').read_bytes())
        source=work/'source.json';source.write_bytes((root/'examples/synthetic_keller_source.json').read_bytes())
        plans=[];profiles=[];cores=[];observations=[]
        for index in (1,2,3):
            graph=work/f'graph-{index}.osmell'
            run([*cli,'import-keller',table,'--source',source,'--row',index,'--output',graph])
            doc=json.loads(graph.read_bytes());obs=next(r for r in doc['resources'] if r['type']=='observation')
            # Opaque context remains outside the selected projection but recoverable.
            doc['org.example.future']={'opaque':[None,2**70], 'scope':'Declared synthetic fixture; not an observed outcome of this run'}
            raw=(json.dumps(doc,indent=3)+'\r\n').encode();graph.write_bytes(raw)
            core=work/f'core-{index}.osmell'
            selected_index=next((i for i,r in enumerate(obs['results']) if r['scheme']['id']=='org.opensmell.perceptual.measurements' and r['scheme']['version']=='0.1'),0)
            cmd=[*cli,'export-observation-core',graph,'--observation-id',obs['id'],'--result-index',str(selected_index),
                 '--odor-id',f'urn:caller:synthetic:odor-{index}','--output',core]
            if index==3:
                run(cmd,1);assert not core.exists();graph.unlink();continue
            run(cmd);before=core.read_bytes();run(cmd,2);assert core.read_bytes()==before
            parsed=json.loads(before);rep=parsed['odor']['representations'][0]
            assert rep['type']=='perceptual' and rep['data']==obs['results'][selected_index]['data']
            assert len(parsed['odor']['representations'])==1 and parsed['odor']['id']==f'urn:caller:synthetic:odor-{index}'
            recovered=work/f'recovered-{index}.osmell'
            run([*cli,'extract-observation-source',core,'--output',recovered]);assert recovered.read_bytes()==raw
            run([*cli,'extract-observation-source',core,'--output',recovered],2)
            profile=json.loads((root/'examples/offline_perceptual_profile.json').read_bytes())
            # Explicit caller policy for known supplied scales/units. No automatic
            # production mapper selection or unit conversion is being exercised.
            if index==2:profile['bindings']=profile['bindings'][:2]
            bound={b['property'] for b in profile['bindings']}
            profile['org.opensmell.experimental.core-perceptual-policy']={'version':'0.1','normalization':'value-minus-min-over-range',
                'measurements':[{k:deepcopy(v) for k,v in m.items() if k in {'property','unit','scale'}}
                                for m in rep['data']['measurements'] if m['property'] in bound]}
            path=work/f'profile-{index}.json';path.write_text(json.dumps(profile));profiles.append(path)
            plan=work/f'plan-{index}.json';run([*cli,'plan-core',core,'--representation-index','0','--profile',path,'--duration','.1','--output',plan])
            assert [c['intensity'] for c in json.loads(plan.read_bytes())['plan']['commands']]==([.26,0,.89] if index==1 else [.8,.2])
            shutil.copyfile(core,output/core.name);shutil.copyfile(plan,output/plan.name)
            plans.append(plan);cores.append(core);observations.append((obs['id'],raw))
            graph.unlink();recovered.unlink()
        table.unlink();source.unlink()
        for path in [*profiles,*cores]:path.unlink()
        target=work/'target.json';target.write_text(json.dumps(json.loads((root/'examples/offline_perceptual_profile.json').read_bytes())['capabilities']))
        for plan in plans:
            frame=json.loads(run([*cli,'encode-frame',plan,'--capabilities',target]));assert frame['transport']=='not_opened'
            (output/(plan.stem+'-frame.json')).write_text(json.dumps(frame,indent=2))
        shutil.copyfile(root/'examples/lifecycle_adapter/python_device.py',work/'device.py')
        shutil.copyfile(root/'examples/lifecycle_adapter/device.cjs',work/'device.cjs')
        endpoints=[('python',[str(python),'-I',str(work/'device.py')],'opensmell-local-simulator-001'),
                   ('node',['node',str(work/'device.cjs')],'opensmell-node-simulator-001')]
        if host:endpoints.append(('native',[str(host),'--realtime'],'opensmell-esp32-lifecycle-led-001'))
        for name,command,identity in endpoints:
            receipt=output/(name+'-receipt.json')
            r=json.loads(run([*cli,'run-sequence',*plans,'--software-command-json',json.dumps(command),'--expected-device-id',identity,'--output',receipt]))
            assert r['status']=='completed' and [s['state'] for s in r['sequence']['steps']]==['completed','completed']
            result['cases'].append({'endpoint':name,'states':['completed','completed']});save()
        # Alter exported Core while retaining the original graph snapshot.
        exported=json.loads((output/'core-1.osmell').read_bytes())
        exported['odor']['representations'][0]['data']['measurements'][0]['value']=100
        changed=work/'stale.osmell';changed.write_text(json.dumps(exported))
        run([*cli,'extract-observation-source',changed,'--output',work/'bad-recovery'],1)
        assert not (work/'bad-recovery').exists()
        # Test the normal downstream boundary, even if the nested Core and outer
        # source snapshot are edited together. A process sentinel must not run.
        artifact=json.loads(plans[0].read_bytes())
        marker=artifact['source']['document']['org.opensmell.experimental.core-perceptual-selection']['source']
        bad=changed.read_bytes();import hashlib
        marker.update(data=base64.b64encode(bad).decode(),sha256=hashlib.sha256(bad).hexdigest(),byte_count=len(bad))
        stale=work/'stale-plan.json';stale.write_text(json.dumps(artifact))
        flag=work/'must-not-launch';command=[str(python),'-c',f"from pathlib import Path;Path({str(flag)!r}).write_text('launched')"]
        refused=json.loads(run([*cli,'run-sequence',stale,'--software-command-json',json.dumps(command),
                               '--expected-device-id','opensmell-local-simulator-001','--output',output/'stale-refusal.json'],1))
        assert refused['status']=='invalid' and not flag.exists() and not refused['transcript']
        result.update(result='passed',exact_graph_recovered=True,selected_data_unchanged=True,
             unmeasured_refused_without_output=True,stale_source_refused_before_process=True,
             collision_preserved=True,original_preparation_paths_removed=True)
        save()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
