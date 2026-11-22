"""Fresh installed PySerial -> owned POSIX PTY -> actual compiled native sketch."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import venv
from .serial_pty_bench import NativeSerialBench


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-load',action='store_true',help='Explicit fake-enable dry-load native target; owned PTY only')
    parser.add_argument('wheel',type=Path);parser.add_argument('--host',type=Path,required=True)
    parser.add_argument('--serial-wheel',type=Path,help='Explicit optional local PySerial wheel; otherwise host dependency inherited')
    parser.add_argument('--evidence-directory',type=Path,required=True)
    args=parser.parse_args()
    device_id = 'opensmell-esp32-dry-load-001' if args.dry_load else 'opensmell-esp32-lifecycle-led-001'
    root=Path(__file__).resolve().parents[1]
    wheel=args.wheel.resolve(strict=True);host=args.host.resolve(strict=True)
    evidence=args.evidence_directory.resolve();evidence.mkdir(parents=True,exist_ok=False)
    result={'status':'incomplete','physical_validation':False,'path':'installed SDK -> PySerial -> owned POSIX PTY -> actual native sketch','simulated_dry_enable':args.dry_load,'expected_device_id':device_id,'cases':[]}
    def save():(evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        with tempfile.TemporaryDirectory(prefix='opensmell-installed-serial-') as directory:
            work=Path(directory);venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
            python=work/'venv/bin/python';env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
            def run(command,expected=0):
                r=subprocess.run([str(c) for c in command],cwd=work,env=env,capture_output=True,timeout=45)
                if r.returncode!=expected:raise RuntimeError(f'{command}: {r.returncode} {r.stdout!r} {r.stderr!r}')
                return r.stdout
            run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
            if args.serial_wheel:run([python,'-m','pip','install','--no-index','--no-deps',args.serial_wheel.resolve(strict=True)])
            location=run([python,'-I','-c','import opensmell,serial; print(opensmell.__file__); print(serial.__version__)']).decode()
            assert str(work/'venv') in location
            result['installed_location']=location
            for mapper,rid in [('semantic','e6ad8ce3-dc6e-5d94-9287-57665d48fc0b'),('perceptual','219ef28c-9b58-52f2-93a7-0807f5897857')]:
                profile = json.loads((root / f'examples/offline_{mapper}_profile.json').read_bytes())
                if args.dry_load:
                    profile['capabilities']['device_id'] = device_id
                    profile['capabilities']['max_duration'] = 5
                    profile['description'] = 'Illustrative electrical duty for proposed resistive dummy loads; no physical validation or odor claim.'
                profile_path = work / 'profile.json'
                profile_path.write_text(json.dumps(profile))
                for action,duration,fault,identity,expected,state,count in [
                    ('complete',.1,None,device_id,0,'completed',1),
                    ('stop',5,None,device_id,0,'stopped',1),
                    ('stop',5,'lost',device_id,1,'unknown',1),
                    ('complete',.1,'partial',device_id,1,'unknown',1),
                    ('stop',5,None,'wrong-device',3,None,0),
                    ('stop',5,'invalid',device_id,1,None,0)]:
                    name=f'{mapper}-{action}-{fault or identity}'
                    raw=run([python,'-I','-m','opensmell','plan',root/'examples/multisource_diphenyl_ether.osmell','--profile',profile_path,'--resource-id',rid,'--duration',duration])
                    if fault=='invalid':
                        altered=json.loads(raw);altered['plan']['commands'][0]['intensity']=.123;raw=json.dumps(altered).encode()
                    plan=work/'plan.json';plan.write_bytes(raw);output=evidence/(name+'.json')
                    with NativeSerialBench(host,fault=fault,simulate_dry_enable=args.dry_load) as bench:
                        command=[python,'-I','-m','opensmell.experimental.serial_bench',plan,'--port',bench.port,'--expected-device-id',identity,'--action',action,'--output',output]
                        report=json.loads(run(command,expected))
                        assert (report['execution']['state'] if report.get('execution') else None)==state,report
                        assert sum(r['type']=='render' for r in bench.requests)==count
                        if fault=='invalid':assert not bench.requests and report['status']=='invalid'
                        before=output.read_bytes();requests=len(bench.requests)
                        run(command,2);assert output.read_bytes()==before and len(bench.requests)==requests
                        result['cases'].append({'name':name,'status':report['status'],'state':state,'renders':count,'report_collision_refused':True})
                        save()
            result['status']='passed'
    except BaseException as error:
        result.update(status='error',error=str(error));save();raise
    save();print(json.dumps(result))

if __name__=='__main__':main()
