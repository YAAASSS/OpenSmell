"""Installed SDK consumer of an explicitly selected trusted native LED or dry resistive-load sketch.

Software process pipes only. Copy this file outside the checkout after installing
OpenSmell; compile the native sketch separately. Never select a serial device.
"""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import time

from opensmell._json import decode_bytes
from opensmell.experimental.core_interchange import interchange_registry
from opensmell.experimental.generic_graph import generic_graph_from_dict
from opensmell.experimental.lifecycle_adapter import LifecycleAdapter
from opensmell.experimental.planning import plan_with_profile
from opensmell.experimental.process_transport import ProcessTransport
from opensmell.experimental.rendering import RenderRequest

DEVICE_ID='opensmell-esp32-lifecycle-led-001'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-load',action='store_true',help='Explicit fake dry-load enable on native harness only; no physical GPIO')
    parser.add_argument('--native-host',type=Path,required=True,help='Explicit trusted native executable, not a serial port')
    parser.add_argument('--graph',type=Path,required=True)
    parser.add_argument('--profile',type=Path,required=True)
    parser.add_argument('--resource-id',required=True)
    parser.add_argument('--output',type=Path,required=True,help='New checkpointed software report')
    args=parser.parse_args()
    device_id = "opensmell-esp32-dry-load-001" if args.dry_load else DEVICE_ID
    command_args = ["--realtime", "--simulate-enable"] if args.dry_load else ["--realtime"]
    host=args.native_host.resolve(strict=True)
    if not host.is_file(): parser.error('Trusted native host must be a regular file')
    graph_raw=args.graph.read_bytes(); profile_raw=args.profile.read_bytes()
    graph=generic_graph_from_dict(decode_bytes(graph_raw),registry=interchange_registry())
    profile=decode_bytes(profile_raw)
    short=plan_with_profile(graph,RenderRequest(args.resource_id,.1),profile)
    long=plan_with_profile(graph,RenderRequest(args.resource_id,5),profile)
    report={'experimental':True,'physical_validation':False,'result':'incomplete',
            'scope':'Actual sketch in explicitly selected native harness; no physical output observation.',
            'simulated_dry_enable':args.dry_load,'expected_device_id':device_id,
            'native_sha256':hashlib.sha256(host.read_bytes()).hexdigest(),
            'graph_sha256':hashlib.sha256(graph_raw).hexdigest(),'profile_sha256':hashlib.sha256(profile_raw).hexdigest(),
            'resource_id':args.resource_id,'plans':{'short':asdict(short),'long':asdict(long)},
            'transcript':[],'results':{}}
    # Reserve before launch so collision cannot cause a duplicate run.
    with args.output.open('x',encoding='utf-8') as output:
        def save():
            output.seek(0);output.truncate();json.dump(report,output,indent=2,allow_nan=False);output.write('\n');output.flush()
        class Recorded:
            def __init__(self): self.transport=ProcessTransport([str(host),*command_args],startup_timeout=5)
            def exchange(self,message):
                entry={'request':decode_bytes(message.encode())};report['transcript'].append(entry);save()
                reply=self.transport.exchange(message);entry['response']=decode_bytes(reply.encode());save();return reply
            def close(self): self.transport.close()
        save()
        try:
            with LifecycleAdapter(Recorded(),expected_device_id=device_id) as client:
                if args.dry_load:
                    before=len(report['transcript'])
                    try: client.render(replace(long,duration=5.001),request_id='over-limit')
                    except ValueError: pass
                    else: raise AssertionError('Dry-load duration limit accepted')
                    assert len(report['transcript'])==before
                    report['duration_refused_before_io']=True
                run=client.render(short,request_id='completion');save()
                deadline=time.monotonic()+3
                while run['state'] in {'accepted','running'} and time.monotonic()<deadline:
                    time.sleep(.02);run=client.status(run['execution_id'])
                assert run['state']=='completed',run
                report['results']['completion']=run;save()
                before=len(report['transcript'])
                try: client.render(short,request_id='completion')
                except ValueError: pass
                else: raise AssertionError('Duplicate client request ID accepted')
                assert len(report['transcript'])==before
                report['duplicate_request_refused_before_io']=True
                run=client.render(long,request_id='stop')
                run=client.stop(run['execution_id']);assert run['state']=='stopped',run
                report['results']['stop']=run;save()
                run=client.render(long,request_id='disconnect');client.close()
                assert client.execution['state']=='unknown'
                report['results']['disconnect']=client.execution
                report['result']='passed'
        except BaseException as error:
            report.update(result='error',error=str(error));save();raise
        save()
    print(json.dumps(report,allow_nan=False))

if __name__=='__main__': main()
