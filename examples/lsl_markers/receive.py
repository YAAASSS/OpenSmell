"""Independent pylsl receiver; intentionally imports no OpenSmell code."""
import argparse
import json
from pathlib import Path
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-id',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    with a.output.open('x',encoding='utf-8') as output:
        report={'status':'incomplete','physical_validation':False,'samples':[]}
        def save():
            output.seek(0);output.truncate();json.dump(report,output,indent=2);output.write('\n');output.flush()
        save()
        import pylsl
        pylsl.set_config_content('[multicast]\nResolveScope = machine\n[lab]\nKnownPeers = {127.0.0.1}\n')
        found=pylsl.resolve_byprop('source_id',a.source_id,minimum=1,timeout=10)
        if len(found)!=1:raise ValueError('Require exactly one selected LSL stream')
        inlet=pylsl.StreamInlet(found[0],recover=False)
        try:
            inlet.open_stream(timeout=5)
            deadline=time.monotonic()+180
            while time.monotonic()<deadline and len(report['samples'])<512:
                sample,stamp=inlet.pull_sample(timeout=.5)
                if sample is None:continue
                marker=json.loads(sample[0])
                report['samples'].append({'marker':marker,'lsl_timestamp':stamp});save()
                if marker.get('kind')=='run_finished':
                    report.update(status='received',run_status=marker['status'],pylsl_version=pylsl.__version__,liblsl=pylsl.library_info())
                    save();print(json.dumps({'status':'received','samples':len(report['samples'])}));return 0
            raise TimeoutError('No final software marker; incomplete reception')
        finally:inlet.close_stream()


if __name__=='__main__':raise SystemExit(main())
