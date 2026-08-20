"""
data/mock_compounds.py — KeTox mock inference database

Single source of truth for:
  - KNOWN_COMPOUNDS  : per-compound prediction responses
  - COMPOUND_ALIASES : input normalisation aliases → KNOWN_COMPOUNDS key
  - PERFORMANCE_METRICS : model evaluation metrics for /api/performance

When real ML inference is wired in (services/predictor.py), KNOWN_COMPOUNDS
becomes a cache of pre-computed results only, and new SMILES go through
predict_compound() instead of a dict lookup.
"""

# ---------------------------------------------------------------------------
# Compound prediction data
# ---------------------------------------------------------------------------

KNOWN_COMPOUNDS: dict = {
    "ketoconazole": {
        "name": "Ketoconazole",
        "cid": 47576,
        "formula": "C₂₆H₂₈Cl₂N₄O₄",
        "smiles": "CC(=O)N1CCN(CC1)c2ccc(OC[C@@H]3CO[C@@](Cn4ccnc4)(c5ccc(Cl)cc5Cl)O3)cc2",
        "structure_image_url": "/static/img/mol_ketoconazole.jpg",
        "verdict": "toxic",
        "confidence": 0.87,
        "summary": (
            "Ketoconazole is a potent reference inhibitor of CYP3A4 (87% confidence). "
            "Its lipophilic core, dichlorophenyl group, and imidazole nitrogen coordinate "
            "strongly with the CYP3A4 heme iron, resulting in marked inhibition and "
            "potential for hepatotoxicity."
        ),
        "models": {
            "random_forest": {"label": "toxic", "probability": 0.84},
            "gcn":           {"label": "toxic", "probability": 0.91},
        },
        "similarity": {
            "tanimoto": 1.00,
            "category": "Sibling-like",
            "category_description": "Exact match to reference compound Ketoconazole (Tanimoto = 1.00).",
        },
        "pbpk": {
            "css_mg_per_L": 2.14,
            "css_label": "Elevated",
            "css_threshold": 1.0,
            "css_note": "Predicted steady-state liver concentration (2.14 mg/L) exceeds the safety threshold of 1.0 mg/L.",
        },
        "shap": [
            {"feature": "RingCount",         "value":  0.31},
            {"feature": "MolLogP",           "value":  0.24},
            {"feature": "NumHAcceptors",     "value":  0.18},
            {"feature": "TPSA",              "value": -0.12},
            {"feature": "NumRotatableBonds", "value": -0.09},
            {"feature": "MolWt",             "value":  0.07},
        ],
        "lime": [
            {"feature": "RingCount > 3",        "weight":  0.28, "direction": "toxic"},
            {"feature": "MolLogP > 4.0",        "weight":  0.21, "direction": "toxic"},
            {"feature": "NumHDonors ≤ 1",       "weight":  0.15, "direction": "toxic"},
            {"feature": "TPSA ≤ 70",            "weight": -0.14, "direction": "safe"},
            {"feature": "NumAromaticRings ≤ 2", "weight": -0.10, "direction": "safe"},
        ],
    },
    "aspirin": {
        "name": "Aspirin (Acetylsalicylic acid)",
        "cid": 2244,
        "formula": "C₉H₈O₄",
        "smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "structure_image_url": "/static/img/mol_input_placeholder.jpg",
        "verdict": "safe",
        "confidence": 0.94,
        "summary": (
            "Aspirin is predicted to be non-inhibitory toward CYP3A4 with high probability "
            "(94%), indicating minimal CYP3A4-mediated liver toxicity risk."
        ),
        "models": {
            "random_forest": {"label": "safe", "probability": 0.08},
            "gcn":           {"label": "safe", "probability": 0.05},
        },
        "similarity": {
            "tanimoto": 0.12,
            "category": "Safe-like",
            "category_description": "Low structural similarity to Ketoconazole (Tanimoto = 0.12).",
        },
        "pbpk": {
            "css_mg_per_L": 0.28,
            "css_label": "Normal",
            "css_threshold": 1.0,
            "css_note": "Predicted steady-state liver concentration (0.28 mg/L) is well below the warning threshold.",
        },
        "shap": [
            {"feature": "TPSA",              "value": -0.29},
            {"feature": "NumHAcceptors",     "value": -0.22},
            {"feature": "MolLogP",           "value": -0.19},
            {"feature": "RingCount",         "value": -0.15},
            {"feature": "MolWt",             "value": -0.11},
            {"feature": "NumRotatableBonds", "value":  0.04},
        ],
        "lime": [
            {"feature": "RingCount ≤ 1",        "weight": -0.31, "direction": "safe"},
            {"feature": "MolLogP ≤ 2.0",        "weight": -0.26, "direction": "safe"},
            {"feature": "MolWt ≤ 200",          "weight": -0.18, "direction": "safe"},
            {"feature": "NumAromaticRings ≤ 1", "weight": -0.14, "direction": "safe"},
            {"feature": "NumHAcceptors > 2",    "weight":  0.08, "direction": "toxic"},
        ],
    },
    "fluconazole": {
        "name": "Fluconazole",
        "cid": 3365,
        "formula": "C₁₃H₁₂F₂N₆O",
        "smiles": "OC(Cn1cncn1)(Cn1cncn1)c1ccc(F)cc1F",
        "structure_image_url": "/static/img/mol_input_placeholder.jpg",
        "verdict": "toxic",
        "confidence": 0.82,
        "summary": (
            "Fluconazole is predicted to inhibit CYP3A4 (82% probability). "
            "As a triazole antifungal, it interacts directly with the CYP3A4 active site."
        ),
        "models": {
            "random_forest": {"label": "toxic", "probability": 0.79},
            "gcn":           {"label": "toxic", "probability": 0.85},
        },
        "similarity": {
            "tanimoto": 0.48,
            "category": "Stranger-like",
            "category_description": "Moderate structural similarity to Ketoconazole (Tanimoto = 0.48).",
        },
        "pbpk": {
            "css_mg_per_L": 1.62,
            "css_label": "Elevated",
            "css_threshold": 1.0,
            "css_note": "Predicted steady-state liver concentration (1.62 mg/L) exceeds the safety threshold.",
        },
        "shap": [
            {"feature": "RingCount",         "value":  0.27},
            {"feature": "MolLogP",           "value":  0.19},
            {"feature": "NumHAcceptors",     "value":  0.22},
            {"feature": "TPSA",              "value": -0.08},
            {"feature": "NumRotatableBonds", "value": -0.06},
            {"feature": "MolWt",             "value":  0.05},
        ],
        "lime": [
            {"feature": "NumAromaticRings > 2", "weight":  0.25, "direction": "toxic"},
            {"feature": "NumHAcceptors > 4",    "weight":  0.18, "direction": "toxic"},
            {"feature": "MolLogP ≤ 3.0",        "weight": -0.12, "direction": "safe"},
            {"feature": "TPSA ≤ 90",            "weight": -0.09, "direction": "safe"},
        ],
    },
    "acetaminophen": {
        "name": "Acetaminophen (Paracetamol)",
        "cid": 1983,
        "formula": "C₈H₉NO₂",
        "smiles": "CC(=O)Nc1ccc(O)cc1",
        "structure_image_url": "/static/img/mol_input_placeholder.jpg",
        "verdict": "safe",
        "confidence": 0.91,
        "summary": (
            "Acetaminophen is predicted to be non-inhibitory toward CYP3A4 (91% probability). "
            "Primarily metabolised via glucuronidation/sulfation."
        ),
        "models": {
            "random_forest": {"label": "safe", "probability": 0.09},
            "gcn":           {"label": "safe", "probability": 0.07},
        },
        "similarity": {
            "tanimoto": 0.09,
            "category": "Safe-like",
            "category_description": "Minimal structural similarity to Ketoconazole (Tanimoto = 0.09).",
        },
        "pbpk": {
            "css_mg_per_L": 0.35,
            "css_label": "Normal",
            "css_threshold": 1.0,
            "css_note": "Predicted steady-state liver concentration (0.35 mg/L) is well below the safety threshold.",
        },
        "shap": [
            {"feature": "TPSA",          "value": -0.25},
            {"feature": "MolLogP",       "value": -0.21},
            {"feature": "RingCount",     "value": -0.18},
            {"feature": "MolWt",         "value": -0.14},
        ],
        "lime": [
            {"feature": "RingCount ≤ 1", "weight": -0.28, "direction": "safe"},
            {"feature": "MolLogP ≤ 1.5", "weight": -0.22, "direction": "safe"},
        ],
    },
}

