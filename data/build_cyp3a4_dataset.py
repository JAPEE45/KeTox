"""
data/build_cyp3a4_dataset.py

Generates and populates data/cyp3a4_compounds.csv with known CYP3A4 inhibitors,
substrates, non-inhibitors, reference drugs, and assay compounds (PubChem AID 884 / 1851).
Standardizes all SMILES into RDKit canonical SMILES for O(1) instant local lookup.
"""

import os
import csv
import pandas as pd
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(DATA_DIR, "cyp3a4_compounds.csv")

INITIAL_COMPOUNDS = [
    # Reference & Potent CYP3A4 Inhibitors
    {"name": "Ketoconazole", "smiles": "CC(=O)N1CCN(CC1)c2ccc(OC[C@@H]3CO[C@@](Cn4ccnc4)(c5ccc(Cl)cc5Cl)O3)cc2", "cid": 47576, "class": "Inhibitor (Strong)", "source": "PubChem / Reference"},
    {"name": "Itraconazole", "smiles": "CCC(C)n1ncn1-c2ccc(cc2)N3CCN(CC3)c4ccc(OCC5COC(Cn6cncn6)(c7ccc(Cl)cc7Cl)O5)cc4", "cid": 55283, "class": "Inhibitor (Strong)", "source": "PubChem / FDA"},
    {"name": "Ritonavir", "smiles": "CC(C)c1nc(cn1C)CSC(=O)NC(C(C)C)C(=O)NC(Cc2ccccc2)CC(C(Cc3ccccc3)NC(=O)OCc4cncs4)O", "cid": 392622, "class": "Inhibitor (Strong)", "source": "PubChem / FDA"},
    {"name": "Clarithromycin", "smiles": "CCC1C(C(C(C(=O)C(CC(C(C(C(C(=O)O1)C)OC2CC(C(C(O2)C)O)(C)OC)C)OC3C(C(CC(O3)C)N(C)C)O)(C)O)C)C)O", "cid": 84029, "class": "Inhibitor (Strong)", "source": "PubChem / FDA"},
    {"name": "Telithromycin", "smiles": "CCC1C(C(C(C(=O)C(CC(C(C(C(C(=O)O1)C)n2ccc3c2cccn3)C)OC4C(C(CC(O4)C)N(C)C)O)(C)O)C)C)O", "cid": 6918241, "class": "Inhibitor (Strong)", "source": "PubChem / FDA"},
    {"name": "Fluconazole", "smiles": "OC(Cn1cncn1)(Cn2cncn2)c3ccc(F)cc3F", "cid": 3365, "class": "Inhibitor (Moderate)", "source": "PubChem / Reference"},
    {"name": "Voriconazole", "smiles": "CC(c1ncc(F)c(n1)F)C(O)(Cn2cncn2)c3ccc(F)cc3F", "cid": 166548, "class": "Inhibitor (Moderate)", "source": "PubChem / FDA"},
    {"name": "Posaconazole", "smiles": "CCC(C)n1ncn1-c2ccc(cc2)N3CCN(CC3)c4ccc(OCC5COC(Cn6cncn6)(c7ccc(F)cc7F)O5)cc4", "cid": 468595, "class": "Inhibitor (Strong)", "source": "PubChem / FDA"},
    {"name": "Erythromycin", "smiles": "CCC1C(C(C(C(=O)C(CC(C(C(C(C(=O)O1)C)OC2CC(C(C(O2)C)O)(C)OC)C)OC3C(C(CC(O3)C)N(C)C)O)(C)O)C)C)O", "cid": 12560, "class": "Inhibitor (Moderate)", "source": "PubChem / FDA"},
    {"name": "Diltiazem", "smiles": "CC(=O)OC1C(c2ccc(OC)cc2)Sc3ccccc3N(CCN(C)C)C1=O", "cid": 39186, "class": "Inhibitor (Moderate)", "source": "PubChem / FDA"},
    {"name": "Verapamil", "smiles": "COc1ccc(CCN(C)CCCC(C#N)(C(C)C)c2ccc(OC)c(OC)c2)cc1OC", "cid": 2520, "class": "Inhibitor (Moderate)", "source": "PubChem / FDA"},
    {"name": "Miconazole", "smiles": "Clc1ccc(COC(Cn2ccnc2)c3ccc(Cl)cc3Cl)cc1Cl", "cid": 4189, "class": "Inhibitor (Strong)", "source": "PubChem / FDA"},
    {"name": "Clotrimazole", "smiles": "Clc1ccccc1C(c2ccccc2)(c3ccccc3)n4ccnc4", "cid": 2812, "class": "Inhibitor (Strong)", "source": "PubChem / FDA"},

    # Reference CYP3A4 Substrates
    {"name": "Midazolam", "smiles": "CC1=NC=C2N1C3=C(C=C(C=C3)Cl)C(=NC2)C4=CC=CC=C4F", "cid": 4192, "class": "Substrate (Index)", "source": "PubChem / FDA"},
    {"name": "Simvastatin", "smiles": "CCC(C)(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C12", "cid": 54454, "class": "Substrate", "source": "PubChem / FDA"},
    {"name": "Lovastatin", "smiles": "CCC(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C12", "cid": 53232, "class": "Substrate", "source": "PubChem / FDA"},
    {"name": "Atorvastatin", "smiles": "CC(C)c1c(C(=O)Nc2ccccc2)c(c3ccccc3)c(c4ccc(F)cc4)n1CCC(O)CC(O)CC(=O)O", "cid": 60823, "class": "Substrate", "source": "PubChem / FDA"},
    {"name": "Nifedipine", "smiles": "COC(=O)C1=C(C)NC(C)=C(C(=O)OC)C1c2ccccc2[N+](=O)[O-]", "cid": 4485, "class": "Substrate", "source": "PubChem / FDA"},
    {"name": "Felodipine", "smiles": "CCOC(=O)C1=C(C)NC(C)=C(C(=O)OC)C1c2cccc(Cl)c2Cl", "cid": 3333, "class": "Substrate", "source": "PubChem / FDA"},
    {"name": "Amlodipine", "smiles": "CCOC(=O)C1=C(COCCN)NC(C)=C(C(=O)OC)C1c2ccccc2Cl", "cid": 2162, "class": "Substrate", "source": "PubChem / FDA"},
    {"name": "Diazepam", "smiles": "CN1C(=O)CN=C(c2ccccc2)c3cc(Cl)ccc13", "cid": 3016, "class": "Substrate", "source": "PubChem / FDA"},
    {"name": "Alprazolam", "smiles": "CC1=NN=C2CN=C(C3=CC=CC=C3)C4=C(C=CC(=C4)Cl)N12", "cid": 2118, "class": "Substrate", "source": "PubChem / FDA"},
    {"name": "Triazolam", "smiles": "CC1=NN=C2CN=C(C3=CC=CC=C3Cl)C4=C(C=CC(=C4)Cl)N12", "cid": 5505, "class": "Substrate", "source": "PubChem / FDA"},
    {"name": "Omeprazole", "smiles": "COc1ccc2[nH]c(S(=O)Cc3ncc(C)c(OC)c3C)nc2c1", "cid": 4594, "class": "Substrate / Weak Inhibitor", "source": "PubChem / FDA"},
    {"name": "Sildenafil", "smiles": "CCCC1=NN(C)C(=O)C2=C1N=C(NC2=O)c3cc(S(=O)(=O)N4CCN(C)CC4)ccc3OCC", "cid": 135398744, "class": "Substrate", "source": "PubChem / FDA"},

    # Confirmed Non-Inhibitors / Safe Compounds (PubChem AID 884 / 1851)
    {"name": "Aspirin (Acetylsalicylic acid)", "smiles": "CC(=O)Oc1ccccc1C(=O)O", "cid": 2244, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Paracetamol (Acetaminophen)", "smiles": "CC(=O)Nc1ccc(O)cc1", "cid": 1983, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Ibuprofen", "smiles": "CC(C)Cc1ccc(C(C)C(=O)O)cc1", "cid": 3672, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Caffeine", "smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O", "cid": 2519, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Glucose", "smiles": "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O", "cid": 5793, "class": "Non-Inhibitor (Safe)", "source": "PubChem"},
    {"name": "Metformin", "smiles": "CN(C)C(=N)NC(=N)N", "cid": 4091, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Atenolol", "smiles": "CC(C)NCC(O)COc1ccc(CC(N)=O)cc1", "cid": 2249, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 1851"},
    {"name": "Propranolol", "smiles": "CC(C)NCC(O)COc1cccc2ccccc12", "cid": 4946, "class": "Non-Inhibitor / Weak", "source": "PubChem AID 884"},
    {"name": "Warfarin", "smiles": "CC(=O)CC(c1ccccc1)c2c(O)c3ccccc3oc2=O", "cid": 54678486, "class": "Non-Inhibitor (CYP2C9)", "source": "PubChem"},
    {"name": "Amoxicillin", "smiles": "CC1(C)SC2C(NC(=O)C(N)c3ccc(O)cc3)C(=O)N2C1C(=O)O", "cid": 33613, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Penicillin G", "smiles": "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O", "cid": 5904, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Ascorbic acid (Vitamin C)", "smiles": "OCC(O)C1OC(=O)C(O)=C1O", "cid": 54670067, "class": "Non-Inhibitor (Safe)", "source": "PubChem"},
    {"name": "Nicotinamide (Vitamin B3)", "smiles": "NC(=O)c1cccnc1", "cid": 936, "class": "Non-Inhibitor (Safe)", "source": "PubChem"},
    {"name": "Naproxen", "smiles": "COc1ccc2cc(C(C)C(=O)O)ccc2c1", "cid": 156391, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Metoprolol", "smiles": "COCCc1ccc(OCC(O)CNC(C)C)cc1", "cid": 4171, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Hydrochlorothiazide", "smiles": "NS(=O)(=O)c1cc2c(cc1Cl)NCNS2(=O)=O", "cid": 3639, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Furosemide", "smiles": "NS(=O)(=O)c1cc(c(cc1Cl)NCc2ccco2)C(=O)O", "cid": 3440, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Salbutamol (Albuterol)", "smiles": "CC(C)(C)NCC(O)c1ccc(O)c(CO)c1", "cid": 2088, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Ranitidine", "smiles": "CNC(=C[N+](=O)[O-])NCCSCc1ccc(CN(C)C)o1", "cid": 5039, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
    {"name": "Famotidine", "smiles": "NS(=O)(=O)N=C(N)NCCSCc1csc(N=C(N)N)n1", "cid": 3325, "class": "Non-Inhibitor (Safe)", "source": "PubChem AID 884"},
]

def build_dataset():
    records = []
    seen = set()

    for item in INITIAL_COMPOUNDS:
        raw_smiles = item["smiles"].strip()
        mol = Chem.MolFromSmiles(raw_smiles)
        if mol is None:
            continue

        canon_smiles = Chem.CanonSmiles(raw_smiles)
        formula = rdMolDescriptors.CalcMolFormula(mol)
        mol_wt = round(rdMolDescriptors.CalcExactMolWt(mol), 2)

        records.append({
            "name": item["name"],
            "canonical_smiles": canon_smiles,
            "smiles": raw_smiles,
            "formula": formula,
            "mol_wt": mol_wt,
            "cid": item.get("cid", ""),
            "activity_class": item.get("class", ""),
            "source": item.get("source", "Curated")
        })
        seen.add(canon_smiles)

    df = pd.DataFrame(records)
    df.to_csv(CSV_FILE_PATH, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"Compiled {len(df)} compounds into {CSV_FILE_PATH}")

if __name__ == "__main__":
    build_dataset()
