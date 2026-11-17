"""Prepare an explicit pinned wheelhouse for the first offline kit target."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request
from email.parser import BytesParser
from zipfile import ZipFile

PINS = {'jsonschema':'4.26.0', 'attrs':'26.1.0', 'jsonschema-specifications':'2025.9.1',
        'referencing':'0.37.0', 'rpds-py':'2026.9.1', 'typing-extensions':'4.16.0'}
TARGET = {'implementation':'CPython', 'python':'3.12', 'system':'Linux', 'machine':'x86_64', 'minimum_glibc':'2.28'}


def require_target():
    libc, version = platform.libc_ver()
    if (platform.python_implementation() != 'CPython' or sys.version_info[:2] != (3,12)
            or platform.system() != 'Linux' or platform.machine() != 'x86_64'
            or libc != 'glibc' or tuple(map(int,version.split('.')[:2])) < (2,28)):
        raise ValueError('Offline kit first target requires CPython3.12, Linux x86_64, glibc>=2.28')


def metadata(raw):
    with ZipFile(io.BytesIO(raw)) as archive:
        paths = [n for n in archive.namelist() if n.endswith('.dist-info/METADATA')]
        if len(paths) != 1:
            raise ValueError('Wheel must have one METADATA')
        meta = BytesParser().parsebytes(archive.read(paths[0]))
        licenses = {n:archive.read(n).decode('utf-8') for n in archive.namelist()
                    if '.dist-info/' in n and ('license' in n.lower() or n.lower().endswith('copying'))}
    if not licenses:
        raise ValueError('Dependency wheel must retain license texts')
    return {'name':meta['Name'], 'version':meta['Version'], 'requires_python':meta['Requires-Python'],
            'requires_dist':meta.get_all('Requires-Dist', []), 'license_expression':meta['License-Expression'],
            'license_texts':licenses}


def load_wheelhouse(path):
    inventory = json.loads((path/'inventory.json').read_bytes())
    if inventory.get('format') != 'org.opensmell.experimental.offline-dependencies' or inventory.get('version') != '0.1' or inventory.get('target') != TARGET or inventory.get('pins') != PINS:
        raise ValueError('Unsupported offline dependency inventory/target/pins')
    entries = inventory.get('wheels', [])
    if len(entries) != len(PINS) or len({e['filename'] for e in entries}) != len(entries):
        raise ValueError('Incomplete/duplicate wheel inventory')
    payload = {}
    names = {}
    for entry in entries:
        name = entry['filename']
        if Path(name).name != name or not name.endswith('.whl'):
            raise ValueError('Invalid wheel filename')
        raw = (path/name).read_bytes()
        if len(raw) != entry['byte_length'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Dependency wheel bytes differ from inventory')
        parsed = metadata(raw)
        if parsed != entry['metadata']:
            raise ValueError('Dependency wheel metadata differs from inventory')
        normalized = parsed['name'].lower().replace('_','-')
        if normalized in names or PINS.get(normalized) != parsed['version']:
            raise ValueError('Unexpected/duplicate dependency identity')
        names[normalized] = parsed['version']
        payload['wheelhouse/'+name] = raw
    if names != PINS or set(p.name for p in path.glob('*.whl')) != {e['filename'] for e in entries}:
        raise ValueError('Wheelhouse differs from pinned closure')
    payload['wheelhouse/inventory.json'] = (json.dumps(inventory,indent=2)+'\n').encode()
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path,help='New dependency directory; explicit network acquisition')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    subprocess.run([sys.executable,'-m','pip','--isolated','download','--index-url','https://pypi.org/simple',
                    '--no-cache-dir','--only-binary=:all:','--no-deps','--platform','manylinux_2_28_x86_64',
                    '--platform','manylinux_2_17_x86_64','--python-version','312','--implementation','cp',
                    '--abi','cp312','--abi','abi3','--abi','none','--dest',args.output,
                    *[f'{n}=={v}' for n,v in PINS.items()]],check=True)
    entries=[]
    for wheel in sorted(args.output.glob('*.whl')):
        raw=wheel.read_bytes(); meta=metadata(raw)
        url=f"https://pypi.org/pypi/{meta['name']}/{meta['version']}/json"
        with urllib.request.urlopen(url,timeout=30) as response:
            release=json.load(response)
        published=next(e for e in release['urls'] if e['filename']==wheel.name)
        digest=hashlib.sha256(raw).hexdigest()
        if digest != published['digests']['sha256']:
            raise ValueError('Downloaded bytes differ from PyPI release digest')
        entries.append({'filename':wheel.name,'byte_length':len(raw),'sha256':digest,
                        'release_metadata_url':url,'download_url':published['url'],'metadata':meta})
    inventory={'format':'org.opensmell.experimental.offline-dependencies','version':'0.1',
               'target':TARGET,'pins':PINS,'wheels':entries,
               'limits':['Explicit acquisition from public PyPI; hashes identify bytes, not signatures.',
                         'Only the declared Linux/CPython target; no universal compatibility or security audit claim.']}
    (args.output/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
    load_wheelhouse(args.output)
    print(json.dumps({'status':'prepared','target':TARGET,'wheel_count':len(entries)}))

if __name__=='__main__':
    main()
