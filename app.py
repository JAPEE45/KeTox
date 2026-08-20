"""
KeTox — CYP3A4 Hepatotoxicity Predictor
Flask application entry point.

MOCK MODE: The /predict route returns hardcoded JSON for frontend development.
Replace with real ML inference when the backend (RDKit, RF model, GCN, SHAP, LIME) is ready.
"""

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/performance")
def performance():
    return render_template("performance.html")


# ---------------------------------------------------------------------------
# API route — mock prediction
# ---------------------------------------------------------------------------
# Known compounds lookup database for realistic mock inference
# ---------------------------------------------------------------------------
KNOWN_COMPOUNDS = {
    "ketoconazole": {
        "name": "Ketoconazole",
        "cid": 47576,
        "formula": "C₂₆H₂₈Cl₂N₄O₄",
        "smiles": "CC(=O)N1CCN(CC1)c2ccc(OC[C@@H]3CO[C@@](Cn4ccnc4)(c5ccc(Cl)cc5Cl)O3)cc2",
        "verdict": "toxic",
        "confidence": 0.87,
        "summary": (
            "Ketoconazole is a potent reference inhibitor of CYP3A4 (87% confidence). "
            "Its lipophilic core, dichlorophenyl group, and imidazole nitrogen coordinate strongly "
            "with the CYP3A4 heme iron, resulting in marked inhibition and potential for hepatotoxicity."
        ),
        "models": {
            "random_forest": {"label": "toxic", "probability": 0.84},
            "gcn":            {"label": "toxic", "probability": 0.91},
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
            "css_note": "Predicted steady-state liver concentration (2.14 mg/L) exceeds the safety threshold of 1.0 mg/L derived from reference IC₅₀ bioassays.",
        },
        "shap": [
            {"feature": "RingCount",          "value":  0.31},
            {"feature": "MolLogP",            "value":  0.24},
            {"feature": "NumHAcceptors",      "value":  0.18},
            {"feature": "TPSA",               "value": -0.12},
            {"feature": "NumRotatableBonds",  "value": -0.09},
            {"feature": "MolWt",              "value":  0.07},
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
        "verdict": "safe",
        "confidence": 0.94,
        "summary": (
            "Aspirin is predicted to be non-inhibitory toward CYP3A4 with high probability (94%), "
            "indicating minimal CYP3A4-mediated liver toxicity risk. Its low molecular weight, "
            "high polarity, and absence of azole or bulky hydrophobic rings preclude strong CYP3A4 binding."
        ),
        "models": {
            "random_forest": {"label": "safe", "probability": 0.08},
            "gcn":            {"label": "safe", "probability": 0.05},
        },
        "similarity": {
            "tanimoto": 0.12,
            "category": "Safe-like",
            "category_description": "Low structural similarity to Ketoconazole (Tanimoto = 0.12). Lacks the bulky halogenated heterocyclic scaffold.",
        },
        "pbpk": {
            "css_mg_per_L": 0.28,
            "css_label": "Normal",
            "css_threshold": 1.0,
            "css_note": "Predicted steady-state liver concentration (0.28 mg/L) is well below the warning threshold of 1.0 mg/L.",
        },
        "shap": [
            {"feature": "TPSA",               "value": -0.29},
            {"feature": "NumHAcceptors",      "value": -0.22},
            {"feature": "MolLogP",            "value": -0.19},
            {"feature": "RingCount",          "value": -0.15},
            {"feature": "MolWt",              "value": -0.11},
            {"feature": "NumRotatableBonds",  "value":  0.04},
        ],
        "lime": [
            {"feature": "RingCount ≤ 1",        "weight": -0.31, "direction": "safe"},
            {"feature": "MolLogP ≤ 2.0",        "weight": -0.26, "direction": "safe"},
            {"feature": "MolWt ≤ 200",          "weight": -0.18, "direction": "safe"},
            {"feature": "NumAromaticRings ≤ 1", "weight": -0.14, "direction": "safe"},
            {"feature": "NumHAcceptors > 2",         "weight":  0.08, "direction": "toxic"},
        ],
    },
    "fluconazole": {
        "name": "Fluconazole",
        "cid": 3365,
        "formula": "C₁₃H₁₂F₂N₆O",
        "smiles": "OC(Cn1cncn1)(Cn1cncn1)c1ccc(F)cc1F",
        "verdict": "toxic",
        "confidence": 0.82,
        "summary": (
            "Fluconazole is predicted to inhibit CYP3A4 (82% probability). As a triazole antifungal, "
            "it interacts directly with the active site of CYP3A4, exhibiting moderate-to-strong enzyme inhibition."
        ),
        "models": {
            "random_forest": {"label": "toxic", "probability": 0.79},
            "gcn":            {"label": "toxic", "probability": 0.85},
        },
        "similarity": {
            "tanimoto": 0.48,
            "category": "Stranger-like",
            "category_description": "Moderate structural similarity to Ketoconazole (Tanimoto = 0.48) — shares the azole pharmacophore within a distinct bis-triazole core.",
        },
        "pbpk": {
            "css_mg_per_L": 1.62,
            "css_label": "Elevated",
            "css_threshold": 1.0,
            "css_note": "Predicted steady-state liver concentration (1.62 mg/L) exceeds the safety threshold of 1.0 mg/L.",
        },
        "shap": [
            {"feature": "RingCount",          "value":  0.27},
            {"feature": "MolLogP",            "value":  0.19},
            {"feature": "NumHAcceptors",      "value":  0.22},
            {"feature": "TPSA",               "value": -0.08},
            {"feature": "NumRotatableBonds",  "value": -0.06},
            {"feature": "MolWt",              "value":  0.05},
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
        "verdict": "safe",
        "confidence": 0.91,
        "summary": (
            "Acetaminophen is predicted to be non-inhibitory toward CYP3A4 (91% probability). "
            "Primarily metabolised via glucuronidation/sulfation, it does not act as a potent CYP3A4 inhibitor."
        ),
        "models": {
            "random_forest": {"label": "safe", "probability": 0.09},
            "gcn":            {"label": "safe", "probability": 0.07},
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
            {"feature": "TPSA",               "value": -0.25},
            {"feature": "MolLogP",            "value": -0.21},
            {"feature": "RingCount",          "value": -0.18},
            {"feature": "MolWt",              "value": -0.14},
        ],
        "lime": [
            {"feature": "RingCount ≤ 1",        "weight": -0.28, "direction": "safe"},
            {"feature": "MolLogP ≤ 1.5",        "weight": -0.22, "direction": "safe"},
        ],
    },
}


# ---------------------------------------------------------------------------
# API route — mock prediction by molecule name
# REPLACE THIS ENTIRE FUNCTION with real inference once backend is ready.
# ---------------------------------------------------------------------------

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"status": "error", "message": "No JSON body received."}), 400

    # Accept compound_name, name, or legacy smiles key
    compound_name = (
        data.get("compound_name") or
        data.get("name") or
        data.get("query") or
        data.get("smiles") or
        ""
    ).strip()

    if not compound_name:
        return jsonify({"status": "error", "message": "Please enter a valid molecule or compound name."}), 400

    if len(compound_name) < 2:
        return jsonify({
            "status": "error",
            "message": "Invalid compound name. Please enter a valid molecule name (e.g. Ketoconazole, Aspirin, Fluconazole)."
        }), 422

    # Normalize lookup key
    norm_key = compound_name.lower().replace("-", " ").replace("_", " ")

    # Check for direct alias matches
    matched_entry = None
    if "keto" in norm_key:
        matched_entry = KNOWN_COMPOUNDS["ketoconazole"]
    elif "aspirin" in norm_key or "acetylsalicylic" in norm_key or "safe" in norm_key:
        matched_entry = KNOWN_COMPOUNDS["aspirin"]
    elif "flucon" in norm_key or "toxic" in norm_key:
        matched_entry = KNOWN_COMPOUNDS["fluconazole"]
    elif "paracetamol" in norm_key or "acetaminophen" in norm_key:
        matched_entry = KNOWN_COMPOUNDS["acetaminophen"]
    else:
        for k, entry in KNOWN_COMPOUNDS.items():
            if k in norm_key:
                matched_entry = entry
                break

    if matched_entry:
        response_data = dict(matched_entry)
        response_data["status"] = "ok"
        response_data["compound_name"] = compound_name if compound_name.lower() not in ["safe compound example", "toxic compound example"] else matched_entry["name"]
        return jsonify(response_data)

    # Fallback generic prediction for custom entered molecule names
    is_safe = any(w in norm_key for w in ["safe", "caffeine", "vitamin", "glucose", "water", "ethanol", "ibuprofen"])
    custom_name = compound_name.title()

    if is_safe:
        return jsonify({
            "status": "ok",
            "compound_name": custom_name,
            "smiles": "C1=CC=CC=C1...",
            "formula": "Generic Organic",
            "verdict": "safe",
            "confidence": 0.91,
            "summary": f"{custom_name} is predicted to be non-inhibitory toward CYP3A4 (91% confidence), indicating low risk of CYP3A4-mediated liver toxicity.",
            "models": {
                "random_forest": {"label": "safe", "probability": 0.09},
                "gcn":            {"label": "safe", "probability": 0.06},
            },
            "similarity": {
                "tanimoto": 0.15,
                "category": "Safe-like",
                "category_description": f"Low structural overlap with Ketoconazole (Tanimoto = 0.15).",
            },
            "pbpk": {
                "css_mg_per_L": 0.31,
                "css_label": "Normal",
                "css_threshold": 1.0,
                "css_note": "Predicted steady-state liver concentration (0.31 mg/L) is safely below the warning threshold.",
            },
            "shap": [
                {"feature": "TPSA",               "value": -0.25},
                {"feature": "MolLogP",            "value": -0.20},
                {"feature": "RingCount",          "value": -0.16},
                {"feature": "MolWt",              "value": -0.12},
            ],
            "lime": [
                {"feature": "RingCount ≤ 2",        "weight": -0.29, "direction": "safe"},
                {"feature": "MolLogP ≤ 2.5",        "weight": -0.24, "direction": "safe"},
            ],
        })
    else:
        return jsonify({
            "status": "ok",
            "compound_name": custom_name,
            "smiles": "C1=CC=CC=C1...",
            "formula": "Generic Organic",
            "verdict": "toxic",
            "confidence": 0.85,
            "summary": f"{custom_name} is predicted to inhibit CYP3A4 with 85% probability, suggesting potential for hepatic enzyme inhibition.",
            "models": {
                "random_forest": {"label": "toxic", "probability": 0.82},
                "gcn":            {"label": "toxic", "probability": 0.88},
            },
            "similarity": {
                "tanimoto": 0.58,
                "category": "Stranger-like",
                "category_description": f"Moderate structural similarity to reference inhibitor Ketoconazole.",
            },
            "pbpk": {
                "css_mg_per_L": 1.78,
                "css_label": "Elevated",
                "css_threshold": 1.0,
                "css_note": "Predicted steady-state liver concentration (1.78 mg/L) exceeds the warning threshold of 1.0 mg/L.",
            },
            "shap": [
                {"feature": "RingCount",          "value":  0.28},
                {"feature": "MolLogP",            "value":  0.22},
                {"feature": "NumHAcceptors",      "value":  0.17},
                {"feature": "TPSA",               "value": -0.10},
            ],
            "lime": [
                {"feature": "RingCount > 2",        "weight":  0.24, "direction": "toxic"},
                {"feature": "MolLogP > 3.0",        "weight":  0.19, "direction": "toxic"},
            ],
        })


# ---------------------------------------------------------------------------
# Dev server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
