"""Compile included actual sketch; no downloads, PlatformIO, ports or endpoint launch."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
ROOT=Path(__file__).resolve().parent
PIN='f9fe8557f13d8949eafd49ebd93a2929c4e5065f'

def validate(root):
    raw=(root/'native/inventory.json').read_bytes()
    if len(raw)>262144: raise ValueError('Oversized native inventory')
    inventory=json.loads(raw)
    if inventory.get('format')!='org.opensmell.experimental.native-kit' or inventory.get('version')!='0.1' or inventory.get('dependency',{}).get('commit')!=PIN:
        raise ValueError('Unsupported native inventory/dependency')
    files=inventory.get('files')
    if not isinstance(files,dict) or not 1<=len(files)<=512: raise ValueError('Invalid native inventory')
    for name,expected in files.items():
        path=PurePosixPath(name)
        if not name.startswith('native/') or path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError('Unsafe native file path')
        local=root/name
        if local.is_symlink() or not local.resolve().is_relative_to(root.resolve()): raise ValueError('Native file escapes kit')
        data=local.read_bytes()
        if len(data)!=expected['byte_length'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:
            raise ValueError('Native file differs from inventory: '+name)
    actual={p.relative_to(root).as_posix() for p in (root/'native').rglob('*') if p.is_file()}
    if actual!=set(files)|{'native/inventory.json'}: raise ValueError('Unexpected/missing native files')
    return inventory,hashlib.sha256(raw).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler',required=True,type=Path,help='Explicit trusted local C++17 compiler executable')
    parser.add_argument('--output',required=True,type=Path,help='New build directory; no overwrite')
    args=parser.parse_args()
    inventory,digest=validate(ROOT)
    compiler=args.compiler.resolve(strict=True)
    if not compiler.is_file(): raise ValueError('Compiler must be a regular executable')
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    report={'result':'incomplete','physical_validation':False,'inventory_sha256':digest,'dependency':inventory['dependency'],'compiler':str(compiler)}
    def save(): (output/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        executable=output/('dry-load-host.exe' if os.name=='nt' else 'dry-load-host')
        subprocess.run([sys.executable,str(ROOT/'native/tools/build_esp32_host.py'),'--dry-load','--compiler',str(compiler),'--arduinojson',str(ROOT/'native/ArduinoJson'),'--output',str(executable)],check=True,timeout=150)
        report.update(result='built',executable=str(executable),executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest())
    except BaseException as error:
        report.update(result='error',detail=str(error));save();raise
    save();print(json.dumps(report))
if __name__=='__main__':main()
