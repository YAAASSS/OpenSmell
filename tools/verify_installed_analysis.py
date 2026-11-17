"""Fresh-wheel installed observation export and a real optional Pandas consumer."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import venv


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel',type=Path)
    parser.add_argument('--published-preparation',type=Path,help='Explicit prepared scientific CSV/source directory; no fetching')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]; wheel=args.wheel.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='opensmell-installed-analysis-') as directory:
        work=Path(directory)
        venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        def run(arguments,expected=0):
            r=subprocess.run([str(x) for x in arguments],cwd=work,env=env,capture_output=True,timeout=60)
            if r.returncode!=expected:
                raise RuntimeError(f'{arguments}: {r.returncode} {r.stdout!r} {r.stderr!r}')
            return r.stdout
        def cli(*arguments,expected=0):
            return run([python,'-I','-m','opensmell',*arguments],expected)
        run([python,'-m','pip','install','--no-deps','--no-index','--ignore-installed',wheel])
        location=run([python,'-I','-c','import opensmell; print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv')
        (work/'analyze.py').write_bytes((root/'examples/pandas_analysis/analyze.py').read_bytes())
        if args.published_preparation:
            csv=args.published_preparation/'observations.csv'; source=args.published_preparation/'source.json'
            counts=[8,0,3]; kind='dataset'
        else:
            csv=root/'examples/synthetic_keller.csv'; source=root/'examples/synthetic_keller_source.json'
            counts=[4,2,0]; kind='synthetic'
        for row,expected_count in enumerate(counts,1):
            graph=work/f'graph-{row}.osmell'
            cli('import-keller',csv,'--source',source,'--row',row,'--output',graph)
            raw=graph.read_bytes()
            artifact=json.loads(cli('observation-table',graph,'--output',f'table-{row}.json') or (work/f'table-{row}.json').read_bytes())
            assert artifact['status']=='projected' and artifact['coverage']['measurement_count']==expected_count
            assert base64.b64decode(artifact['source']['data'])==raw and artifact['context']['org.opensmell.experimental.perceptual-csv-import']['source']['kind']==kind
            cli('observation-table',graph,'--output',f'table-{row}.json',expected=2)
            result=json.loads(run([python,'-I','analyze.py',graph,'--output-directory',f'analysis-{row}']))
            assert result['measurement_rows']==expected_count and result['categorical_rows']==1
            assert result['dtypes']['value']=='Float64' and result['dtypes']['observation_id']=='string'
            run([python,'-I','analyze.py',graph,'--output-directory',f'analysis-{row}'],expected=1)
            if row==1:
                run([python,'-I','-c',"import pandas as p; d=p.read_csv('analysis-1/measurements.csv',dtype={'value':'Float64','scale_min':'Float64','scale_max':'Float64','observation_id':'string','property':'string'},keep_default_na=False); assert float(d.loc[d['property']=='flower','value'].iloc[0])==26; assert float(d.loc[d['property']=='grass','value'].iloc[0])=="+('38' if kind=='dataset' else '0')])
        document=json.loads((work/'graph-1.osmell').read_bytes())
        obs=next(r for r in document['resources'] if r['type']=='observation')
        obs['results'].append({'scheme':{'id':'org.example.opaque','version':'1'},'data':{'keep':True}})
        (work/'partial.osmell').write_text(json.dumps(document))
        cli('observation-table','partial.osmell','--output','partial.json',expected=3)
        partial=json.loads(run([python,'-I','analyze.py','partial.osmell','--output-directory','partial'],expected=3))
        assert partial['coverage']['issues'][0]['code']=='uninterpreted_result'
        obs['results']=[{'scheme':{'id':'org.opensmell.perceptual.measurements','version':'0.1'},'data':{'measurements':[{'property':'large','value':2**53+1,'scale':{'min':0,'max':2**54}}]}}]
        (work/'large.osmell').write_text(json.dumps(document))
        exact=json.loads(cli('observation-table','large.osmell'))
        assert exact['tables']['measurements'][0]['value']==2**53+1
        run([python,'-I','analyze.py','large.osmell','--output-directory','must-not-exist'],expected=1)
        assert not (work/'must-not-exist').exists()
        # Existing real multisource graph has category annotations and missing units.
        real=root/'examples/multisource_diphenyl_ether.osmell'
        result=json.loads(run([python,'-I','analyze.py',real,'--output-directory','legacy-real']))
        assert result['measurement_rows']==7 and result['categorical_rows']==1
        print(json.dumps({'result':'passed','source_kind':kind,'selected_rows':[1,2,3],'measurement_rows':counts,
                          'real_multisource_measurements':7,'exact_source_preserved':True,'partial_coverage_retained':True,
                          'pandas_lossy_conversion_refused':True,'installed_sdk_outside_checkout':True,'physical_validation':False}))

if __name__=='__main__':
    main()
