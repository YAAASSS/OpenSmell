"""Optional RDKit consumer of one explicitly selected installed-SDK Molecule0.1.

No source rewriting, chemical joining, identifier lookup, device or odor claim.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

from opensmell._json import decode_bytes
from opensmell.exceptions import OpenSmellError
from opensmell.experimental.core_interchange import interchange_registry
from opensmell.experimental.generic_graph import generic_graph_from_dict
from opensmell.experimental.molecule import Molecule


def analyze_graph(raw, resource_id):
    if not isinstance(raw,bytes) or len(raw)>8*1048576:
        raise ValueError('Generic graph bytes required, at most 8 MiB')
    doc=decode_bytes(raw)
    graph=generic_graph_from_dict(doc,registry=interchange_registry())
    selected=graph.get(resource_id)
    if not isinstance(selected,Molecule):
        raise ValueError('Select an explicitly present supported Molecule0.1 resource')
    smiles=selected.smiles
    if not smiles:
        raise ValueError('Selected molecule has no declared SMILES; no identifier lookup is performed')
    # Plain SMILES only. Do not silently interpret names/CX metadata or truncate NUL.
    if any(c.isspace() or ord(c)<32 or ord(c)==127 for c in smiles) or '|' in smiles:
        raise ValueError('Plain SMILES required; names, whitespace/control characters and CXSMILES are unsupported')
    from rdkit import Chem, rdBase
    from rdkit.Chem import Descriptors, rdMolDescriptors
    params=Chem.SmilesParserParams();params.parseName=False;params.allowCXSMILES=False
    params.sanitize=True;params.removeHs=False
    mol=Chem.MolFromSmiles(smiles,params)
    if mol is None:raise ValueError('RDKit refused the declared SMILES under the documented parser policy')
    canonical=Chem.MolToSmiles(mol,canonical=True,isomericSmiles=True)
    digest=hashlib.sha256(raw).hexdigest()
    mol.SetProp('OpenSmell_Resource_ID_JSON',json.dumps(resource_id,ensure_ascii=True))
    mol.SetProp('OpenSmell_Source_SHA256',digest)
    mol.SetProp('OpenSmell_Declared_SMILES_JSON',json.dumps(smiles,ensure_ascii=True))
    stream=io.StringIO()
    with Chem.SDWriter(stream) as writer:writer.write(mol)
    sdf=stream.getvalue().encode('utf-8')
    recovered=list(Chem.ForwardSDMolSupplier(io.BytesIO(sdf),removeHs=False,strictParsing=True))
    if (len(recovered)!=1 or recovered[0] is None or
            Chem.MolToSmiles(recovered[0],canonical=True,isomericSmiles=True)!=canonical):
        raise ValueError('RDKit SDF re-read changed the computed isomeric structure; export refused')
    report={'format':'org.opensmell.experimental.rdkit-molecule-trial','version':'0.1',
            'status':'analyzed','experimental':True,'physical_validation':False,
            'source_sha256':digest,'selected_resource_id':resource_id,
            'selected_resource':next(r for r in doc['resources'] if r['id']==resource_id),
            'declared_smiles':smiles,'rdkit_version':rdBase.rdkitVersion,
            'parser_policy':{'plain_smiles_only':True,'sanitize':True,'removeHs':False,'parseName':False,'allowCXSMILES':False},
            'computed':{'canonical_isomeric_smiles':canonical,
                        'formula':rdMolDescriptors.CalcMolFormula(mol),
                        'exact_molecular_weight':Descriptors.ExactMolWt(mol),
                        'atoms_in_rdkit_mol':mol.GetNumAtoms(),'heavy_atoms':mol.GetNumHeavyAtoms(),
                        'fragments':len(Chem.GetMolFrags(mol)),
                        'specified_stereo_centers':len(Chem.FindMolChiralCenters(mol,includeUnassigned=False))},
            'sdf_reread':{'records':1,'canonical_isomeric_structure_equal':True},
            'limits':['Molecule0.1 transports opaque SMILES; these are separate RDKit computations, not OpenSmell validation or source replacement.',
                      'RDKit sanitization, aromaticity and canonicalization are library/version-dependent interpretation, not authenticated chemical identity.',
                      'Any SDF coordinates are serialization output, not measured geometry; no measured conformer or odor result is supplied.',
                      'Identifiers and supplied provenance are not authenticated, joined or resolved; source bytes remain authoritative.',
                      'Unknown graph/representation/context fields remain in source.osmell; SDF is not a full graph round-trip.']}
    return sdf,report


def export_analysis(raw,resource_id,directory):
    output=Path(directory)
    if output.exists():raise FileExistsError('Output directory already exists')
    sdf,report=analyze_graph(raw,resource_id)
    output.mkdir(parents=True,exist_ok=False)
    (output/'report.json').write_text('{"status":"incomplete","physical_validation":false}\n')
    files={'source.osmell':raw,'molecule.sdf':sdf}
    for name,data in files.items():
        with (output/name).open('xb') as target:target.write(data)
    report['files']={name:{'sha256':hashlib.sha256(data).hexdigest(),'byte_count':len(data)} for name,data in files.items()}
    pending=output/'report.pending';pending.write_text(json.dumps(report,indent=2,ensure_ascii=True,allow_nan=False)+'\n')
    pending.replace(output/'report.json')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph',type=Path);parser.add_argument('--resource-id',required=True)
    parser.add_argument('--output-directory',type=Path,required=True)
    args=parser.parse_args()
    try:
        with args.graph.open('rb') as source:raw=source.read(8*1048576+1)
        print(json.dumps(export_analysis(raw,args.resource_id,args.output_directory),ensure_ascii=True,allow_nan=False))
        return 0
    except OSError as error:
        print(json.dumps({'status':'error','error':str(error)}));return 2
    except ImportError as error:
        print(json.dumps({'status':'dependency_missing','error':str(error)}));return 2
    except (OpenSmellError,ValueError,TypeError,KeyError,RecursionError,OverflowError) as error:
        print(json.dumps({'status':'refused','error':str(error)}));return 1

if __name__=='__main__':raise SystemExit(main())
