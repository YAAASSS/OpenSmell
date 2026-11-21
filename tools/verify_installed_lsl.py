"""Actual optional LSL receiver against copied installed-SDK software bridge."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
import venv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('wheel',type=Path);p.add_argument('--evidence-directory',type=Path,required=True)
    p.add_argument('--dependency-directory',type=Path,required=True,help='Explicit local pylsl1.18.7/NumPy2.2.6 wheel directory')
    a=p.parse_args();wheel=a.wheel.resolve(strict=True);root=Path(__file__).resolve().parents[1]
    evidence=a.evidence_directory.resolve();evidence.mkdir(parents=True,exist_ok=False)
    result={'result':'incomplete','physical_validation':False,'cases':[],
            'scope':'Actual pylsl optional runtime; inherited build dependencies; no clean/offline or outside-adoption claim'}
    def save():(evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-installed-lsl-') as directory:
        work=Path(directory);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        def run(cmd,expected=0):
            r=subprocess.run([str(x) for x in cmd],cwd=work,env=env,capture_output=True,timeout=60)
            if r.returncode!=expected:raise RuntimeError(f'{cmd}: {r.returncode} {r.stdout!r} {r.stderr!r}')
            return r.stdout
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        run([python,'-m','pip','install','--no-index','--find-links',a.dependency_directory.resolve(),'--ignore-installed','pylsl==1.18.7','numpy==2.2.6'])
        location=run([python,'-I','-c','import opensmell;print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv')
        result['runtime']=json.loads(run([python,'-I','-c','import pylsl,json;print(json.dumps({"pylsl":pylsl.__version__,"liblsl":pylsl.library_info()}))']))
        assert result['runtime']['pylsl']=='1.18.7'
        for name in ('bridge.py','receive.py'):shutil.copyfile(root/'examples/lsl_markers'/name,work/name)
        for name,source in [('device.py','python_device.py'),('device.cjs','device.cjs')]:
            shutil.copyfile(root/'examples/lifecycle_adapter'/source,work/name)
        # A separate trusted fault endpoint retains actual SDK protocol semantics.
        (work/'fault.py').write_text('''import json,sys
from opensmell.experimental.lifecycle_simulator import SimulatedEndpoint
from opensmell.experimental.device_protocol import error_response
endpoint=SimulatedEndpoint(); mode=sys.argv[1]
for line in sys.stdin:
 request=json.loads(line)
 if request['type']=='render':
  if mode=='unknown':break
  if mode=='rejected':print(json.dumps(error_response('busy','Explicit software refusal')),flush=True);continue
 print(endpoint.exchange(line),flush=True)
''')
        source=work/'source.osmell';shutil.copyfile(root/'examples/multisource_diphenyl_ether.osmell',source)
        profile=work/'profile.json';shutil.copyfile(root/'examples/offline_perceptual_profile.json',profile)
        rid='219ef28c-9b58-52f2-93a7-0807f5897857'
        for duration in ('.1','5'):
            table=work/f'table-{duration}.csv';table.write_text(f'trial_id,resource_id,duration\ncaller-first,{rid},{duration}\ncaller-second,{rid},.1\n')
            run([python,'-I','-m','opensmell','prepare-experiment',table,'--graph',source,'--profile',profile,'--output-directory',work/f'prepared-{duration}'])
        for label,command,identity,expected,extra in (
            ('python',[str(python),'-I','-u',str(work/'device.py')],'opensmell-local-simulator-001','completed',[]),
            ('node',['node',str(work/'device.cjs')],'opensmell-node-simulator-001','completed',[]),
            ('stop-python',[str(python),'-I','-u',str(work/'device.py')],'opensmell-local-simulator-001','stopped',['--stop-after-first-acceptance']),
            ('stop-node',['node',str(work/'device.cjs')],'opensmell-node-simulator-001','stopped',['--stop-after-first-acceptance']),
            ('rejected',[str(python),'-I','-u',str(work/'fault.py'),'rejected'],'opensmell-local-simulator-001','rejected',[]),
            ('unknown',[str(python),'-I','-u',str(work/'fault.py'),'unknown'],'opensmell-local-simulator-001','unknown',[])):
            source_id='opensmell-proof-'+uuid.uuid4().hex
            receiver_out=evidence/f'{label}-receiver.json';sender_out=evidence/f'{label}-sender.json'
            receiver=subprocess.Popen([str(python),'-I',str(work/'receive.py'),'--source-id',source_id,'--output',str(receiver_out)],cwd=work,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                prepared=work/('prepared-5' if extra else 'prepared-.1')
                cmd=[python,'-I',work/'bridge.py',prepared/'plan-001.json',prepared/'plan-002.json','--software-command-json',json.dumps(command),
                     '--expected-device-id',identity,'--source-id',source_id,'--output',sender_out,*extra]
                run(cmd,0 if expected=='completed' else 3)
                stdout,stderr=receiver.communicate(timeout=15)
                if receiver.returncode!=0:raise RuntimeError(f'Receiver failed: {stdout!r} {stderr!r}')
            finally:
                if receiver.poll() is None:receiver.kill();receiver.communicate()
            sent=json.loads(sender_out.read_bytes());received=json.loads(receiver_out.read_bytes())
            assert sent['status']==expected and received['run_status']==expected and received['status']=='received'
            assert [x['marker'] for x in sent['events']]==[x['marker'] for x in received['samples']]
            assert [x['outlet_timestamp'] for x in sent['events']]==[x['lsl_timestamp'] for x in received['samples']]
            states=[s['state'] for s in sent['sequence']['steps']]
            assert states==(['completed','completed'] if expected=='completed' else [expected,'not_attempted'])
            assert [s['step_id'] for s in sent['sequence']['steps']]==['caller-first','caller-second']
            assert all(not x['marker']['physical_validation'] for x in received['samples'])
            result['cases'].append({'name':label,'states':states,'markers_received':len(received['samples'])});save()
        # Missing receiver and existing evidence must fail before launching a child.
        flag=work/'child-must-not-launch'
        guarded=[str(python),'-c',f"from pathlib import Path;Path({str(flag)!r}).write_text('launched')"]
        prepared=work/'prepared-.1'
        absent=evidence/'no-consumer.json'
        args=[python,'-I',work/'bridge.py',prepared/'plan-001.json','--software-command-json',json.dumps(guarded),
              '--expected-device-id','opensmell-local-simulator-001','--source-id','absent-'+uuid.uuid4().hex,'--output',absent]
        run(args,expected=1)
        assert not flag.exists() and json.loads(absent.read_bytes())['sequence'] is None
        original=absent.read_bytes();run(args,expected=1)
        assert absent.read_bytes()==original and not flag.exists()
        result['no_consumer_no_child']=True;result['collision_no_child']=True
        result['result']='passed';save();print(json.dumps(result))


if __name__=='__main__':main()
