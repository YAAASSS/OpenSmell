"""Installed SDK -> explicit Pandas dtypes, no scientific normalization or means."""
import argparse
import json
import math
from pathlib import Path

import pandas as pd
from opensmell.experimental.observation_table import observation_table, MAX_BYTES

COLUMNS=['source_sha256','observation_id','stimulus_id','target_id','source_path','property',
         'value','scale_min','scale_max','unit','unit_presence','result_index','measurement_index','dilution_json']


def frames(artifact):
    rows=[]
    resources={r['id']:r for r in artifact['context']['resources']}
    for record in artifact['tables']['measurements']:
        record=dict(record)
        for field in ('value','scale_min','scale_max'):
            value=record[field]
            try:
                floating=float(value)
            except OverflowError as error:
                raise ValueError('Numeric value cannot be represented by Pandas Float64') from error
            if not math.isfinite(floating) or floating != value:
                raise ValueError('Pandas Float64 would round an exact SDK numeric value; retain the JSON artifact instead')
        stimulus=resources.get(record['stimulus_id'],{})
        if stimulus.get('type')!='stimulus':
            dilution=None
        else:
            dilution=[c for c in stimulus.get('conditions',[]) if c.get('property')=='dilution']
        record['dilution_json']=None if dilution is None else json.dumps(dilution,ensure_ascii=True,allow_nan=False)
        rows.append(record)
    measurements=pd.DataFrame.from_records(rows,columns=COLUMNS)
    for column in COLUMNS:
        dtype='Float64' if column in ('value','scale_min','scale_max') else 'Int64' if column in ('result_index','measurement_index') else 'string'
        measurements[column]=measurements[column].astype(dtype)
    categories=pd.DataFrame.from_records(artifact['tables']['categorical'])
    return measurements,categories


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file',type=Path)
    parser.add_argument('--output-directory',type=Path,required=True,help='New directory; never overwrite')
    args=parser.parse_args()
    with args.file.open('rb') as source:
        artifact=observation_table(source.read(MAX_BYTES+1))
    measurements,categories=frames(artifact)
    args.output_directory.mkdir(parents=True,exist_ok=False)
    (args.output_directory/'analysis.json').write_text(json.dumps(artifact,indent=2,ensure_ascii=True,allow_nan=False)+'\n',encoding='utf-8')
    # CSV is a derived human/analysis view; JSON snapshot/context is authoritative.
    measurements.to_csv(args.output_directory/'measurements.csv',index=False)
    (args.output_directory/'categorical.json').write_text(json.dumps(artifact['tables']['categorical'],indent=2,ensure_ascii=True,allow_nan=False)+'\n',encoding='utf-8')
    summary={'status':artifact['status'],'pandas_version':pd.__version__,'source_sha256':artifact['source']['sha256'],
             'measurement_rows':len(measurements),'categorical_rows':len(categories),
             'coverage':artifact['coverage'],'dtypes':{c:str(t) for c,t in measurements.dtypes.items()},
             'limits':['No joins, means, imputation or unit conversion. CSV is derived; JSON preserves exact source bytes and context.',
                       'Pandas is an optional external consumer, not part of the SDK runtime or offline wheelhouse.']}
    (args.output_directory/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary))
    return 3 if artifact['status']=='partial' else 0

if __name__=='__main__':
    raise SystemExit(main())
