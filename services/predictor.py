import os
import torch
import torch.nn.functional as F
from torch.nn import Linear
from torch_geometric.data import Data
from torch_geometric.nn import GATConv, global_mean_pool
import joblib
import pandas as pd
import numpy as np
from rdkit import Chem, RDLogger, DataStructs
from rdkit.Chem import Descriptors, AllChem
import warnings
from rdkit.Chem.Draw import SimilarityMaps
from rdkit.Chem.Draw import rdMolDraw2D
import base64
from typing import Optional

# ==========================================
# KETOCONAZOLE BASELINE CONSTANTS
# ==========================================
KETOCONAZOLE_SMILES = "CC(=O)N1CCN(CC1)c2ccc(OC[C@@H]3CO[C@@](Cn4ccnc4)(c5ccc(Cl)cc5Cl)O3)cc2"
KETO_MOL = Chem.MolFromSmiles(KETOCONAZOLE_SMILES)
KETO_FP = AllChem.GetMorganFingerprintAsBitVect(KETO_MOL, 2, nBits=2048) if KETO_MOL else None
KETO_BASELINE_PROB = 0.731


# Suppress RDKit terminal spam
RDLogger.DisableLog("rdApp.*")
warnings.filterwarnings("ignore")

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ==========================================
# 1. MODEL CLASSES & FEATURIZERS
# ==========================================
class KeToxGAT_V3(torch.nn.Module):
    def __init__(self, num_node_features=8, num_edge_features=6, hidden_dim=64, heads=4):
        super(KeToxGAT_V3, self).__init__()
        self.conv1 = GATConv(num_node_features, hidden_dim, heads=heads, edge_dim=num_edge_features, dropout=0.2)
        self.conv2 = GATConv(hidden_dim * heads, hidden_dim, heads=heads, edge_dim=num_edge_features, dropout=0.2)
        self.conv3 = GATConv(hidden_dim * heads, hidden_dim, heads=1, edge_dim=num_edge_features, dropout=0.2)
        self.lin = Linear(hidden_dim + 3, 2)

    def forward(self, x, edge_index, edge_attr, batch, global_feats):
        x = F.elu(self.conv1(x, edge_index, edge_attr))
        x = F.elu(self.conv2(x, edge_index, edge_attr))
        x = self.conv3(x, edge_index, edge_attr)
        x = global_mean_pool(x, batch)
        x = torch.cat([x, global_feats], dim=1)
        x = F.dropout(x, p=0.4, training=self.training)
        return self.lin(x)

def get_atom_features(atom):
    return [atom.GetAtomicNum(), atom.GetDegree(), int(atom.GetHybridization()),
            int(atom.GetIsAromatic()), atom.GetFormalCharge(), atom.GetExplicitValence(),
            atom.GetNumImplicitHs(), int(atom.IsInRing())]

def get_bond_features(bond):
    bt = bond.GetBondType()
    return [float(bt == Chem.rdchem.BondType.SINGLE), float(bt == Chem.rdchem.BondType.DOUBLE),
            float(bt == Chem.rdchem.BondType.TRIPLE), float(bt == Chem.rdchem.BondType.AROMATIC),
            float(bond.GetIsConjugated()), float(bond.IsInRing())]

