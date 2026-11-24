"""Explicit human-operated serial sequences. Never discovers ports or flashes.

Autonomous verification must use only a pseudo-terminal created by the verifier.
Endpoint observations are not independent electrical or olfactory measurements.
"""
import argparse
import json
import math
from pathlib import Path

from .serial_device_transport import SerialDeviceTransport
from .transport_sequence import MAX_BYTES, run_transport_sequence


def run_serial_sequence(inputs, port, *, expected_device_id, startup_delay=0,
                        on_progress=None, stop_requested=None):
    """Run explicit passive plans on a human-selected port; own one serial session.

    All offline plans preflight before opening the port; live capabilities for
    every step preflight before the first render. No retry/reconnect/auto-arming.
    stop_requested is cooperative; Ctrl-C closes with uncertainty, not Stop.
    """
    validate_serial_config(port, startup_delay)
    return run_transport_sequence(inputs,
        lambda: SerialDeviceTransport(port, startup_delay=startup_delay),
        expected_device_id=expected_device_id, on_progress=on_progress,
        stop_requested=stop_requested,
        transport_context={'kind':'human-selected-serial','port':port,'startup_delay':startup_delay})


def validate_serial_config(port, startup_delay):
    if not isinstance(port, str) or not port.strip() or '\0' in port or len(port)>1024:
        raise ValueError('Explicit human-selected port required (max1024 characters)')
    if (isinstance(startup_delay, bool) or not isinstance(startup_delay, (int,float))
            or not math.isfinite(startup_delay) or not 0<=startup_delay<=30):
        raise ValueError('Startup delay must be finite, 0 through 30 seconds')

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plans', nargs='+', type=Path, help='Explicit plan paths in caller order, max16')
    parser.add_argument('--port', required=True, help='Human-selected port; no discovery')
    parser.add_argument('--expected-device-id', required=True)
    parser.add_argument('--startup-delay', type=float, default=0)
    parser.add_argument('--action', choices=['complete','stop-first'], required=True)
    parser.add_argument('--output', type=Path, required=True, help='New checkpointed report; never overwrite')
    args=parser.parse_args(argv)
    try:
        with args.output.open('x',encoding='utf-8') as output:
            stop=[False]
            def save(report):
                output.seek(0);output.truncate();json.dump(report,output,indent=2,allow_nan=False);output.write('\n');output.flush()
                sequence=report.get('sequence')
                if args.action=='stop-first' and sequence:
                    stop[0]=any(s['state'] in {'accepted','running'} for s in sequence['steps']) or stop[0]
            save({'status':'incomplete','physical_validation':False,'acceptance':'not_attempted'})
            try:
                if not 1<=len(args.plans)<=16: raise ValueError('Require1–16 explicit plans')
                validate_serial_config(args.port,args.startup_delay)
                inputs=[]
                for path in args.plans:
                    with path.open('rb') as source:inputs.append(source.read(MAX_BYTES+1))
            except (ValueError,TypeError,OSError) as error:
                report={'status':'invalid','physical_validation':False,'detail':str(error)}
            else:
                # Do not relabel/overwrite uncertain intent after a checkpoint failure.
                report=run_serial_sequence(inputs,args.port,expected_device_id=args.expected_device_id,
                    startup_delay=args.startup_delay,on_progress=save,stop_requested=lambda:stop[0])
            save(report)
        print(json.dumps(report,allow_nan=False))
        expected='completed' if args.action=='complete' else 'stopped'
        return 0 if report['status']==expected else 3 if report['status'] in {'invalid','incompatible','rejected'} else 1
    except OSError as error:
        print(json.dumps({'status':'error','detail':str(error)}));return 2


if __name__=='__main__':raise SystemExit(main())
