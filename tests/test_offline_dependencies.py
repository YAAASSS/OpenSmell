"""Offline bundle identity gates; complete isolated installation is verified in CI."""
import copy
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from tools.offline_dependencies import PINS, TARGET, load_wheelhouse, metadata, require_target
from tools.build_developer_kit import make_archive


def fake_wheel(name, version):
    data=io.BytesIO()
    with ZipFile(data,'w') as z:
        z.writestr(f'{name}.dist-info/METADATA',f'Name: {name}\nVersion: {version}\nLicense-Expression: MIT\n')
        z.writestr(f'{name}.dist-info/licenses/LICENSE','Synthetic fixture license')
    return data.getvalue()


@pytest.fixture
def wheelhouse(tmp_path):
    entries=[]
    for name,version in PINS.items():
        filename=name.replace('-','_')+'-'+version+'-py3-none-any.whl'
        raw=fake_wheel(name,version);(tmp_path/filename).write_bytes(raw)
        entries.append({'filename':filename,'byte_length':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'metadata':metadata(raw)})
    manifest={'format':'org.opensmell.experimental.offline-dependencies','version':'0.1','target':TARGET,'pins':PINS,'wheels':entries}
    (tmp_path/'inventory.json').write_text(json.dumps(manifest))
    return tmp_path,manifest


def test_bundle_preserves_wheels_licenses_and_target(wheelhouse):
    path,manifest=wheelhouse
    payload=load_wheelhouse(path)
    with ZipFile(io.BytesIO(make_archive(payload,{'test':True},offline_target=TARGET))) as z:
        m=json.loads(z.read('manifest.json'))
        assert m['offline_target']==TARGET and 'Pinned Python wheels' in m['limits'][1]
        for entry in manifest['wheels']:
            assert z.read('wheelhouse/'+entry['filename'])==(path/entry['filename']).read_bytes()
            assert entry['metadata']['license_texts']


@pytest.mark.parametrize('damage',['bytes','missing','extra','duplicate','path','pins','target','metadata'])
def test_bundle_refusals(wheelhouse,damage):
    path,manifest=wheelhouse
    first=manifest['wheels'][0]
    if damage=='bytes': (path/first['filename']).write_bytes(b'altered')
    elif damage=='missing': (path/first['filename']).unlink()
    elif damage=='extra': (path/'extra.whl').write_bytes(b'extra')
    elif damage=='duplicate': manifest['wheels'][-1]=copy.deepcopy(first)
    elif damage=='path': first['filename']='../escape.whl'
    elif damage=='pins': manifest['pins']={}
    elif damage=='target': manifest['target']={}
    elif damage=='metadata': first['metadata']['version']='different'
    (path/'inventory.json').write_text(json.dumps(manifest))
    with pytest.raises((ValueError,OSError)):
        load_wheelhouse(path)


def test_unsupported_target_refused(monkeypatch):
    monkeypatch.setattr('tools.offline_dependencies.platform.machine',lambda:'aarch64')
    with pytest.raises(ValueError,match='first target'):
        require_target()
