"""Installed synthetic trial/observation pipeline; analysis never starts a device."""
import argparse
import base64
import csv
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import venv


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();wheel=args.wheel.resolve(strict=True);output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parents[1]
    proof={'result':'incomplete','source_kind':'synthetic','physical_validation':False}
    def save():(output/'result.json').write_text(json.dumps(proof,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-installed-trial-analysis-') as tmp:
        work=Path(tmp);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        def run(command,code=0):
            r=subprocess.run(list(map(str,command)),cwd=work,env=env,capture_output=True,timeout=60)
            assert r.returncode==code,(command,r.returncode,r.stdout[-1000:],r.stderr[-1000:])
            return r.stdout
        def cli(*command,code=0):return run([python,'-I','-m','opensmell',*command],code)
        run([python,'-m','pip','install','--no-deps','--no-index','--ignore-installed',wheel])
        location=run([python,'-I','-c','import opensmell;print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv')
        proof['installed_outside_checkout']=True
        proof['dependency_scope']='Installed wheel with inherited build/Pandas dependencies, not clean offline closure'
        # Import explicitly synthetic source; do not invent or claim participant data.
        source=work/'source.json';source.write_bytes((root/'examples/synthetic_keller_source.json').read_bytes())
        original=work/'observations.csv';original.write_bytes((root/'examples/synthetic_keller.csv').read_bytes())
        parts=[];ids=[]
        for index in (1,2,3):
            path=work/f'part-{index}.osmell'
            cli('import-keller',original,'--source',source,'--row',index,'--output',path)
            part=json.loads(path.read_bytes());parts.append(part)
            ids.append(next(r['id'] for r in part['resources'] if r['type']=='observation'))
        graph=deepcopy(parts[0]);resources={}
        for part in parts:
            for resource in part['resources']:
                if resource['id'] in resources:assert resources[resource['id']]==resource
                resources[resource['id']]=resource
        graph['resources']=list(reversed(list(resources.values())))  # graph order must not determine trial order
        graph['org.example.synthetic-join-proof']={'parts':parts,'unknown':[None,2**70],
             'scope':'Synthetic declared source observations; not outcomes measured from the software run'}
        graph_raw=(json.dumps(graph,indent=3)+'\n').encode()
        observations=work/'observations.osmell';observations.write_bytes(graph_raw)
        profile=work/'profile.json';profile.write_bytes((root/'examples/offline_perceptual_profile.json').read_bytes())
        table=work/'trials.csv';table.write_text('trial_id,resource_id,duration,note\n'+''.join(
             f'{trial},{rid},{duration},{note}\n' for trial,rid,duration,note in
             [('trial-A',ids[0],.1,'caller-A'),('trial-B',ids[1],.2,'caller-B'),('trial-C',ids[0],.1,'caller-C')]))
        cli('prepare-experiment',table,'--graph',observations,'--profile',profile,'--output-directory',work/'original-dossier')
        moved=work/'relocated dossier';shutil.move(work/'original-dossier',moved)
        for path in [source,original,profile,table,*[work/f'part-{i}.osmell' for i in (1,2,3)]]:path.unlink()
        report=output/'completed-report.json'
        cli('run-experiment',moved,'--software-command-json',json.dumps([str(python),'-I','-m','opensmell','simulate-device']),
            '--expected-device-id','opensmell-local-simulator-001','--action','complete','--output',report)
        bindings=work/'bindings.csv';bindings.write_text('trial_id,observation_id,declared_context\n'+''.join(
             f'trial-{trial},{oid},explicit-synthetic-association\n' for trial,oid in zip('ABC',ids)))
        binding_raw=bindings.read_bytes()
        def analysis(name,receipt=report,code=0):
            cli('analyze-experiment',moved,'--report',receipt,'--observations',observations,'--bindings',bindings,
                '--output-directory',output/name,code=code)
            return json.loads((output/name/'analysis.json').read_bytes())
        joined=analysis('joined')
        assert joined['status']=='joined' and len(joined['tables']['measurements'])==6
        assert [t['trial_id'] for t in joined['tables']['trials']]==['trial-A','trial-B','trial-C']
        assert [t['measurement_count'] for t in joined['tables']['trials']]==[4,2,0]
        assert [r['ordinal'] for r in joined['tables']['measurements']]==[1]*4+[2]*2
        assert base64.b64decode(joined['inputs']['observations']['data'])==graph_raw
        assert base64.b64decode(joined['inputs']['bindings']['data'])==binding_raw
        assert base64.b64decode(joined['inputs']['execution_report']['data'])==report.read_bytes()
        assert not any(m['property']=='pleasantness' for m in joined['tables']['measurements'])
        assert next(m for m in joined['tables']['measurements'] if m['property']=='grass')['value']==0
        run([python,'-I','-c',"import pandas as p;d=p.read_csv(r'"+str(output/'joined/measurements.csv')+"',dtype='string',keep_default_na=False);assert list(d.trial_id.unique())==['trial-A','trial-B'];assert d.loc[d.property=='grass','value'].iloc[0]=='0'"])
        before=(output/'joined/analysis.json').read_bytes()
        cli('analyze-experiment',moved,'--report',report,'--observations',observations,'--bindings',bindings,'--output-directory',output/'joined',code=2)
        assert (output/'joined/analysis.json').read_bytes()==before
        # SDK-produced uncertain receipt, not a hand-edited successful report.
        consumer=work/'uncertain.py';consumer.write_text('''import json,sys
from opensmell.experimental.experiment_run import run_prepared_experiment
from opensmell.experimental.lifecycle_simulator import SimulatedEndpoint
class Lost:
 def __init__(self):self.t=SimulatedEndpoint();self.renders=0
 def exchange(self,line):
  req=json.loads(line);reply=self.t.exchange(line)
  if req['type']=='render':
   self.renders+=1
   if self.renders==2:raise OSError('Verifier injected lost reply after simulator acceptance')
  return reply
 def close(self):self.t.close()
r=run_prepared_experiment(sys.argv[1],Lost,expected_device_id='opensmell-local-simulator-001')
with open(sys.argv[2],'x') as out:json.dump(r,out)
''')
        uncertain=output/'uncertain-report.json';run([python,'-I',consumer,moved,uncertain])
        partial=analysis('uncertain',uncertain,3)
        assert [t['receipt_state'] for t in partial['tables']['trials']]==['completed','unknown','not_attempted']
        assert len(partial['tables']['measurements'])==6 and not partial['physical_validation']
        bindings.write_bytes(binding_raw+f'trial-B,{ids[0]},conflicting\n'.encode())
        ambiguous=analysis('ambiguous',code=3)
        assert any(i['code']=='ambiguous_observation_binding' for i in ambiguous['coverage']['issues'])
        assert all(m['trial_id']!='trial-A' for m in ambiguous['tables']['measurements'])
        bindings.write_bytes(binding_raw);bad=json.loads(report.read_bytes());bad['prepared_experiment']['trial_order'].reverse()
        stale=work/'stale.json';stale.write_text(json.dumps(bad))
        cli('analyze-experiment',moved,'--report',stale,'--observations',observations,'--bindings',bindings,'--output-directory',output/'stale',code=1)
        assert not (output/'stale').exists()
        proof.update(result='passed',measurement_counts=[4,2,0],pandas_consumer=True,
              ambiguous_without_double_count=True,uncertain_state_preserved=True,stale_before_output=True,
              collision_preserved=True,exact_inputs_preserved=True,execution='not_attempted_for_analysis')
        save()
    print(json.dumps(proof,indent=2))

if __name__=='__main__':main()
