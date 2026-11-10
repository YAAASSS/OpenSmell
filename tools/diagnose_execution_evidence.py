"""Passive diagnostics for Local Explorer exports; never imports a device transport."""
import argparse
import json
import math
from pathlib import Path
import sys

REPORT = 'opensmell.local-execution-evidence.v1'
HISTORY = 'opensmell.local-execution-history.v1'
PROFILE = 'local-simulator-lifecycle-v1'
MAX_BYTES = 32 * 1024 * 1024


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def loads(text):
    def invalid(value):
        raise ValueError('Non-finite JSON number: ' + value)
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite JSON number')
        return number
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=invalid, parse_float=finite)


def diagnose(document):
    """Return findings without modifying the document or replaying its contents.

    Consistency is not authenticity, adapter certification, or an odor measurement.
    Unknown extensions are ignored and the original input is never rewritten.
    """
    findings, reports = [], []

    def add(severity, code, path, message):
        findings.append(dict(severity=severity, code=code, path=path, message=message))

    if not isinstance(document, dict) or document.get('format') not in (REPORT, HISTORY):
        add('error', 'unsupported_format', '$', 'Expected a Local Explorer evidence report or history v1.')
        items = []
    elif document['format'] == REPORT:
        items = [document]
    else:
        items = document.get('reports')
        retention = document.get('retention', {})
        if isinstance(retention, dict) and retention.get('evicted_reports'):
            add('warning', 'evicted_reports', '$.retention', 'Earlier reports were evicted; this is not a complete session.')
        if not isinstance(items, list) or len(items) > 10:
            add('error', 'invalid_history', '$.reports', 'Expected at most ten retained reports.')
            items = []
        elif not items:
            add('warning', 'empty_history', '$.reports', 'No execution evidence is present.')
    seen = set()
    for index, report in enumerate(items):
        path = '$' if document.get('format') == REPORT else f'$.reports[{index}]'
        start = len(findings)
        if not isinstance(report, dict) or report.get('format') != REPORT:
            add('error', 'invalid_report', path, 'Unsupported report format.')
            continue
        rid = report.get('report_id')
        if not isinstance(rid, str) or not rid or rid in seen:
            add('error', 'report_identity', path + '.report_id', 'Missing, invalid or duplicate report ID.')
        else:
            seen.add(rid)
        execution = report.get('execution')
        events = report.get('exchanges')
        plan = report.get('plan')
        if not isinstance(execution, dict) or not isinstance(events, list) or not isinstance(plan, dict):
            add('error', 'invalid_structure', path, 'Expected execution/plan objects and an exchanges array.')
            continue
        state = execution.get('state')
        if execution.get('report_id') != rid:
            add('error', 'snapshot_identity', path + '.execution.report_id', 'Snapshot does not identify this report.')
        omitted = report.get('omitted_events')
        incomplete = omitted != 0
        if type(omitted) is not int or omitted < 0:
            add('error', 'invalid_omissions', path, 'omitted_events must be a nonnegative integer.')
        elif omitted:
            add('warning', 'omitted_events', path, 'Some exchanges were omitted; absence cannot disprove a claim.')
        accepted = rejected = False
        execution_id = None
        last_observation = None
        render_count = 0
        for number, event in enumerate(events):
            ep = path + f'.exchanges[{number}]'
            if not isinstance(event, dict):
                add('error', 'invalid_event', ep, 'Exchange must be an object.')
                continue
            if event.get('text_truncated'):
                incomplete = True
                add('warning', 'truncated_text', ep, 'Truncated exchange cannot be fully checked.')
                continue
            if event.get('transport_error') or event.get('invalid_response_type'):
                add('warning', 'transport_failure', ep, 'Transport did not provide a usable response; outcome may remain unknown.')
            messages = {}
            for key in ('request_text', 'response_text'):
                if key not in event and key == 'response_text':
                    add('warning', 'missing_response', ep, 'No recorded response; no completion can be inferred.')
                    continue
                try:
                    message = loads(event[key])
                    if not isinstance(message, dict):
                        raise ValueError('Expected object')
                    messages[key] = message
                except (KeyError, TypeError, ValueError, RecursionError):
                    add('warning', 'unreadable_exchange', ep + '.' + key, 'Not an unambiguous JSON object; cannot support an observation.')
            request, response = messages.get('request_text', {}), messages.get('response_text', {})
            kind = request.get('type')
            if kind == 'render':
                render_count += 1
                if render_count > 1:
                    add('error', 'multiple_renders', ep, 'One report contains multiple render requests.')
                for field in ('duration', 'commands'):
                    if request.get(field) != plan.get(field):
                        add('error', 'plan_mismatch', ep, 'Render ' + field + ' differs from the exported plan.')
                accepted = response.get('type') == 'ok'
                rejected = response.get('type') == 'error'
                execution_id = response.get('execution_id')
                if response and execution.get('response') != response:
                    add('error', 'acceptance_mismatch', ep, 'Snapshot render response differs from recorded response.')
            elif kind in ('execution_status', 'stop') and response:
                if (not accepted or not isinstance(execution_id, str) or not execution_id
                        or request.get('execution_id') != execution_id
                        or response.get('execution_id') != execution_id
                        or request.get('profile') != PROFILE or response.get('profile') != PROFILE
                        or response.get('state') not in ('running', 'completed', 'stopped')):
                    add('warning', 'invalid_observation', ep, 'Uncorrelated or unsupported response; cannot establish execution state.')
                    continue
                if last_observation and last_observation['state'] in ('completed', 'stopped') and response['state'] != last_observation['state']:
                    add('error', 'terminal_changed', ep, 'Device changed a previously terminal state.')
                last_observation = response
        if render_count == 0:
            add('warning', 'missing_render', path, 'No complete render request is available.')
        if state in ('running', 'completed', 'stopped'):
            if not last_observation:
                add('warning' if incomplete else 'error', 'unsupported_state', path + '.execution', 'Claimed state lacks a correlated device observation.')
            elif (last_observation.get('state') != state or execution.get('execution_id') != execution_id
                  or execution.get('observation') != last_observation):
                add('warning' if incomplete else 'error', 'snapshot_mismatch', path + '.execution', 'Snapshot differs from the last available correlated observation.')
        elif state == 'accepted':
            add('warning', 'acceptance_only', path, 'Acceptance is not evidence of completion.')
            if not accepted and not incomplete:
                add('error', 'unsupported_acceptance', path, 'No recorded successful render response.')
        elif state == 'rejected':
            if not rejected:
                add('warning' if incomplete else 'error', 'unsupported_rejection', path, 'No recorded render refusal.')
        elif state in ('unknown', 'uncertain', 'sending'):
            add('warning', 'unresolved_outcome', path, 'Outcome remains unresolved; do not infer completion or replay automatically.')
        else:
            add('error', 'unsupported_state', path, 'Unrecognized snapshot state.')
        reports.append(dict(report_id=rid, state=state, simulated=report.get('simulated'),
                            findings=len(findings)-start))
    errors = sum(f['severity'] == 'error' for f in findings)
    warnings = sum(f['severity'] == 'warning' for f in findings)
    return dict(format='opensmell.evidence-diagnostics.v1',
                verdict='inconsistent' if errors else 'incomplete' if warnings else 'consistent',
                errors=errors, warnings=warnings, reports=reports, findings=findings,
                limitations=['Passive client-record consistency checks only; not authenticated telemetry.',
                             'No command execution, physical compatibility or measured olfactory result.'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path, help='Evidence report or history JSON export')
    parser.add_argument('--json', action='store_true', help='Emit machine-readable diagnostics')
    args = parser.parse_args(argv)
    try:
        with args.file.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Input exceeds 32 MiB')
        result = diagnose(loads(raw.decode('utf-8')))
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        result = dict(verdict='invalid-input', errors=1, warnings=0, reports=[],
                      findings=[dict(severity='error', code='invalid_input', path='$', message=str(exc))])
    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(f"{result['verdict']}: {len(result['reports'])} report(s), {result['errors']} error(s), {result['warnings']} warning(s)")
        for f in result['findings']:
            print(f"{f['severity']} {f['code']} {f['path']}: {f['message']}")
        print('Consistency only; no device contacted, no odor measurement or authenticity verified.')
    return 2 if result['errors'] else 1 if result['warnings'] else 0


if __name__ == '__main__':
    sys.exit(main())
