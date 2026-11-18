"""Explicit human-operated serial LED bench. Never discovers ports or flashes.

For autonomous verification, use only a pseudo-terminal created by the software
verifier. A real board trial requires explicit human port/plan/action selection.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import time

from .._json import decode_bytes
from .frame_export import encode_plan_frame, _snapshot
from .lifecycle_adapter import LifecycleAdapter
from .rendering import RenderingPlan, DeviceCommand
from .serial_device_transport import SerialDeviceTransport


def run_bench(raw, port, identity, action, *, startup_delay=0, on_progress=None):
    """One explicit plan only; no retries/reconnect or implicit Stop on failure."""
    if not isinstance(raw, bytes) or len(raw)>8*1048576:
        raise ValueError('Plan must be bytes, at most 8 MiB')
    if action not in {'complete','stop'}:
        raise ValueError('Choose complete or stop explicitly')
    if not isinstance(port,str) or not port.strip() or not isinstance(identity,str) or not identity.strip():
        raise ValueError('Explicit port and expected identity required')
    if isinstance(startup_delay,bool) or not isinstance(startup_delay,(int,float)) or not math.isfinite(startup_delay) or not 0<=startup_delay<=30:
        raise ValueError('Startup delay must be finite, from 0 through 30 seconds')
    artifact=decode_bytes(raw)
    try: target=artifact['profile']['document']['capabilities']
    except (KeyError,TypeError): raise ValueError('Offline-plan profile/capabilities required') from None
    exported=encode_plan_frame(raw,json.dumps(target,allow_nan=False).encode())
    message=decode_bytes(exported['frame']['line'].encode())
    plan=RenderingPlan([DeviceCommand(c['channel'],c['intensity']) for c in message['commands']],message['duration'])
    report={'format':'org.opensmell.experimental.serial-bench','version':'0.1','experimental':True,
            'status':'incomplete','physical_validation':False,'input':_snapshot(raw),'port':port,
            'expected_device_id':identity,'action':action,'context':exported['context'],
            'acceptance':'not_attempted','execution':None,'transcript':[],
            'limits':['Endpoint replies are not independent electrical or odor observations.',
                      'Closing serial is not Stop; a device may continue its bounded plan.',
                      'Source/profile hashes are declarations; exact plan artifact retained.',
                      'One attempt only; no automatic retry, reconnect or recovery.']}
    def save():
        if on_progress:on_progress(deepcopy(report))
    save()
    transport=None;client=None
    class Recorded:
        def exchange(self,line):
            entry={'request_line':line+'\n'};report['transcript'].append(entry)
            if decode_bytes(line.encode()).get('type')=='render':report['acceptance']='unknown'
            save()
            try:
                reply=transport.exchange(line);entry['response_line']=reply;return reply
            except Exception as error:
                entry['error']=str(error);raise
            finally:save()
        def close(self):transport.close()
    try:
        transport=SerialDeviceTransport(port,startup_delay=startup_delay)
        client=LifecycleAdapter(Recorded(),expected_device_id=identity)
        client.capabilities.require_plan(plan)
        run=client.render(plan,request_id='manual-bench-plan')
        report['acceptance']=run['state'] if run['state'] in {'accepted','rejected'} else 'unknown'
        report['execution']=run;save()
        if run['state']=='accepted':
            if action=='stop':run=client.stop(run['execution_id'])
            else:
                deadline=time.monotonic()+plan.duration+3
                while run['state'] in {'accepted','running'} and time.monotonic()<deadline:
                    time.sleep(.02);run=client.status(run['execution_id'])
                    report['execution']=run;save()
            report['execution']=run
        expected='completed' if action=='complete' else 'stopped'
        report['status']='observed' if run['state']==expected else 'rejected' if run['state']=='rejected' else 'unknown'
    except Exception as error:
        report.update(status='unknown' if report['acceptance']!='not_attempted' or any('error' in e for e in report['transcript']) else 'incompatible',detail=str(error))
    finally:
        if client:
            client.close();report['execution']=client.execution
            if report['execution'] and report['execution']['state']=='unknown':report['status']='unknown'
        if transport:transport.close()
        save()
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path)
    parser.add_argument('--port',required=True,help='Explicit human-selected port; no discovery')
    parser.add_argument('--expected-device-id',required=True)
    parser.add_argument('--action',choices=['complete','stop'],required=True)
    parser.add_argument('--startup-delay',type=float,default=0,help='Explicit settling seconds; opening some boards resets them')
    parser.add_argument('--output',type=Path,required=True,help='New checkpointed report; never overwrite')
    args=parser.parse_args(argv)
    try:
        with args.plan.open('rb') as source:raw=source.read(8*1048576+1)
        with args.output.open('x',encoding='utf-8') as output:
            def save(report):
                output.seek(0);output.truncate();json.dump(report,output,indent=2,allow_nan=False);output.write('\n');output.flush()
            save({'status':'incomplete','acceptance':'not_attempted','physical_validation':False})
            try:report=run_bench(raw,args.port,args.expected_device_id,args.action,startup_delay=args.startup_delay,on_progress=save)
            except Exception as error:
                report={'status':'invalid','acceptance':'not_attempted','physical_validation':False,'detail':str(error)}
            save(report)
        print(json.dumps(report,allow_nan=False))
        return 0 if report['status']=='observed' else 3 if report['status'] in {'rejected','incompatible'} else 1
    except OSError as error:
        print(json.dumps({'status':'error','detail':str(error)}));return 2


if __name__=='__main__':raise SystemExit(main())
