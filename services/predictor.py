"""
services/predictor.py — KeTox Prediction Service

Defines the standard `predict_compound()` interface.

CURRENT STATE: MOCK MODE
All values returned are hardcoded/heuristic. Replace each section marked
[REAL BACKEND] once the corresponding ML component is integrated.

INTEGRATION ROADMAP:
  Phase 1 — RDKit descriptors:  compute real molecular features from SMILES
  Phase 2 — Random Forest:      load and run trained RF model
  Phase 3 — GCN:                load and run trained GCN model
  Phase 4 — PBPK:               compute Css from real PBPK compartment model
  Phase 5 — XAI:                SHAP TreeExplainer + LIME + GraphGrad-CAM
  Phase 6 — Structure image:    RDKit Draw.MolToImage → serve as PNG

USAGE (from app.py):
  from services.predictor import predict_compound
  result = predict_compound(smiles="CC(=O)Nc1ccc(O)cc1")
"""

from __future__ import annotations
from typing import Optional


def predict_compound(
    smiles: str,
    compound_name: Optional[str] = None,
) -> dict:
    """
    Run the full KeTox prediction pipeline for a given SMILES string.

    Parameters
    ----------
    smiles : str
        Input SMILES notation for the molecule.
    compound_name : str, optional
        Human-readable name for display. Defaults to smiles[:30].

    Returns
    -------
    dict  — matches the /predict JSON schema:

        status                : "ok" | "error"
        compound_name         : str
        smiles                : str
        formula               : str
        structure_image_url   : str    (URL path to 2D structure PNG)

        verdict               : "toxic" | "safe"
        confidence            : float  (0–1, ensemble)
        summary               : str

        models:
          random_forest       : { label, probability }
          gcn                 : { label, probability }

        similarity:
          tanimoto            : float   (0–1 vs. Ketoconazole)
          category            : "Sibling-like" | "Stranger-like" | "Safe-like"
          category_description: str

        pbpk:
          css_mg_per_L        : float   (predicted steady-state liver concentration)
          css_label           : "Elevated" | "Normal"
          css_threshold       : float   (safety threshold, default 1.0 mg/L)
          css_note            : str

        shap : [ { feature, value } ]    (positive = toward toxic)
        lime : [ { feature, weight, direction } ]

    MOCKED FIELDS (replace when real backend is ready):
      formula, structure_image_url   → Phase 1 (RDKit)
      models.random_forest           → Phase 2 (RF model)
      models.gcn                     → Phase 3 (GCN model)
      pbpk.*                         → Phase 4 (PBPK compartment model)
      shap, lime                     → Phase 5 (XAI: SHAP + LIME + GraphGrad-CAM)
      structure_image_url            → Phase 6 (RDKit Draw.MolToImage)
    """
    # ── [REAL BACKEND] Phase 1: Parse and validate SMILES ───────────────────
    # from rdkit import Chem
    # from rdkit.Chem import rdMolDescriptors
    # mol = Chem.MolFromSmiles(smiles)
    # if mol is None:
    #     return {"status": "error", "message": "Invalid SMILES string."}
    # canonical_smiles = Chem.MolToSmiles(mol)
    # formula = rdMolDescriptors.CalcMolFormula(mol)

    name = compound_name or smiles[:30]

    # ── [MOCK] Generic toxic prediction — replace all fields below ───────────
    return {
        "status": "ok",
        "compound_name": name,
        "smiles": smiles,
        "formula": "C??H??N??O??",                              # [REAL: Phase 1]
        "structure_image_url": "/static/img/mol_input_placeholder.jpg",  # [REAL: Phase 6]

        "verdict": "toxic",
        "confidence": 0.85,                                     # [REAL: Phase 2+3 ensemble]
        "summary": (
            f"{name} is predicted to inhibit CYP3A4 with 85% probability "
            "(mock — real ML inference not connected)."
        ),

        "models": {                                             # [REAL: Phase 2 + Phase 3]
            "random_forest": {"label": "toxic", "probability": 0.82},
            "gcn":           {"label": "toxic", "probability": 0.88},
        },

        "similarity": {                                         # [REAL: Phase 1 — RDKit Tanimoto]
            "tanimoto": 0.50,
            "category": "Stranger-like",
            "category_description": (
                "Moderate structural similarity to Ketoconazole (mock Tanimoto = 0.50)."
            ),
        },

        "pbpk": {                                               # [REAL: Phase 4]
            "css_mg_per_L": 1.50,
            "css_label": "Elevated",
            "css_threshold": 1.0,
            "css_note": (
                "Predicted steady-state liver concentration (1.50 mg/L) "
                "exceeds the safety threshold of 1.0 mg/L. (Mock PBPK.)"
            ),
        },

        "shap": [                                               # [REAL: Phase 5]
            {"feature": "RingCount",     "value":  0.28},
            {"feature": "MolLogP",       "value":  0.22},
            {"feature": "NumHAcceptors", "value":  0.17},
            {"feature": "TPSA",          "value": -0.10},
        ],

        "lime": [                                               # [REAL: Phase 5]
            {"feature": "RingCount > 2", "weight":  0.24, "direction": "toxic"},
            {"feature": "MolLogP > 3.0", "weight":  0.19, "direction": "toxic"},
        ],
    }
