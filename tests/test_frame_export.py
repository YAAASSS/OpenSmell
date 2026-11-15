"""Plan/source/target consistency and real CLI framing without transport access."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from opensmell.experimental.frame_export import encode_plan_frame

ROOT = Path(__file__).resolve().parents[1]
TARGET = (ROOT / 'hardware/esp32/led_capabilities.json').read_bytes()


@pytest.fixture(scope='module')
def raw_plan():
    result = subprocess.run([sys.executable, '-m', 'opensmell', 'plan',
                             str(ROOT / 'examples/multisource_diphenyl_ether.osmell'), '--profile',
                             str(ROOT / 'examples/offline_semantic_profile.json'), '--resource-id',
                             'e6ad8ce3-dc6e-5d94-9287-57665d48fc0b', '--duration', '5'], capture_output=True, check=True)
    return result.stdout


def test_original_bytes_unknown_extensions_and_exact_frame(raw_plan):
    value = json.loads(raw_plan)
    value['future'] = {'uninterpreted': [None, 'text', 123456789012345678901]}
    raw = json.dumps(value, indent=4).encode() + b'\r\n'
    exported = encode_plan_frame(raw, TARGET)
    assert base64.b64decode(exported['input']['data']) == raw
    assert base64.b64decode(exported['target']['data']) == TARGET
    assert exported['input']['sha256'] == hashlib.sha256(raw).hexdigest()
    line = exported['frame']['line'].encode()
    assert line.endswith(b'\n') and line.count(b'\n') == 1
    assert len(line) == exported['frame']['line_bytes'] == exported['frame']['message_bytes'] + 1
    assert hashlib.sha256(line).hexdigest() == exported['frame']['sha256']
    assert json.loads(line) == {'protocol_version':'0.1', 'type':'render', 'duration':5,
                               'commands':[{'channel':0,'intensity':0.25},{'channel':1,'intensity':0.6}]}
    assert exported['transport'] == 'not_opened'
    assert exported['acceptance'] == exported['execution'] == 'not_observed'
    assert exported['physical_validation'] is False


@pytest.mark.parametrize('mutation', [
    lambda v: v.update(version='9'), lambda v: v.update(execution='accepted'),
    lambda v: v['plan'].update(duration=31), lambda v: v['plan'].update(duration=True),
    lambda v: v['plan'].update(commands=[]),
    lambda v: v['plan']['commands'].append(deepcopy(v['plan']['commands'][0])),
    lambda v: v['plan']['commands'][0].update(channel=True),
    lambda v: v['plan']['commands'][0].update(intensity=True),
    lambda v: v['plan']['commands'][0].update(intensity=0.4),
    lambda v: v['request'].update(resource_id='absent'),
    lambda v: v['profile']['document']['bindings'][0].update(intensity=0.3),
    lambda v: v['profile'].update(sha256='not-a-hash'),
])
def test_inconsistent_or_invalid_input_refused(raw_plan, mutation):
    value = json.loads(raw_plan); mutation(value)
    with pytest.raises((ValueError, TypeError, KeyError)):
        encode_plan_frame(json.dumps(value).encode(), TARGET)


@pytest.mark.parametrize('mutation', [lambda t: t.update(max_duration=1),
    lambda t: t.update(channels=t['channels'][1:]),
    lambda t: t['channels'][0].update(max_intensity=0.2),
    lambda t: t.update(protocol_version='9')])
def test_supplied_target_checked_independently(raw_plan, mutation):
    value = json.loads(TARGET); mutation(value)
    with pytest.raises(ValueError): encode_plan_frame(raw_plan,json.dumps(value).encode())


def test_inclusive_framing_boundary(raw_plan):
    count=encode_plan_frame(raw_plan,TARGET)['frame']['message_bytes']
    assert encode_plan_frame(raw_plan,TARGET,max_message_bytes=count)['status']=='encoded'
    with pytest.raises(ValueError): encode_plan_frame(raw_plan,TARGET,max_message_bytes=count-1)


@pytest.mark.parametrize('raw', [b'{',b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e999}',b'\xff',b'[]'])
def test_strict_input_boundary(raw):
    with pytest.raises((ValueError,TypeError)): encode_plan_frame(raw,TARGET)


def test_cli_stdin_output_and_existing_path_refused(raw_plan,tmp_path):
    output=tmp_path/'frame.json'
    def run(*args,data=raw_plan):
        return subprocess.run([sys.executable,'-m','opensmell','encode-frame','-',
            '--capabilities',str(ROOT/'hardware/esp32/led_capabilities.json'),*map(str,args)],
            input=data,capture_output=True)
    result=run('--output',output)
    assert result.returncode==0, result.stderr
    before=output.read_bytes()
    assert run('--output',output).returncode==2
    assert output.read_bytes()==before
    assert run(data=b'{}').returncode==1
    assert json.loads(run().stdout)['status']=='encoded'