# ---------------------------------------------------------------------------
# Alias table — exact input strings that map to KNOWN_COMPOUNDS keys.
# Add entries here when new compounds are added above.
# ---------------------------------------------------------------------------
COMPOUND_ALIASES: dict[str, str] = {
    # Ketoconazole
    "ketoconazole":       "ketoconazole",
    "keto":               "ketoconazole",
    # Aspirin
    "aspirin":            "aspirin",
    "acetylsalicylic acid": "aspirin",
    "acetylsalicylate":   "aspirin",
    # Fluconazole
    "fluconazole":        "fluconazole",
    "flucon":             "fluconazole",
    # Acetaminophen
    "acetaminophen":      "acetaminophen",
    "paracetamol":        "acetaminophen",
    "tylenol":            "acetaminophen",
}

# ---------------------------------------------------------------------------
# Performance metrics
# ---------------------------------------------------------------------------

PERFORMANCE_METRICS: dict = {
    "rf": {
        "overall":  {"accuracy": 0.926, "sensitivity": 0.907, "specificity": 0.947, "mcc": 0.852},
        "sibling":  {"accuracy": 0.891, "sensitivity": 0.872, "specificity": 0.921, "mcc": 0.795},
        "stranger": {"accuracy": 0.934, "sensitivity": 0.908, "specificity": 0.956, "mcc": 0.863},
        "safe":     {"accuracy": 0.952, "sensitivity": 0.941, "specificity": 0.963, "mcc": 0.902},
        "cm": {
            "sibling":  {"tp": 156, "fn": 23, "fp": 18, "tn": 192},
            "stranger": {"tp": 201, "fn": 19, "fp": 14, "tn": 228},
            "safe":     {"tp": 12,  "fn": 8,  "fp": 5,  "tn": 350},
        },
    },
    "gcn": {
        "overall":  {"accuracy": 0.911, "sensitivity": 0.892, "specificity": 0.930, "mcc": 0.824},
        "sibling":  {"accuracy": 0.873, "sensitivity": 0.855, "specificity": 0.895, "mcc": 0.750},
        "stranger": {"accuracy": 0.918, "sensitivity": 0.894, "specificity": 0.938, "mcc": 0.831},
        "safe":     {"accuracy": 0.941, "sensitivity": 0.928, "specificity": 0.957, "mcc": 0.885},
        "cm": {
            "sibling":  {"tp": 148, "fn": 31, "fp": 22, "tn": 188},
            "stranger": {"tp": 196, "fn": 23, "fp": 17, "tn": 225},
            "safe":     {"tp": 11,  "fn": 9,  "fp": 6,  "tn": 349},
        },
    },
}
