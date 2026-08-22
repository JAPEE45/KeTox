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
    """Predict CYP3A4 hepatotoxicity — handles both SMILES strings and chemical compound names."""
    from flask import session
    body = request.get_json(silent=True)

    if not body:
        return jsonify({"status": "error", "message": "No JSON body received."}), 400

    query = (
        body.get("compound_name") or
        body.get("name") or
        body.get("query") or
        body.get("smiles") or
        ""
    ).strip()

    if not query:
        return jsonify({
            "status": "error",
            "message": "Please enter a valid molecule SMILES string or compound name.",
        }), 400

    if len(query) < 2:
        return jsonify({
            "status": "error",
            "message": "Invalid input (too short). Example valid inputs: Ketoconazole, Aspirin, or a SMILES string.",
        }), 422

    from services.compound_lookup import resolve_compound_input
    resolved = resolve_compound_input(query)

    if not resolved["is_valid"]:
        return jsonify({
            "status": "error",
            "message": f"Could not parse '{query}' as a valid SMILES string or recognize it in the chemical dataset.",
        }), 422

    from services.predictor import predict_compound
    result = predict_compound(smiles=resolved["smiles"], compound_name=resolved["compound_name"])
    
    # Enrich response with metadata if matched in local dataset
    if resolved.get("metadata"):
        result["dataset_metadata"] = resolved["metadata"]

    # Automatically save prediction to SQLite history
    if result.get("status") == "ok":
        try:
            from services.db import save_prediction_history
            user_id = session.get("user_id")
            user_email = session.get("email")
            save_prediction_history(result, user_id=user_id, user_email=user_email)
        except Exception as e:
            # Non-blocking error for history logging
            print(f"Warning: Failed to log prediction history: {e}")

    return jsonify(result)


@api_bp.route("/api/performance")
def api_performance():
    """Return model evaluation metrics as JSON."""
    return jsonify({"status": "ok", "data": PERFORMANCE_METRICS})


@api_bp.route("/api/prediction-history", methods=["GET"])
def api_prediction_history():
    """Query prediction history log with filters and pagination."""
    from services.db import get_prediction_history
    
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    search = request.args.get("search", "").strip() or None
    verdict = request.args.get("verdict", "").strip() or None
    agreement = request.args.get("agreement", "").strip() or None
    model_view = request.args.get("model_view", "").strip() or None
    sort_by = request.args.get("sort_by", "date_desc").strip()

    data = get_prediction_history(
        limit=limit,
        offset=offset,
        search=search,
        verdict=verdict,
        agreement=agreement,
        model_view=model_view,
        sort_by=sort_by
    )
    return jsonify(data)


@api_bp.route("/api/prediction-history/stats", methods=["GET"])
def api_prediction_history_stats():
    """Return aggregated historical prediction analytics and comparative model breakdown."""
    from services.db import get_prediction_history_stats
    stats = get_prediction_history_stats()
    return jsonify(stats)


@api_bp.route("/api/prediction-history/seed", methods=["POST"])
def api_prediction_history_seed():
    """Re-seed default curated historical predictions into SQLite."""
    from services.db import seed_prediction_history
    try:
        seed_prediction_history(force=True)
        return jsonify({"status": "ok", "message": "Prediction history successfully re-seeded."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/api/prediction-history/<int:item_id>", methods=["DELETE"])
def api_delete_prediction_history_item(item_id):
    """Delete a single history entry by ID."""
    from services.db import delete_prediction_history_item
    result = delete_prediction_history_item(item_id)
    return jsonify(result)


@api_bp.route("/api/prediction-history/clear", methods=["DELETE"])
def api_clear_prediction_history():
    """Clear all historical predictions."""
    from services.db import clear_prediction_history
    result = clear_prediction_history()
    return jsonify(result)

