"""Actual-sketch native lifecycle bench. No physical/serial access."""
import argparse
import json
from pathlib import Path

from opensmell.experimental.native_replay import _NativePipe

PROFILE='local-simulator-lifecycle-v1'
DEVICE='opensmell-esp32-lifecycle-led-001'


def verify(host):
    transcript=[]
    p=_NativePipe(host)
    checks=0
    def exchange(message):
        nonlocal checks
        line=(json.dumps(message,separators=(',',':')) if isinstance(message,dict) else message)+'\n'
        raw,value=p.exchange(line)
        transcript.append({'request_line':line,'response_line':raw});checks+=1
        return value
    def render(duration=5,commands=None):
        return {'protocol_version':'0.1','type':'render','duration':duration,
                'commands':commands if commands is not None else [{'channel':0,'intensity':.25},{'channel':2,'intensity':.8}]}
    def observe(eid,kind='execution_status',profile=PROFILE):
        return exchange({'type':kind,'profile':profile,'execution_id':eid})
    try:
        assert exchange({'protocol_version':'0.1','type':'hello'})['device_id']==DEVICE
        assert exchange({'protocol_version':'0.1','type':'get_capabilities'})['max_duration']==30
        assert exchange({'type':'lifecycle_capabilities'})['stop'] is True
        assert exchange('!pins')['host_pwm']==[0,0,0]
        # Validate whole plans before any output change, including malformed members.
        invalid=[render(31),render(.099),render(True),render(1,[]),render(1,[None]),
                 render(1,[{'channel':True,'intensity':1}]),render(1,[{'channel':3,'intensity':1}]),
                 render(1,[{'channel':0,'intensity':1},{'channel':0,'intensity':0}]),
                 render(1,[{'channel':0,'intensity':False}]),render(1,[{'channel':0,'intensity':1.1}])]
        for request in invalid:
            assert exchange(request)['type']=='error'
            assert exchange('!pins')['host_pwm']==[0,0,0]
        run=exchange(render());first=run['execution_id']
        assert observe(first)['state']=='running'
        assert exchange('!pins')['host_pwm']==[64,0,204]
        assert exchange(render())['code']=='busy'
        assert observe(first,'stop','wrong')['code']=='unsupported_profile'
        assert observe(first+'\0suffix','stop')['code']=='unknown_execution'
        assert observe('stale','stop')['code']=='unknown_execution'
        assert exchange('!pins')['host_pwm']==[64,0,204]
        assert observe(first,'stop')['state']=='stopped'
        assert exchange('!pins')['host_pwm']==[0,0,0]
        assert observe(first,'stop')['state']=='stopped'
        second=exchange(render(.1,[{'channel':1,'intensity':.6}]))['execution_id']
        assert first!=second
        assert observe(first,'stop')['code']=='unknown_execution'
        assert exchange('!pins')['host_pwm']==[0,153,0]
        exchange('!advance 99');assert observe(second)['state']=='running'
        exchange('!advance 2');assert observe(second)['state']=='completed'
        assert exchange('!pins')['host_pwm']==[0,0,0]
        assert observe(second,'stop')['state']=='completed'
        # Explicit fake-clock rollover exercises the same uint32_t elapsed code.
        exchange('!advance '+str(2**32-50-101))
        third=exchange(render(.1))['execution_id']
        exchange('!advance 102');assert observe(third)['state']=='completed'
        assert exchange('!pins')['host_pwm']==[0,0,0]
        assert exchange('{')['type']=='error'
        assert exchange('x'*1025)['type']=='error'
        assert exchange({'protocol_version':'0.1','type':'hello'})['device_id']==DEVICE
    finally:
        p.close()
    # Fresh-process boot token must not revive a prior ID; this is not persistent reconciliation.
    p=_NativePipe(host)
    try:
        assert observe(third,'stop')['code']=='unknown_execution'
        fresh=exchange(render())['execution_id'];assert fresh not in {first,second,third}
        assert observe(third,'stop')['code']=='unknown_execution'
        assert observe(fresh,'stop')['state']=='stopped'
        assert exchange('!pins')['host_pwm']==[0,0,0]
    finally:p.close()
    return {'result':'passed','exchanges':checks,'physical_validation':False,
            'scope':'Actual compiled sketch; fake serial/PWM/clock, no board access',
            'transcript':transcript}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('host',type=Path)
    parser.add_argument('--output',type=Path,help='New evidence JSON')
    args=parser.parse_args()
    # Reserve before launch; an interrupted report is not a passing trial.
    if args.output:
        with args.output.open('x',encoding='utf-8') as output:
            output.write('{"result":"incomplete","physical_validation":false}\n');output.flush()
            report=verify(args.host.resolve(strict=True))
            output.seek(0);output.truncate();json.dump(report,output,indent=2);output.write('\n')
    else:report=verify(args.host.resolve(strict=True))
    print(json.dumps({k:v for k,v in report.items() if k!='transcript'}))

if __name__=='__main__':main()
