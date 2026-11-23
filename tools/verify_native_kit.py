"""Extract optional kit, compile real sketch and use installed entries. Software only."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--compiler',type=Path,required=True)
    parser.add_argument('--serial-wheel',type=Path)
    parser.add_argument('--output',type=Path,required=True,help='New evidence directory')
    args=parser.parse_args(); archive=args.archive.resolve(strict=True)
    compiler=args.compiler.resolve(strict=True)
    args.output.mkdir(parents=True,exist_ok=False)
    result={'result':'incomplete','physical_validation':False,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    def save(): (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-native-kit-') as tmp:
        work=Path(tmp);kit=work/'kit';kit.mkdir()
        with zipfile.ZipFile(archive) as z:
            names=z.namelist()
            if len(set(names))!=len(names) or any(not (kit/n).resolve().is_relative_to(kit) for n in names): raise ValueError('Unsafe ZIP')
            z.extractall(kit)
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        env['PYTHONDONTWRITEBYTECODE']='1'
        venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv/bin/python'
        def run(command,expected=0):
            r=subprocess.run([str(c) for c in command],cwd=kit,env=env,capture_output=True,text=True,timeout=180)
            if r.returncode!=expected: raise RuntimeError(f'{command}: {r.returncode} {r.stdout} {r.stderr}')
            return r.stdout
        wheel,=(kit/'packages').glob('*.whl')
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        if args.serial_wheel: run([python,'-m','pip','install','--no-index','--no-deps',args.serial_wheel.resolve(strict=True)])
        location=run([python,'-I','-c','import opensmell; print(opensmell.__file__)']).strip()
        assert Path(location).is_relative_to(work/'venv')
        result['installed_outside_checkout']=True
        result['dependency_scope']='Build dependencies inherited; SDK wheel locally installed, not a new clean Python closure proof'
        run([python,'native_bench.py','--compiler',compiler,'--output','build'])
        result['build']=json.loads((kit/'build/build.json').read_bytes())
        before=(kit/'build/build.json').read_bytes()
        run([python,'native_bench.py','--compiler',compiler,'--output','build'],expected=1)
        assert (kit/'build/build.json').read_bytes()==before
        host=kit/'build/dry-load-host'
        run([python,'-I','native/tools/verify_dry_load.py',host,'--output','native-proof.json'])
        native=json.loads((kit/'native-proof.json').read_bytes());assert native['result']=='passed'
        (args.output/'native.json').write_text(json.dumps(native,indent=2)+'\n')
        raw=run([python,'-I','-m','opensmell','plan','data/multisource_diphenyl_ether.osmell','--profile','native/hardware/esp32/dry_load_profile.json','--resource-id','e6ad8ce3-dc6e-5d94-9287-57665d48fc0b','--duration','5'])
        (kit/'plan.json').write_text(raw)
        run([python,'-I','-m','opensmell','lifecycle-trial','plan.json','--software-command-json',json.dumps([str(host),'--realtime','--simulate-enable']),'--expected-device-id','opensmell-esp32-dry-load-001','--output','trial.json'])
        trial=json.loads((kit/'trial.json').read_bytes());assert trial['status']=='passed'
        (args.output/'trial.json').write_text(json.dumps(trial,indent=2)+'\n')
        (kit/'device-plan.json').write_text(json.dumps(json.loads(raw)['plan']))
        run(['npm','install','--offline','--ignore-scripts','--no-audit','--no-fund','--package-lock=false',*list((kit/'packages').glob('*.tgz'))])
        node=json.loads(run(['node','try_client.cjs',json.dumps([str(host),'--realtime','--simulate-enable']),'opensmell-esp32-dry-load-001','device-plan.json']))
        assert [node[k]['state'] for k in ['completed','stopped','unknown']]==['completed','stopped','unknown']
        (args.output/'node.json').write_text(json.dumps(node,indent=2)+'\n')
        sys.dont_write_bytecode=True
        spec=importlib.util.spec_from_file_location('extracted_pty',kit/'native/tools/serial_pty_bench.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with module.NativeSerialBench(host,simulate_dry_enable=True) as bench:
            run([python,'-I','-m','opensmell.experimental.serial_bench','plan.json','--port',bench.port,'--expected-device-id','opensmell-esp32-dry-load-001','--action','stop','--output','serial.json'])
            serial=json.loads((kit/'serial.json').read_bytes());assert serial['execution']['state']=='stopped'
            (args.output/'serial.json').write_text(json.dumps(serial,indent=2)+'\n')
        # Source/include changes must fail before compiler execution/output creation.
        altered=kit/'native/hardware/esp32/lifecycle_experiment.h'; original=altered.read_bytes();altered.write_bytes(original+b'\n// changed\n')
        run([python,'native_bench.py','--compiler',compiler,'--output','bad-source'],expected=1)
        assert not (kit/'bad-source').exists();altered.write_bytes(original)
        added=kit/'native/hardware/esp32/host/extra.h';added.write_text('// unexpected')
        run([python,'native_bench.py','--compiler',compiler,'--output','bad-added'],expected=1)
        assert not (kit/'bad-added').exists();added.unlink()
        result.update(result='passed',native_exchanges=native['exchanges'],states=['completed','stopped','unknown'],serial='owned PTY Stop',collision_refused=True,changed_source_refused=True,added_include_refused=True)
        save()
    print(json.dumps(result))

if __name__=='__main__':main()
