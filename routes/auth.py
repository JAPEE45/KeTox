"""
routes/auth.py — KeTox User Authentication API & Session Routes

Registers:
  POST /api/auth/signup         — register a new account in MongoDB
  POST /api/auth/signin         — authenticate credentials and set session
  POST /api/auth/logout         — clear active user session
  GET  /api/auth/me             — fetch profile of currently logged-in user
  POST /api/auth/reset-password — handle password reset request
  GET  /api/health/db           — test MongoDB connection status
"""

from flask import Blueprint, request, jsonify, session
from services.db import (
    create_user,
    verify_user_credentials,
    find_user_by_email,
    check_db_connection,
    update_user_password,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/health/db", methods=["GET"])
def health_db():
    """Diagnostic endpoint to check MongoDB connectivity."""
    status = check_db_connection()
    return jsonify(status), (200 if status["connected"] else 503)


@auth_bp.route("/api/auth/signup", methods=["POST"])
def signup():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}

    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or "Student"
    other_role = (data.get("other_role") or "").strip()

    if not first_name or not last_name:
        return jsonify({"status": "error", "message": "First and last name are required."}), 400

    if not email or "@" not in email:
        return jsonify({"status": "error", "message": "Please enter a valid email address."}), 400

    if len(password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters long."}), 400

    result = create_user(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        role=role,
        other_role=other_role,
    )

    if result["status"] == "ok":
        user = result["user"]
        # Set session
        session["user_id"] = user.get("_id") or user.get("id")
        session["user_email"] = user.get("email")
        session["user_name"] = user.get("full_name")
        return jsonify({
            "status": "ok",
            "message": "Account created successfully.",
            "user": user,
        }), 201

    return jsonify(result), 400


@auth_bp.route("/api/auth/signin", methods=["POST"])
def signin():
    """Authenticate user with email & password."""
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required."}), 400

    result = verify_user_credentials(email=email, password=password)

    if result["status"] == "ok":
        user = result["user"]
        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        session["user_name"] = user["full_name"]
        return jsonify({
            "status": "ok",
            "message": "Logged in successfully.",
            "user": user,
        }), 200

    return jsonify(result), 401


@auth_bp.route("/api/auth/logout", methods=["POST", "GET"])
def logout():
    """Clear the active user session."""
    session.clear()
    return jsonify({"status": "ok", "message": "Logged out successfully."}), 200


@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    """Return the profile info of the currently authenticated user."""
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"status": "unauthenticated", "user": None}), 200

    user = find_user_by_email(user_email)
    if not user:
        session.clear()
        return jsonify({"status": "unauthenticated", "user": None}), 200

    safe_user = {
        "id": str(user.get("_id")),
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "full_name": user.get("full_name", f"{user.get('first_name', '')} {user.get('last_name', '')}"),
        "email": user.get("email", ""),
        "role": user.get("role", "Student"),
    }
    return jsonify({"status": "ok", "user": safe_user}), 200


@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    """Handle password reset requests."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()

    if not email or "@" not in email:
        return jsonify({"status": "error", "message": "Please enter a valid email address."}), 400

    # Verify if user exists
    user = find_user_by_email(email)
    # Always return a polite success message to prevent user enumeration attacks
    return jsonify({
        "status": "ok",
        "message": "If an account exists with that email, a password reset link has been dispatched.",
    }), 200
