"""Passively copy packaged software starter resources into a new workspace."""
import hashlib
from importlib.resources import files
import json
from pathlib import Path


TEMPLATES = ('README.md','sample.osmell','profile.json')


def init_workspace(directory):
    """Create exclusively; never launch, plan, execute, merge or overwrite files."""
    package = files('opensmell').joinpath('starter')
    payloads = {name:package.joinpath(name).read_bytes() for name in TEMPLATES}
    result = {'format':'org.opensmell.experimental.starter-workspace','version':'0.1',
              'status':'created','experimental':True,'execution':'not_attempted','physical_validation':False,
              'data_basis':'declared synthetic software starter; no empirical measurement',
              'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'byte_count':len(raw)} for name,raw in payloads.items()},
              'limits':['Hashes identify original template bytes, not signatures or current edited-file validity.',
                        'No automatic planning, child launch, hardware connection or physical output.',
                        'Explicit software command/identity required separately; no registry release or adoption claim.']}
    output = Path(directory)
    output.mkdir(parents=True,exist_ok=False)
    marker = output/'workspace.json'
    marker.write_text('{"status":"incomplete","execution":"not_attempted"}\n')
    for name, raw in payloads.items():
        with (output/name).open('xb') as target:target.write(raw)
    pending = output/'workspace.pending'
    with pending.open('x',encoding='utf-8') as target:json.dump(result,target,indent=2);target.write('\n')
    pending.replace(marker)
    return result
