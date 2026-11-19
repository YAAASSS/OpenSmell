"""GraphML behavior with the real external reader, not XML implementation mirrors."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import networkx as nx
import pytest
from opensmell.experimental.reference_graph import project_reference_graph, export_reference_graph

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'examples/multisource_diphenyl_ether.osmell'


def test_real_multisource_bundle_networkx(tmp_path):
    raw=SOURCE.read_bytes();manifest=export_reference_graph(raw,tmp_path/'bundle')
    g=nx.read_graphml(tmp_path/'bundle/references.graphml',force_multigraph=True)
    assert g.is_directed() and g.is_multigraph()
    assert len(g)==5 and g.number_of_edges()==4
    assert (tmp_path/'bundle/source.osmell').read_bytes()==raw
    assert manifest['coverage']['unresolved_target_ids']==[]
    result=subprocess.run([sys.executable,str(ROOT/'examples/networkx_graph/inspect_bundle.py'),str(tmp_path/'bundle'),
                           '--resource-id','219ef28c-9b58-52f2-93a7-0807f5897857'],capture_output=True,check=True)
    report=json.loads(result.stdout)
    assert report['outgoing_reference_occurrences']==2 and len(report['reachable_target_ids'])==3


def fixture():
    doc=json.loads(SOURCE.read_bytes())
    observation=next(r for r in doc['resources'] if r['type']=='observation')
    # Two independently declared references to the same unresolved ID.
    absent='missing <&>\\n\x00 café'
    observation['stimulus']['resource_id']=absent
    observation['target']['resource_id']=absent
    observation['stimulus']['future']={'number':2**64+1}
    doc['resources'].append({'id':'opaque','type':'org.future.unknown','type_version':'9',
                             'payload':{'resource_id':'not-a-known-reference','value':2**64+1}})
    doc['future']={'keep':[None,2**64+1]}
    return doc,observation['id'],absent


def test_parallel_unresolved_opaque_and_xml_characters(tmp_path):
    doc,rid,absent=fixture();raw=json.dumps(doc,ensure_ascii=True).encode()
    manifest=export_reference_graph(raw,tmp_path/'bundle')
    g=nx.read_graphml(tmp_path/'bundle/references.graphml',force_multigraph=True,edge_key_type=str)
    ids={json.loads(d['resource_id_json']):n for n,d in g.nodes(data=True)}
    assert g.number_of_edges(ids[rid],ids[absent])==2
    assert not g.nodes[ids[absent]]['present'] and g.nodes[ids['opaque']]['present']
    assert not g.nodes[ids['opaque']]['understood']
    assert 'not-a-known-reference' not in ids
    assert json.loads(g.nodes[ids['opaque']]['resource_json'])==doc['resources'][-1]
    assert any(json.loads(d['reference_extra_json']).get('future')=={'number':2**64+1} for _,_,d in g.edges(data=True))
    assert manifest['coverage']['unresolved_target_ids']==[absent]
    assert (tmp_path/'bundle/source.osmell').read_bytes()==raw


@pytest.mark.parametrize('raw',[b'{}',b'{"a":1,"a":2}',b'[]',b'\xff',b'x'*(8*1048576+1)])
def test_invalid_input_does_not_create_output(tmp_path,raw):
    with pytest.raises(Exception):export_reference_graph(raw,tmp_path/'no-output')
    assert not (tmp_path/'no-output').exists()


def test_cli_stdin_and_no_overwrite(tmp_path):
    command=[sys.executable,'-m','opensmell','reference-graph','-','--output-directory',str(tmp_path/'bundle')]
    first=subprocess.run(command,input=SOURCE.read_bytes(),capture_output=True)
    assert first.returncode==0,first.stdout
    before={p.name:p.read_bytes() for p in (tmp_path/'bundle').iterdir()}
    assert subprocess.run(command,input=SOURCE.read_bytes(),capture_output=True).returncode==2
    assert before=={p.name:p.read_bytes() for p in (tmp_path/'bundle').iterdir()}


def test_consumer_refuses_modified_graphml(tmp_path):
    export_reference_graph(SOURCE.read_bytes(),tmp_path/'bundle')
    path=tmp_path/'bundle/references.graphml';path.write_bytes(path.read_bytes()+b' ')
    result=subprocess.run([sys.executable,str(ROOT/'examples/networkx_graph/inspect_bundle.py'),str(tmp_path/'bundle'),
                           '--resource-id','219ef28c-9b58-52f2-93a7-0807f5897857'],capture_output=True)
    assert result.returncode!=0 and b'do not match manifest' in result.stderr


def test_self_reference_and_deterministic_projection(tmp_path):
    doc=json.loads(SOURCE.read_bytes())
    annotation=next(r for r in doc['resources'] if r['type']=='org.opensmell.annotation')
    annotation['subject']['resource_id']=annotation['id']
    raw=json.dumps(doc).encode();xml,coverage=project_reference_graph(raw)
    assert project_reference_graph(raw)==(xml,coverage)
    path=tmp_path/'self.graphml';path.write_bytes(xml)
    graph=nx.read_graphml(path,force_multigraph=True)
    assert len(list(nx.selfloop_edges(graph)))==1
