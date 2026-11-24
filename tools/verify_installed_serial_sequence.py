"""Installed ordered caller trials -> owned PTY -> actual sketch. No physical port."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import venv
from .serial_pty_bench import NativeSerialBench


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel',type=Path)
    parser.add_argument('--host',type=Path,required=True,help='Explicit trusted native lifecycle sketch executable')
    parser.add_argument('--dry-host',type=Path)
    parser.add_argument('--serial-wheel',type=Path)
    parser.add_argument('--output',type=Path,required=True,help='New proof directory')
    args=parser.parse_args();args.output=args.output.resolve();root=Path(__file__).resolve().parents[1]
    host=args.host.resolve(strict=True);wheel=args.wheel.resolve(strict=True)
    args.output.mkdir(parents=True,exist_ok=False)
    result={'result':'incomplete','physical_validation':False,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'native_sha256':hashlib.sha256(host.read_bytes()).hexdigest(),'cases':[]}
    def save():(args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    with tempfile.TemporaryDirectory(prefix='opensmell-installed-serial-sequence-') as tmp:
        work=Path(tmp);env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        venv.EnvBuilder(with_pip=True,system_site_packages=True).create(work/'venv')
        python=work/'venv/bin/python'
        def run(command,expected=0):
            r=subprocess.run([str(x) for x in command],cwd=work,env=env,capture_output=True,timeout=60)
            if r.returncode!=expected:raise RuntimeError(f'{command}: {r.returncode} {r.stdout!r} {r.stderr!r}')
            return r.stdout
        run([python,'-m','pip','install','--no-index','--no-deps','--ignore-installed',wheel])
        if args.serial_wheel:run([python,'-m','pip','install','--no-index','--no-deps',args.serial_wheel.resolve(strict=True)])
        location=run([python,'-I','-c','import opensmell,serial;print(opensmell.__file__)']).decode().strip()
        assert Path(location).is_relative_to(work/'venv')
        result['installed_outside_checkout']=True
        result['dependency_scope']='Installed wheel, inherited build dependencies; owned POSIX PTYs, not clean closure or physical serial evidence'
        graph=work/'caller.osmell';graph.write_bytes((root/'examples/multisource_diphenyl_ether.osmell').read_bytes())
        profile=work/'profile.json';profile.write_bytes((root/'examples/offline_perceptual_profile.json').read_bytes())
        # Explicit caller table selects the same documented resource at distinct durations.
        table=work/'caller.csv';table.write_text('trial_id,resource_id,duration,condition\nfirst,219ef28c-9b58-52f2-93a7-0807f5897857,0.1,opaque-first\nsecond,219ef28c-9b58-52f2-93a7-0807f5897857,0.2,opaque-second\n')
        run([python,'-I','-m','opensmell','prepare-experiment',table,'--graph',graph,'--profile',profile,'--output-directory',work/'experiment'])
        manifest=json.loads((work/'experiment/experiment.json').read_bytes())
        # Verifier explicitly selects the trusted preparation's caller order.
        plans=[work/'experiment'/row['plan_file'] for row in manifest['trials']]
        assert len(plans)==2,manifest
        raw=[p.read_bytes() for p in plans]
        assert json.loads(raw[0])['plan']['duration'] != json.loads(raw[1])['plan']['duration']
        # Remove original caller sources; retained passive artifacts must suffice.
        graph.unlink();profile.unlink();table.unlink()
        long=work/'long.json'
        # Prepare a separate normal plan from retained input snapshots, not by editing a plan.
        (work/'graph.osmell').write_bytes((root/'examples/multisource_diphenyl_ether.osmell').read_bytes())
        (work/'profile.json').write_bytes((root/'examples/offline_semantic_profile.json').read_bytes())
        long.write_bytes(run([python,'-I','-m','opensmell','plan','graph.osmell','--profile','profile.json','--resource-id','e6ad8ce3-dc6e-5d94-9287-57665d48fc0b','--duration','5']))
        endpoints=[('led',host,'opensmell-esp32-lifecycle-led-001',False)]
        if args.dry_host:endpoints.append(('dry',args.dry_host.resolve(strict=True),'opensmell-esp32-dry-load-001',True))
        for label,native,identity,dry in endpoints:
            cases=[('complete',None,plans,0,['completed','completed']),
                   ('stop-first',None,[long,plans[1]],0,['stopped','not_attempted']),
                   ('complete','second-lost',[*plans,plans[0]],1,['completed','unknown','not_attempted']),
                   ('complete','second-refused',[*plans,plans[0]],3,['completed','rejected','not_attempted'])]
            for action,fault,selected,code,states in cases:
                name=f'{label}-{action}-{fault or "normal"}'
                with NativeSerialBench(native,fault=fault,simulate_dry_enable=dry) as bench:
                    output=args.output/(name+'.json')
                    command=[python,'-I','-m','opensmell.experimental.serial_sequence',*selected,'--port',bench.port,'--expected-device-id',identity,'--action',action,'--output',output]
                    report=json.loads(run(command,code));steps=report['sequence']['steps']
                    assert [s['state'] for s in steps]==states,report
                    for step,path in zip(steps,selected):assert base64.b64decode(step['context']['input']['data'])==path.read_bytes()
                    renders=sum(q['type']=='render' for q in bench.requests)
                    assert renders==(1 if action=='stop-first' else 2)
                    if action=='complete' and fault is None:
                        assert [q['duration'] for q in bench.requests if q['type']=='render']==[.1,.2]
                    if fault=='second-lost':assert len([r for r in bench.downstream_replies if r['request_type']=='render'])==2
                    before=output.read_bytes();count=len(bench.requests)
                    run(command,2);assert output.read_bytes()==before and len(bench.requests)==count
                    (args.output/(name+'-harness.json')).write_text(json.dumps({'scope':'Software bridge observations, not client receipts','requests':bench.requests,'downstream_replies':bench.downstream_replies},indent=2)+'\n')
                    result['cases'].append({'case':name,'states':states,'renders':renders,'collision_refused':True});save()
        # Invalid last input must fail before even opening the PTY/handshake.
        invalid=work/'invalid.json';invalid.write_bytes(b'{}')
        with NativeSerialBench(host) as bench:
            command=[python,'-I','-m','opensmell.experimental.serial_sequence',plans[0],invalid,'--port',bench.port,'--expected-device-id',endpoints[0][2],'--action','complete','--output',args.output/'invalid.json']
            report=json.loads(run(command,3));assert report['status']=='invalid' and not bench.requests
        # Late live duration refusal on dry target: all offline plans remain valid.
        if args.dry_host:
            late=work/'six-seconds.json'
            late.write_bytes(run([python,'-I','-m','opensmell','plan','graph.osmell','--profile','profile.json','--resource-id','e6ad8ce3-dc6e-5d94-9287-57665d48fc0b','--duration','6']))
            with NativeSerialBench(args.dry_host.resolve(strict=True),simulate_dry_enable=True) as bench:
                report=json.loads(run([python,'-I','-m','opensmell.experimental.serial_sequence',plans[0],late,'--port',bench.port,'--expected-device-id','opensmell-esp32-dry-load-001','--action','complete','--output',args.output/'late-capabilities.json'],3))
                assert report['status']=='invalid' and not any(q['type']=='render' for q in bench.requests)
            result['late_live_capability_no_render']=True
        with NativeSerialBench(host) as bench:
            report=json.loads(run([python,'-I','-m','opensmell.experimental.serial_sequence',*plans,'--port',bench.port,'--expected-device-id','wrong-identity','--action','complete','--output',args.output/'wrong-identity.json'],3))
            assert report['status']=='incompatible' and not any(q['type']=='render' for q in bench.requests)
        result['wrong_identity_no_render']=True
        result.update(result='passed',invalid_last_no_io=True)
        save()
    print(json.dumps(result))

if __name__=='__main__':main()
