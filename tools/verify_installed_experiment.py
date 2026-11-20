"""Outside-checkout caller table -> portable passive plans -> software receipts."""
import argparse
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
    a=p.parse_args();root=Path(__file__).resolve().parents[1];wheel=a.wheel.resolve(strict=True)
    evidence=a.evidence_directory.resolve();evidence.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='opensmell-installed-experiment-') as directory:
        work=Path(directory);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        def run(command, expected=0):
            r=subprocess.run([str(x) for x in command],cwd=work,env=env,capture_output=True,timeout=60)
            if r.returncode!=expected:raise RuntimeError(f'{command}: {r.returncode} {r.stdout!r} {r.stderr!r}')
            return r.stdout
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        location=run([python,'-I','-c','import opensmell;print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv')
        cli=[python,'-I','-m','opensmell']
        # Caller changes source extensions, profile and row order; not a fixed self-test.
        graph=json.loads((root/'examples/multisource_diphenyl_ether.osmell').read_bytes())
        graph['caller_opaque']={'retain':[None,2**65]}
        profile=json.loads((root/'examples/offline_perceptual_profile.json').read_bytes())
        # Select a different resource by making a declared synthetic second observation.
        rid='219ef28c-9b58-52f2-93a7-0807f5897857'
        second=json.loads(json.dumps(next(r for r in graph['resources'] if r['id']==rid)))
        second['id']='caller-second-observation';graph['resources'].append(second)
        raw=(json.dumps(graph,indent=3)+'\n').encode();(work/'caller.osmell').write_bytes(raw)
        (work/'profile.json').write_text(json.dumps(profile,indent=3))
        table=b'\xef\xbb\xbftrial_id,resource_id,duration,caller_note\r\nsecond,caller-second-observation,.2,"keep, this"\r\nfirst,'+rid.encode()+b',.1,explicit-order\r\n'
        (work/'caller.csv').write_bytes(table)
        cmd=[*cli,'prepare-experiment','caller.csv','--graph','caller.osmell','--profile','profile.json','--output-directory',work/'prepared']
        report=json.loads(run(cmd));assert report['status']=='prepared' and report['execution']=='not_attempted'
        bundle=work/'relocated';shutil.move(work/'prepared',bundle)
        # Remove preparation inputs: replay depends only on the retained dossier.
        for name in ('caller.csv','caller.osmell','profile.json'):(work/name).unlink()
        for name,entry in report['files'].items():
            data=(bundle/name).read_bytes();assert hashlib.sha256(data).hexdigest()==entry['sha256'] and len(data)==entry['byte_count']
        assert (bundle/'source.osmell').read_bytes()==raw and (bundle/'trials.csv').read_bytes()==table
        assert [r['trial_id'] for r in report['trials']]==['second','first']
        plans=[bundle/r['plan_file'] for r in report['trials']]
        cases=[]
        for label,source,command,identity in (
            ('python',root/'examples/lifecycle_adapter/python_device.py',[str(python),'-I','-u',str(work/'device.py')],'opensmell-local-simulator-001'),
            ('node',root/'examples/lifecycle_adapter/device.cjs',['node',str(work/'device.cjs')],'opensmell-node-simulator-001')):
            shutil.copyfile(source,work/('device.py' if label=='python' else 'device.cjs'))
            receipt=json.loads(run([*cli,'run-sequence',*plans,'--software-command-json',json.dumps(command),'--expected-device-id',identity,'--output',work/f'{label}-receipt.json']))
            assert receipt['status']=='completed'
            assert [s['plan']['duration'] for s in receipt['sequence']['steps']]==[.2,.1]
            assert [s['context']['request']['resource_id'] for s in receipt['sequence']['steps']]==['caller-second-observation',rid]
            (evidence/f'{label}-receipt.json').write_text(json.dumps(receipt,indent=2))
            cases.append({'endpoint':label,'status':'completed','trials':['second','first']})
        shutil.copytree(bundle,evidence/'prepared')
        # Invalid late selection refuses the whole protocol before any output.
        (work/'bad.csv').write_bytes(table+b'bad,missing,.1,refuse\r\n')
        refused=[*cli,'prepare-experiment',work/'bad.csv','--graph',bundle/'source.osmell','--profile',bundle/'profile.json','--output-directory',work/'must-not-exist']
        failure=json.loads(run(refused,expected=1));assert not (work/'must-not-exist').exists()
        (evidence/'refusal.json').write_text(json.dumps(failure,indent=2))
        # Reprepare from retained exact input, then refuse an output collision.
        cmd=[*cli,'prepare-experiment',bundle/'trials.csv','--graph',bundle/'source.osmell','--profile',bundle/'profile.json','--output-directory',work/'reproduced']
        again=json.loads(run(cmd));assert again==report
        assert all((work/'reproduced'/name).read_bytes()==(bundle/name).read_bytes() for name in report['files'])
        run(cmd,expected=2)
        result={'result':'passed','experimental':True,'physical_validation':False,'installed_outside_checkout':True,
                'cases':cases,'relocated_after_inputs_deleted':True,'exact_repreparation':True,'invalid_late_row_no_output':True,
                'collision_refused':True,'scope':'Inherited build dependencies; no clean/offline dependency claim or third-party adoption.'}
        (evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
