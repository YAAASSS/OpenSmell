"""Passive, loss-preserving observation projection for external analysis tools."""
import base64
import hashlib

from .._json import decode_bytes
from ..exceptions import SchemeValidationError
from ..schemes.perceptual_measurements import validate
from .core_interchange import interchange_registry
from .generic_graph import GenericResource, generic_graph_from_dict

FORMAT = 'org.opensmell.experimental.observation-table'
MAX_BYTES = 8 * 1048576
PERCEPTUAL = {'id':'org.opensmell.perceptual.measurements','version':'0.1'}
CATEGORIES = 'org.opensmell.experimental.observation.categories'
SEMANTIC = 'org.opensmell.semantic.annotations'


def observation_table(raw):
    """Project known measurements into rows; retain all source bytes and context.

    A complete projection only means no unsupported/invalid data was encountered
    in the declared scope. It is not a scientific, chemical or source validation.
    Unknown contracts and invalid measurements are reported, never guessed/coerced.
    """
    if not isinstance(raw, bytes):
        raise TypeError('Graph input must be bytes')
    if len(raw) > MAX_BYTES:
        raise ValueError('Graph exceeds 8 MiB')
    document = decode_bytes(raw)
    if not isinstance(document, dict) or 'opensmell' in document:
        raise ValueError('Expected an unambiguous Generic ResourceGraph0.1')
    graph = generic_graph_from_dict(document, registry=interchange_registry())
    digest = hashlib.sha256(raw).hexdigest()
    rows, categorical, observations, issues = [], [], [], []
    resources = {r['id']:r for r in document['resources']}

    def issue(path, code, detail):
        issues.append({'path':path,'code':code,'detail':detail})

    for index,(typed,resource) in enumerate(zip(graph.resources,document['resources'])):
        path=f'/resources/{index}'
        if isinstance(typed,GenericResource):
            issue(path,'uninterpreted_resource','Unknown resource type/version retained in context and snapshot')
            continue
        if resource['type']=='org.opensmell.annotation':
            scheme=resource['scheme']
            if scheme.get('id')==SEMANTIC and scheme.get('version')=='0.1':
                categorical.append({'resource_id':resource['id'],'source_path':path,'kind':'semantic_annotation',
                                    'scheme':scheme,'data':resource.get('data',{}),'provenance':resource.get('provenance')})
            else:
                issue(path,'uninterpreted_annotation','Scheme/version not projected')
            continue
        if resource['type']!='observation':
            continue
        stimulus_id=resource['stimulus']['resource_id']
        target_id=(resource.get('target') or {}).get('resource_id')
        before=len(rows)
        for field,ref,expected in [('stimulus',stimulus_id,'stimulus'),('target',target_id,'observation_target')]:
            if ref is not None and (ref not in resources or resources[ref]['type']!=expected):
                issue(path+'/'+field,'unresolved_context_reference','Referenced '+expected+' is unavailable; ID retained without inferred context')
        for result_index,result in enumerate(resource.get('results',[])):
            result_path=f'{path}/results/{result_index}'
            scheme=result['scheme']
            if scheme.get('id')==CATEGORIES and scheme.get('version')=='0.1':
                categorical.append({'resource_id':resource['id'],'source_path':result_path,'kind':'observation_categories',
                                    'scheme':scheme,'data':result.get('data',{}),'provenance':resource.get('provenance')})
                continue
            if scheme.get('id')!=PERCEPTUAL['id'] or scheme.get('version')!=PERCEPTUAL['version']:
                issue(result_path,'uninterpreted_result','Scheme/version not projected')
                continue
            measurements=result.get('data',{}).get('measurements')
            if not isinstance(measurements,list) or not measurements:
                issue(result_path,'invalid_measurements','Known scheme requires a nonempty measurements array')
                continue
            for measurement_index,measurement in enumerate(measurements):
                measurement_path=f'{result_path}/data/measurements/{measurement_index}'
                try:
                    validate({'measurements':[measurement]})
                    if 'unit' in measurement and measurement['unit'] is not None and (
                            not isinstance(measurement['unit'],str) or not measurement['unit'].strip()):
                        raise ValueError('Explicit unit must be a nonblank string or null')
                except (SchemeValidationError,ValueError) as error:
                    issue(measurement_path,'invalid_measurement',str(error))
                    continue
                rows.append({'source_sha256':digest,'observation_id':resource['id'],
                             'stimulus_id':stimulus_id,'target_id':target_id,'result_index':result_index,
                             'measurement_index':measurement_index,'source_path':measurement_path,
                             'property':measurement['property'],'value':measurement['value'],
                             'scale_min':measurement['scale']['min'],'scale_max':measurement['scale']['max'],
                             'unit':measurement.get('unit'),
                             'unit_presence':'missing' if 'unit' not in measurement else 'null' if measurement['unit'] is None else 'value'})
        observations.append({'observation_id':resource['id'],'stimulus_id':stimulus_id,'target_id':target_id,
                             'measurement_count':len(rows)-before,'source_path':path})
    return {'format':FORMAT,'version':'0.1','experimental':True,
            'status':'partial' if issues else 'projected','execution':'not_attempted','physical_validation':False,
            'source':{'encoding':'base64','data':base64.b64encode(raw).decode('ascii'),
                      'sha256':digest,'byte_count':len(raw)},
            'tables':{'measurements':rows,'categorical':categorical,'observations':observations},
            'context':document,'coverage':{'issues':issues,'measurement_count':len(rows),
                                          'categorical_count':len(categorical),'observation_count':len(observations)},
            'limits':['Known perceptual0.1 numeric projection only; no normalization, joining, imputation or aggregation.',
                      'Absent measurements produce no numeric row; zero remains zero; source unit/scale retained without conversion.',
                      'Categorical payloads stay opaque and separate from numerical values.',
                      'Context and original bytes preserve unknown fields and rejected payloads; partial is not full validation.',
                      'Source declarations are unauthenticated; no device acceptance, physical execution or measured odor result is established.']}
