"""Raw lexical CSV selection, full-stream validation and bounded storage."""
import csv
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tracemalloc
import pytest
from opensmell.experimental.csv_selection import select_keller_csv, SELECTION_KEY, MAX_RECORD_BYTES, MAX_OUTPUT_BYTES
from opensmell.experimental.perceptual_cohort import import_keller_cohort, COHORT_KEY

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'examples/synthetic_keller_source.json').read_bytes()
HEADER=b'CID,Odor,Odor dilution,Subject # (this study),FLOWER,GRASS,WOOD,note\r\n'
FIRST='1,"é, source",1/100,subject,26,0,89,"multi\r\nline"\r\n'.encode()
SECOND=b'1,second,1/1000,subject,80,20,,unknown,extra\n' # ragged intentionally
LAST='1,last,1/1000,subject,80,20,,尾'.encode()

def call(tmp_path,raw=HEADER+FIRST+LAST,rows=(2,1),source=SOURCE):
    path=tmp_path/'input.csv';path.write_bytes(raw)
    out=tmp_path/'selection';return select_keller_csv(path,rows=rows,source_raw=source,directory=out),out

def test_bytes_multiline_bom_eof_order_and_downstream_provenance(tmp_path):
    original=b'\xef\xbb\xbf'+HEADER+FIRST+LAST
    source=json.loads(SOURCE);source['future']={'huge':2**70,'unknown':[None,True]};raw_source=json.dumps(source,indent=3).encode()+b'\r\n'
    report,out=call(tmp_path,original,source=raw_source);selected=(out/'observations.csv').read_bytes()
    assert selected==b'\xef\xbb\xbf'+HEADER+LAST+b'\n'+FIRST
    assert (out/'original-source.json').read_bytes()==raw_source
    ctx=report['selection'];assert ctx['input']['sha256']==hashlib.sha256(original).hexdigest()
    assert ctx['input']['byte_count']==len(original) and ctx['input']['data_record_count']==2 and not ctx['input']['embedded']
    assert [r['source_record'] for r in ctx['records']]==[2,1]
    assert ctx['records'][0]['separator_added'] and not ctx['records'][1]['separator_added']
    for r in ctx['records']:
        left=original[r['source_byte_offset']:r['source_byte_offset']+r['original_byte_count']]
        right=selected[r['selected_byte_offset']:r['selected_byte_offset']+r['original_byte_count']]
        assert left==right and hashlib.sha256(left).hexdigest()==r['original_sha256']
    derived=json.loads((out/'source.json').read_bytes());assert derived['future']==source['future'] and derived[SELECTION_KEY]==ctx
    graph=json.loads(import_keller_cohort(selected,rows=[1,2],source=derived))
    assert graph[COHORT_KEY]['counts']=={'accepted':2,'refused':0}
    assert graph[COHORT_KEY]['source'][SELECTION_KEY]['records'][0]['source_record']==2

@pytest.mark.parametrize('ending',[b'\n',b'\r',b'\r\n'])
def test_line_terminators_are_not_normalized(tmp_path,ending):
    head=HEADER.replace(b'\r\n',ending);row=b'1,plain,1/1,subject,0,,,note'+ending
    r,out=call(tmp_path,head+row+row,rows=[2,1]);assert (out/'observations.csv').read_bytes()==head+row+row

@pytest.mark.parametrize('rows',[[],[1,1],[0],[-1],[True],[1.0],['1'],list(range(1,102)),None,'1',[99]])
def test_invalid_missing_selection_no_output(tmp_path,rows):
    with pytest.raises((ValueError,TypeError)):call(tmp_path,rows=rows)
    assert not (tmp_path/'selection').exists()

@pytest.mark.parametrize('suffix',[SECOND,b'"unterminated',b'\xff',b'\n'])
def test_late_syntax_structure_or_utf8_error_no_output(tmp_path,suffix):
    with pytest.raises((ValueError,UnicodeError,csv.Error)):call(tmp_path,HEADER+FIRST+suffix,rows=[1])
    assert not (tmp_path/'selection').exists()

