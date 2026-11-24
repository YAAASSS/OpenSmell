"""Installed relocated dossier -> CLI -> actual native lifecycle sketch. Software only."""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import venv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('wheel',type=Path);p.add_argument('--host',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();wheel=a.wheel.resolve(strict=True);host=a.host.resolve(strict=True)
    output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    proof={'result':'incomplete','physical_validation':False,'cases':[]}
    def save():(output/'result.json').write_text(json.dumps(proof,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-installed-experiment-') as tmp:
        work=Path(tmp);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv/bin/python';env={k:v for k,v in os.environ.items() if k not in {'PYTHONHOME','PYTHONPATH'}}
        def run(args,code=0):
            r=subprocess.run(list(map(str,args)),cwd=work,env=env,capture_output=True,timeout=60)
            assert r.returncode==code,(args,r.returncode,r.stdout[-1500:],r.stderr[-1500:])
            return r.stdout
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        location=run([python,'-I','-c','import opensmell;print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv')
        proof['installed_outside_checkout']=True
        proof['dependency_scope']='Installed wheel with inherited build dependencies, not clean offline closure'
        graph=work/'caller.osmell';profile=work/'caller-profile.json';table=work/'caller.csv'
        graph.write_bytes((root/'examples/multisource_diphenyl_ether.osmell').read_bytes())
        profile.write_bytes((root/'examples/offline_perceptual_profile.json').read_bytes())
        table.write_text('trial_id,resource_id,duration,condition\n'+''.join(
            f'{name},219ef28c-9b58-52f2-93a7-0807f5897857,{duration},{note}\n'
            for name,duration,note in [('first',1,'opaque-A'),('second',.1,'opaque-B'),('third',.2,'opaque-C')]))
        run([python,'-I','-m','opensmell','prepare-experiment',table,'--graph',graph,'--profile',profile,'--output-directory',work/'original'])
        moved=work/'relocated dossier';shutil.move(work/'original',moved)
        for path in (graph,profile,table):path.unlink()
        manifest=(moved/'experiment.json').read_bytes()
        # Explicit trusted verifier wrapper injects faults; never selected from dossier.
        wrapper=work/'fault-wrapper.py'
        wrapper.write_text('''import json,os,sys
from opensmell.experimental.process_transport import ProcessTransport
t=ProcessTransport([sys.argv[1],"--realtime"],startup_timeout=5)
mode=sys.argv[2];count=0
try:
 for line in sys.stdin:
  req=json.loads(line)
  with open(sys.argv[3],'a') as log:log.write(json.dumps(req)+'\\n')
  if req['type']=='render':count+=1
  if count==2 and req['type']=='render' and mode=='refused':
   reply=json.dumps({'protocol_version':'0.1','type':'error','code':'busy','message':'Verifier injected refusal before native forwarding'})
  else:reply=t.exchange(line.rstrip('\\n'))
  if count==2 and req['type']=='render' and mode=='lost':break
  print(reply.rstrip("\\r\\n"),flush=True)
finally:t.close()
''')
        for mode,action,code,states in [('normal','complete',0,['completed']*3),('normal','stop-first',0,['stopped','not_attempted','not_attempted']),('lost','complete',1,['completed','unknown','not_attempted']),('refused','complete',3,['completed','rejected','not_attempted'])]:
            name=mode+'-'+action;log=output/(name+'-requests.jsonl');report=output/(name+'.json')
            cmd=[python,'-I','-m','opensmell','run-experiment',moved,'--software-command-json',json.dumps([str(python),'-I',str(wrapper),str(host),mode,str(log)]),'--expected-device-id','opensmell-esp32-lifecycle-led-001','--action',action,'--output',report]
            result=json.loads(run(cmd,code));steps=result['sequence']['steps']
            assert [s['state'] for s in steps]==states,result
            assert [s['trial_id'] for s in steps]==['first','second','third']
            assert base64.b64decode(result['prepared_experiment']['manifest']['data'])==manifest
            for step in steps:
                raw=base64.b64decode(step['context']['input']['data']);obj=json.loads(raw)
                assert obj['org.opensmell.experimental.trial']['record']['trial_id']==step['trial_id']
            before=report.read_bytes();traffic=log.read_bytes();run(cmd,2)
            assert report.read_bytes()==before and log.read_bytes()==traffic
            proof['cases'].append({'name':name,'states':states,'collision_no_traffic':True});save()
        # Hash-consistent corrupted trial binding still refuses before process launch.
        bad=json.loads((moved/'plan-003.json').read_bytes());bad['org.opensmell.experimental.trial']['record']['condition']='tampered'
        raw=json.dumps(bad).encode();(moved/'plan-003.json').write_bytes(raw)
        import hashlib
        m=json.loads(manifest);m['files']['plan-003.json']={'sha256':hashlib.sha256(raw).hexdigest(),'byte_count':len(raw)}
        (moved/'experiment.json').write_text(json.dumps(m))
        log=output/'invalid-requests.jsonl'
        run([python,'-I','-m','opensmell','run-experiment',moved,'--software-command-json',json.dumps([str(python),'-I',str(wrapper),str(host),'normal',str(log)]),'--expected-device-id','opensmell-esp32-lifecycle-led-001','--action','complete','--output',output/'invalid.json'],1)
        assert not log.exists()
        proof['tampered_binding_no_process']=True;proof['result']='passed';save()
    print(json.dumps(proof,indent=2))

if __name__=='__main__':main()
