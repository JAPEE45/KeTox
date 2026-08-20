"""
routes/api.py — KeTox JSON API routes

Registers:
  POST /predict         — mock compound prediction
  GET  /api/performance — model evaluation metrics

Data comes from data.mock_compounds (single source of truth).
Matching uses an exact alias table — no substring guessing.

INTEGRATION NOTE:
  When real ML inference is ready, replace the lookup + fallback block
  in predict() with:
    from services.predictor import predict_compound
    result = predict_compound(smiles=smiles, compound_name=compound_name)
    return jsonify(result)
"""

from flask import Blueprint, request, jsonify
from data.mock_compounds import KNOWN_COMPOUNDS, COMPOUND_ALIASES, PERFORMANCE_METRICS

api_bp = Blueprint("api", __name__)


# ---------------------------------------------------------------------------
# Generic fallback responses (used when no compound is matched)
# ---------------------------------------------------------------------------

def _safe_fallback(name: str) -> dict:
    return {
        "status": "ok",
        "compound_name": name,
        "smiles": "C1=CC=CC=C1...",
        "formula": "Generic Organic",
        "structure_image_url": "/static/img/mol_input_placeholder.jpg",
        "verdict": "safe",
        "confidence": 0.91,
        "summary": f"{name} is predicted to be non-inhibitory toward CYP3A4 (91% confidence).",
        "models": {
            "random_forest": {"label": "safe", "probability": 0.09},
            "gcn":           {"label": "safe", "probability": 0.06},
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
            {"feature": "TPSA",      "value": -0.25},
            {"feature": "MolLogP",   "value": -0.20},
            {"feature": "RingCount", "value": -0.16},
            {"feature": "MolWt",     "value": -0.12},
        ],
        "lime": [
            {"feature": "RingCount ≤ 2", "weight": -0.29, "direction": "safe"},
            {"feature": "MolLogP ≤ 2.5", "weight": -0.24, "direction": "safe"},
        ],
    }


def _toxic_fallback(name: str) -> dict:
    return {
        "status": "ok",
        "compound_name": name,
        "smiles": "C1=CC=CC=C1...",
        "formula": "Generic Organic",
        "structure_image_url": "/static/img/mol_input_placeholder.jpg",
        "verdict": "toxic",
        "confidence": 0.85,
        "summary": f"{name} is predicted to inhibit CYP3A4 with 85% probability.",
        "models": {
            "random_forest": {"label": "toxic", "probability": 0.82},
            "gcn":           {"label": "toxic", "probability": 0.88},
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
            "css_note": "Predicted steady-state liver concentration (1.78 mg/L) exceeds the warning threshold.",
        },
        "shap": [
            {"feature": "RingCount",     "value":  0.28},
            {"feature": "MolLogP",       "value":  0.22},
            {"feature": "NumHAcceptors", "value":  0.17},
            {"feature": "TPSA",          "value": -0.10},
        ],
        "lime": [
            {"feature": "RingCount > 2", "weight":  0.24, "direction": "toxic"},
            {"feature": "MolLogP > 3.0", "weight":  0.19, "direction": "toxic"},
        ],
    }


# Known-safe generic compound names (simple heuristic for unmatched inputs)
_GENERIC_SAFE_NAMES = frozenset(
    ["caffeine", "vitamin", "glucose", "water", "ethanol", "ibuprofen"]
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@api_bp.route("/predict", methods=["POST"])
def predict():
    """Mock compound prediction — returns structured JSON matching /predict schema."""
    body = request.get_json(silent=True)

    if not body:
        return jsonify({"status": "error", "message": "No JSON body received."}), 400

    compound_name = (
        body.get("compound_name") or
        body.get("name") or
        body.get("query") or
        body.get("smiles") or
        ""
    ).strip()

    if not compound_name:
        return jsonify({
            "status": "error",
            "message": "Please enter a valid molecule or compound name.",
        }), 400

    if len(compound_name) < 2:
        return jsonify({
            "status": "error",
            "message": "Invalid compound name (too short). Example valid names: Ketoconazole, Aspirin, Fluconazole.",
        }), 422

    # Normalise
    norm_key = compound_name.lower().replace("-", " ").replace("_", " ").strip()

    # Step 1 — exact KNOWN_COMPOUNDS key
    matched = KNOWN_COMPOUNDS.get(norm_key)
    # Step 2 — alias table  (exact match only, no substring guessing)
    if matched is None:
        canonical = COMPOUND_ALIASES.get(norm_key)
        if canonical:
            matched = KNOWN_COMPOUNDS.get(canonical)

    if matched:
        response = dict(matched)
        response["status"] = "ok"
        response["compound_name"] = matched["name"]
        return jsonify(response)

    # Generic fallback for unrecognised names
    custom_name = compound_name.title()
    is_safe = any(word in norm_key for word in _GENERIC_SAFE_NAMES)
    fallback = _safe_fallback(custom_name) if is_safe else _toxic_fallback(custom_name)
    return jsonify(fallback)


@api_bp.route("/api/performance")
def api_performance():
    """Return model evaluation metrics as JSON."""
    return jsonify({"status": "ok", "data": PERFORMANCE_METRICS})
