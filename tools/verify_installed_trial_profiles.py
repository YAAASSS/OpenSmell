"""Installed explicit trial profiles -> relocated dossier -> Python/Node/native software receipts."""
import argparse
import base64
from copy import deepcopy
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
    p.add_argument('wheel',type=Path);p.add_argument('--host',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();wheel=a.wheel.resolve(strict=True);host=a.host.resolve(strict=True) if a.host else None
    output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    result={'result':'incomplete','physical_validation':False,'cases':[]}
    def save():(output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-trial-profiles-') as tmp:
        work=Path(tmp);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        def run(cmd,code=0):
            r=subprocess.run(list(map(str,cmd)),cwd=work,env=env,capture_output=True,timeout=90)
            assert r.returncode==code,(cmd,r.returncode,r.stdout[-1000:],r.stderr[-1000:])
            return r.stdout
        cli=[python,'-I','-m','opensmell']
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        location=run([python,'-I','-c','import opensmell;print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv')
        table=work/'source.csv';source=work/'source.json';graph=work/'graph.osmell'
        table.write_bytes((root/'examples/synthetic_keller.csv').read_bytes());source.write_bytes((root/'examples/synthetic_keller_source.json').read_bytes())
        run([*cli,'import-keller-cohort',table,'--source',source,'--rows','1','2','--output',graph])
        ids=[r['observation_id'] for r in json.loads(graph.read_bytes())['org.opensmell.experimental.perceptual-csv-cohort']['results']]
        profile=json.loads((root/'examples/offline_perceptual_profile.json').read_bytes())
        profile['future']={'opaque':[2**70,None]}
        other=deepcopy(profile);other['bindings']=other['bindings'][:2]
        other['bindings'][0]['channel']=1;other['bindings'][1]['channel']=0
        bundle={'format':'org.opensmell.experimental.trial-profiles','version':'0.1',
                'profiles':{'first':profile,'second':other,'third':profile},'future':'retained'}
        profiles=work/'policies.json';profiles.write_text(json.dumps(bundle,indent=3)+'\n');policy_raw=profiles.read_bytes()
        trials=work/'trials.csv';trials.write_text('trial_id,resource_id,duration,note\n'+
            f'first,{ids[0]},1,explicit-policy-A\nsecond,{ids[1]},.1,explicit-policy-B\nthird,{ids[0]},.2,tail-not-retried\n')
        prep=[*cli,'prepare-experiment',trials,'--graph',graph,'--trial-profiles',profiles]
        run([*prep,'--output-directory',work/'original']);run([*prep,'--output-directory',work/'original'],2)
        bad=deepcopy(bundle);del bad['profiles']['second'];profiles.write_text(json.dumps(bad))
        run([*prep,'--output-directory',work/'must-not-exist'],1);assert not (work/'must-not-exist').exists()
        moved=work/'relocated dossier';shutil.move(work/'original',moved)
        for path in (table,source,graph,profiles,trials):path.unlink()
        manifest=(moved/'experiment.json').read_bytes();assert json.loads(manifest)['version']=='0.2'
        expected=[{0:.26,1:0,2:.89},{0:.2,1:.8},{0:.26,1:0,2:.89}]
        for i,values in enumerate(expected,1):
            plan=json.loads((moved/f'plan-{i:03d}.json').read_bytes())
            assert {c['channel']:c['intensity'] for c in plan['plan']['commands']}==values
        shutil.copyfile(root/'examples/lifecycle_adapter/python_device.py',work/'device.py')
        shutil.copyfile(root/'examples/lifecycle_adapter/device.cjs',work/'device.cjs')
        wrapper=work/'wrapper.py'
        wrapper.write_text('''import json,sys
from opensmell.experimental.process_transport import ProcessTransport
t=ProcessTransport(json.loads(sys.argv[1]),startup_timeout=5);count=0
try:
 for line in sys.stdin:
  req=json.loads(line)
  with open(sys.argv[3],'a') as f:f.write(json.dumps(req)+'\\n')
  if req['type']=='render':count+=1
  if count==2 and req['type']=='render' and sys.argv[2]=='refused':
   reply=json.dumps({'protocol_version':'0.1','type':'error','code':'busy','message':'Explicit verifier refusal'})
  else:reply=t.exchange(line.rstrip('\\n'))
  if count==2 and req['type']=='render' and sys.argv[2]=='lost':break
  print(reply.rstrip('\\r\\n'),flush=True)
finally:t.close()
''')
        endpoints=[('python',[str(python),'-I',str(work/'device.py')],'opensmell-local-simulator-001'),
                   ('node',['node',str(work/'device.cjs')],'opensmell-node-simulator-001')]
        if host:endpoints.append(('native',[str(host),'--realtime'],'opensmell-esp32-lifecycle-led-001'))
        for name,command,identity in endpoints:
            for mode,action,code,states in [('normal','complete',0,['completed']*3),('normal','stop-first',0,['stopped','not_attempted','not_attempted']),('lost','complete',1,['completed','unknown','not_attempted']),('refused','complete',3,['completed','rejected','not_attempted'])]:
                case=name+'-'+mode+'-'+action;log=output/(case+'-requests.jsonl');receipt=output/(case+'.json')
                cmd=[*cli,'run-experiment',moved,'--software-command-json',json.dumps([str(python),'-I',str(wrapper),json.dumps(command),mode,str(log)]),
                     '--expected-device-id',identity,'--action',action,'--output',receipt]
                report=json.loads(run(cmd,code));assert [s['state'] for s in report['sequence']['steps']]==states
                assert [s['trial_id'] for s in report['sequence']['steps']]==['first','second','third']
                assert base64.b64decode(report['prepared_experiment']['retained_inputs']['profiles.json']['data'])==policy_raw
                if action=='complete' and mode=='normal':
                    renders=[json.loads(l) for l in log.read_text().splitlines() if json.loads(l)['type']=='render']
                    assert len(renders)==3
                    assert [{c['channel']:c['intensity'] for c in r['commands']} for r in renders]==expected
                before=receipt.read_bytes();traffic=log.read_bytes();run(cmd,2);assert receipt.read_bytes()==before and log.read_bytes()==traffic
                result['cases'].append({'case':case,'states':states});save()
        # Hash-consistent policy edit still contradicts retained plans before IO.
        altered=json.loads(policy_raw);altered['profiles']['second']['bindings'][0]['channel']=2
        raw=json.dumps(altered).encode();(moved/'profiles.json').write_bytes(raw)
        m=json.loads(manifest);m['files']['profiles.json']={'sha256':hashlib.sha256(raw).hexdigest(),'byte_count':len(raw)}
        (moved/'experiment.json').write_text(json.dumps(m));flag=work/'must-not-launch'
        command=[str(python),'-c',f"from pathlib import Path;Path({str(flag)!r}).touch()"]
        report=json.loads(run([*cli,'run-experiment',moved,'--software-command-json',json.dumps(command),
            '--expected-device-id','opensmell-local-simulator-001','--action','complete','--output',output/'stale.json'],1))
        assert not flag.exists() and not report['transcript']
        result.update(result='passed',installed_outside_checkout=True,originals_removed=True,invalid_last_policy_no_output=True,
                      stale_policy_no_process=True,collision_no_traffic=True,dependency_scope='Inherited Python build dependencies; not clean closure or third-party adoption')
        save()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
