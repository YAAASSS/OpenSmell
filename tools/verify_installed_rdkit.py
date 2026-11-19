"""Install the SDK wheel in a fresh target; run optional RDKit consumers outside checkout.

RDKit/runtime dependencies come from the explicit test environment; no downloads.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('wheel',type=Path)
    p.add_argument('--evidence-directory',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];wheel=a.wheel.resolve(strict=True)
    evidence=a.evidence_directory.resolve();evidence.mkdir(parents=True,exist_ok=False)
    summary={'status':'incomplete','physical_validation':False,'cases':[]}
    def save():(evidence/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    save()
    try:
        with tempfile.TemporaryDirectory(prefix='opensmell-installed-rdkit-') as directory:
            work=Path(directory);sdk=work/'installed-sdk'
            env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
            def run(command,expected=0):
                r=subprocess.run([str(x) for x in command],cwd=work,env=env,capture_output=True,timeout=90)
                if r.returncode!=expected:raise RuntimeError(f'{command}: {r.returncode} {r.stdout!r} {r.stderr!r}')
                return r.stdout
            run([sys.executable,'-I','-m','pip','install','--no-index','--no-deps','--target',sdk,wheel])
            location=run([sys.executable,'-I','-c','import sys;sys.path.insert(0,sys.argv[1]);import opensmell;print(opensmell.__file__)',sdk]).decode().strip()
            assert Path(location).is_relative_to(sdk)
            summary['sdk_installed_outside_checkout']=True
            summary['dependency_scope']='Fresh local SDK wheel target selected first in isolated Python path; RDKit/dependencies inherited from explicit test runtime, not clean offline closure'
            for name in ('analyze','read_sdf'):shutil.copyfile(root/f'examples/rdkit_molecule/{name}.py',work/f'{name}.py')
            def analyze(source,rid,output,expected=0):
                return json.loads(run([sys.executable,'-I','-c',
                    'import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
                    sdk,work/'analyze.py',source,'--resource-id',rid,'--output-directory',output],expected))
            for name,rid,formula in [('beta-pinene','2d5a1039-904c-5b19-a60f-71c1ada5bac2','C10H16'),
                                     ('diphenyl-ether','e6ad8ce3-dc6e-5d94-9287-57665d48fc0b','C12H10O')]:
                file='multisource_beta_pinene.osmell' if name=='beta-pinene' else 'multisource_diphenyl_ether.osmell'
                raw=(root/'examples'/file).read_bytes();source=work/'caller.osmell';source.write_bytes(raw)
                output=evidence/name;report=analyze(source,rid,output)
                assert report['computed']['formula']==formula
                assert (output/'source.osmell').read_bytes()==raw
                reader=json.loads(run([sys.executable,'-I',work/'read_sdf.py',output/'molecule.sdf']))
                assert reader['resource_id']==rid and reader['declared_smiles']==report['declared_smiles']
                assert reader['source_sha256']==hashlib.sha256(raw).hexdigest()
                assert reader['computed_canonical_isomeric_smiles']==report['computed']['canonical_isomeric_smiles']
                (evidence/(name+'-reader.json')).write_text(json.dumps(reader,indent=2)+'\n')
                before={p.name:p.read_bytes() for p in output.iterdir()};analyze(source,rid,output,2)
                assert before=={p.name:p.read_bytes() for p in output.iterdir()}
                summary['cases'].append({'name':name,'formula':formula,'stereo_centers':report['computed']['specified_stereo_centers'],
                                         'source_exact':True,'sdf_reader_equal':True,'overwrite_refused':True})
                save()
            doc=json.loads((root/'examples/multisource_beta_pinene.osmell').read_bytes());rid='2d5a1039-904c-5b19-a60f-71c1ada5bac2'
            doc['synthetic_trial']={'kind':'synthetic','purpose':'unknown-context preservation and explicit-H consumer proof'}
            selected=next(r for r in doc['resources'] if r['id']==rid)
            selected['smiles']='[2H]O[H]';doc['future']={'large_integer':2**64+1}
            doc['resources'].append({'id':'opaque','type':'org.future.unknown','type_version':'9','payload':{'smiles':'invalid not selected'}})
            raw=json.dumps(doc).encode();source.write_bytes(raw)
            report=analyze(source,rid,evidence/'synthetic-explicit-h')
            assert (evidence/'synthetic-explicit-h/source.osmell').read_bytes()==raw
            assert report['computed']['atoms_in_rdkit_mol']==3 and report['sdf_reread']['canonical_isomeric_structure_equal']
            summary['cases'].append({'name':'synthetic-explicit-h','source_exact':True,'atoms':3,'unknown_content_preserved':True})
            refusals=[]
            for label,smiles,version,target in [('invalid-valence','[CH5]','0.1',rid),('name-suffix','CC trailing','0.1',rid),
                ('cxsmiles','CC |atomProp:0.foo.bar|','0.1',rid),('nul','CC\x00hidden','0.1',rid),
                ('identifier-only',None,'0.1',rid),('unsupported-version','CC','9',rid),('missing-resource','CC','0.1','absent')]:
                if smiles is None:selected.pop('smiles',None)
                else:selected['smiles']=smiles
                selected['type_version']=version
                source.write_text(json.dumps(doc));out=evidence/('refused-'+label)
                refusal=analyze(source,target,out,1)
                assert refusal['status']=='refused' and not out.exists()
                refusals.append({'name':label,'result':refusal})
            (evidence/'refusals.json').write_text(json.dumps(refusals,indent=2)+'\n')
            summary.update(status='passed',refusals=len(refusals),rdkit_version=report['rdkit_version'])
    except BaseException as error:
        summary.update(status='error',error=str(error));save();raise
    save();print(json.dumps(summary))

if __name__=='__main__':main()
