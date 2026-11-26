"""Explicit semantic or perceptual Core selection to an ordinary experimental offline plan.

No chemical representation required; no new Core or device wire contract.
"""
import base64
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json

from .._json import decode_bytes
from ..validation import validate_document
from .core_interchange import interchange_registry
from .generic_graph import generic_graph_from_dict, GENERIC_RESOURCE_GRAPH_FORMAT
from .planning import plan_with_profile
from .rendering import RenderRequest

SELECTION_KEY = 'org.opensmell.experimental.core-semantic-selection'
MAX_CORE_BYTES = 4 * 1048576


def project_core_selection(raw, representation_index):
    """Project exactly one selected supported representation, retaining all bytes."""
    if not isinstance(raw, bytes) or len(raw) > MAX_CORE_BYTES:
        raise ValueError('Core bytes required; at most 4 MiB')
    document = decode_bytes(raw)
    if not isinstance(document, dict) or 'format' in document or document.get('opensmell') != '0.1':
        raise ValueError('Expected an unambiguous Core 0.1 document')
    validate_document(document)
    from .observation_core import validate_observation_core
    validate_observation_core(document)
    representations = document['odor']['representations']
    if type(representation_index) is not int or not 0 <= representation_index < len(representations):
        raise ValueError('Explicit zero-based representation index required and must exist')
    selected = representations[representation_index]
    if selected['type'] == 'perceptual':
        from .core_perceptual import project_perceptual_selection
        return project_perceptual_selection(raw, document, representation_index)
    scheme = selected['scheme']
    if (selected['type'] != 'semantic' or scheme['id'] != 'org.opensmell.semantic.annotations'
            or scheme['version'] != '0.1'):
        raise ValueError('Selected representation must be semantic annotations 0.1; no automatic fallback')
    digest = hashlib.sha256(raw).hexdigest()
    subject = f'urn:opensmell:core-selection:{digest}:{representation_index}'
    projection = {
        'format': GENERIC_RESOURCE_GRAPH_FORMAT, 'version': '0.1',
        SELECTION_KEY: {'version':'0.1','representation_index':representation_index,
                        'source':{'encoding':'base64','data':base64.b64encode(raw).decode('ascii'),
                                  'sha256':digest,'byte_count':len(raw)}},
        'resources': [
            {'id':subject,'type':'org.opensmell.experimental.core-odor-selection','type_version':'0.1',
             'core_odor_id':document['odor']['id'],'representation_index':representation_index},
            {'id':subject+':annotation','type':'org.opensmell.annotation','type_version':'0.1',
             'subject':{'resource_id':subject},'scheme':deepcopy(scheme),'data':deepcopy(selected['data']),
             'core_representation_context':{k:deepcopy(v) for k,v in selected.items() if k not in {'scheme','data'}}}
        ]}
    return projection, subject


def validate_core_projection(document):
    """Recompute this reserved projection from retained Core bytes before export/send.

    Other generic graphs are unchanged. Integrity is not source authentication;
    removing this application convention does not authenticate a different graph.
    """
    from .core_perceptual import SELECTION_KEY as PERCEPTUAL_KEY
    keys = [key for key in (SELECTION_KEY, PERCEPTUAL_KEY) if key in document]
    if not keys:
        return
    if len(keys) != 1:
        raise ValueError('Ambiguous Core selection projection')
    selection = document[keys[0]]
    if not isinstance(selection, dict) or selection.get('version') != '0.1':
        raise ValueError('Unsupported Core selection projection')
    snapshot = selection.get('source')
    if not isinstance(snapshot, dict) or snapshot.get('encoding') != 'base64':
        raise ValueError('Missing exact Core source snapshot')
    if not isinstance(snapshot.get('data'), str) or len(snapshot['data']) > 4*((MAX_CORE_BYTES+2)//3):
        raise ValueError('Invalid or oversized Core source snapshot')
    try:
        raw = base64.b64decode(snapshot['data'], validate=True)
    except (ValueError, UnicodeError) as error:
        raise ValueError('Invalid Core snapshot encoding') from error
    expected, _ = project_core_selection(raw, selection.get('representation_index'))
    # Strict JSON comparison distinguishes bool/int and other mutated metadata.
    if json.dumps(document,sort_keys=True,allow_nan=False) != json.dumps(expected,sort_keys=True,allow_nan=False):
        raise ValueError('Core projection does not match exact source and selected representation; reprepare')


def plan_core_bytes(raw, profile_raw, *, representation_index, duration):
    """Return a passive offline-plan0.1; explicit supported selection and profile only."""
    if not isinstance(profile_raw, bytes) or len(profile_raw) > 1048576:
        raise ValueError('Profile bytes required; at most 1 MiB')
    projection, subject = project_core_selection(raw, representation_index)
    profile = decode_bytes(profile_raw)
    from .core_perceptual import SELECTION_KEY as PERCEPTUAL_KEY
    kind = 'perceptual' if PERCEPTUAL_KEY in projection else 'semantic'
    if not isinstance(profile, dict) or profile.get('mapper') != kind:
        raise ValueError('Selected Core ' + kind + ' representation requires an explicit ' + kind + ' mapping profile')
    graph = generic_graph_from_dict(projection, registry=interchange_registry())
    request = RenderRequest(subject, duration)
    plan = plan_with_profile(graph, request, profile)
    encoded_projection = json.dumps(projection,sort_keys=True,allow_nan=False).encode()
    artifact = {'format':'org.opensmell.experimental.offline-plan','version':'0.1','status':'planned',
                'execution':'not_attempted','capability_basis':'supplied_profile_not_live_device',
                'source':{'input':'explicit Core ' + kind + ' projection','sha256':hashlib.sha256(encoded_projection).hexdigest(),
                          'document':projection},
                'profile':{'input':'supplied profile','sha256':hashlib.sha256(profile_raw).hexdigest(),'document':profile},
                'request':asdict(request),'plan':asdict(plan),
                'limitations':[('Only the explicitly selected Core semantic annotations0.1 are interpreted.' if kind == 'semantic' else 'Only selected experimental Core perceptual measurements0.1 are mapped under explicit unit/scale/normalization policy.'),
                               'Exact Core bytes retain all other representations and provenance; no chemical identity is inferred.',
                               'Application mapping and supplied capabilities; no command, acceptance, execution or odor result.',
                               'Projection is an experimental application convention; hashes are not signatures.']}
    if len(json.dumps(artifact,allow_nan=False).encode()) > 8*1048576:
        raise ValueError('Resulting offline plan exceeds the existing 8 MiB input bound')
    return artifact
