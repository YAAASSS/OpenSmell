"""Passive, ordered trial-table compiler. No transport or executable selection."""
import csv
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path

from .._json import decode_bytes
from .core_interchange import interchange_registry
from .generic_graph import generic_graph_from_dict
from .planning import plan_with_profile
from .rendering import RenderRequest
from .frame_export import encode_plan_frame


def prepare_experiment(table_raw, graph_raw, profile_raw, directory):
    """Compile one explicit CSV/graph/profile into normal offline-plan artifacts.

    Required CSV columns: trial_id,resource_id,duration. Other columns are opaque
    caller annotations. All rows validate before exclusive directory creation.
    Exact source bytes are retained. No skip, shuffle, implicit resource/profile,
    command, execution, authentication or physical interpretation is supplied.
    """
    for raw, bound in ((table_raw, 65536), (graph_raw, 8*1048576), (profile_raw, 1048576)):
        if not isinstance(raw, bytes) or len(raw) > bound:
            raise ValueError("CSV/graph/profile require bytes within 64 KiB/8 MiB/1 MiB")
    reader = csv.reader(io.StringIO(table_raw.decode('utf-8-sig'), newline=''), strict=True)
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("Trial table is empty") from None
    required = {'trial_id', 'resource_id', 'duration'}
    if (not required.issubset(header) or len(set(header)) != len(header)
            or any(not name.strip() for name in header)):
        raise ValueError("Unique nonempty headers including trial_id,resource_id,duration required")
    doc, profile = decode_bytes(graph_raw), decode_bytes(profile_raw)
    graph = generic_graph_from_dict(doc, registry=interchange_registry())
    sha = lambda raw: hashlib.sha256(raw).hexdigest()
    rows, plans, ids, total = [], {}, set(), 0
    for row in reader:
        if len(rows) >= 16 or len(row) != len(header):
            raise ValueError("At most 16 complete trial rows are allowed; blank/ragged rows refused")
        record = dict(zip(header, row)); trial_id = record['trial_id']
        if not trial_id.strip() or len(trial_id) > 128 or trial_id in ids:
            raise ValueError("Unique trial IDs of 1–128 characters required")
        ids.add(trial_id)
        request = RenderRequest(record['resource_id'], float(record['duration']))
        plan = plan_with_profile(graph, request, profile)
        total += plan.duration
        if total > 120:
            raise ValueError("Total requested duration exceeds 120 seconds")
        artifact = {'format':'org.opensmell.experimental.offline-plan','version':'0.1','status':'planned',
                    'execution':'not_attempted','capability_basis':'supplied_profile_not_live_device',
                    'source':{'input':'source.osmell','sha256':sha(graph_raw),'document':doc},
                    'profile':{'input':'profile.json','sha256':sha(profile_raw),'document':profile},
                    'request':asdict(request),'plan':asdict(plan),
                    'org.opensmell.experimental.trial':{'ordinal':len(rows)+1,'record':record,'table_sha256':sha(table_raw)},
                    'limitations':['Caller mapping and supplied capabilities; no command, observed execution or odor result.']}
        encoded = (json.dumps(artifact, indent=2, allow_nan=False, ensure_ascii=True)+'\n').encode()
        # Use the same actionable-artifact checks as the normal frame/sequence entry.
        encode_plan_frame(encoded, json.dumps(profile['capabilities'], allow_nan=False).encode())
        name = f'plan-{len(rows)+1:03d}.json'  # Caller IDs never become filenames.
        plans[name] = encoded
        rows.append({'ordinal':len(rows)+1,'trial_id':trial_id,'record':record,'plan_file':name})
    if not rows:
        raise ValueError("At least one trial row required")
    if sum(map(len, plans.values())) > 16*1048576:
        raise ValueError("Combined offline plans exceed sequence input bound of 16 MiB")
    files = {'trials.csv':table_raw,'source.osmell':graph_raw,'profile.json':profile_raw,**plans}
    result = {'format':'org.opensmell.experimental.prepared-experiment','version':'0.1','status':'prepared',
              'experimental':True,'execution':'not_attempted','physical_validation':False,
              'total_requested_duration':total,'trials':rows,
              'files':{name:{'sha256':sha(raw),'byte_count':len(raw)} for name,raw in files.items()},
              'limits':['CSV order is caller design, not randomized or scientifically validated.',
                        'Opaque annotations do not alter resource selection, mapping or duration.',
                        'Hashes identify supplied bytes, not authenticity; unknown source context retained.',
                        'Preparation is passive; sending requires an independent explicit software invocation.',
                        'A plan is not a command, acceptance, execution observation or measured odor outcome.']}
    output = Path(directory); output.mkdir(parents=True, exist_ok=False)
    marker = output/'experiment.json'
    marker.write_text('{"status":"incomplete","execution":"not_attempted"}\n')
    for name, raw in files.items():
        with (output/name).open('xb') as target: target.write(raw)
    pending = output/'experiment.pending'
    with pending.open('x') as target: json.dump(result, target, indent=2, allow_nan=False); target.write('\n')
    pending.replace(marker)
    return result
