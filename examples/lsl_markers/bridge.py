"""Explicit software plans -> optional local LSL software-observation markers.

Run from any directory with an installed SDK and pylsl 1.18.7. No hardware.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time

from opensmell._json import decode_bytes
from opensmell.experimental.lifecycle_adapter import LifecycleAdapter
from opensmell.experimental.process_transport import ProcessTransport
from opensmell.experimental.sequence import SequenceRunner, SequenceStep
from opensmell.experimental.software_sequence import prepare_steps


class MarkerRelay:
    """Project changes in SDK snapshots; a push is not a receiver acknowledgement."""
    def __init__(self, outlet, clock):
        self.outlet, self.clock = outlet, clock
        self.events, self._seen = [], {}

    def emit(self, kind, report, **fields):
        event = {'format':'org.opensmell.example.lsl-marker','version':'0.1',
                 'event_index':len(self.events), 'kind':kind,'run_id':report['run_id'],
                 'clock_basis':'LSL local_clock at software callback; not physical onset',
                 'physical_validation':False, **fields}
        stamp = self.clock()
        self.outlet.push_sample([json.dumps(event,allow_nan=False)], timestamp=stamp)
        self.events.append({'marker':event,'outlet_timestamp':stamp})

    def __call__(self, report):
        if not self.events:
            self.emit('run_started',report)
        for step in report['steps']:
            execution = step['execution'] or {}
            # Keep correlation and uncertainty; omit source/private payloads from stream.
            snapshot = {'trial_id':step['step_id'],'state':step['state'],
                        'request_id':execution.get('request_id'),
                        'execution_id':execution.get('execution_id'),
                        'detail':execution.get('detail')}
            if self._seen.get(step['step_id']) == snapshot:
                continue
            self.emit('step_snapshot',report,**snapshot,
                      basis='SDK passive snapshot; not_attempted/unknown may precede I/O')
            self._seen[step['step_id']] = snapshot

    def finish(self, report):
        self(report)
        self.emit('run_finished',report,status=report['status'])


def load_steps(paths):
    if not 1 <= len(paths) <= 16:raise ValueError('Supply 1–16 explicit plans')
    inputs=[]
    for path in paths:
        with Path(path).open('rb') as source:inputs.append(source.read(8*1048576+1))
        if sum(map(len,inputs))>16*1048576:raise ValueError('Inputs exceed16MiB')
    prepared=prepare_steps(inputs);steps=[];ids=set()
    for step,raw in zip(prepared,inputs):
        artifact=decode_bytes(raw)
        trial_id=artifact.get('org.opensmell.experimental.trial',{}).get('record',{}).get('trial_id',step.step_id)
        if not isinstance(trial_id,str) or not trial_id.strip() or len(trial_id)>128 or trial_id in ids:
            raise ValueError('Unique explicit trial IDs required')
        ids.add(trial_id);steps.append(SequenceStep(trial_id,step.plan,step.context))
    return steps


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plans',nargs='+');p.add_argument('--software-command-json',required=True)
    p.add_argument('--expected-device-id',required=True);p.add_argument('--source-id',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stop-after-first-acceptance',action='store_true',help='Explicit cooperative Stop demonstration')
    a=p.parse_args()
    steps=load_steps(a.plans)
    command=json.loads(a.software_command_json)
    if not isinstance(command,list) or not 1<=len(command)<=64 or any(not isinstance(s,str) or '\0' in s for s in command) or not command[0].strip():
        p.error('Explicit trusted executable/argument array required')
    if not a.source_id.strip() or len(a.source_id)>128:p.error('Source ID of1–128 characters required')
    # Reserve evidence before starting an outlet or child. Optional dependency only.
    with a.output.open('x',encoding='utf-8') as output:
        report={'status':'incomplete','physical_validation':False,'events':[], 'sequence':None}
        def save():
            output.seek(0);output.truncate();json.dump(report,output,indent=2,allow_nan=False);output.write('\n');output.flush()
        save()
        transport=client=relay=None
        try:
            import pylsl
            # Machine-scope discovery for this example; not a network security boundary.
            pylsl.set_config_content('[multicast]\nResolveScope = machine\n[lab]\nKnownPeers = {127.0.0.1}\n')
            info=pylsl.StreamInfo('OpenSmell software observations','Markers',1,0,'string',a.source_id)
            info.desc().append_child_value('scope','Experimental software observations; no physical odor onset')
            outlet=pylsl.StreamOutlet(info)
            report.update(source_id=a.source_id,pylsl_version=pylsl.__version__,liblsl=pylsl.library_info())
            if not outlet.wait_for_consumers(5):raise TimeoutError('No LSL consumer; no software process launched')
            relay=MarkerRelay(outlet,pylsl.local_clock)
            transport=ProcessTransport(command,startup_timeout=5)
            client=LifecycleAdapter(transport,expected_device_id=a.expected_device_id)
            def progress(snapshot):
                relay(snapshot)
                report.update(sequence=snapshot,events=deepcopy(relay.events));save()
                if a.stop_after_first_acceptance and snapshot['steps'][0]['state']=='accepted':runner.request_stop()
            runner=SequenceRunner(client,steps,on_progress=progress)
            sequence=runner.run()
            relay.finish(sequence)
            report.update(status=sequence['status'],sequence=sequence,events=deepcopy(relay.events))
            save()
            # Allow queued samples to leave; only the receiver's saved file proves receipt.
            time.sleep(0.2)
        except (Exception,KeyboardInterrupt) as error:
            report.update(status='error',detail=str(error) or type(error).__name__);save()
            return 1
        finally:
            if client:client.close()
            if transport:transport.close()
        print(json.dumps({'status':report['status'],'markers_pushed':len(report['events']),'receiver_acknowledged':False}))
        return 0 if report['status']=='completed' else 3


if __name__=='__main__':raise SystemExit(main())
