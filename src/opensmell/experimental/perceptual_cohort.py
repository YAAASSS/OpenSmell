"""Bounded selected prepared-CSV cohort. Passive, no joins or aggregation."""
import base64
import binascii
import csv
import hashlib
import io
import json

from .._json import decode_bytes
from ..exceptions import OpenSmellError
from .perceptual_import import import_keller_csv, _source, IMPORT_KEY, IDENTITY_COLUMNS, RATING_COLUMNS
from .generic_graph import GenericResourceGraph, generic_graph_to_dict
from .core_interchange import interchange_registry

COHORT_KEY = 'org.opensmell.experimental.perceptual-csv-cohort'
MAX_CSV_BYTES = 512 * 1024
MAX_GRAPH_BYTES = 2 * 1048576
MAX_RECORDS = 100


def import_keller_cohort(raw, *, rows, source):
    """Return bounded graph bytes, preserving selection order and every outcome.

    Reuse single-row occurrence IDs and validators. Source/CSV errors refuse the
    whole operation; invalid/missing selected records become explicit refusals.
    Exact whole CSV retained, including unselected data; no redaction implied.
    """
    if not isinstance(raw, bytes):
        raise TypeError('CSV input must be bytes')
    if len(raw) > MAX_CSV_BYTES:
        raise ValueError('Cohort CSV exceeds 512 KiB')
    if (not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= MAX_RECORDS
            or any(type(r) is not int or r < 1 for r in rows) or len(set(rows)) != len(rows)):
        raise ValueError('Select 1..100 unique positive logical data records in caller order')
    source, source_hash = _source(source)
    reader = csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
    headers = next(reader, None)
    if (not headers or any(not h or h != h.strip() for h in headers)
            or len(set(headers)) != len(headers) or any(h not in headers for h in IDENTITY_COLUMNS)
            or not any(h in headers for h in RATING_COLUMNS)):
        raise ValueError('Invalid prepared CSV headers')
    # Syntax is global for this whole-CSV snapshot, unlike selected single-row import.
    for _ in reader:
        pass
    resources, outcomes = [], []
    for row in rows:
        try:
            graph = import_keller_csv(raw, row=row, source=source)
        except (OpenSmellError, ValueError, TypeError, csv.Error, OverflowError) as error:
            outcomes.append({'data_record': row, 'status': 'refused', 'error': str(error)})
        else:
            context = graph.extra[IMPORT_KEY]
            outcomes.append({'data_record': row, 'status': 'accepted',
                             'observation_id': context['primary_resource_id'], 'import_context': context})
            resources.extend(graph.resources)
    accepted = sum(r['status'] == 'accepted' for r in outcomes)
    context = {'version': '0.1', 'requested_records': list(rows),
               'status': 'complete' if accepted == len(rows) else 'partial' if accepted else 'refused',
               'counts': {'accepted': accepted, 'refused': len(rows)-accepted}, 'results': outcomes,
               'source': source, 'source_manifest_sha256': source_hash,
               'csv': {'encoding': 'base64', 'data': base64.b64encode(raw).decode('ascii'),
                       'byte_count': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
               'limitations': ['Whole original CSV retained, including unselected/invalid records; not redacted.',
                              'Caller source/license/subject/CID declarations are unverified, not authenticated.',
                              'Occurrence IDs retained; no chemical/person joins, aggregation, imputation or commands.',
                              'Accepted includes observations without numeric results; planning may refuse.',
                              'Only extract-keller-source recomputes this convention; ordinary graph consumers do not.']}
    graph = GenericResourceGraph(resources=resources, extra={COHORT_KEY: context})
    output = (json.dumps(generic_graph_to_dict(graph, registry=interchange_registry()),
                         indent=2, ensure_ascii=True, allow_nan=False)+'\n').encode()
    if len(output) > MAX_GRAPH_BYTES:
        raise ValueError('Serialized cohort graph exceeds 2 MiB; select a smaller prepared source/cohort')
    return output


def extract_keller_source(raw):
    """Recover exact CSV only after recomputing the complete cohort convention."""
    if not isinstance(raw, bytes):
        raise TypeError('Graph input must be bytes')
    if len(raw) > MAX_GRAPH_BYTES:
        raise ValueError('Cohort graph exceeds 2 MiB')
    document = decode_bytes(raw)
    if not isinstance(document, dict) or 'opensmell' in document:
        raise ValueError('Expected an unambiguous cohort graph')
    context = document.get(COHORT_KEY)
    if not isinstance(context, dict) or context.get('version') != '0.1':
        raise ValueError('Missing/unsupported cohort context')
    snapshot = context.get('csv')
    if (not isinstance(snapshot, dict) or snapshot.get('encoding') != 'base64'
            or not isinstance(snapshot.get('data'), str) or len(snapshot['data']) > 4*((MAX_CSV_BYTES+2)//3)):
        raise ValueError('Invalid/bounded CSV snapshot required')
    try:
        source = base64.b64decode(snapshot['data'], validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError('Invalid CSV snapshot encoding') from error
    if (type(snapshot.get('byte_count')) is not int or len(source) != snapshot['byte_count']
            or hashlib.sha256(source).hexdigest() != snapshot.get('sha256')):
        raise ValueError('CSV snapshot hash/size mismatch')
    expected = decode_bytes(import_keller_cohort(source, rows=context.get('requested_records'), source=context.get('source')))
    # Exact JSON comparison also distinguishes bool/int and null/absent. Original
    # source byte identity does not require unchanged outer JSON whitespace.
    canonical = lambda d: json.dumps(d, sort_keys=True, ensure_ascii=True, allow_nan=False)
    if canonical(document) != canonical(expected):
        raise ValueError('Cohort source/selection/outcomes/resources are inconsistent; re-import changes')
    return source