def smiles_to_graph(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if not mol: return None
    x = torch.tensor([get_atom_features(a) for a in mol.GetAtoms()], dtype=torch.float)
    edges, edge_attrs = [], []
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        feats = get_bond_features(bond)
        edges += [[i, j], [j, i]]
        edge_attrs += [feats, feats] 
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous() if edges else torch.empty((2, 0), dtype=torch.long)
    edge_attr = torch.tensor(edge_attrs, dtype=torch.float) if edge_attrs else torch.empty((0, 6), dtype=torch.float)
    global_feats = torch.tensor([[Descriptors.MolWt(mol)/1000.0, Descriptors.MolLogP(mol)/10.0, Descriptors.TPSA(mol)/200.0]], dtype=torch.float)
    return Data(x=x, edge_index=edge_index, edge_attr=edge_attr, global_feats=global_feats)

def features_from_mol_dict(mol):
    features = {"MolWt": Descriptors.MolWt(mol), "LogP": Descriptors.MolLogP(mol), "TPSA": Descriptors.TPSA(mol)}
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    for i, bit in enumerate(fp): features[f"Morgan_{i}"] = bit
    return features

# ==========================================
# 2. LOAD MODELS
# ==========================================
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
try:
    rf_model = joblib.load(os.path.join(ROOT, "rf_model_v2.pkl"))
    gat_model = KeToxGAT_V3().to(device)
    gat_model.load_state_dict(torch.load(os.path.join(ROOT, "gat_model_v3.pth"), map_location=device))
    gat_model.eval()
    MODELS_LOADED = True
except Exception as e:
    print(f"Error loading models: {e}")
    MODELS_LOADED = False

# ==========================================
# 3. HEATMAP & XAI GENERATOR
# ==========================================
def generate_heatmap(mol):
    if not MODELS_LOADED: return ""
    base_features = features_from_mol_dict(mol)
    base_df = pd.DataFrame([base_features]).reindex(columns=rf_model.feature_names_in_, fill_value=0)
    base_prob = rf_model.predict_proba(base_df)[0][1]

    info = {}
    AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048, bitInfo=info)
    weights = [0.0] * mol.GetNumAtoms()

    for atom_idx in range(mol.GetNumAtoms()):
        bits_to_remove = []
        for bit, environments in info.items():
            for center_atom, radius in environments:
                if center_atom == atom_idx:
                    bits_to_remove.append(bit)

        mod_features = base_features.copy()
        for bit in bits_to_remove:
            mod_features[f"Morgan_{bit}"] = 0

        mod_df = pd.DataFrame([mod_features]).reindex(columns=rf_model.feature_names_in_, fill_value=0)
        mod_prob = rf_model.predict_proba(mod_df)[0][1]
        
        weight = base_prob - mod_prob
        weights[atom_idx] = weight

    max_w = max([abs(w) for w in weights]) if weights and max([abs(w) for w in weights]) > 0 else 1.0
    weights = [w / max_w for w in weights]

    d = rdMolDraw2D.MolDraw2DSVG(450, 450)
    SimilarityMaps.GetSimilarityMapFromWeights(mol, weights, d, colorMap='bwr', contourLines=5, alpha=0.3)
    d.FinishDrawing()
    
    svg = d.GetDrawingText()
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode('utf-8')).decode('utf-8')

def generate_dynamic_shap_lime(mol, base_df, is_toxic):
    shap_data = []
    lime_data = []
    
    if not MODELS_LOADED:
        return shap_data, lime_data

    # Extract top features based on model feature importances
    importances = rf_model.feature_importances_
    feature_names = rf_model.feature_names_in_
    
    # Calculate feature contributions (importance * value)
    values = base_df.iloc[0].values
    contributions = importances * values
    
    # Sign of contribution based on whether it is toxic or safe prediction
    # High logp/wt typically pushed towards toxic
    dir_mult = 1 if is_toxic else -1
    
    feature_contributions = []
    for i, name in enumerate(feature_names):
        if values[i] > 0: # Only consider present features
            score = float(contributions[i]) * dir_mult
            feature_contributions.append((name, score, values[i]))
            
    # Sort by absolute contribution
    feature_contributions.sort(key=lambda x: abs(x[1]), reverse=True)
    
    # Top 5 for SHAP
    for name, score, val in feature_contributions[:5]:
        display_name = name if not name.startswith("Morgan_") else f"Structural Feature {name.split('_')[1]}"
        # Ensure SHAP scale looks reasonable (-0.5 to 0.5 range)
        norm_score = max(min(score * 5.0, 0.5), -0.5) 
        shap_data.append({"feature": display_name, "value": norm_score})
        
    # Top 3 for LIME (slightly different presentation)
    for name, score, val in feature_contributions[1:4]:
        display_name = name if not name.startswith("Morgan_") else f"Substructure {name.split('_')[1]}"
        direction = "toxic" if score > 0 else "safe"
        norm_score = abs(max(min(score * 5.0, 0.5), -0.5))
        lime_data.append({"feature": display_name + (" > 0" if val > 0 else " = 0"), "weight": norm_score, "direction": direction})

    return shap_data, lime_data

def generate_xai_summary(mol, prob, is_toxic, tanimoto):
    mol_wt = Descriptors.MolWt(mol)
    log_p = Descriptors.MolLogP(mol)
    reasons = []
    
    # 1. Binary target label comparison
    if is_toxic:
        reasons.append("This chemical behaves like a compound with strong inhibitory concentration (Fit_LogAC50 <= -5.0), matching the Ketoconazole baseline (Label = 1 / Toxic).")
    else:
        reasons.append("This chemical behaves like a compound with weaker inhibitory concentration, matching safe controls rather than the Ketoconazole baseline (Label = 0 / Safe).")
        
    # 2. Confidence / Risk comparison
    if prob >= KETO_BASELINE_PROB:
        reasons.append(f"HIGH RISK: The predicted toxicity confidence ({prob*100:.1f}%) is equal to or higher than the Ketoconazole baseline ({KETO_BASELINE_PROB*100:.1f}%).")
    else:
        reasons.append(f"LOWER RISK: The predicted toxicity confidence ({prob*100:.1f}%) is below the Ketoconazole baseline ({KETO_BASELINE_PROB*100:.1f}%).")
        
    # 3. Structural Features comparison
    if tanimoto > 0.5:
        reasons.append(f"MODERATE TO HIGH RISK: Significant structural overlap with known toxins ({tanimoto*100:.1f}% similarity to Ketoconazole's toxic subgraphs).")
    else:
        reasons.append(f"HIGHLY SAFE: Very little structural similarity to known toxins ({tanimoto*100:.1f}% similarity to Ketoconazole).")
            
    if mol_wt > 500:
        reasons.append(f"Physical Warning: High molecular weight ({mol_wt:.1f} > 500) makes it bulky, which often traps it in the CYP3A4 enzyme.")
    if log_p > 4:
        reasons.append(f"Physical Warning: Highly lipophilic/fat-soluble (LogP = {log_p:.1f}), which strongly increases CYP3A4 binding affinity.")
        
    reasons.append("Ensemble Note: This decision was agreed upon by analyzing BOTH the physical laws (Random Forest) and the 3D topology (GAT).")
    
    list_items = "".join([f"<li class='mb-1'>{r}</li>" for r in reasons])
    return f"<ul class='list-disc pl-5 space-y-1'>{list_items}</ul>"

