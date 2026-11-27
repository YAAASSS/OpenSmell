"""Verified passive experiment dossier to an explicitly chosen lifecycle transport."""
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile

from .._json import decode_bytes
from .experiment import prepare_experiment, prepare_experiment_profiles
from .frame_export import _snapshot
from .transport_sequence import prepare_steps, run_transport_sequence


def load_prepared_experiment(directory):
    """Read once, verify hashes and recompute all trial bindings before any IO.

    Only fixed preparation filenames are read. Extra passive manifest/plan keys
    survive in exact snapshots; they never choose a transport or executable.
    Hashes establish consistency, not authenticity or scientific validity.
    """
    root = Path(directory).resolve(strict=True)
    def read(name, bound):
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Expected regular retained file: " + name)
        with path.open('rb') as source:
            raw = source.read(bound + 1)
        if len(raw) > bound:
            raise ValueError("Retained file exceeds bound: " + name)
        return raw
    manifest_raw = read('experiment.json', 1048576)
    manifest = decode_bytes(manifest_raw)
    if not isinstance(manifest, dict):
        raise ValueError('Experiment manifest must be an object')
    if manifest.get('version') not in {'0.1', '0.2'}:
        raise ValueError('Unsupported prepared experiment version')
    per_trial = manifest['version'] == '0.2'
    profile_name = 'profiles.json' if per_trial else 'profile.json'
    compiler = prepare_experiment_profiles if per_trial else prepare_experiment
    raw = {name: read(name, bound) for name, bound in
           [('trials.csv', 65536), ('source.osmell', 8*1048576), (profile_name, 1048576)]}
    # Reuse the normal compiler so loader and preparation have one mapping rule.
    with tempfile.TemporaryDirectory(prefix='opensmell-experiment-check-') as tmp:
        target = Path(tmp) / 'recomputed'
        expected = compiler(raw['trials.csv'], raw['source.osmell'], raw[profile_name], target)
        for key in ('format', 'version', 'status', 'experimental', 'execution',
                    'physical_validation', 'total_requested_duration', 'trials'):
            if manifest.get(key) != expected[key]:
                raise ValueError('Prepared experiment binding mismatch: ' + key)
        files = manifest.get('files')
        if not isinstance(files, dict) or set(files) != set(expected['files']):
            raise ValueError('Unexpected retained file inventory')
        plans = []
        for row in expected['trials']:
            name = row['plan_file']  # generated fixed filename, never untrusted path
            value = read(name, 8*1048576)
            plans.append(value)
            if sum(map(len, plans)) > 16*1048576:
                raise ValueError('Combined plans exceed 16 MiB')
            actual_plan, expected_plan = decode_bytes(value), decode_bytes((target/name).read_bytes())
            if not isinstance(actual_plan, dict):
                raise ValueError('Trial plan must be an object')
            for key in expected_plan:
                if actual_plan.get(key) != expected_plan[key]:
                    raise ValueError('Trial plan binding mismatch: ' + name + '/' + key)
            raw[name] = value
        for name, value in raw.items():
            entry = files[name]
            if (not isinstance(entry, dict) or entry.get('sha256') != hashlib.sha256(value).hexdigest()
                    or entry.get('byte_count') != len(value)):
                raise ValueError('Retained file digest/size mismatch: ' + name)
    prepare_steps(plans)
    context = {'manifest': _snapshot(manifest_raw),
               'retained_inputs': {name: _snapshot(raw[name]) for name in
                                   ('trials.csv', 'source.osmell', profile_name)},
               'trial_order': deepcopy(expected['trials'])}
    return plans, context


def run_prepared_experiment(directory, transport_factory, *, expected_device_id,
                            transport_context=None, on_progress=None, stop_requested=None):
    """Verify a selected dossier, then own the separately selected lazy transport.

    Invalid dossiers raise before transport creation. Progress storage is caller
    supplied, cooperative Stop and uncertain outcomes follow the sequence SDK.
    Returned/callback reports retain exact manifest, inputs and per-step plans.
    """
    plans, context = load_prepared_experiment(directory)
    def enrich(report):
        report['prepared_experiment'] = deepcopy(context)
        if report.get('sequence'):
            for step, trial in zip(report['sequence']['steps'], context['trial_order']):
                step['trial_id'] = trial['trial_id']
        return report
    def progress(report):
        if on_progress is not None:
            on_progress(enrich(report))
    if on_progress is not None and not callable(on_progress):
        raise TypeError('on_progress must be callable')
    return enrich(run_transport_sequence(plans, transport_factory,
        expected_device_id=expected_device_id, transport_context=transport_context,
        on_progress=progress, stop_requested=stop_requested))
