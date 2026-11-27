import csv
from copy import deepcopy
import json
from pathlib import Path
import pytest
from opensmell.experimental.perceptual_cohort import import_keller_cohort, extract_keller_source, COHORT_KEY, MAX_CSV_BYTES, MAX_GRAPH_BYTES
from opensmell.experimental.perceptual_import import import_keller_csv, IMPORT_KEY
from opensmell.experimental.generic_graph import generic_graph_to_dict
from opensmell.experimental.core_interchange import interchange_registry
from opensmell.experimental.observation_table import observation_table

ROOT=Path(__file__).resolve().parents[1]
RAW=(ROOT/'examples/synthetic_keller.csv').read_bytes()
SOURCE=json.loads((ROOT/'examples/synthetic_keller_source.json').read_bytes())

def cohort(raw=RAW,rows=(2,1,3,4,99),source=SOURCE):
    return import_keller_cohort(raw,rows=rows,source=source)

def test_cohort_reuses_occurrences_order_context_and_recovers_every_source_byte():
    source=deepcopy(SOURCE);source['future']={'big':2**70,'unknown':[None,True]}
    raw=b'\xef\xbb\xbf'+RAW.replace(b'\n',b'\r\n');result=cohort(raw,source=source);doc=json.loads(result);meta=doc[COHORT_KEY]
    assert meta['counts']=={'accepted':3,'refused':2} and meta['status']=='partial'
    assert [r['data_record'] for r in meta['results']]==[2,1,3,4,99]
    assert len(doc['resources'])==12
    assert extract_keller_source(result)==raw
    for i,row in enumerate([2,1,3]):
        single=generic_graph_to_dict(import_keller_csv(raw,row=row,source=source),registry=interchange_registry())
        assert doc['resources'][i*4:i*4+4]==single['resources']
        assert meta['results'][i]['import_context']==single[IMPORT_KEY]
    assert meta['results'][2]['import_context']['measurement_count']==0
    assert len(observation_table(result)['tables']['observations'])==3

@pytest.mark.parametrize('rows',[[],[1,1],[0],[-1],[True],[1.0],['1'],list(range(1,102)),None,'1'])
def test_bad_selection_refuses(rows):
    with pytest.raises((ValueError,TypeError)):cohort(rows=rows)

@pytest.mark.parametrize('raw',[b'bad\n1\n',b'\xff',b'CID,CID\n1,2\n',RAW+b'"unterminated'])
def test_global_syntax_header_errors_refuse(raw):
    with pytest.raises((ValueError,UnicodeError,csv.Error)):cohort(raw)

@pytest.mark.parametrize('source',[{},None,{'kind':'synthetic'}])
def test_bad_source_is_global(source):
    with pytest.raises((ValueError,TypeError)):cohort(source=source)

def test_all_refused_still_retains_source_and_never_silently_succeeds():
    raw=cohort(rows=[4,99]);d=json.loads(raw)
    assert d['resources']==[] and d[COHORT_KEY]['status']=='refused'
    assert extract_keller_source(raw)==RAW

def test_input_and_serialized_output_bounds():
    with pytest.raises(ValueError,match='512 KiB'):cohort(b' '* (MAX_CSV_BYTES+1))
    source=deepcopy(SOURCE);source['future']='x'*800000
    with pytest.raises(ValueError,match='2 MiB'):cohort(source=source)
    with pytest.raises(ValueError,match='2 MiB'):extract_keller_source(b' '*(MAX_GRAPH_BYTES+1))

@pytest.mark.parametrize('change',[
    lambda d:d.update(opensmell='0.1'),
    lambda d:d[COHORT_KEY]['results'][0].update(status='refused'),
    lambda d:d[COHORT_KEY]['counts'].update(accepted=True),
    lambda d:d[COHORT_KEY]['requested_records'].reverse(),
    lambda d:d['resources'][0].update(id='altered'),
    lambda d:d[COHORT_KEY]['csv'].update(data='!'),
    lambda d:d[COHORT_KEY]['csv'].update(sha256='0'*64),
    lambda d:d[COHORT_KEY]['csv'].update(byte_count=True),
    lambda d:d[COHORT_KEY].update(version='9'),
    lambda d:d.update(future='changed'),
])
def test_inconsistent_cohort_cannot_recover_as_verified(change):
    d=json.loads(cohort());change(d)
    with pytest.raises(ValueError):extract_keller_source(json.dumps(d).encode())

def test_unknown_source_is_copied_and_originals_not_mutated():
    s=deepcopy(SOURCE);s['future']={'x':[None,2**70]};before=deepcopy(s)
    a=cohort(source=s);assert s==before
    s['future']['x'].append(9);assert json.loads(a)[COHORT_KEY]['source']==before