def test_numeric_invalid_is_selected_verbatim_for_normal_cohort_refusal(tmp_path):
    raw=HEADER+b'1,bad,1/1,subject,101,,,unchanged\n'
    r,out=call(tmp_path,raw,rows=[1]);assert (out/'observations.csv').read_bytes()==raw
    graph=json.loads(import_keller_cohort(raw,rows=[1],source=json.loads((out/'source.json').read_bytes())))
    assert graph[COHORT_KEY]['counts']=={'accepted':0,'refused':1}

def test_record_output_source_bounds_and_reserved_context(tmp_path):
    with pytest.raises(ValueError,match='64 KiB'):call(tmp_path,HEADER+b'1,a,1/1,s,0,,,'+b'x'*MAX_RECORD_BYTES+b'\n',rows=[1])
    assert not (tmp_path/'selection').exists()
    line=b'1,a,1/1,s,0,,,'+b'x'*60000+b'\n'
    with pytest.raises(ValueError,match='512 KiB'):call(tmp_path,HEADER+line*9,rows=list(range(1,10)))
    with pytest.raises(ValueError,match='Source declaration'):call(tmp_path,source=b' '*(1048576+1))
    s=json.loads(SOURCE);s[SELECTION_KEY]={'future':'do not overwrite'}
    with pytest.raises(ValueError,match='reserved'):call(tmp_path,source=json.dumps(s).encode())

def test_concurrent_change_detection_and_existing_output(tmp_path,monkeypatch):
    from opensmell.experimental import csv_selection as module
    path=tmp_path/'input.csv';raw=HEADER+FIRST+LAST;path.write_bytes(raw)
    old=module._Lines.__next__;changed=[False]
    def mutate(self):
        line=old(self)
        if not changed[0]:path.write_bytes(raw+b'\n');changed[0]=True
        return line
    monkeypatch.setattr(module._Lines,'__next__',mutate)
    with pytest.raises((ValueError,csv.Error)):select_keller_csv(path,rows=[1],source_raw=SOURCE,directory=tmp_path/'no')
    assert not (tmp_path/'no').exists()
    monkeypatch.setattr(module._Lines,'__next__',old)
    path.write_bytes(raw);out=tmp_path/'existing';out.mkdir();(out/'keep').write_text('preserved')
    with pytest.raises(FileExistsError):select_keller_csv(path,rows=[1],source_raw=SOURCE,directory=out)
    assert (out/'keep').read_text()=='preserved' and path.read_bytes()==raw

def test_stream_larger_than_eight_mib_has_small_traced_peak(tmp_path):
    path=tmp_path/'large.csv';row=b'1,plain,1/1,subject,26,0,89,'+b'x'*1000+b'\n'
    digest=hashlib.sha256()
    with path.open('wb') as stream:
        stream.write(HEADER);digest.update(HEADER)
        for _ in range(10000):stream.write(row);digest.update(row)
    assert path.stat().st_size>8*1048576
    tracemalloc.start()
    report=select_keller_csv(path,rows=[10000,1],source_raw=SOURCE,directory=tmp_path/'selected')
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert peak<4*1048576
    assert report['selection']['input']['sha256']==digest.hexdigest()
    assert report['selection']['input']['data_record_count']==10000

@pytest.mark.parametrize('raw',[b'',b'bad\n1\n',b'CID,CID\n1,2\n',HEADER.replace(b'CID',b'cid')+FIRST])
def test_invalid_header_refuses_before_output(tmp_path,raw):
    with pytest.raises(ValueError):call(tmp_path,raw,rows=[1])
    assert not (tmp_path/'selection').exists()

def test_nonregular_and_oversized_input_refuse_without_scan(tmp_path):
    with pytest.raises(ValueError):select_keller_csv(tmp_path,rows=[1],source_raw=SOURCE,directory=tmp_path/'no')
    path=tmp_path/'sparse.csv'
    with path.open('wb') as f:f.truncate(1024*1048576+1)
    with pytest.raises(ValueError):select_keller_csv(path,rows=[1],source_raw=SOURCE,directory=tmp_path/'no')
    assert not (tmp_path/'no').exists()
