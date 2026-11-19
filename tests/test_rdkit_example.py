"""Optional external chemistry consumer; SDK's opaque Molecule contract unchanged."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rdkit_example',ROOT/'examples/rdkit_molecule/analyze.py')
consumer=importlib.util.module_from_spec(spec);spec.loader.exec_module(consumer)
SOURCE=ROOT/'examples/multisource_beta_pinene.osmell'
RID='2d5a1039-904c-5b19-a60f-71c1ada5bac2'


def variant(**changes):
    doc=json.loads(SOURCE.read_bytes());resource=next(r for r in doc['resources'] if r['id']==RID)
    resource.update(changes)
    if changes.get("smiles", "present") is None:resource.pop("smiles")
    return json.dumps(doc).encode()


@pytest.mark.parametrize('name,rid,formula,centers',[
 ('multisource_beta_pinene.osmell',RID,'C10H16',2),
 ('multisource_diphenyl_ether.osmell','e6ad8ce3-dc6e-5d94-9287-57665d48fc0b','C12H10O',0)])
def test_real_structures_sdf_reopen_and_source_exact(tmp_path,name,rid,formula,centers):
    Chem=pytest.importorskip('rdkit.Chem')
    raw=(ROOT/'examples'/name).read_bytes();output=tmp_path/'new'
    report=consumer.export_analysis(raw,rid,output)
    mol=list(Chem.SDMolSupplier(str(output/'molecule.sdf'),removeHs=False))[0]
    assert mol is not None
    assert Chem.MolToSmiles(mol,canonical=True,isomericSmiles=True)==report['computed']['canonical_isomeric_smiles']
    assert report['computed']['formula']==formula and report['computed']['specified_stereo_centers']==centers
    assert report['declared_smiles']==next(r['smiles'] for r in json.loads(raw)['resources'] if r['id']==rid)
    assert (output/'source.osmell').read_bytes()==raw
    before={p.name:p.read_bytes() for p in output.iterdir()}
    with pytest.raises(FileExistsError):consumer.export_analysis(raw,rid,output)
    assert before=={p.name:p.read_bytes() for p in output.iterdir()}


@pytest.mark.parametrize('smiles',['CC name','CC\x00hidden','CC |atomProp:0.foo.bar|','CC\nmore'])
def test_unsupported_smiles_never_truncated_or_exported(tmp_path,smiles):
    with pytest.raises(ValueError,match='Plain SMILES'):
        consumer.export_analysis(variant(smiles=smiles),RID,tmp_path/'no')
    assert not (tmp_path/'no').exists()


@pytest.mark.parametrize('change,rid',[
 ({'smiles':None},RID),({'type_version':'9.0'},RID),({},'absent')])
def test_no_lookup_or_inferred_molecule_selection(tmp_path,change,rid):
    with pytest.raises(ValueError):consumer.export_analysis(variant(**change),rid,tmp_path/'no')
    assert not (tmp_path/'no').exists()


def test_chemically_invalid_smiles_refused_separately_from_sdk(tmp_path):
    pytest.importorskip('rdkit')
    raw=variant(smiles='[CH5]')
    with pytest.raises(ValueError,match='RDKit refused'):consumer.export_analysis(raw,RID,tmp_path/'no')
    assert not (tmp_path/'no').exists()


def test_unknown_context_and_explicit_hydrogen_survive(tmp_path):
    pytest.importorskip('rdkit')
    doc=json.loads(variant(smiles='[2H]O[H]'));doc['future']={'n':2**64+1}
    doc['resources'].append({'id':'future','type':'org.future.unknown','type_version':'8','payload':{'smiles':'CC not-selected'}})
    raw=json.dumps(doc).encode();report=consumer.export_analysis(raw,RID,tmp_path/'new')
    assert (tmp_path/'new/source.osmell').read_bytes()==raw
    assert report['computed']['atoms_in_rdkit_mol']==3 and report['parser_policy']['removeHs'] is False
    assert report['sdf_reread']['canonical_isomeric_structure_equal']
