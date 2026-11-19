"""Independent NetworkX consumer of a locally generated OpenSmell GraphML bundle.

Requires NetworkX3.4.2; no OpenSmell import, file mutation, source fetching or device.
"""
import argparse
import hashlib
import json
from pathlib import Path
import networkx as nx


def inspect_bundle(directory, resource_id):
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_bytes())
    if (manifest.get('format')!='org.opensmell.experimental.reference-graph-bundle'
            or manifest.get('version')!='0.1' or manifest.get('status')!='exported'):
        raise ValueError('Expected a complete reference-graph bundle')
    for name in ('source.osmell','references.graphml'):
        raw=(directory/name).read_bytes();record=manifest['files'][name]
        if len(raw)!=record['byte_count'] or hashlib.sha256(raw).hexdigest()!=record['sha256']:
            raise ValueError('Bundle bytes do not match manifest: '+name)
    graph=nx.read_graphml(directory/'references.graphml',force_multigraph=True,edge_key_type=str)
    if not graph.is_directed():raise ValueError('Expected directed structural references')
    coverage=manifest['coverage']
    if len(graph)!=coverage['node_count'] or graph.number_of_edges()!=coverage['reference_occurrences']:
        raise ValueError('Projection coverage count mismatch')
    ids={node:json.loads(data['resource_id_json']) for node,data in graph.nodes(data=True)}
    selected=[node for node,data in graph.nodes(data=True) if ids[node]==resource_id and data['present']]
    if len(selected)!=1:raise ValueError('Select one resource present in the source')
    node=selected[0]
    return {'consumer':'NetworkX','networkx_version':nx.__version__,'coverage':'partial',
            'physical_validation':False,'resource_id':resource_id,
            'source_sha256':manifest['files']['source.osmell']['sha256'],
            'node_count':len(graph),'reference_occurrences':graph.number_of_edges(),
            'outgoing_reference_occurrences':graph.out_degree(node),
            'direct_target_ids':sorted(ids[n] for n in graph.successors(node)),
            'reachable_target_ids':sorted(ids[n] for n in nx.descendants(graph,node)),
            'unresolved_target_ids':sorted(ids[n] for n,d in graph.nodes(data=True) if not d['present']),
            'uninterpreted_resource_ids':sorted(ids[n] for n,d in graph.nodes(data=True) if d['present'] and not d['understood']),
            'limits':['Reachability is structural only, not chemical equivalence, causality or a measured odor result.',
                      'Manifest hashes identify supplied bytes, not signatures or source authentication.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path);parser.add_argument('--resource-id',required=True)
    args=parser.parse_args()
    print(json.dumps(inspect_bundle(args.bundle,args.resource_id),ensure_ascii=True))

if __name__=='__main__':main()
