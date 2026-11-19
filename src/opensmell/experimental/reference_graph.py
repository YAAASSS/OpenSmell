"""Passive, experimental structural-reference GraphML projection (stdlib only)."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from .._json import decode_bytes
from .core_interchange import interchange_registry
from .generic_graph import generic_graph_from_dict, GenericResource
from .reference_discovery import discover_graph_references

MAX_BYTES = 8 * 1048576
NS = 'http://graphml.graphdrawing.org/xmlns'


def project_reference_graph(raw):
    """Return GraphML bytes and coverage for known structural references only.

    IDs are graph-local opaque values, never chemical equivalence claims. One
    directed edge per discovery occurrence preserves parallel references. Unknown
    resources remain nodes with uninterpreted JSON; missing targets are explicit
    placeholders. The exact original input must accompany this partial view.
    """
    if not isinstance(raw, bytes) or len(raw)>MAX_BYTES:
        raise ValueError('Expected graph bytes, at most 8 MiB')
    document=decode_bytes(raw)
    graph=generic_graph_from_dict(document,registry=interchange_registry())
    references=discover_graph_references(graph)
    nodes=[];by_id={};unknown=[]
    for index,(resource,original) in enumerate(zip(graph.resources,document['resources'])):
        understood=not isinstance(resource,GenericResource)
        if not understood:unknown.append(resource.id)
        node={'node_id':f'n{len(nodes)}','resource_id':resource.id,'present':True,
              'understood':understood,'source_index':index,'resource':original}
        by_id[resource.id]=node['node_id'];nodes.append(node)
    missing=[]
    for reference in references:
        if reference.target_id not in by_id:
            missing.append(reference.target_id)
            node={'node_id':f'n{len(nodes)}','resource_id':reference.target_id,'present':False,
                  'understood':False,'source_index':-1,'resource':None}
            by_id[reference.target_id]=node['node_id'];nodes.append(node)
    root=ET.Element('graphml',xmlns=NS)
    keys=[('sha256','graph','string'),('resource_id_json','node','string'),
          ('resource_json','node','string'),('present','node','boolean'),
          ('understood','node','boolean'),('source_index','node','int'),
          ('reference_extra_json','edge','string'),('discovery_index','edge','int')]
    for name,scope,kind in keys:
        ET.SubElement(root,'key',{'id':name,'for':scope,'attr.name':name,'attr.type':kind})
    body=ET.SubElement(root,'graph',{'id':'opensmell','edgedefault':'directed'})
    def data(element,key,value):ET.SubElement(element,'data',{'key':key}).text=value
    def encoded(value):return json.dumps(value,ensure_ascii=True,allow_nan=False,separators=(',',':'))
    digest=hashlib.sha256(raw).hexdigest();data(body,'sha256',digest)
    for node in nodes:
        item=ET.SubElement(body,'node',{'id':node['node_id']})
        data(item,'resource_id_json',encoded(node['resource_id']))
        data(item,'resource_json',encoded(node['resource']))
        for field in ('present','understood'):data(item,field,str(node[field]).lower())
        data(item,'source_index',str(node['source_index']))
    for index,reference in enumerate(references):
        edge=ET.SubElement(body,'edge',{'id':f'e{index}','source':by_id[reference.source_id],'target':by_id[reference.target_id]})
        data(edge,'reference_extra_json',encoded(reference.reference.extra))
        data(edge,'discovery_index',str(index))
    xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n'
    report={'projection':'known-structural-references-v1','experimental':True,'physical_validation':False,
            'coverage':'partial','source_sha256':digest,'resource_count':len(graph.resources),
            'node_count':len(nodes),'reference_occurrences':len(references),
            'unresolved_target_ids':missing,'uninterpreted_resource_ids':unknown,
            'nodes':[{k:v for k,v in n.items() if k!='resource'} for n in nodes],
            'limits':['Only registered structural references are projected; arbitrary JSON/scheme payloads are never scanned.',
                      'No edge role/path or chemical identity/equivalence is inferred; each edge is one discovery occurrence.',
                      'Known resource envelopes may contain unknown schemes; understood is not full scientific validation.',
                      'GraphML edits do not modify the original .osmell; no GraphML-to-OpenSmell reconstruction is supplied.',
                      'Provenance is supplied, not authenticated; neither device action nor odor outcome is established.']}
    return xml,report


def export_reference_graph(raw, output_directory):
    """Validate first, exclusively create a bundle, retain source bytes unchanged."""
    xml,coverage=project_reference_graph(raw)
    output=Path(output_directory)
    output.mkdir(parents=True,exist_ok=False)
    manifest={'format':'org.opensmell.experimental.reference-graph-bundle','version':'0.1',
              'status':'incomplete','coverage':coverage}
    path=output/'manifest.json'
    path.write_text(json.dumps(manifest,indent=2,ensure_ascii=True)+'\n')
    files={'source.osmell':raw,'references.graphml':xml}
    for name,data in files.items():
        with (output/name).open('xb') as target:target.write(data)
    manifest.update(status='exported',files={name:{'sha256':hashlib.sha256(data).hexdigest(),'byte_count':len(data)} for name,data in files.items()})
    pending=output/'manifest.pending'
    pending.write_text(json.dumps(manifest,indent=2,ensure_ascii=True)+'\n')
    pending.replace(path)
    return manifest
