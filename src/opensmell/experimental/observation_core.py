"""Passive selected observation-result -> Core, retaining exact source context."""
import base64
from copy import deepcopy
import hashlib
import json

from .._json import decode_bytes
from ..validation import validate_document
from ..schemes.perceptual_measurements import validate
from .core_interchange import interchange_registry
from .generic_graph import generic_graph_from_dict
from .resources import Observation

EXPORT_KEY = 'org.opensmell.experimental.observation-core-export'
RESULT_CONTEXT_KEY = 'org.opensmell.experimental.observation-result-context'
MAX_GRAPH_BYTES = 2 * 1048576
MAX_CORE_BYTES = 4 * 1048576


def export_observation_core(raw, *, observation_id, result_index, odor_id):
    """Select one supplied quantitative result, not an inferred odor identity.

    Preserve the entire exact graph, other results, unknown data and provenance.
    No unit conversion, normalization, aggregation, default selection or IO.
    """
    if not isinstance(raw, bytes) or len(raw) > MAX_GRAPH_BYTES:
        raise ValueError('Graph bytes required, at most2MiB for this embedded-source export')
    if any(not isinstance(v,str) or not v.strip() or len(v)>128 for v in (observation_id,odor_id)):
        raise ValueError('Explicit observation and caller-owned odor IDs of1–128 characters required')
    document = decode_bytes(raw)
    if not isinstance(document,dict) or 'opensmell' in document:
        raise ValueError('Expected an unambiguous Generic ResourceGraph0.1')
    graph = generic_graph_from_dict(document,registry=interchange_registry())
    observation = graph.get(observation_id)
    if not isinstance(observation,Observation):
        raise ValueError('Select an existing supported Observation resource, not a subject/stimulus/molecule')
    original = next(r for r in document['resources'] if r['id'] == observation_id)
    results = original.get('results',[])
    if type(result_index) is not int or not 0 <= result_index < len(results):
        raise ValueError('Explicit zero-based existing result index required')
    selected = results[result_index]
    if (selected['scheme'].get('id') != 'org.opensmell.perceptual.measurements'
            or selected['scheme'].get('version') != '0.1'):
        raise ValueError('Selected result must use provisional perceptual measurements0.1; no fallback')
    validate(selected['data'])
    for m in selected['data']['measurements']:
        if 'unit' in m and m['unit'] is not None and (not isinstance(m['unit'],str) or not m['unit'].strip()):
            raise ValueError('Selected measurement unit must be nonblank string/null/absent')
    digest = hashlib.sha256(raw).hexdigest()
    result = {'opensmell':'0.1','odor':{'id':odor_id,
        'representations':[{'type':'perceptual','scheme':deepcopy(selected['scheme']),
            'data':deepcopy(selected['data']),
            'provenance':{'source_graph_sha256':digest,'observation_id':observation_id,'result_index':result_index,
                          'scope':'Explicit selected supplied result; no authenticated or inferred odor equivalence'},
            RESULT_CONTEXT_KEY:{k:deepcopy(v) for k,v in selected.items() if k not in {'scheme','data'}}}],
        'metadata':{'description':'Explicit projection of one supplied observation result; not inferred chemistry or presentation.'}},
        EXPORT_KEY:{'version':'0.1','operation':'passive-result-selection',
            'selection':{'observation_id':observation_id,'result_index':result_index,'odor_id':odor_id},
            'source':{'encoding':'base64','data':base64.b64encode(raw).decode('ascii'),
                      'sha256':digest,'byte_count':len(raw)},
            'limits':['Caller odor ID is not a chemical identity or stimulus/participant equivalence claim.',
                      'Only selected result is projected; exact entire graph retains context, other results and unknown data.',
                      'No unit conversion, normalization, averaging, transport, execution or measured odor result is established.',
                      'Integrity/content identifiers are not source authentication.']}}
    validate_document(result)
    encoded = (json.dumps(result,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()
    if len(encoded)>MAX_CORE_BYTES:
        raise ValueError('Result exceeds4MiB Core input bound; no truncation is permitted')
    return encoded


def validate_observation_core(document):
    """Recompute the reserved export from source before its Core data is consumed.

    Other Core documents are unchanged. Removing an unsigned convention cannot
    authenticate the resulting independent document; this is consistency only.
    """
    if EXPORT_KEY not in document:
        return None
    context = document[EXPORT_KEY]
    if not isinstance(context,dict) or context.get('version') != '0.1':
        raise ValueError('Unsupported observation Core export convention')
    snapshot = context.get('source');selection = context.get('selection')
    if (not isinstance(snapshot,dict) or snapshot.get('encoding') != 'base64'
            or not isinstance(snapshot.get('data'),str) or len(snapshot['data']) > 4*((MAX_GRAPH_BYTES+2)//3)
            or not isinstance(selection,dict)):
        raise ValueError('Expected bounded exact graph source and explicit export selection')
    try:
        original = base64.b64decode(snapshot['data'],validate=True)
    except (ValueError,UnicodeError) as error:
        raise ValueError('Invalid embedded graph encoding') from error
    if (type(snapshot.get('byte_count')) is not int or snapshot['byte_count'] != len(original)
            or snapshot.get('sha256') != hashlib.sha256(original).hexdigest()):
        raise ValueError('Embedded graph integrity mismatch')
    expected = decode_bytes(export_observation_core(original,
        observation_id=selection.get('observation_id'),result_index=selection.get('result_index'),odor_id=selection.get('odor_id')))
    if json.dumps(document,sort_keys=True,allow_nan=False) != json.dumps(expected,sort_keys=True,allow_nan=False):
        raise ValueError('Core export does not match original graph/selection; re-export from changed source')
    return original


def extract_observation_source(raw):
    """Recover exact original graph bytes from a consistent exported Core."""
    if not isinstance(raw,bytes) or len(raw)>MAX_CORE_BYTES:
        raise ValueError('Exported Core bytes required, at most4MiB')
    document = decode_bytes(raw)
    if not isinstance(document,dict) or document.get('opensmell') != '0.1' or 'format' in document:
        raise ValueError('Expected an unambiguous Core0.1 export')
    validate_document(document)
    original = validate_observation_core(document)
    if original is None:
        raise ValueError('No supported observation export source snapshot')
    return original
