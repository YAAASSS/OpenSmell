"""Explicit optional native sources; no download, compile or execution at packing."""
import hashlib
import json
from pathlib import Path
import subprocess
PIN = 'f9fe8557f13d8949eafd49ebd93a2929c4e5065f'
ROOT = Path(__file__).resolve().parents[1]
FILES = ['hardware/esp32/host/Arduino.h','hardware/esp32/host/main.cpp','hardware/esp32/lifecycle_experiment.h','hardware/esp32/opensmell_device_protocol_0_1/opensmell_device_protocol_0_1.ino','hardware/esp32/dry_load_profile.json','hardware/esp32/DRY_LOAD.md','hardware/esp32/DRY_LOAD_RESULTS.md','tools/build_esp32_host.py','tools/verify_dry_load.py','tools/serial_pty_bench.py']

def native_payloads(directory):
    dependency = Path(directory).resolve(strict=True)
    def git(*args):
        return subprocess.check_output(['git','-C',str(dependency),*args],timeout=30)
    if git('rev-parse','HEAD').decode().strip() != PIN:
        raise ValueError('Native kit requires pinned ArduinoJson commit '+PIN)
    names = git('ls-tree','-r','--name-only','HEAD','--','src','LICENSE.txt').decode().splitlines()
    if 'src/ArduinoJson.h' not in names or 'LICENSE.txt' not in names:
        raise ValueError('Pinned headers/license missing')
    result = {'native/'+p:(ROOT/p).read_bytes() for p in FILES}
    for name in names:
        if not (name.startswith('src/') or name=='LICENSE.txt') or '..' in Path(name).parts:
            raise ValueError('Unexpected dependency path')
        result['native/ArduinoJson/'+name] = git('show','HEAD:'+name)
    inventory = {'format':'org.opensmell.experimental.native-kit','version':'0.1',
                 'dependency':{'name':'ArduinoJson','version':'7.2.1','commit':PIN,'source':'https://github.com/bblanchon/ArduinoJson','selection':'committed src/ and LICENSE.txt blobs'},
                 'files':{p:{'sha256':hashlib.sha256(b).hexdigest(),'byte_length':len(b)} for p,b in sorted(result.items())}}
    result['native/inventory.json']=(json.dumps(inventory,indent=2)+'\n').encode()
    result['native_bench.py']=(ROOT/'examples/developer_kit/native_bench.py').read_bytes()
    result['NATIVE_BENCH.md']=(ROOT/'examples/developer_kit/NATIVE_BENCH.md').read_bytes()
    return result
