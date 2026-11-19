"""One explicit molecule/observation -> RDKit/SDF + separate passive SDK plan.

The computed chemistry is never an input to odor/channel mapping. No transport.
"""
import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path

from opensmell._json import decode_bytes
from opensmell.cli import inspect_bytes
from opensmell.exceptions import OpenSmellError
from opensmell.experimental.core_interchange import interchange_registry
from opensmell.experimental.generic_graph import generic_graph_from_dict
from opensmell.experimental.resources import Observation,Stimulus
from opensmell.experimental.planning import plan_with_profile
from opensmell.experimental.rendering import RenderRequest

# Both repository and extracted-kit filenames are supported; never input-selected.
_here=Path(__file__).resolve().parent
_analysis_path=_here/'analyze_molecule.py'
if not _analysis_path.exists():_analysis_path=_here/'analyze.py'
_spec=importlib.util.spec_from_file_location('opensmell_rdkit_example',_analysis_path)
_analysis=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_analysis)


def export_experiment(raw,profile_raw,*,molecule_id,observation_id,resource_id,duration,directory):
    output=Path(directory)
    if output.exists():raise FileExistsError('Output directory already exists')
    if not isinstance(raw,bytes) or len(raw)>8*1048576 or not isinstance(profile_raw,bytes) or len(profile_raw)>1048576:
        raise ValueError('Graph/profile bytes required, at most 8 MiB/1 MiB')
    doc=decode_bytes(raw);profile=decode_bytes(profile_raw)
    graph=generic_graph_from_dict(doc,registry=interchange_registry())
    observation=graph.get(observation_id)
    if not isinstance(observation,Observation):raise ValueError('Select one present supported Observation')
    stimulus=graph.get(observation.stimulus.resource_id)
    if not isinstance(stimulus,Stimulus) or stimulus.source is None or stimulus.source.resource_id!=molecule_id:
        raise ValueError('Explicit observation -> stimulus -> selected molecule link required')
    if resource_id not in {molecule_id,observation_id}:
        raise ValueError('Mapping resource must explicitly select the linked molecule or observation')
    request=RenderRequest(resource_id,duration)
    plan=plan_with_profile(graph,request,profile)
    # Validate both paths before creating any output; no descriptor-driven mapping.
    sdf,molecular=_analysis.analyze_graph(raw,molecule_id)
    source_hash=hashlib.sha256(raw).hexdigest();profile_hash=hashlib.sha256(profile_raw).hexdigest()
    artifact={'format':'org.opensmell.experimental.offline-plan','version':'0.1','status':'planned',
              'execution':'not_attempted','capability_basis':'supplied_profile_not_live_device',
              'source':{'input':'source.osmell',**inspect_bytes(raw),'document':doc},
              'profile':{'input':'profile.json','sha256':profile_hash,'document':profile},
              'request':{'resource_id':resource_id,'duration':request.duration},'plan':asdict(plan),
              'limitations':['Application-defined mapping, supplied capabilities; no execution or odor reproduction.',
                             'RDKit computations are a separate result, not mapping inputs.']}
    molecular=_analysis._write_analysis_bundle(raw,sdf,molecular,output)
    marker=output/'experiment.json'
    marker.write_text('{"status":"incomplete","physical_validation":false}\n')
    with (output/'profile.json').open('xb') as target:target.write(profile_raw)
    plan_raw=(json.dumps(artifact,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()
    with (output/'plan.json').open('xb') as target:target.write(plan_raw)
    result={'format':'org.opensmell.experimental.scientific-plan-trial','version':'0.1','status':'prepared',
            'experimental':True,'physical_validation':False,'execution':'not_attempted',
            'source_sha256':source_hash,'profile_sha256':profile_hash,
            'selection':{'molecule_id':molecule_id,'observation_id':observation_id,'stimulus_id':stimulus.id,
                         'mapping_resource_id':resource_id},
            'link_basis':'Explicit graph structural references only; no identifier/SMILES equivalence join',
            'chemistry_is_separate_from_mapping':True,'rdkit_version':molecular['rdkit_version'],
            'plan':asdict(plan),'plan_sha256':hashlib.sha256(plan_raw).hexdigest(),
            'limits':['Exact source/profile bytes retained; source provenance/capabilities remain supplied declarations.',
                      'Molecular computation and subjective odor data are separate; no averaging, chemical join or descriptor-to-channel inference.',
                      'A passive plan is not a command, acceptance, observed execution or measured odor outcome.']}
    pending=output/'experiment.pending';pending.write_text(json.dumps(result,indent=2,ensure_ascii=True,allow_nan=False)+'\n')
    pending.replace(marker)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('graph',type=Path);p.add_argument('--profile',type=Path,required=True)
    for name in ('molecule-id','observation-id','resource-id'):p.add_argument('--'+name,required=True)
    p.add_argument('--duration',type=float,required=True);p.add_argument('--output-directory',type=Path,required=True)
    a=p.parse_args()
    try:
        with a.graph.open('rb') as source:raw=source.read(8*1048576+1)
        with a.profile.open('rb') as source:profile=source.read(1048576+1)
        report=export_experiment(raw,profile,molecule_id=a.molecule_id,observation_id=a.observation_id,
                                 resource_id=a.resource_id,duration=a.duration,directory=a.output_directory)
        print(json.dumps(report,ensure_ascii=True,allow_nan=False));return 0
    except (OSError,ImportError) as error:
        print(json.dumps({'status':'error','error':str(error)}));return 2
    except (OpenSmellError,ValueError,TypeError,KeyError,RecursionError,OverflowError) as error:
        print(json.dumps({'status':'refused','error':str(error)}));return 1

if __name__=='__main__':raise SystemExit(main())
