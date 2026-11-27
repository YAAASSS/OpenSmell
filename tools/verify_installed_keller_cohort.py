"""Installed selected quantitative cohort -> analysis/graph Node -> Core/Node -> Python plans and exact CSV recovery."""
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();wheel=args.wheel.resolve(strict=True)
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    evidence={'result':'incomplete','physical_validation':False,'source_kind':'declared synthetic CSV'}
    def save():(output/'result.json').write_text(json.dumps(evidence,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-installed-js-core-') as tmp:
        work=Path(tmp);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME','NODE_PATH'}}
        def run(command,expected=(0,),cwd=work):
            r=subprocess.run(list(map(str,command)),cwd=cwd,env=env,capture_output=True,timeout=120)
            assert r.returncode in expected,(command,r.returncode,r.stdout[-1500:],r.stderr[-1500:])
            return r.stdout
        cli=[python,'-I','-m','opensmell']
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        location=run([python,'-I','-c','import opensmell;print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv')
        # npm pack uses the source only for packaging; consumers below use installed files.
        npm=shutil.which('npm');assert npm
        npm_cli=Path(npm).resolve()
        if os.name=='nt':npm_cli=Path(shutil.which('node')).parent/'node_modules/npm/bin/npm-cli.js'
        npm_command=['node',npm_cli] if npm_cli.suffix=='.js' else [npm]
        packed=json.loads(run([*npm_command,'pack','--ignore-scripts','--json','--pack-destination',output],cwd=root/'packages/javascript'))[0]
        archive=output/packed['filename'];assert archive.is_file()
        (work/'package.json').write_text('{"private":true,"type":"module"}')
        run([*npm_command,'install','--offline','--ignore-scripts','--no-audit','--no-fund','--package-lock=false',archive])
        node_cli=work/'node_modules/.bin/opensmell-inspect-js'
        if os.name=='nt':node_cli=work/'node_modules/@opensmell/graph-reader/cli.cjs'
        def inspect(path,target=None,expected=(0,3)):
            return json.loads(run(['node',node_cli,'--core',path,*(['--copy',target] if target else [])],expected))
        table=work/'caller.csv';table.write_bytes((root/'examples/synthetic_keller.csv').read_bytes())
        source=work/'source.json';source.write_bytes((root/'examples/synthetic_keller_source.json').read_bytes())
        graph=work/'graph.osmell'
        raw_csv=table.read_bytes()
        run([*cli,'import-keller-cohort',table,'--source',source,'--rows','2','1','3','4','99','--output',graph])
        raw=graph.read_bytes();doc=json.loads(raw)
        key='org.opensmell.experimental.perceptual-csv-cohort';meta=doc[key]
        assert meta['counts']=={'accepted':3,'refused':2}
        assert [r['data_record'] for r in meta['results']]==[2,1,3,4,99]
        run([*cli,'import-keller-cohort',table,'--source',source,'--rows','1','--output',graph],(2,));assert graph.read_bytes()==raw
        run([*cli,'import-keller-cohort',table,'--source',source,'--rows','1','1','--output',work/'invalid-selection'],(1,))
        assert not (work/'invalid-selection').exists()
        graph_copy=work/'node-graph.osmell'
        graph_report=json.loads(run(['node',node_cli,graph,'--copy',graph_copy],(0,3)))
        assert graph_copy.read_bytes()==raw and len(graph_report['observations'])==3
        table.unlink();source.unlink();graph.unlink()
        graph=graph_copy
        recovered_csv=work/'recovered.csv';run([*cli,'extract-keller-source',graph,'--output',recovered_csv]);assert recovered_csv.read_bytes()==raw_csv
        run([*cli,'extract-keller-source',graph,'--output',recovered_csv],(2,));assert recovered_csv.read_bytes()==raw_csv
        analysis=json.loads(run([*cli,'observation-table',graph]))
        assert analysis['coverage']['observation_count']==3
        ids=[r['observation_id'] for r in meta['results'] if r['status']=='accepted']
        assert [r['observation_id'] for r in analysis['tables']['observations']]==ids
        assert analysis['tables']['observations'][2]['measurement_count']==0
        second=next(r for r in doc['resources'] if r['id']==ids[0])
        assert {m['property']:m['value'] for m in second['results'][1]['data']['measurements']}=={'flower':80,'grass':20}
        profile2=json.loads((root/'examples/offline_perceptual_profile.json').read_bytes());profile2['bindings']=profile2['bindings'][:2]
        profile2['org.opensmell.experimental.core-perceptual-policy']={'version':'0.1','normalization':'value-minus-min-over-range',
          'measurements':[{k:v for k,v in m.items() if k in {'property','unit','scale'}} for m in second['results'][1]['data']['measurements']]}
        (work/'profile2.json').write_text(json.dumps(profile2))
        second_core=work/'second.osmell';run([*cli,'export-observation-core',graph,'--observation-id',ids[0],'--result-index','1','--odor-id','urn:caller:second','--output',second_core])
        inspect(second_core,work/'second-copy.osmell')
        run([*cli,'plan-core',work/'second-copy.osmell','--representation-index','0','--profile',work/'profile2.json','--duration','.1','--output',output/'second-plan.json'])
        assert [c['intensity'] for c in json.loads((output/'second-plan.json').read_bytes())['plan']['commands']]==[.8,.2]
        bad=json.loads(raw);bad[key]['results'][0]['status']='refused';(work/'tampered.osmell').write_text(json.dumps(bad))
        run([*cli,'extract-keller-source',work/'tampered.osmell','--output',work/'must-not-exist'],(1,));assert not (work/'must-not-exist').exists()
        run([*cli,'export-observation-core',graph,'--observation-id',ids[2],'--result-index','0','--odor-id','urn:caller:unmeasured','--output',work/'unmeasured'],(1,));assert not (work/'unmeasured').exists()
        shutil.copyfile(graph,output/'cohort.osmell');shutil.copyfile(recovered_csv,output/'original.csv')
        (output/'observation-table.json').write_text(json.dumps(analysis,indent=2))
        obs=next(r for r in doc['resources'] if r['id']==ids[1])
        selected=next(i for i,r in enumerate(obs['results']) if r['scheme']['id']=='org.opensmell.perceptual.measurements')
        core=work/'selected-core.osmell'
        run([*cli,'export-observation-core',graph,'--observation-id',obs['id'],'--result-index',selected,'--odor-id','urn:caller:js-core','--output',core])
        original=core.read_bytes();graph.unlink()
        transfer=work/'node-transfer.osmell';report=inspect(core,transfer)
        assert transfer.read_bytes()==original and report['file']['sha256']==hashlib.sha256(original).hexdigest()
        entries=report['core']['representations'][0]['entries']
        assert {e['property']:float(e['value']['json']) for e in entries if e['property'] in {'flower','grass','wood'}}=={'flower':26,'grass':0,'wood':89}
        assert report['core']['odor_id']=='urn:caller:js-core'
        assert report['core']['representations'][0]['provenance']['presence']=='value'
        (output/'export-inspection.json').write_text(json.dumps(report,indent=2))
        run(['node',node_cli,'--core',core,'--copy',transfer],(2,));assert transfer.read_bytes()==original
        core.unlink()
        recovered=work/'recovered.osmell';run([*cli,'extract-observation-source',transfer,'--output',recovered]);assert recovered.read_bytes()==raw
        profile=json.loads((root/'examples/offline_perceptual_profile.json').read_bytes())
        profile['org.opensmell.experimental.core-perceptual-policy']={'version':'0.1','normalization':'value-minus-min-over-range',
            'measurements':[{k:deepcopy(v) for k,v in m.items() if k in {'property','unit','scale'}} for m in obs['results'][selected]['data']['measurements'] if m['property'] in {b['property'] for b in profile['bindings']}]}
        policy=work/'profile.json';policy.write_text(json.dumps(profile))
        plan=output/'plan.json';run([*cli,'plan-core',transfer,'--representation-index','0','--profile',policy,'--duration','.1','--output',plan])
        assert [c['intensity'] for c in json.loads(plan.read_bytes())['plan']['commands']]==[.26,0,.89]
        shutil.copyfile(transfer,output/'node-transfer.osmell');shutil.copyfile(recovered,output/'recovered-graph.osmell')
        # Separate standalone Core source with mixed unit presence and unknown representations.
        fixture=(root/'examples/core_perceptual_only.osmell').read_bytes()
        (work/'quantitative.osmell').write_bytes(fixture)
        # ESM checks safe display fields and independent original-byte copy.
        (work/'consumer.mjs').write_text('''import assert from 'node:assert/strict';
import fs from 'node:fs';
import reader, {inspectCoreBytes, CORE_LIMIT} from '@opensmell/graph-reader';
assert.equal(reader.inspectCoreBytes,inspectCoreBytes);assert.equal(CORE_LIMIT,4194304);
const original=fs.readFileSync('quantitative.osmell');const result=await inspectCoreBytes(original);
assert.equal(result.report.status,'partial');const reps=result.report.core.representations;
assert.equal(reps.length,3);assert.equal(reps[2].status,'opaque');
const entries=reps[0].entries;assert.equal(entries[0].value.json,'2.5');
assert.equal(entries[1].value.json,'0');assert.equal(entries[0].unit.text,'rating');
assert.equal(entries[1].unit.presence,'null');assert.equal(entries[2].unit.presence,'missing');
assert.match(reps[2].data.json,/1180591620717411303424/);
const copy=result.copyBytes();copy[0]=0;original[0]=0;
assert.equal(result.copyBytes()[0],123);fs.writeFileSync('esm-copy.osmell',result.copyBytes(),{flag:'wx'});
''')
        run(['node','consumer.mjs']);assert (work/'esm-copy.osmell').read_bytes()==fixture
        # CJS keeps tokens JS Number cannot represent, without exposing rounded values.
        lexemes=b'{"opensmell":"0.1","odor":{"id":"x","representations":[{"type":"perceptual","scheme":{"id":"org.opensmell.perceptual.measurements","version":"0.1"},"data":{"measurements":[{"property":"tiny","value":1e-400},{"property":"huge","value":9007199254740993},{"property":"null","value":null},{"property":"missing"}]}},{"type":"opaque","scheme":{"id":"future","version":"9"},"data":{"negativeZero":-0,"huge":1e400}}]},"future":0.10000000000000000001}\r\n'
        (work/'lexemes.osmell').write_bytes(lexemes)
        (work/'consumer.cjs').write_text('''const assert=require('node:assert/strict');const fs=require('node:fs');const reader=require('@opensmell/graph-reader');
assert.ok(require.resolve('@opensmell/graph-reader').startsWith(process.cwd()));
(async()=>{const r=await reader.inspectCoreBytes(fs.readFileSync('lexemes.osmell'));assert.equal(r.report.status,'partial');
const e=r.report.core.representations[0].entries;assert.equal(e[0].value.json,'1e-400');assert.equal(e[1].value.json,'9007199254740993');
assert.equal(e[2].value.presence,'null');assert.equal(e[3].value.presence,'missing');
fs.writeFileSync('cjs-copy.osmell',r.copyBytes(),{flag:'wx'});})().catch(e=>{console.error(e);process.exitCode=1});
''')
        run(['node','consumer.cjs']);assert (work/'cjs-copy.osmell').read_bytes()==lexemes
        (output/'lexical-input.osmell').write_bytes(lexemes);shutil.copyfile(work/'cjs-copy.osmell',output/'lexical-copy.osmell')
        for name,bad in [('ambiguous',b'{"opensmell":"0.1","format":"graph"}'),('duplicate',b'{"opensmell":"0.1","opensmell":"0.1"}'),('invalid',b'{"opensmell":"0.1","odor":null}')]:
            path=work/(name+'.osmell');path.write_bytes(bad);target=work/(name+'-no-copy')
            assert inspect(path,target,(1,))['status']=='rejected' and not target.exists()
        (work/'oversize.osmell').write_bytes(b' '*4194305);run(['node',node_cli,'--core',work/'oversize.osmell'],(1,))
        evidence.update(result='passed',cohort_counts={'accepted':3,'refused':2},exact_csv_recovered=True,unmeasured_kept=True,second_plan=[.8,.2],tampered_cohort_refused=True,python_installed_outside_checkout=True,node_installed_outside_checkout=True,
            npm_archive=archive.name,npm_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),modules=['CJS','ESM'],cli='installed --core',
            original_paths_removed=True,exact_core_transfer=True,exact_embedded_graph_recovery=True,
            quantitative_plan=[.26,0,.89],unsafe_numeric_lexemes_retained=True,unit_presence_retained=True,
            ambiguous_duplicate_invalid_oversize_refused=True,copy_collision_preserved=True,
            scope='Limited JS envelope/quantitative inspection, no Python schema/registry/export-marker parity; inherited Python dependencies, not clean closure or third-party adoption')
        save()
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':main()
