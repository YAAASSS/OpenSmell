"""Windows package packing uses Node argument arrays, not a batch shell."""
from types import SimpleNamespace
import importlib
import pytest
module=importlib.import_module('tools.npm_command')


def test_windows_standard_npm_layout_preserves_spaces(tmp_path,monkeypatch):
    folder=tmp_path/'Node with spaces & literal';folder.mkdir()
    cli=folder/'node_modules/npm/bin/npm-cli.js';cli.parent.mkdir(parents=True);cli.write_text('// local fixture')
    monkeypatch.setattr(module,'os',SimpleNamespace(name='nt'))
    monkeypatch.setattr(module.shutil,'which',lambda name:str(folder/('npm.cmd' if name=='npm' else 'node.exe')))
    assert module.npm_command()==[str(folder/'node.exe'),str(cli)]
    cli.unlink()
    with pytest.raises(RuntimeError,match='standard'):module.npm_command()


def test_missing_npm_refuses(monkeypatch):
    monkeypatch.setattr(module.shutil,'which',lambda name:None)
    with pytest.raises(RuntimeError,match='npm'):module.npm_command()
