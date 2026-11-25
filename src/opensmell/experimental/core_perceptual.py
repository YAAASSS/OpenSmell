"""Experimental Core quantitative projection; no measured Observation is invented."""
import base64
from copy import deepcopy
import hashlib
import math

from ..schemes.perceptual_measurements import validate
from .generic_graph import GENERIC_RESOURCE_GRAPH_FORMAT, generic_graph_to_dict
from .perceptual_channel_mapper import PerceptualChannelMapper
from .rendering import DeviceCommand, RenderingPlan

SELECTION_KEY = 'org.opensmell.experimental.core-perceptual-selection'
POLICY_KEY = 'org.opensmell.experimental.core-perceptual-policy'
NORMALIZATION = 'value-minus-min-over-range'
SCHEME = {'id':'org.opensmell.perceptual.measurements','version':'0.1'}


def project_perceptual_selection(raw, document, index):
    """Project one already envelope-validated Core representation as opaque data."""
    selected = document['odor']['representations'][index]
    if selected['type'] != 'perceptual' or any(selected['scheme'].get(k) != v for k,v in SCHEME.items()):
        raise ValueError('Selected perceptual representation must use measurements0.1')
    validate(selected['data'])
    digest = hashlib.sha256(raw).hexdigest()
    subject = f'urn:opensmell:core-perceptual-selection:{digest}:{index}'
    return {'format':GENERIC_RESOURCE_GRAPH_FORMAT,'version':'0.1',
            SELECTION_KEY:{'version':'0.1','representation_index':index,
                           'source':{'encoding':'base64','data':base64.b64encode(raw).decode('ascii'),
                                     'sha256':digest,'byte_count':len(raw)}},
            'resources':[{'id':subject,'type':'org.opensmell.experimental.core-perceptual-representation',
                          'type_version':'0.1','core_odor_id':document['odor']['id'],
                          'scheme':deepcopy(selected['scheme']),'data':deepcopy(selected['data']),
                          'core_representation_context':{k:deepcopy(v) for k,v in selected.items() if k not in {'scheme','data'}}}]},subject


def map_core_perceptual(graph, request, profile, mapper):
    """Reuse the demonstration mapper's formula under explicit source expectations.

    Only this reserved Core projection understands the policy extension. Ordinary
    graph/semantic mapping remains unchanged. Units are compared, never converted.
    """
    from .core_planning import validate_core_projection
    document = generic_graph_to_dict(graph)
    validate_core_projection(document)
    if not isinstance(mapper, PerceptualChannelMapper):
        raise ValueError('Core perceptual selection requires mapper:perceptual')
    selected = document['resources'][0]
    if request.resource_id != selected['id']:
        raise ValueError('Request must select the explicitly projected Core subject')
    policy = profile.get(POLICY_KEY)
    if (not isinstance(policy, dict) or policy.get('version') != '0.1'
            or policy.get('normalization') != NORMALIZATION):
        raise ValueError('Explicit Core perceptual policy/version and normalization required')
    expectations = policy.get('measurements')
    if not isinstance(expectations, list) or not expectations:
        raise ValueError('Core perceptual policy requires measurement expectations')
    by_property = {}
    for entry in expectations:
        if (not isinstance(entry, dict) or not isinstance(entry.get('property'), str)
                or not entry['property'].strip() or entry['property'] in by_property):
            raise ValueError('Unique nonblank policy properties required')
        scale = entry.get('scale')
        if (not isinstance(scale, dict) or any(isinstance(scale.get(k), bool)
                or not isinstance(scale.get(k),(int,float)) for k in ('min','max'))
                or scale['min'] >= scale['max']):
            raise ValueError('Policy requires explicit numeric min<max scale')
        try:
            if not all(math.isfinite(float(scale[k])) for k in ('min','max')) or float(scale['min']) >= float(scale['max']):
                raise ValueError('Policy scale must be finite and usable by the float demonstration mapper')
        except OverflowError as error:
            raise ValueError('Policy scale exceeds demonstration mapper range') from error
        if 'unit' in entry and entry['unit'] is not None and (not isinstance(entry['unit'],str) or not entry['unit'].strip()):
            raise ValueError('Policy unit must be a nonblank string or null; omission requires absent source unit')
        by_property[entry['property']] = entry
    if set(by_property) != {b.property for b in mapper.bindings}:
        raise ValueError('Policy properties must match the explicit bindings exactly')
    measurements = selected['data']['measurements']
    commands = []
    for binding in mapper.bindings:
        candidates = [m for m in measurements if m['property'] == binding.property]
        if len(candidates) != 1:
            raise ValueError('Each bound property requires exactly one selected measurement: ' + binding.property)
        measurement, expectation = candidates[0], by_property[binding.property]
        if ('unit' in measurement) != ('unit' in expectation) or measurement.get('unit') != expectation.get('unit'):
            raise ValueError('Selected measurement unit/presence does not match policy: ' + binding.property)
        if any(measurement['scale'][k] != expectation['scale'][k] for k in ('min','max')):
            raise ValueError('Selected measurement scale does not match policy: ' + binding.property)
        try:
            parsed = mapper._parse_measurement(measurement)
            if parsed is None or not math.isfinite(parsed[1]):
                raise ValueError('Selected measurement cannot be normalized')
        except (OverflowError,ZeroDivisionError) as error:
            raise ValueError('Selected measurement exceeds demonstration mapper range') from error
        commands.append(DeviceCommand(binding.channel, parsed[1]))
    return RenderingPlan(commands, request.duration,
                         extra={'mapper':'org.opensmell.experimental.core-perceptual-channel-mapper',
                                'source_resource_id':request.resource_id,'normalization':NORMALIZATION,
                                'policy_key':POLICY_KEY})
