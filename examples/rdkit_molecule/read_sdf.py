"""Read a generated SDF using RDKit only, independently of OpenSmell."""
import argparse
import json
from rdkit import Chem,rdBase
from rdkit.Chem import rdMolDescriptors


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('sdf');a=p.parse_args()
    records=list(Chem.SDMolSupplier(a.sdf,removeHs=False,strictParsing=True))
    if len(records)!=1 or records[0] is None:raise ValueError('Expected one parseable SDF record')
    mol=records[0]
    print(json.dumps({'reader':'RDKit','rdkit_version':rdBase.rdkitVersion,
                      'resource_id':json.loads(mol.GetProp('OpenSmell_Resource_ID_JSON')),
                      'source_sha256':mol.GetProp('OpenSmell_Source_SHA256'),
                      'declared_smiles':json.loads(mol.GetProp('OpenSmell_Declared_SMILES_JSON')),
                      'computed_canonical_isomeric_smiles':Chem.MolToSmiles(mol,canonical=True,isomericSmiles=True),
                      'formula':rdMolDescriptors.CalcMolFormula(mol),'physical_validation':False},ensure_ascii=True))

if __name__=='__main__':main()
