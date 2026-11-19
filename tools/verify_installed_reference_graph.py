"""Fresh installed CLI -> GraphML -> independent NetworkX consumer, no device."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import venv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('wheel',type=Path);p.add_argument('--networkx-wheel',type=Path)
    p.add_argument('--evidence-directory',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1];wheel=a.wheel.resolve(strict=True)
    evidence=a.evidence_directory.resolve();evidence.mkdir(parents=True,exist_ok=False)
    summary={'status':'incomplete','physical_validation':False,'cases':[]}
    def save():(evidence/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    save()
    try:
        with tempfile.TemporaryDirectory(prefix='opensmell-graphml-installed-') as name:
            work=Path(name);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
            python=work/'venv/bin/python';env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
            def run(command,expected=0):
                r=subprocess.run([str(x) for x in command],cwd=work,env=env,capture_output=True,timeout=60)
                if r.returncode!=expected:raise RuntimeError(f'{command}: {r.returncode} {r.stdout!r} {r.stderr!r}')
                return r.stdout
            run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
            if a.networkx_wheel:run([python,'-m','pip','install','--no-index','--no-deps',a.networkx_wheel.resolve(strict=True)])
            location=run([python,'-I','-c','import opensmell,networkx;print(opensmell.__file__);print(networkx.__version__)']).decode()
            assert str(work/'venv') in location;summary['runtime']=location
            summary['dependency_scope']='SDK wheel installed outside checkout; host dependencies inherited or explicitly supplied NetworkX wheel, not a clean offline closure proof'
            shutil.copyfile(root/'examples/networkx_graph/inspect_bundle.py',work/'inspect_bundle.py')
            original=(root/'examples/multisource_diphenyl_ether.osmell').read_bytes()
            variant=json.loads(original);observation=next(r for r in variant['resources'] if r['type']=='observation')
            absent='outside <&> café\x00'
            observation['stimulus']['resource_id']=absent;observation['target']['resource_id']=absent
            variant['resources'].append({'id':'opaque','type':'org.future.unknown','type_version':'9','payload':{'resource_id':'not-inferred','number':2**64+1}})
            for label,raw in [('diphenyl',original),('beta-pinene',(root/'examples/multisource_beta_pinene.osmell').read_bytes()),('partial',json.dumps(variant).encode())]:
                source=work/'caller.osmell';source.write_bytes(raw);doc=json.loads(raw)
                selected=next(r['id'] for r in doc['resources'] if r['type']=='observation')
                output=evidence/label
                command=[python,'-I','-m','opensmell','reference-graph',source,'--output-directory',output]
                manifest=json.loads(run(command));assert (output/'source.osmell').read_bytes()==raw
                report=json.loads(run([python,'-I','inspect_bundle.py',output,'--resource-id',selected]))
                assert report['reference_occurrences']==manifest['coverage']['reference_occurrences']
                assert report['node_count']==manifest['coverage']['node_count']
                before={p.name:p.read_bytes() for p in output.iterdir()};run(command,2)
                assert before=={p.name:p.read_bytes() for p in output.iterdir()}
                if label=='partial':
                    assert report['unresolved_target_ids']==[absent] and report['uninterpreted_resource_ids']==['opaque']
                    assert report['outgoing_reference_occurrences']==2 and report['direct_target_ids']==[absent]
                (evidence/(label+'-networkx.json')).write_text(json.dumps(report,indent=2)+'\n')
                summary['cases'].append({'name':label,'nodes':report['node_count'],'edges':report['reference_occurrences'],'source_exact':True,'overwrite_refused':True,'coverage':'partial'})
                save()
            shutil.copytree(evidence/'diphenyl',work/'modified')
            with (work/'modified/references.graphml').open('ab') as output:output.write(b' ')
            run([python,'-I','inspect_bundle.py',work/'modified','--resource-id',selected],1)
            summary.update(status='passed',modified_bundle_refused=True)
    except BaseException as error:
        summary.update(status='error',error=str(error));save();raise
    save();print(json.dumps(summary))

if __name__=='__main__':main()
