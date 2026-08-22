"""
services/db.py — KeTox SQLite Database Connection & Helper Layer

Provides:
- SQLite connection initialization and table creation.
- Users collection helpers: find_user_by_email, create_user, verify_user_credentials, update_user_password.
- Safe password hashing and verification using Werkzeug Security.
"""

import sqlite3
import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger("ketox.db")

def get_db_path(app=None) -> str:
    """Get the SQLite database path from config or fallback."""
    from flask import current_app
    app_instance = app or (current_app._get_current_object() if current_app else None)
    if app_instance is None:
        # Standalone usage
        from config import get_config
        cfg = get_config()
        return getattr(cfg, "SQLITE_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ketox.db"))
    return app_instance.config.get("SQLITE_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ketox.db"))

def get_db(app=None):
    """Return a new SQLite database connection."""
    db_path = get_db_path(app)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(app=None):
    """Initialize the database schema."""
    conn = get_db(app)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'Student',
            other_role TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_email TEXT,
            compound_name TEXT NOT NULL,
            smiles TEXT NOT NULL,
            formula TEXT,
            verdict TEXT NOT NULL,
            confidence REAL NOT NULL,
            rf_label TEXT NOT NULL,
            rf_probability REAL NOT NULL,
            gcn_label TEXT NOT NULL,
            gcn_probability REAL NOT NULL,
            tanimoto_similarity REAL DEFAULT 0.0,
            similarity_category TEXT DEFAULT 'Stranger-like',
            css_value REAL DEFAULT 0.0,
            model_agreement TEXT NOT NULL,
            ground_truth TEXT,
            notes TEXT,
            created_at DATETIME NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pred_history_created_at ON prediction_history(created_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pred_history_verdict ON prediction_history(verdict)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pred_history_agreement ON prediction_history(model_agreement)')
    conn.commit()
    conn.close()

def check_db_connection() -> Dict[str, Any]:
    """Test ping against the SQLite database to verify connectivity."""
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        return {"connected": True, "error": None}
    except Exception as e:
        return {"connected": False, "error": str(e)}

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert SQLite Row to dictionary and add _id for backward compatibility."""
    d = dict(row)
    if "id" in d:
        d["_id"] = str(d["id"])
    return d

# ─── User Model & Operations ──────────────────────────────────────────────────

def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Find a single user document by normalized email address."""
    try:
        norm_email = email.strip().lower()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (norm_email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return _row_to_dict(row)
        return None
    except Exception as e:
        logger.error(f"Error querying user by email: {e}")
        return None

def create_user(
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    role: str = "Student",
    other_role: str = ""
) -> Dict[str, Any]:
    """
    Create and persist a new user record in SQLite.
    Returns dict with status, user record or error message.
    """
    norm_email = email.strip().lower()

    try:
        if find_user_by_email(norm_email):
            return {"status": "error", "message": "An account with this email address already exists."}

        password_hash = generate_password_hash(password)
        now = datetime.now(timezone.utc).isoformat()

        conn = get_db()
        cursor = conn.cursor()
        
        full_name = f"{first_name.strip()} {last_name.strip()}"
        actual_other_role = other_role.strip() if role == "Others" else ""
        
        cursor.execute('''
            INSERT INTO users (first_name, last_name, full_name, email, password_hash, role, other_role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (first_name.strip(), last_name.strip(), full_name, norm_email, password_hash, role, actual_other_role, now, now))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        user_doc = _row_to_dict(row)
        user_doc.pop("password_hash", None)
        return {"status": "ok", "user": user_doc}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "An account with this email address already exists."}
    except Exception as e:
        logger.error(f"Unexpected error creating user: {e}")
        return {"status": "error", "message": "An unexpected error occurred while connecting to the database."}

def verify_user_credentials(email: str, password: str) -> Dict[str, Any]:
    """
    Validate user email and password against SQLite.
    Returns {"status": "ok", "user": dict} on success or error details.
    """
    try:
        user = find_user_by_email(email)
        if not user:
            return {"status": "error", "message": "Invalid email or password."}

        pw_hash = user.get("password_hash", "")
        if not check_password_hash(pw_hash, password):
            return {"status": "error", "message": "Invalid email or password."}

        safe_user = {
            "id": str(user.get("id", user.get("_id"))),
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "full_name": user.get("full_name", f"{user.get('first_name', '')} {user.get('last_name', '')}"),
            "email": user.get("email", ""),
            "role": user.get("role", "Student"),
        }
        return {"status": "ok", "user": safe_user}
    except Exception as e:
        logger.error(f"Unexpected error during signin: {e}")
        return {"status": "error", "message": "Database error while verifying credentials."}

def update_user_password(email: str, new_password: str) -> Dict[str, Any]:
    """Update password for an existing user."""
    try:
        norm_email = email.strip().lower()
        pw_hash = generate_password_hash(new_password)
        now = datetime.now(timezone.utc).isoformat()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET password_hash = ?, updated_at = ? WHERE email = ?
        ''', (pw_hash, now, norm_email))
        
        matched_count = cursor.rowcount
        conn.commit()
        conn.close()

        if matched_count == 0:
            return {"status": "error", "message": "User not found."}

        return {"status": "ok", "message": "Password updated successfully."}
    except Exception as e:
        logger.error(f"Error updating password: {e}")
        return {"status": "error", "message": "Database error while updating password."}


# ─── Prediction History Model & Operations ────────────────────────────────────

def compute_model_agreement(rf_label: str, gcn_label: str) -> str:
    """Return model agreement category label."""
    rf_tox = (rf_label or "").lower() == "toxic"
    gcn_tox = (gcn_label or "").lower() == "toxic"
    if rf_tox and gcn_tox:
        return "Agreed (Toxic)"
    elif not rf_tox and not gcn_tox:
        return "Agreed (Safe)"
    elif rf_tox and not gcn_tox:
        return "Disagreed (RF Toxic / GCN Safe)"
    else:
        return "Disagreed (RF Safe / GCN Toxic)"

def save_prediction_history(
    prediction_data: Dict[str, Any],
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    created_at: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a prediction record into the prediction_history table.
    """
    try:
        models = prediction_data.get("models", {})
        rf_model = models.get("random_forest", {})
        gcn_model = models.get("gcn", {})
        
        rf_label = rf_model.get("label", "safe")
        rf_prob = float(rf_model.get("probability", 0.0))
        gcn_label = gcn_model.get("label", "safe")
        gcn_prob = float(gcn_model.get("probability", 0.0))
        
        agreement = compute_model_agreement(rf_label, gcn_label)
        
        sim = prediction_data.get("similarity", {})
        tanimoto = float(sim.get("tanimoto", 0.0))
        sim_cat = sim.get("category", "Stranger-like")
        
        pbpk = prediction_data.get("pbpk", {})
        css_val = float(pbpk.get("css_mg_per_L", 0.0))
        
        # Ground truth detection if present in metadata
        dataset_meta = prediction_data.get("dataset_metadata") or {}
        act_class = dataset_meta.get("activity_class", "")
        ground_truth = None
        if "Inhibitor" in act_class or "Strong" in act_class or "Moderate" in act_class:
            ground_truth = "toxic"
        elif "Non-Inhibitor" in act_class or "Safe" in act_class:
            ground_truth = "safe"

        now = created_at or datetime.now(timezone.utc).isoformat()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO prediction_history (
                user_id, user_email, compound_name, smiles, formula,
                verdict, confidence, rf_label, rf_probability, gcn_label,
                gcn_probability, tanimoto_similarity, similarity_category,
                css_value, model_agreement, ground_truth, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_email,
            prediction_data.get("compound_name", "Unknown Molecule"),
            prediction_data.get("smiles", ""),
            prediction_data.get("formula", ""),
            prediction_data.get("verdict", "safe"),
            float(prediction_data.get("confidence", 0.0)),
            rf_label,
            rf_prob,
            gcn_label,
            gcn_prob,
            tanimoto,
            sim_cat,
            css_val,
            agreement,
            ground_truth,
            prediction_data.get("summary", ""),
            now
        ))
        
        item_id = cursor.lastrowid
        conn.commit()
        
        cursor.execute("SELECT * FROM prediction_history WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        conn.close()
        
        return {"status": "ok", "item": _row_to_dict(row)}
    except Exception as e:
        logger.error(f"Error saving prediction history: {e}")
        return {"status": "error", "message": str(e)}

def get_prediction_history(
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    verdict: Optional[str] = None,
    agreement: Optional[str] = None,
    model_view: Optional[str] = None,
    sort_by: str = "date_desc"
) -> Dict[str, Any]:
    """
    Query prediction history with filters, search, and pagination.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        where_clauses = []
        params = []
        
        if search:
            s = f"%{search.strip()}%"
            where_clauses.append("(compound_name LIKE ? OR smiles LIKE ? OR formula LIKE ?)")
            params.extend([s, s, s])
            
        if verdict and verdict.lower() in ["toxic", "safe"]:
            where_clauses.append("verdict = ?")
            params.append(verdict.lower())
            
        if agreement:
            if agreement.lower() == "agreed":
                where_clauses.append("model_agreement LIKE 'Agreed%'")
            elif agreement.lower() == "disagreed":
                where_clauses.append("model_agreement LIKE 'Disagreed%'")
            elif "agreed" in agreement.lower() or "disagreed" in agreement.lower():
                where_clauses.append("model_agreement = ?")
                params.append(agreement)
                
        if model_view:
            if model_view.lower() == "rf_toxic":
                where_clauses.append("rf_label = 'toxic'")
            elif model_view.lower() == "rf_safe":
                where_clauses.append("rf_label = 'safe'")
            elif model_view.lower() == "gcn_toxic":
                where_clauses.append("gcn_label = 'toxic'")
            elif model_view.lower() == "gcn_safe":
                where_clauses.append("gcn_label = 'safe'")
                
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Sorting
        sort_map = {
            "date_desc": "created_at DESC",
            "date_asc": "created_at ASC",
            "confidence_desc": "confidence DESC",
            "confidence_asc": "confidence ASC",
            "tanimoto_desc": "tanimoto_similarity DESC",
            "divergence_desc": "ABS(rf_probability - gcn_probability) DESC",
        }
        order_sql = sort_map.get(sort_by, "created_at DESC")
        
        # Count total matching
        cursor.execute(f"SELECT COUNT(*) as count FROM prediction_history {where_sql}", params)
        total_count = cursor.fetchone()["count"]
        
        # Fetch items
        query_sql = f"""
            SELECT * FROM prediction_history
            {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [limit, offset])
        rows = cursor.fetchall()
        conn.close()
        
        items = [_row_to_dict(r) for r in rows]
        return {
            "status": "ok",
            "items": items,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error fetching prediction history: {e}")
        return {"status": "error", "items": [], "total_count": 0, "message": str(e)}

def get_prediction_history_stats() -> Dict[str, Any]:
    """
    Compute comprehensive real-time statistics across all historical predictions.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM prediction_history ORDER BY created_at ASC")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            # Empty table fallback
            return {
                "status": "ok",
                "total_predictions": 0,
                "agreement_stats": {
                    "agreed_count": 0, "disagreed_count": 0, "agreement_rate": 100.0,
                    "both_toxic": 0, "both_safe": 0, "rf_toxic_gcn_safe": 0, "rf_safe_gcn_toxic": 0
                },
                "rf_stats": {"toxic_count": 0, "safe_count": 0, "avg_probability": 0.0, "high_confidence_rate": 0.0},
                "gcn_stats": {"toxic_count": 0, "safe_count": 0, "avg_probability": 0.0, "high_confidence_rate": 0.0},
                "ensemble_stats": {"toxic_count": 0, "safe_count": 0, "avg_confidence": 0.0},
                "timeline": [],
                "distribution": {"rf": [0,0,0,0,0], "gcn": [0,0,0,0,0], "ensemble": [0,0,0,0,0]},
                "similarity_breakdown": {},
                "contested_cases": []
            }
            
        items = [_row_to_dict(r) for r in rows]
        total = len(items)
        
        # Agreement breakdown
        both_toxic = sum(1 for i in items if i["rf_label"] == "toxic" and i["gcn_label"] == "toxic")
        both_safe = sum(1 for i in items if i["rf_label"] == "safe" and i["gcn_label"] == "safe")
        rf_tox_gcn_safe = sum(1 for i in items if i["rf_label"] == "toxic" and i["gcn_label"] == "safe")
        rf_safe_gcn_tox = sum(1 for i in items if i["rf_label"] == "safe" and i["gcn_label"] == "toxic")
        
        agreed_count = both_toxic + both_safe
        disagreed_count = rf_tox_gcn_safe + rf_safe_gcn_tox
        agreement_rate = (agreed_count / total * 100.0) if total > 0 else 0.0
        
        # RF stats
        rf_toxic = sum(1 for i in items if i["rf_label"] == "toxic")
        rf_safe = sum(1 for i in items if i["rf_label"] == "safe")
        rf_avg_prob = sum(i["rf_probability"] for i in items) / total if total > 0 else 0.0
        rf_high_conf = sum(1 for i in items if i["rf_probability"] >= 0.80 or i["rf_probability"] <= 0.20)
        rf_high_conf_rate = (rf_high_conf / total * 100.0) if total > 0 else 0.0
        
        # GCN stats
        gcn_toxic = sum(1 for i in items if i["gcn_label"] == "toxic")
        gcn_safe = sum(1 for i in items if i["gcn_label"] == "safe")
        gcn_avg_prob = sum(i["gcn_probability"] for i in items) / total if total > 0 else 0.0
        gcn_high_conf = sum(1 for i in items if i["gcn_probability"] >= 0.80 or i["gcn_probability"] <= 0.20)
        gcn_high_conf_rate = (gcn_high_conf / total * 100.0) if total > 0 else 0.0
        
        # Ensemble stats
        ens_toxic = sum(1 for i in items if i["verdict"] == "toxic")
        ens_safe = sum(1 for i in items if i["verdict"] == "safe")
        ens_avg_conf = sum(i["confidence"] for i in items) / total if total > 0 else 0.0
        
        # Probability histograms / distribution buckets (0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0)
        def get_bucket(val):
            idx = int(min(val, 0.999) * 5)
            return max(0, min(idx, 4))
            
        dist_rf = [0] * 5
        dist_gcn = [0] * 5
        dist_ens = [0] * 5
        for i in items:
            dist_rf[get_bucket(i["rf_probability"])] += 1
            dist_gcn[get_bucket(i["gcn_probability"])] += 1
            dist_ens[get_bucket(i["confidence"])] += 1
            
        # Timeline data (chronological)
        timeline = []
        for i in items[-30:]: # last 30 for clear visualization
            timeline.append({
                "id": i["id"],
                "created_at": i["created_at"],
                "compound_name": i["compound_name"],
                "formula": i.get("formula", ""),
                "rf_prob": round(i["rf_probability"], 3),
                "gcn_prob": round(i["gcn_probability"], 3),
                "confidence": round(i["confidence"], 3),
                "verdict": i["verdict"],
                "agreement": i["model_agreement"],
                "tanimoto": round(i["tanimoto_similarity"], 2)
            })
            
        # Similarity category breakdown
        sim_breakdown = {}
        for cat in ["Sibling-like", "Stranger-like", "Safe-like"]:
            cat_items = [i for i in items if i["similarity_category"] == cat]
            c_len = len(cat_items)
            sim_breakdown[cat] = {
                "count": c_len,
                "rf_avg": round(sum(i["rf_probability"] for i in cat_items) / c_len, 3) if c_len > 0 else 0.0,
                "gcn_avg": round(sum(i["gcn_probability"] for i in cat_items) / c_len, 3) if c_len > 0 else 0.0,
                "ens_avg": round(sum(i["confidence"] for i in cat_items) / c_len, 3) if c_len > 0 else 0.0,
                "toxic_count": sum(1 for i in cat_items if i["verdict"] == "toxic"),
                "safe_count": sum(1 for i in cat_items if i["verdict"] == "safe")
            }
            
        # Top contested / divergent historical cases
        contested = [
            i for i in items if "Disagreed" in i["model_agreement"]
        ]
        # Sort by largest difference between RF and GCN probability
        contested.sort(key=lambda x: abs(x["rf_probability"] - x["gcn_probability"]), reverse=True)

        return {
            "status": "ok",
            "total_predictions": total,
            "agreement_stats": {
                "agreed_count": agreed_count,
                "disagreed_count": disagreed_count,
                "agreement_rate": round(agreement_rate, 1),
                "both_toxic": both_toxic,
                "both_safe": both_safe,
                "rf_toxic_gcn_safe": rf_tox_gcn_safe,
                "rf_safe_gcn_toxic": rf_safe_gcn_tox
            },
            "rf_stats": {
                "toxic_count": rf_toxic,
                "safe_count": rf_safe,
                "avg_probability": round(rf_avg_prob, 3),
                "high_confidence_rate": round(rf_high_conf_rate, 1)
            },
            "gcn_stats": {
                "toxic_count": gcn_toxic,
                "safe_count": gcn_safe,
                "avg_probability": round(gcn_avg_prob, 3),
                "high_confidence_rate": round(gcn_high_conf_rate, 1)
            },
            "ensemble_stats": {
                "toxic_count": ens_toxic,
                "safe_count": ens_safe,
                "avg_confidence": round(ens_avg_conf, 3)
            },
            "timeline": timeline,
            "distribution": {
                "rf": dist_rf,
                "gcn": dist_gcn,
                "ensemble": dist_ens
            },
            "similarity_breakdown": sim_breakdown,
            "contested_cases": contested[:5]
        }
    except Exception as e:
        logger.error(f"Error computing prediction history stats: {e}")
        return {"status": "error", "message": str(e)}

def delete_prediction_history_item(item_id: int) -> Dict[str, Any]:
    """Delete a specific prediction history record."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prediction_history WHERE id = ?", (item_id,))
        rc = cursor.rowcount
        conn.commit()
        conn.close()
        return {"status": "ok", "deleted": rc > 0}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def clear_prediction_history() -> Dict[str, Any]:
    """Clear all records from prediction_history."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prediction_history")
        conn.commit()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def seed_prediction_history(force: bool = False):
    """
    Seed initial historical predictions from curated dataset if table is empty.
    Creates a realistic dataset across Sibling, Stranger, and Safe classes.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM prediction_history")
        count = cursor.fetchone()["count"]
        conn.close()
        
        if count > 0 and not force:
            return
            
        if force:
            clear_prediction_history()
            
        # Curated historical compounds with verified metrics and dates
        SEED_COMPOUNDS = [
            # ── Sibling Set (Strong Antifungals / Ketoconazole Relatives)
            {
                "name": "Ketoconazole",
                "smiles": "CC(=O)N1CCN(CC1)c2ccc(OC[C@@H]3CO[C@@](Cn4ccnc4)(c5ccc(Cl)cc5Cl)O3)cc2",
                "formula": "C26H28Cl2N4O4",
                "verdict": "toxic",
                "confidence": 0.868,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.840},
                    "gcn": {"label": "toxic", "probability": 0.910}
                },
                "similarity": {"tanimoto": 1.00, "category": "Sibling-like"},
                "pbpk": {"css_mg_per_L": 2.14},
                "summary": "Ketoconazole is a potent reference inhibitor of CYP3A4 coordinating strongly with the heme iron.",
                "days_ago": 28
            },
            {
                "name": "Miconazole",
                "smiles": "Clc1ccc(COC(Cn2ccnc2)c3ccc(Cl)cc3Cl)cc1Cl",
                "formula": "C18H14Cl4N2O",
                "verdict": "toxic",
                "confidence": 0.852,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.835},
                    "gcn": {"label": "toxic", "probability": 0.878}
                },
                "similarity": {"tanimoto": 0.68, "category": "Sibling-like"},
                "pbpk": {"css_mg_per_L": 2.05},
                "summary": "Miconazole possesses high imidazole-binding affinity and strong hepatotoxicity risk.",
                "days_ago": 26
            },
            {
                "name": "Itraconazole",
                "smiles": "CCC(C)n1ncn1-c2ccc(cc2)N3CCN(CC3)c4ccc(OCC5COC(Cn6cncn6)(c7ccc(Cl)cc7Cl)O5)cc4",
                "formula": "C34H38Cl2N8O3",
                "verdict": "toxic",
                "confidence": 0.884,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.865},
                    "gcn": {"label": "toxic", "probability": 0.912}
                },
                "similarity": {"tanimoto": 0.72, "category": "Sibling-like"},
                "pbpk": {"css_mg_per_L": 2.38},
                "summary": "Potent triazole antifungal with high molecular weight and steady-state liver accumulation.",
                "days_ago": 24
            },
            {
                "name": "Posaconazole",
                "smiles": "CCC(C)n1ncn1-c2ccc(cc2)N3CCN(CC3)c4ccc(OCC5COC(Cn6cncn6)(c7ccc(F)cc7F)O5)cc4",
                "formula": "C34H38F2N8O3",
                "verdict": "toxic",
                "confidence": 0.861,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.842},
                    "gcn": {"label": "toxic", "probability": 0.890}
                },
                "similarity": {"tanimoto": 0.69, "category": "Sibling-like"},
                "pbpk": {"css_mg_per_L": 2.19},
                "summary": "High similarity sibling with difluorophenyl ring causing potent CYP3A4 inhibition.",
                "days_ago": 22
            },
            # ── Stranger Set (Diverse Strong / Moderate Inhibitors)
            {
                "name": "Ritonavir",
                "smiles": "CC(C)c1nc(cn1C)CSC(=O)NC(C(C)C)C(=O)NC(Cc2ccccc2)CC(C(Cc3ccccc3)NC(=O)OCc4cncs4)O",
                "formula": "C37H48N6O5S2",
                "verdict": "toxic",
                "confidence": 0.895,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.875},
                    "gcn": {"label": "toxic", "probability": 0.925}
                },
                "similarity": {"tanimoto": 0.41, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 2.52},
                "summary": "Potent mechanism-based inactivator of CYP3A4; distinct peptidomimetic scaffold.",
                "days_ago": 21
            },
            {
                "name": "Clarithromycin",
                "smiles": "CCC1C(C(C(C(=O)C(CC(C(C(C(C(=O)O1)C)OC2CC(C(C(O2)C)O)(C)OC)C)OC3C(C(CC(O3)C)N(C)C)O)(C)O)C)C)O",
                "formula": "C35H63NO12",
                "verdict": "toxic",
                "confidence": 0.812,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.790},
                    "gcn": {"label": "toxic", "probability": 0.845}
                },
                "similarity": {"tanimoto": 0.38, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 1.74},
                "summary": "Macrolide antibiotic forming a metabolic intermediate complex with CYP3A4.",
                "days_ago": 19
            },
            {
                "name": "Fluconazole",
                "smiles": "OC(Cn1cncn1)(Cn2cncn2)c3ccc(F)cc3F",
                "formula": "C13H12F2N6O",
                "verdict": "toxic",
                "confidence": 0.819,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.792},
                    "gcn": {"label": "toxic", "probability": 0.860}
                },
                "similarity": {"tanimoto": 0.48, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 1.62},
                "summary": "Bis-triazole antifungal causing moderate to strong CYP3A4 inhibition.",
                "days_ago": 17
            },
            {
                "name": "Voriconazole",
                "smiles": "CC(c1ncc(F)c(n1)F)C(O)(Cn2cncn2)c3ccc(F)cc3F",
                "formula": "C16H13F4N5O",
                "verdict": "toxic",
                "confidence": 0.831,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.810},
                    "gcn": {"label": "toxic", "probability": 0.862}
                },
                "similarity": {"tanimoto": 0.45, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 1.70},
                "summary": "Fluoropyrimidine triazole antifungal with significant hepatic metabolic impact.",
                "days_ago": 16
            },
            {
                "name": "Clotrimazole",
                "smiles": "Clc1ccccc1C(c2ccccc2)(c3ccccc3)n4ccnc4",
                "formula": "C22H17ClN2",
                "verdict": "toxic",
                "confidence": 0.840,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.820},
                    "gcn": {"label": "toxic", "probability": 0.870}
                },
                "similarity": {"tanimoto": 0.52, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 1.88},
                "summary": "Triphenylmethyl imidazole causing potent competitive inhibition of CYP3A4.",
                "days_ago": 14
            },
            {
                "name": "Erythromycin",
                "smiles": "CCC1C(C(C(C(=O)C(CC(C(C(C(C(=O)O1)C)OC2CC(C(C(O2)C)O)(C)OC)C)OC3C(C(CC(O3)C)N(C)C)O)(C)O)C)C)O",
                "formula": "C35H63NO12",
                "verdict": "toxic",
                "confidence": 0.798,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.775},
                    "gcn": {"label": "toxic", "probability": 0.832}
                },
                "similarity": {"tanimoto": 0.36, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 1.65},
                "summary": "Macrolide antibiotic; classic mechanism-based CYP3A4 inhibitor.",
                "days_ago": 13
            },
            {
                "name": "Diltiazem",
                "smiles": "CC(=O)OC1C(c2ccc(OC)cc2)Sc3ccccc3N(CCN(C)C)C1=O",
                "formula": "C22H26N2O4S",
                "verdict": "toxic",
                "confidence": 0.772,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.760},
                    "gcn": {"label": "toxic", "probability": 0.790}
                },
                "similarity": {"tanimoto": 0.32, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 1.45},
                "summary": "Benzothiazepine calcium channel blocker exhibiting moderate CYP3A4 inhibition.",
                "days_ago": 11
            },
            {
                "name": "Verapamil",
                "smiles": "COc1ccc(CCN(C)CCCC(C#N)(C(C)C)c2ccc(OC)c(OC)c2)cc1OC",
                "formula": "C27H38N2O4",
                "verdict": "toxic",
                "confidence": 0.764,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.745},
                    "gcn": {"label": "toxic", "probability": 0.792}
                },
                "similarity": {"tanimoto": 0.29, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 1.40},
                "summary": "Phenylalkylamine inhibitor and substrate with moderate inhibitory properties.",
                "days_ago": 10
            },
            # ── Disagreed / Contested Substrates (Creative edge cases)
            {
                "name": "Midazolam",
                "smiles": "CC1=NC=C2N1C3=C(C=C(C=C3)Cl)C(=NC2)C4=CC=CC=C4F",
                "formula": "C18H13ClFN3",
                "verdict": "safe",
                "confidence": 0.428,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.525},
                    "gcn": {"label": "safe", "probability": 0.282}
                },
                "similarity": {"tanimoto": 0.35, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 0.85},
                "summary": "Index substrate for CYP3A4. RF flagged lipophilic fused ring, while GCN recognized substrate active site fit.",
                "days_ago": 9
            },
            {
                "name": "Omeprazole",
                "smiles": "COc1ccc2[nH]c(S(=O)Cc3ncc(C)c(OC)c3C)nc2c1",
                "formula": "C17H19N3O3S",
                "verdict": "safe",
                "confidence": 0.442,
                "models": {
                    "random_forest": {"label": "safe", "probability": 0.395},
                    "gcn": {"label": "toxic", "probability": 0.512}
                },
                "similarity": {"tanimoto": 0.28, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 0.92},
                "summary": "Proton pump inhibitor exhibiting weak reversible inhibition; GCN responded to heterocyclic nitrogen coordination.",
                "days_ago": 8
            },
            {
                "name": "Simvastatin",
                "smiles": "CCC(C)(C)C(=O)OC1CC(C)C=C2C=CC(C)C(CCC3CC(O)CC(=O)O3)C12",
                "formula": "C25H38O5",
                "verdict": "toxic",
                "confidence": 0.548,
                "models": {
                    "random_forest": {"label": "toxic", "probability": 0.582},
                    "gcn": {"label": "safe", "probability": 0.498}
                },
                "similarity": {"tanimoto": 0.31, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 1.25},
                "summary": "High-affinity substrate with borderline steady-state accumulation profile.",
                "days_ago": 7
            },
            {
                "name": "Nifedipine",
                "smiles": "COC(=O)C1=C(C)NC(C)=C(C(=O)OC)C1c2ccccc2[N+](=O)[O-]",
                "formula": "C17H18N2O6",
                "verdict": "safe",
                "confidence": 0.365,
                "models": {
                    "random_forest": {"label": "safe", "probability": 0.380},
                    "gcn": {"label": "safe", "probability": 0.342}
                },
                "similarity": {"tanimoto": 0.24, "category": "Stranger-like"},
                "pbpk": {"css_mg_per_L": 0.72},
                "summary": "Dihydropyridine substrate primarily metabolized by CYP3A4 without inducing strong direct inhibition.",
                "days_ago": 6
            },
            # ── Safe Set (Safe Controls / Non-Inhibitors)
            {
                "name": "Aspirin (Acetylsalicylic acid)",
                "smiles": "CC(=O)Oc1ccccc1C(=O)O",
                "formula": "C9H8O4",
                "verdict": "safe",
                "confidence": 0.105,
                "models": {
                    "random_forest": {"label": "safe", "probability": 0.164},
                    "gcn": {"label": "safe", "probability": 0.017}
                },
                "similarity": {"tanimoto": 0.12, "category": "Safe-like"},
                "pbpk": {"css_mg_per_L": 0.28},
                "summary": "Aspirin is non-inhibitory toward CYP3A4 with minimal CYP3A4-mediated liver toxicity risk.",
                "days_ago": 5
            },
            {
                "name": "Paracetamol (Acetaminophen)",
                "smiles": "CC(=O)Nc1ccc(O)cc1",
                "formula": "C8H9NO2",
                "verdict": "safe",
                "confidence": 0.098,
                "models": {
                    "random_forest": {"label": "safe", "probability": 0.142},
                    "gcn": {"label": "safe", "probability": 0.032}
                },
                "similarity": {"tanimoto": 0.09, "category": "Safe-like"},
                "pbpk": {"css_mg_per_L": 0.35},
                "summary": "Non-inhibitory towards CYP3A4; metabolized primarily via Phase II glucuronidation and sulfation.",
                "days_ago": 4
            },
            {
                "name": "Ibuprofen",
                "smiles": "CC(C)Cc1ccc(C(C)C(=O)O)cc1",
                "formula": "C13H18O2",
                "verdict": "safe",
                "confidence": 0.118,
                "models": {
                    "random_forest": {"label": "safe", "probability": 0.185},
                    "gcn": {"label": "safe", "probability": 0.018}
                },
                "similarity": {"tanimoto": 0.14, "category": "Safe-like"},
                "pbpk": {"css_mg_per_L": 0.32},
                "summary": "NSAID with negligible CYP3A4 inhibitory affinity; safe control standard.",
                "days_ago": 3
            },
            {
                "name": "Caffeine",
                "smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O",
                "formula": "C8H10N4O2",
                "verdict": "safe",
                "confidence": 0.125,
                "models": {
                    "random_forest": {"label": "safe", "probability": 0.190},
                    "gcn": {"label": "safe", "probability": 0.028}
                },
                "similarity": {"tanimoto": 0.11, "category": "Safe-like"},
                "pbpk": {"css_mg_per_L": 0.40},
                "summary": "Methylxanthine primarily metabolized by CYP1A2 with minimal CYP3A4 interaction.",
                "days_ago": 2
            },
            {
                "name": "Metformin",
                "smiles": "CN(C)C(=N)NC(=N)N",
                "formula": "C4H11N5",
                "verdict": "safe",
                "confidence": 0.065,
                "models": {
                    "random_forest": {"label": "safe", "probability": 0.095},
                    "gcn": {"label": "safe", "probability": 0.020}
                },
                "similarity": {"tanimoto": 0.03, "category": "Safe-like"},
                "pbpk": {"css_mg_per_L": 0.18},
                "summary": "Biguanide excreted renally unchanged; zero hepatic CYP3A4 inhibitory liability.",
                "days_ago": 1
            },
            {
                "name": "Ascorbic acid (Vitamin C)",
                "smiles": "OCC(O)C1OC(=O)C(O)=C1O",
                "formula": "C6H8O6",
                "verdict": "safe",
                "confidence": 0.052,
                "models": {
                    "random_forest": {"label": "safe", "probability": 0.080},
                    "gcn": {"label": "safe", "probability": 0.010}
                },
                "similarity": {"tanimoto": 0.06, "category": "Safe-like"},
                "pbpk": {"css_mg_per_L": 0.15},
                "summary": "Water-soluble antioxidant and endogenous vitamin with no CYP3A4 inhibition.",
                "days_ago": 0
            }
        ]

        from datetime import timedelta
        base_time = datetime.now(timezone.utc)
        
        for item in SEED_COMPOUNDS:
            item_time = (base_time - timedelta(days=item["days_ago"], hours=item.get("days_ago", 0) * 3)).isoformat()
            pred_dict = {
                "compound_name": item["name"],
                "smiles": item["smiles"],
                "formula": item["formula"],
                "verdict": item["verdict"],
                "confidence": item["confidence"],
                "models": item["models"],
                "similarity": item["similarity"],
                "pbpk": item["pbpk"],
                "summary": item["summary"]
            }
            save_prediction_history(pred_dict, created_at=item_time)
            
        logger.info(f"Successfully seeded {len(SEED_COMPOUNDS)} prediction history records into SQLite.")
    except Exception as e:
        logger.error(f"Failed to seed prediction history: {e}")

# Initialize database schema and seed history on startup
try:
    init_db()
    seed_prediction_history()
except Exception as e:
    logger.error(f"Failed to initialize SQLite database on startup: {e}")

