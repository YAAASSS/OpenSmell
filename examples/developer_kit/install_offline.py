"""Install a verified offline kit into a new clean venv; no package index access."""
import argparse
import json
from pathlib import Path
import subprocess
import venv

from try_kit import check_manifest, ROOT
from offline_dependencies import require_target, load_wheelhouse, TARGET


def install(destination):
    require_target()
    manifest = check_manifest()
    if manifest.get('offline_target') != TARGET:
        raise ValueError('This kit has no supported offline dependency bundle')
    load_wheelhouse(ROOT/'wheelhouse')
    if destination.exists():
        raise ValueError('Environment path already exists; choose a new path')
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(destination)
    python=destination/'bin/python'
    subprocess.run([python,'-I','-m','pip','--isolated','install','--no-index','--no-cache-dir',
                    '--find-links',ROOT/'wheelhouse','--find-links',ROOT/'packages',
                    '--only-binary=:all:','--require-hashes','-r',ROOT/'offline-requirements.txt'],check=True)
    subprocess.run([python,'-I','-m','pip','--isolated','check'],check=True)
    return {'status':'installed','python':str(python),'target':TARGET,'network_index':'disabled',
            'system_site_packages':False,'physical_validation':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--venv',type=Path,required=True,help='New environment directory')
    args=parser.parse_args()
    print(json.dumps(install(args.venv.resolve())))

if __name__=='__main__':
    main()
