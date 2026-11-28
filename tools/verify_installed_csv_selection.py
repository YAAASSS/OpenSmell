"""Installed large-CSV stream selection -> existing cohort/Node/table/Core plan entries."""
import argparse
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('wheel',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();wheel=a.wheel.resolve(strict=True);output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1];result={'result':'incomplete','physical_validation':False}
    def save():(output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-stream-selection-') as tmp:
        work=Path(tmp);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME','NODE_PATH'}}
        def run(cmd,expected=(0,)):
            r=subprocess.run(list(map(str,cmd)),cwd=work,env=env,capture_output=True,timeout=120)
            assert r.returncode in expected,(cmd,r.returncode,r.stdout[-1500:],r.stderr[-1500:]);return r.stdout
        cli=[python,'-I','-m','opensmell']
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        location=run([python,'-I','-c','import opensmell;print(opensmell.__file__)']).decode().strip();assert Path(location).is_relative_to(work/'venv')
        header=b'\xef\xbb\xbfCID,Odor,Odor dilution,Subject # (this study),FLOWER,GRASS,WOOD,note\r\n'
        first='1,"é, source",1/100,subject,26,0,89,"multi\r\nline"\r\n'.encode()
        filler=b'1,unselected,1/1,subject,101,,,'+b'x'*1000+b'\n'  # numeric semantics deliberately not interpreted by selector
        last='1,last,1/1000,subject,80,20,,尾'.encode();path=work/'large.csv';digest=hashlib.sha256()
        with path.open('wb') as stream:
            for raw in (header,first):stream.write(raw);digest.update(raw)
            for _ in range(10000):stream.write(filler);digest.update(filler)
            stream.write(last);digest.update(last)
        input_size=path.stat().st_size;assert input_size>8*1048576
        source=work/'source.json';src=json.loads((root/'examples/synthetic_keller_source.json').read_bytes());src['future']={'huge':2**70,'opaque':[None,True]};source.write_text(json.dumps(src,indent=3))
        # Instrument the normal installed SDK itself, after imports, with a large
        # input already on disk; not a claim about all interpreter/process RSS.
        (work/'measure.py').write_text('''import json,tracemalloc
from pathlib import Path
from opensmell.experimental.csv_selection import select_keller_csv
source=Path('source.json').read_bytes()
tracemalloc.start()
r=select_keller_csv('large.csv',rows=[10002,1],source_raw=source,directory='sdk-selected')
_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
assert peak<4*1048576,peak
print(json.dumps({'peak':peak,'input':r['selection']['input']}))
''')
        memory=json.loads(run([python,'-I',work/'measure.py']))
        assert memory['input']['sha256']==digest.hexdigest() and memory['input']['byte_count']==input_size
        selection=work/'selected'
        args=[*cli,'select-keller-csv',path,'--source',source,'--rows','10002','1','--output-directory',selection]
        report=json.loads(run(args));context=report['selection']
        assert context['input']['data_record_count']==10002 and context['input']['embedded'] is False
        selected=(selection/'observations.csv').read_bytes();assert selected==header+last+b'\n'+first
        assert selected==(work/'sdk-selected/observations.csv').read_bytes()
        assert (selection/'source.json').read_bytes()==(work/'sdk-selected/source.json').read_bytes()
        assert (selection/'original-source.json').read_bytes()==source.read_bytes()
        run(args,(2,));assert (selection/'observations.csv').read_bytes()==selected
        bad=work/'late.csv';shutil.copyfile(path,bad)
        with bad.open('ab') as stream:stream.write(b'\n"unterminated')
        run([*cli,'select-keller-csv',bad,'--source',source,'--rows','1','--output-directory',work/'no-output'],(1,));assert not (work/'no-output').exists()
        bad.unlink();path.unlink();source.unlink()
        graph=work/'cohort.osmell';run([*cli,'import-keller-cohort',selection/'observations.csv','--source',selection/'source.json','--rows','2','1','--output',graph])
        doc=json.loads(graph.read_bytes());meta=doc['org.opensmell.experimental.perceptual-csv-cohort'];assert meta['counts']=={'accepted':2,'refused':0}
        assert meta['source']['org.opensmell.experimental.csv-selection']['input']['sha256']==digest.hexdigest()
        recovered=work/'recovered.csv';run([*cli,'extract-keller-source',graph,'--output',recovered]);assert recovered.read_bytes()==selected
        # Existing installed independent graph reader, actually packed/installed.
        npm=shutil.which('npm');assert npm
        npm_cli=Path(npm).resolve()
        if os.name=='nt':npm_cli=Path(shutil.which('node')).parent/'node_modules/npm/bin/npm-cli.js'
        npm_command=['node',npm_cli] if npm_cli.suffix=='.js' else [npm]
        packed=json.loads(run([*npm_command,'pack',root/'packages/javascript','--ignore-scripts','--json','--pack-destination',work]))[0]
        (work/'package.json').write_text('{"private":true}')
        run([*npm_command,'install','--offline','--ignore-scripts','--no-audit','--no-fund',work/packed['filename']])
        node_cli=work/'node_modules/@opensmell/graph-reader/cli.cjs';copy=work/'node-copy.osmell'
        run(['node',node_cli,graph,'--copy',copy],(0,3));assert copy.read_bytes()==graph.read_bytes()
        table=json.loads(run([*cli,'observation-table',copy],(0,3)));assert table['coverage']['observation_count']==2 and table['coverage']['measurement_count']==5
        plans=[]
        for index,entry in enumerate(meta['results']):
            obs=next(r for r in doc['resources'] if r['id']==entry['observation_id'])
            selected_index=next(i for i,r in enumerate(obs['results']) if r['scheme']['id']=='org.opensmell.perceptual.measurements')
            core=work/f'core-{index}.osmell';run([*cli,'export-observation-core',copy,'--observation-id',obs['id'],'--result-index',selected_index,'--odor-id',f'urn:caller:selected:{index}','--output',core])
            node_core=work/f'core-copy-{index}.osmell';run(['node',node_cli,'--core',core,'--copy',node_core],(0,3));assert node_core.read_bytes()==core.read_bytes()
            profile=json.loads((root/'examples/offline_perceptual_profile.json').read_bytes())
            if index:profile['bindings']=profile['bindings'][:2]
            bound={b['property'] for b in profile['bindings']}
            profile['org.opensmell.experimental.core-perceptual-policy']={'version':'0.1','normalization':'value-minus-min-over-range',
                'measurements':[{k:deepcopy(v) for k,v in m.items() if k in {'property','unit','scale'}} for m in obs['results'][selected_index]['data']['measurements'] if m['property'] in bound]}
            policy=work/f'policy-{index}.json';policy.write_text(json.dumps(profile))
            plan=output/f'plan-{index}.json';run([*cli,'plan-core',node_core,'--representation-index','0','--profile',policy,'--duration','.1','--output',plan])
            values=[c['intensity'] for c in json.loads(plan.read_bytes())['plan']['commands']];assert values==([.26,0,.89] if index==0 else [.8,.2]);plans.append(values)
        for name in ('selection.json','observations.csv','source.json','original-source.json'):shutil.copyfile(selection/name,output/name)
        shutil.copyfile(copy,output/'node-cohort.osmell')
        result.update(result='passed',input_byte_count=input_size,input_sha256=digest.hexdigest(),source_record_count=10002,
            selected_source_rows=[10002,1],traced_python_peak_bytes=memory['peak'],memory_scope='Installed SDK after imports, not total RSS/all inputs/OS memory',
            exact_raw_records=True,declared_separator_addition=True,late_syntax_no_output=True,collision_preserved=True,
            original_large_path_removed=True,exact_selected_csv_recovered=True,exact_node_graph_and_core_transfers=True,
            two_explicit_plans=plans,dependency_scope='Inherited Python dependencies, not clean closure or outside adoption')
        save()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