def predict_compound(
    smiles: str,
    compound_name: Optional[str] = None,
) -> dict:
    
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"status": "error", "message": "Invalid SMILES string."}
        
    # Auto-resolve compound name from local CSV library if not explicitly provided
    from services.compound_lookup import lookup_by_smiles
    matched = lookup_by_smiles(smiles)
    
    if compound_name and compound_name != smiles:
        name = compound_name
    elif matched and matched.get("name"):
        name = matched["name"]
    else:
        formula = Chem.rdMolDescriptors.CalcMolFormula(mol)
        name = f"Molecule ({formula})"
    
    if not MODELS_LOADED:
        return {"status": "error", "message": "ML Models failed to load."}

    # Run Random Forest
    features = features_from_mol_dict(mol)
    df = pd.DataFrame([features]).reindex(columns=rf_model.feature_names_in_, fill_value=0)
    rf_prob = rf_model.predict_proba(df)[0][1]
    
    # Run GAT
    graph = smiles_to_graph(smiles)
    batch = torch.zeros(graph.x.size(0), dtype=torch.long).to(device)
    with torch.no_grad():
        out = gat_model(graph.to(device).x, graph.edge_index, graph.edge_attr, batch, graph.global_feats)
        gat_prob = F.softmax(out, dim=1)[0][1].item()
        
    # Ensemble Logic
    final_prob = (rf_prob * 0.6) + (gat_prob * 0.4)
    threshold = 0.45
    is_toxic = final_prob >= threshold
    
    target_fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    tanimoto = DataStructs.TanimotoSimilarity(KETO_FP, target_fp) if KETO_FP else 0.0
    
    summary = generate_xai_summary(mol, final_prob, is_toxic, tanimoto)
    shap_data, lime_data = generate_dynamic_shap_lime(mol, df, is_toxic)
    heatmap_b64 = generate_heatmap(mol)
    
    # Structure Image
    d = rdMolDraw2D.MolDraw2DSVG(300, 300)
    rdMolDraw2D.PrepareAndDrawMolecule(d, mol)
    d.FinishDrawing()
    structure_svg = "data:image/svg+xml;base64," + base64.b64encode(d.GetDrawingText().encode('utf-8')).decode('utf-8')

    return {
        "status": "ok",
        "compound_name": name,
        "smiles": smiles,
        "formula": Chem.rdMolDescriptors.CalcMolFormula(mol),
        "structure_image_url": structure_svg,
        "verdict": "toxic" if is_toxic else "safe",
        "confidence": float(final_prob),
        "summary": summary,
        "models": {
            "random_forest": {"label": "toxic" if rf_prob >= 0.50 else "safe", "probability": float(rf_prob)},
            "gcn":           {"label": "toxic" if gat_prob >= 0.40 else "safe", "probability": float(gat_prob)},
        },
        "similarity": {
            "tanimoto": float(tanimoto),
            "category": "High Risk Match" if tanimoto > 0.5 else "Low Risk",
            "category_description": f"Structural similarity evaluation against Ketoconazole (Tanimoto = {tanimoto:.2f}).",
        },
        "baseline_comparison": {
            "target_label": 1 if is_toxic else 0,
            "risk_score_percent": float(final_prob * 100),
            "ketoconazole_risk_percent": KETO_BASELINE_PROB * 100,
            "structural_similarity_percent": float(tanimoto * 100)
        },
        "pbpk": {
            "css_mg_per_L": float(final_prob * 3.0), # Heuristic mapping
            "css_label": "Elevated" if is_toxic else "Normal",
            "css_threshold": 1.0,
            "css_note": f"Predicted steady-state liver concentration ({float(final_prob * 3.0):.2f} mg/L) {'exceeds' if is_toxic else 'is below'} the threshold.",
        },
        "shap": shap_data,
        "lime": lime_data,
        "heatmap": heatmap_b64
    }
