"""POSIX pseudo-terminal bridge to an explicitly trusted native sketch. No GPIO."""
import json
import os
import pty
import select
import subprocess
import threading
import tty


class NativeSerialBench:
    def __init__(self, host, *, fault=None, simulate_dry_enable=False):
        self.master,self.slave=pty.openpty();tty.setraw(self.slave)
        self.port=os.ttyname(self.slave)
        command = [str(host), '--realtime']
        if simulate_dry_enable:
            command.append('--simulate-enable')  # Explicit fake GPIO on native executable only.
        self.process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        self.requests=[];self.downstream_replies=[];self.render_count=0;self.fault=fault;self.closed_master=False
        self.done=threading.Event();self.thread=threading.Thread(target=self._relay,daemon=True);self.thread.start()
    def _relay(self):
        pending=[];incoming=b'';outgoing=b''
        try:
            while not self.done.is_set():
                ready,_,_=select.select([self.master,self.process.stdout],[],[],.05)
                if self.master in ready:
                    data=os.read(self.master,4096)
                    if not data:return
                    incoming+=data
                    while b'\n' in incoming:
                        line,incoming=incoming.split(b'\n',1)
                        request=json.loads(line);self.requests.append(request)
                        if request['type']=='render':
                            self.render_count+=1
                            if self.fault=='second-refused' and self.render_count==2:
                                refusal={'protocol_version':'0.1','type':'error','code':'busy','message':'Explicit software proxy refusal'}
                                os.write(self.master,json.dumps(refusal).encode()+b'\n');continue
                        pending.append(request['type'])
                        self.process.stdin.write(line+b'\n');self.process.stdin.flush()
                if self.process.stdout in ready:
                    data=os.read(self.process.stdout.fileno(),4096)
                    if not data:return
                    outgoing+=data
                    while b'\n' in outgoing:
                        line,outgoing=outgoing.split(b'\n',1);kind=pending.pop(0)
                        self.downstream_replies.append({'request_type':kind,'response_line':line.decode('utf-8')+'\n'})
                        if (self.fault=='lost' or self.fault=='second-lost' and self.render_count==2) and kind=='render':
                            os.close(self.master);self.closed_master=True;return
                        if self.fault=='partial' and kind=='execution_status':
                            os.write(self.master,line);continue
                        os.write(self.master,line+b'\n')
        except (OSError,ValueError):
            return
    def close(self):
        self.done.set();self.thread.join(timeout=1)
        self.process.terminate();self.process.wait(timeout=3)
        self.process.stdin.close();self.process.stdout.close()
        if not self.closed_master:os.close(self.master)
        os.close(self.slave)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
