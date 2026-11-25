"""Passive explicit trial/observation join; never constructs or opens a transport."""
import csv
from dataclasses import asdict
from collections import Counter
from copy import deepcopy
import io
import json
from pathlib import Path

from .._json import decode_bytes
from .experiment_run import load_prepared_experiment
from .frame_export import _snapshot
from .observation_table import observation_table
from .transport_sequence import prepare_steps

MAX_REPORT_BYTES = 64 * 1048576
MAX_OBSERVATION_BYTES = 8 * 1048576
MAX_BINDING_BYTES = 65536
TERMINAL = {'completed', 'stopped', 'rejected', 'unknown', 'not_attempted'}


def analyze_experiment(directory, report_raw, observations_raw, bindings_raw):
    """Join explicit CSV trial_id,observation_id pairs to known observation rows.

    Exact inputs are retained; unmatched/ambiguous bindings and unfinished receipts
    make the result partial, never fabricate zero/missing measurements. Reports are
    unauthenticated declarations; consistency is not proof of physical delivery.
    """
    for raw, bound in ((report_raw, MAX_REPORT_BYTES), (observations_raw, MAX_OBSERVATION_BYTES),
                       (bindings_raw, MAX_BINDING_BYTES)):
        if not isinstance(raw, bytes) or len(raw) > bound:
            raise ValueError('Report/observations/bindings require bytes within 64 MiB/8 MiB/64 KiB')
    plans, context = load_prepared_experiment(directory)
    report = decode_bytes(report_raw)
    if (not isinstance(report, dict) or report.get('format') != 'org.opensmell.experimental.transport-sequence'
            or report.get('version') != '0.1' or report.get('physical_validation') is not False):
        raise ValueError('Expected experimental transport-sequence0.1 report without physical validation')
    retained = report.get('prepared_experiment')
    if not isinstance(retained, dict) or any(retained.get(k) != v for k,v in context.items()):
        raise ValueError('Report belongs to a different or altered prepared dossier')
    projected = observation_table(observations_raw)
    issues = [{'scope':'observations', **deepcopy(i)} for i in projected['coverage']['issues']]
    def issue(code, **details):
        issues.append({'scope':'join', 'code':code, **details})
    sequence = report.get('sequence')
    expected_steps = prepare_steps(plans)
    steps = [None] * len(plans)
    if sequence is None:
        issue('no_sequence_receipts')
    else:
        if (not isinstance(sequence, dict) or sequence.get('format') != 'org.opensmell.experimental.sequence'
                or sequence.get('version') != '0.1' or not isinstance(sequence.get('steps'), list)
                or len(sequence['steps']) != len(plans)):
            raise ValueError('Expected one ordered sequence step per prepared trial')
        steps = sequence['steps']
        if sequence.get('physical_validation') is not False:
            raise ValueError('Contradictory physical-validation declaration in sequence')
        if report.get('status') == 'completed' and (sequence.get('status') != 'completed'
                or any(not isinstance(step, dict) or step.get('state') != 'completed' for step in steps)):
            raise ValueError('Completed report requires every declared sequence step to be completed')
        for step, expected, trial in zip(steps, expected_steps, context['trial_order']):
            if (not isinstance(step, dict) or step.get('step_id') != expected.step_id
                    or step.get('trial_id') != trial['trial_id'] or step.get('plan') != asdict(expected.plan)
                    or not isinstance(step.get('context'), dict)
                    or any(step['context'].get(k) != v for k,v in expected.context.items())
                    or not isinstance(step.get('state'), str)):
                raise ValueError('Sequence step/plan snapshot does not match selected dossier')
            execution = step.get('execution')
            if ((execution is None and step['state'] != 'not_attempted')
                    or (execution is not None and (not isinstance(execution, dict)
                        or execution.get('state') != step['state']
                        or execution.get('request_id') != step.get('request_id')
                        or step['state'] == 'not_attempted'))):
                raise ValueError('Inconsistent declared step and execution states')
            if step['state'] not in TERMINAL:
                issue('unfinished_or_uninterpreted_receipt', trial_id=trial['trial_id'], state=step['state'])
    if report.get('phase') != 'finished':
        issue('unfinished_report', phase=report.get('phase'))
    # A failed live preflight can leave a non-complete report whose steps are all
    # not_attempted. Preserve this declaration separately rather than inventing IO.
    if report.get('status') != 'completed':
        issue('sequence_not_completed', declared_status=report.get('status'))
    reader = csv.reader(io.StringIO(bindings_raw.decode('utf-8-sig'), newline=''), strict=True)
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError('Bindings CSV header required') from None
    if (not {'trial_id','observation_id'}.issubset(header) or len(set(header)) != len(header)
            or any(not h.strip() for h in header)):
        raise ValueError('Unique nonblank headers including trial_id,observation_id required')
    records = []
    for row in reader:
        if len(records) >= 4096 or len(row) != len(header):
            raise ValueError('At most4096 complete binding rows; no ragged/blank rows')
        record = dict(zip(header,row))
        if any(not record[k].strip() or len(record[k]) > 128 for k in ('trial_id','observation_id')):
            raise ValueError('Explicit trial/observation IDs of1–128 characters required')
        records.append(record)
    trial_ids = {t['trial_id'] for t in context['trial_order']}
    obs_ids = {o['observation_id'] for o in projected['tables']['observations']}
    counts = Counter(r['observation_id'] for r in records)
    bindings, selected = [], {}
    for index, record in enumerate(records):
        trial, obs = record['trial_id'], record['observation_id']
        problems = []
        if trial not in trial_ids: problems.append('unmatched_trial')
        if obs not in obs_ids: problems.append('unmatched_observation')
        if counts[obs] != 1: problems.append('ambiguous_observation_binding')
        for code in problems: issue(code, binding_index=index, trial_id=trial, observation_id=obs)
        bindings.append({'binding_index':index, 'record':record, 'status':'unmatched_or_ambiguous' if problems else 'joined'})
        if not problems:
            selected[obs] = (trial, index, record)
    trials = []
    for trial, step in zip(context['trial_order'], steps):
        matched = [o for o,b in selected.items() if b[0] == trial['trial_id']]
        if not matched: issue('trial_without_observation', trial_id=trial['trial_id'])
        state = step['state'] if step else 'unrecorded'
        execution = step.get('execution') if step else None
        trials.append({'ordinal':trial['ordinal'], 'trial_id':trial['trial_id'],
                       'caller_record':deepcopy(trial['record']), 'receipt_state':state,
                       'request_id':step.get('request_id') if step else None,
                       'execution_id':execution.get('execution_id') if execution else None,
                       'observation_ids':matched})
    for obs in sorted(obs_ids - selected.keys()): issue('observation_without_trial', observation_id=obs)
    by_trial = {t['trial_id']:t for t in trials}
    def join(rows):
        joined = []
        for row in rows:
            # Categorical projections include semantic annotations. They are not
            # observations and must never be assigned merely by an equal ID.
            obs = row.get('observation_id') or (row.get('resource_id') if row.get('kind') == 'observation_categories' else None)
            if obs not in selected: continue
            trial, index, record = selected[obs]
            joined.append({**deepcopy(row), 'trial_id':trial,
                           'ordinal':by_trial[trial]['ordinal'], 'receipt_state':by_trial[trial]['receipt_state'],
                           'binding_index':index, 'binding_record':deepcopy(record)})
        return sorted(joined, key=lambda row: row["ordinal"])
    measurements = join(projected['tables']['measurements'])
    categorical = join(projected['tables']['categorical'])
    for trial in trials:
        trial['measurement_count'] = sum(r['trial_id'] == trial['trial_id'] for r in measurements)
        trial['categorical_count'] = sum(r['trial_id'] == trial['trial_id'] for r in categorical)
    for obs in selected:
        if not any(r['observation_id'] == obs for r in projected['tables']['measurements']) and not any(
                r.get('kind') == 'observation_categories' and r['resource_id'] == obs for r in projected['tables']['categorical']):
            issue('observation_without_projected_results', observation_id=obs)
    return {'format':'org.opensmell.experimental.trial-analysis', 'version':'0.1',
            'experimental':True, 'status':'partial' if issues else 'joined',
            'execution':'not_attempted', 'physical_validation':False,
            'inputs':{'execution_report':_snapshot(report_raw), 'observations':_snapshot(observations_raw),
                      'bindings':_snapshot(bindings_raw), 'prepared_experiment':context},
            'tables':{'trials':trials, 'measurements':measurements,
                      'categorical':categorical, 'bindings':bindings},
            'observation_projection':projected, 'coverage':{'issues':issues},
            'limits':['Passive explicit ID join; no transport, retry, normalization, imputation, statistics or efficacy claim.',
                      'Each observation may bind once; repeats/ambiguous associations are retained but excluded from joined rows.',
                      'Receipt state, source observation and measured odor outcome remain distinct. Reports and observations are unauthenticated.',
                      'Units/scales and missing/null unit presence are retained. No measurement is generated for absence.',
                      'Joined only denotes complete coverage in this projection, not scientific validity or physical verification.']}


