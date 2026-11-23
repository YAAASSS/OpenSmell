"""Committed dependency selection and extracted build preflight refusals."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import pytest
from tools import native_kit

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_entry',ROOT/'examples/developer_kit/native_bench.py')
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)


def test_committed_dependency_bytes_not_worktree(tmp_path, monkeypatch):
    dep=tmp_path/'dep';dep.mkdir()
    def git(*a): return subprocess.check_output(['git','-C',str(dep),*a])
    git('init','-q');git('config','user.email','test@example.invalid');git('config','user.name','Test')
    (dep/'src').mkdir();(dep/'src/ArduinoJson.h').write_text('committed header')
    (dep/'LICENSE.txt').write_text('license');git('add','.');git('commit','-qm','fixture')
    pin=git('rev-parse','HEAD').decode().strip();monkeypatch.setattr(native_kit,'PIN',pin)
    (dep/'src/ArduinoJson.h').write_text('changed worktree');(dep/'src/untracked.h').write_text('not selected')
    payloads=native_kit.native_payloads(dep)
    assert payloads['native/ArduinoJson/src/ArduinoJson.h']==b'committed header'
    assert not any(p.endswith('untracked.h') for p in payloads)
    assert json.loads(payloads['native/inventory.json'])['dependency']['commit']==pin
    monkeypatch.setattr(native_kit,'PIN','0'*40)
    with pytest.raises(ValueError,match='pinned'): native_kit.native_payloads(dep)


@pytest.mark.parametrize('change',['modified','added','missing','escape','symlink'])
def test_inventory_refuses_changed_inputs(tmp_path,change):
    root=tmp_path/'kit';(root/'native').mkdir(parents=True)
    target=root/'native/source.h';target.write_bytes(b'original')
    inventory={'format':'org.opensmell.experimental.native-kit','version':'0.1','dependency':{'commit':entry.PIN},'files':{'native/source.h':{'sha256':hashlib.sha256(b'original').hexdigest(),'byte_length':8}}}
    (root/'native/inventory.json').write_text(json.dumps(inventory))
    entry.validate(root)
    if change=='modified':target.write_bytes(b'changed')
    if change=='missing':target.unlink()
    if change=='added':(root/'native/extra.h').write_text('header')
    if change=='escape':inventory['files']['../escape.h']=inventory['files'].pop('native/source.h');(root/'native/inventory.json').write_text(json.dumps(inventory))
    if change=='symlink':target.unlink();outside=tmp_path/'outside';outside.write_bytes(b'original');target.symlink_to(outside)
    with pytest.raises((ValueError,FileNotFoundError)):entry.validate(root)
