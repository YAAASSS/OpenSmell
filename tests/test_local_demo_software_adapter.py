"""Custom commands through the same service used by the public CLI/HTTP app."""
import json
import subprocess
import sys

import pytest

from apps.local_demo.hardware import HardwareError
from apps.local_demo.preview_store import PreviewStore, StalePreview
from apps.local_demo.service import FIXTURE, preview
from apps.local_demo.simulator import SIMULATOR_ID
from apps.local_demo.software_adapter import SoftwareAdapterService


def endpoint(tmp_path, mutation="", *, expected_id=SIMULATOR_ID, extra_args=()):
    log = tmp_path / "requests.jsonl"
    script = tmp_path / "software endpoint.py"
    script.write_text('''import json, sys
from pathlib import Path
from apps.local_demo.simulator import SimulatedEndpoint
device = SimulatedEndpoint()
Path(sys.argv[1] + '.started').write_text(json.dumps(sys.argv[2:]))
for line in sys.stdin:
    request = json.loads(line)
    with open(sys.argv[1], 'a') as log:
        log.write(line)
    reply = json.loads(device.exchange(line))
''' + ''.join('    ' + line + '\n' for line in mutation.splitlines()) + '''    print(json.dumps(reply), flush=True)
''')
    # -c keeps the repository on sys.path while testing a script outside it.
    command = [sys.executable, '-u', '-c',
               'import runpy,sys; p=sys.argv.pop(1); runpy.run_path(p,run_name="__main__")',
               str(script), str(log), *extra_args]
    return SoftwareAdapterService(command, expected_id), log


def tracked_preview():
    store = PreviewStore()
    payload = {'client_id': 'custom-software-test', 'revision': 1}
    store.begin(payload)
    ticket = store.publish(payload, preview(FIXTURE.read_text(), duration=5))
    return store, ticket


def test_command_launch_is_explicit_arguments_are_literal_and_close_terminates(tmp_path):
    literal = '; echo NOT_A_SHELL $(ignored) & spaces'
    hardware, log = endpoint(tmp_path, extra_args=[literal])
    try:
        hardware.status()
        hardware.ports()
        tracked_preview()
        assert not log.with_suffix('.jsonl.started').exists()
        with pytest.raises(HardwareError):
            hardware.connect('/dev/ttyUSB0')
        assert not log.exists()
        hardware.connect('SOFTWARE')
        child = hardware._transport.process
        assert json.loads(log.with_suffix('.jsonl.started').read_text()) == [literal]
        assert [json.loads(s)['type'] for s in log.read_text().splitlines()] == [
            'hello', 'get_capabilities', 'lifecycle_capabilities']
        with pytest.raises(HardwareError, match='Already connected'):
            hardware.connect('SOFTWARE')
        hardware.disconnect()
        assert child.poll() is not None
    finally:
        hardware.close()


@pytest.mark.parametrize('mutation,expected_id', [
    ('', 'different-device'),
    ("if request['type'] == 'get_capabilities': reply['device_id'] = 'mismatch'", SIMULATOR_ID),
    ("if request['type'] == 'lifecycle_capabilities': reply['stop'] = False", SIMULATOR_ID),
    ("if request['type'] == 'lifecycle_capabilities': reply['profile'] = 'unknown'", SIMULATOR_ID),
])
def test_incompatible_custom_endpoint_never_receives_render(tmp_path, mutation, expected_id):
    hardware, log = endpoint(tmp_path, mutation, expected_id=expected_id)
    try:
        with pytest.raises(HardwareError):
            hardware.connect('SOFTWARE')
        assert hardware.status()['connection'] == 'disconnected'
        store, ticket = tracked_preview()
        with pytest.raises(HardwareError):
            hardware.send(store, ticket)
        assert all(json.loads(s)['type'] != 'render' for s in log.read_text().splitlines())
    finally:
        hardware.close()


def test_advertised_limits_block_send_before_command(tmp_path):
    hardware, log = endpoint(tmp_path, "if request['type'] == 'get_capabilities': reply['max_duration'] = 1")
    try:
        hardware.connect('SOFTWARE')
        store, ticket = tracked_preview()
        with pytest.raises(HardwareError, match='incompatible'):
            hardware.send(store, ticket)
        assert 'render' not in [json.loads(s)['type'] for s in log.read_text().splitlines()]
    finally:
        hardware.close()


@pytest.mark.parametrize('failure', ['render', 'execution_status'])
def test_lost_reply_exports_unknown_and_never_repeats_command(tmp_path, failure):
    hardware, log = endpoint(tmp_path, f"if request['type'] == {failure!r}: sys.exit(0)")
    try:
        hardware.connect('SOFTWARE')
        store, ticket = tracked_preview()
        if failure == 'render':
            with pytest.raises(HardwareError):
                hardware.send(store, ticket)
        else:
            hardware.send(store, ticket)
        state = hardware.status()
        assert state['execution']['state'] == 'unknown'
        assert state['connection'] == 'disconnected'
        report = hardware.evidence(state['evidence_id'])
        assert report['execution']['state'] == 'unknown'
        assert report['exchanges'][-1]['transport_error']
        assert report['software_adapter']['kind'] == 'custom-software'
        with pytest.raises(StalePreview):
            hardware.send(store, ticket)
        assert sum(json.loads(s)['type'] == 'render' for s in log.read_text().splitlines()) == 1
    finally:
        hardware.close()


def test_missing_executable_keeps_preview_available():
    hardware = SoftwareAdapterService(['opensmell-definitely-missing-executable'], 'test-device')
    try:
        with pytest.raises(HardwareError, match='No render command was sent'):
            hardware.connect('SOFTWARE')
        assert hardware.status()['connection'] == 'disconnected'
        store, ticket = tracked_preview()
        with store.current(ticket) as entry:
            assert not entry['used']
    finally:
        hardware.close()


@pytest.mark.parametrize('options', [
    ['--software-command'],
    ['--software-command', 'node'],
    ['--software-device-id', 'test'],
    ['--simulate', '--software-device-id', 'test', '--software-command', 'node'],
    ['--simulate-node', '--software-device-id', 'test', '--software-command', 'node'],
    ['--software-device-id', '', '--software-command', 'node'],
])
def test_cli_rejects_incomplete_or_conflicting_selection(options):
    result = subprocess.run([sys.executable, '-m', 'apps.local_demo', '--no-browser', *options],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 2
    assert 'error:' in result.stderr
    assert 'http://127.0.0.1' not in result.stdout