def write_analysis_directory(result, directory):
    """Exclusive output; incomplete marker remains if writing fails."""
    output = Path(directory); output.mkdir(parents=True, exist_ok=False)
    marker = output/'analysis.json'; marker.write_text('{"status":"incomplete","execution":"not_attempted"}\n')
    columns = {'trials':['ordinal','trial_id','receipt_state','request_id','execution_id','observation_ids','measurement_count','categorical_count','caller_record'],
               'measurements':['ordinal','trial_id','receipt_state','observation_id','stimulus_id','target_id',
                               'property','value','scale_min','scale_max','unit','unit_presence',
                               'source_sha256','source_path','result_index','measurement_index','binding_index','binding_record']}
    for table, fields in columns.items():
        with (output/(table+'.csv')).open('x', encoding='utf-8', newline='') as target:
            writer = csv.DictWriter(target, fieldnames=fields); writer.writeheader()
            for row in result['tables'][table]:
                writer.writerow({k: json.dumps(row[k], ensure_ascii=True, allow_nan=False) if isinstance(row.get(k),(dict,list)) else row.get(k) for k in fields})
    with (output/'analysis.pending').open('x', encoding='utf-8') as target:
        json.dump(result, target, indent=2, allow_nan=False); target.write('\n')
    (output/'analysis.pending').replace(marker)
