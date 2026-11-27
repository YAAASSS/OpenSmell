"""Installed pinned-public cohort trial; no download, source redistribution or physical IO."""
import tempfile,subprocess,json,os,venv,sys,hashlib,argparse,shutil
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('wheel',type=Path);p.add_argument('--workbook',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();wheel=a.wheel.resolve(strict=True);workbook=a.workbook.resolve(strict=True);output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
(output/'result.json').write_text('{"result":"incomplete","physical_access":false}')
root=Path(__file__).resolve().parents[1];env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME','NODE_PATH'}}
with tempfile.TemporaryDirectory(prefix='opensmell-public-cohort-') as tmp:
 w=Path(tmp);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(w/'venv');py=w/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python');cli=[str(py),'-I','-m','opensmell']
 def run(args,expected=(0,)):
  r=subprocess.run(list(map(str,args)),cwd=w,env=env,capture_output=True,timeout=120);assert r.returncode in expected,(args,r.returncode,r.stdout[-500:],r.stderr[-1000:]);return r.stdout
 run([py,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
 run([py,root/'examples/perceptual_import/prepare_reference.py',workbook,'--output-directory',w/'prepared'])
 raw=(w/'prepared/observations.csv').read_bytes()
 run([*cli,'import-keller-cohort',w/'prepared/observations.csv','--source',w/'prepared/source.json','--rows','1','2','3','--output',w/'cohort.osmell'])
 graph=(w/'cohort.osmell').read_bytes();d=json.loads(graph);ctx=d['org.opensmell.experimental.perceptual-csv-cohort'];assert ctx['counts']=={'accepted':3,'refused':0}
 import shutil
 shutil.rmtree(w/'prepared')
 run([*cli,'extract-keller-source',w/'cohort.osmell','--output',w/'recovered.csv']);assert (w/'recovered.csv').read_bytes()==raw
 npm=shutil.which('npm');assert npm
 npm_cli=Path(npm).resolve()
 if os.name=='nt':npm_cli=Path(shutil.which('node')).parent/'node_modules/npm/bin/npm-cli.js'
 npm_command=['node',npm_cli] if npm_cli.suffix=='.js' else [npm]
 packed=json.loads(run([*npm_command,'pack',root/'packages/javascript','--ignore-scripts','--json','--pack-destination',w]))[0]
 (w/'package.json').write_text('{"private":true}');run([*npm_command,'install','--offline','--ignore-scripts','--no-audit','--no-fund',w/packed['filename']])
 report=json.loads(run(['node',w/'node_modules/@opensmell/graph-reader/cli.cjs',w/'cohort.osmell','--copy',w/'node-copy.osmell'],(0,3)));assert (w/'node-copy.osmell').read_bytes()==graph
 table=json.loads(run([*cli,'observation-table',w/'node-copy.osmell'],(0,3)));assert table['coverage']['observation_count']==3
 results=[]
 for item in ctx['results']:
  obs=next(r for r in d['resources'] if r['id']==item['observation_id']);measurements=next((r['data']['measurements'] for r in obs['results'] if r['scheme']['id']=='org.opensmell.perceptual.measurements'),[])
  results.append({'row':item['data_record'],'measurement_count':len(measurements),'flower':[m['value'] for m in measurements if m['property']=='flower'],'grass':[m['value'] for m in measurements if m['property']=='grass'],'wood':[m['value'] for m in measurements if m['property']=='wood']})
 evidence={'result':'passed','source':'Previously documented pinned publisher workbook; no new source/scale authentication claim','xlsx_sha256':'efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62','prepared_csv_sha256':hashlib.sha256(raw).hexdigest(),'cohort_counts':ctx['counts'],'observations':results,'node_status':report['status'],'exact_csv_recovery':True,'exact_node_transfer':True,'original_preparation_removed':True,'physical_access':False}
 (output/'result.json').write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence,indent=2))
