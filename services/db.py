"""
services/db.py — KeTox MongoDB Database Connection & Helper Layer

Provides:
- MongoDB connection pool initialization via PyMongo with graceful offline/fallback handling.
- Users collection helpers: find_user_by_email, create_user, verify_user_credentials, update_user_password.
- Safe password hashing and verification using Werkzeug Security.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import certifi
from pymongo.errors import PyMongoError, ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger("ketox.db")

_client: Optional[MongoClient] = None
_db = None


def get_mongo_client(app=None) -> Optional[MongoClient]:
    """Return the global MongoClient instance or initialize it."""
    global _client, _db
    if _client is not None:
        return _client

    from flask import current_app
    app_instance = app or (current_app._get_current_object() if current_app else None)

    if app_instance is None:
        # Standalone usage
        from config import get_config
        cfg = get_config()
        uri = cfg.MONGO_URI
        db_name = cfg.MONGO_DB_NAME
    else:
        uri = app_instance.config.get("MONGO_URI", "mongodb://127.0.0.1:27017/ketox")
        db_name = app_instance.config.get("MONGO_DB_NAME", "ketox")

    try:
        # 5 second timeout for quick failover/diagnostics with Windows certifi CA
        _client = MongoClient(
            uri,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
            connect=False
        )
        _db = _client[db_name]
        logger.info(f"MongoDB client initialized for database '{db_name}'")
        return _client
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB client: {e}")
        return None


def get_db(app=None):
    """Return the active MongoDB database object."""
    global _db
    if _db is None:
        get_mongo_client(app)
    return _db


def check_db_connection() -> Dict[str, Any]:
    """Test ping against the MongoDB server to verify live connectivity."""
    client = get_mongo_client()
    if client is None:
        return {"connected": False, "error": "MongoClient not initialized"}
    try:
        client.admin.command("ping")
        return {"connected": True, "error": None}
    except Exception as e:
        return {"connected": False, "error": str(e)}


# ─── User Model & Operations ──────────────────────────────────────────────────

def get_users_collection():
    """Return the users collection, ensuring indexes are built."""
    db = get_db()
    if db is None:
        return None
    users = db["users"]
    try:
        users.create_index("email", unique=True)
    except Exception as e:
        logger.warning(f"Could not ensure unique index on users.email: {e}")
    return users


def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Find a single user document by normalized email address."""
    try:
        users = get_users_collection()
        if users is None:
            return None
        norm_email = email.strip().lower()
        return users.find_one({"email": norm_email})
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
    Create and persist a new user document in MongoDB.
    Returns dict with status, user record or error message.
    """
    norm_email = email.strip().lower()

    try:
        users = get_users_collection()
        if users is None:
            return {"status": "error", "message": "Database is currently unavailable. Please verify your MongoDB connection string in .env."}

        if find_user_by_email(norm_email):
            return {"status": "error", "message": "An account with this email address already exists."}

        password_hash = generate_password_hash(password)
        now = datetime.now(timezone.utc)

        user_doc = {
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "full_name": f"{first_name.strip()} {last_name.strip()}",
            "email": norm_email,
            "password_hash": password_hash,
            "role": role,
            "other_role": other_role.strip() if role == "Others" else "",
            "created_at": now,
            "updated_at": now,
        }

        result = users.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)
        user_doc.pop("password_hash", None)
        return {"status": "ok", "user": user_doc}
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        logger.error(f"MongoDB connection failure: {e}")
        return {
            "status": "error",
            "message": "Cannot connect to MongoDB. Please make sure your MongoDB Atlas URI is set in .env or local MongoDB is running."
        }
    except PyMongoError as e:
        logger.error(f"Error inserting user: {e}")
        return {"status": "error", "message": f"Database error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error creating user: {e}")
        return {"status": "error", "message": "An unexpected error occurred while connecting to the database."}


def verify_user_credentials(email: str, password: str) -> Dict[str, Any]:
    """
    Validate user email and password against MongoDB.
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
            "id": str(user.get("_id")),
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "full_name": user.get("full_name", f"{user.get('first_name', '')} {user.get('last_name', '')}"),
            "email": user.get("email", ""),
            "role": user.get("role", "Student"),
        }
        return {"status": "ok", "user": safe_user}
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        logger.error(f"MongoDB connection failure during signin: {e}")
        return {
            "status": "error",
            "message": "Cannot connect to MongoDB. Please check your database connection in .env."
        }
    except Exception as e:
        logger.error(f"Unexpected error during signin: {e}")
        return {"status": "error", "message": "Database error while verifying credentials."}


def update_user_password(email: str, new_password: str) -> Dict[str, Any]:
    """Update password for an existing user."""
    try:
        users = get_users_collection()
        if users is None:
            return {"status": "error", "message": "Database is unavailable."}

        norm_email = email.strip().lower()
        pw_hash = generate_password_hash(new_password)
        now = datetime.now(timezone.utc)

        result = users.update_one(
            {"email": norm_email},
            {"$set": {"password_hash": pw_hash, "updated_at": now}}
        )

        if result.matched_count == 0:
            return {"status": "error", "message": "User not found."}

        return {"status": "ok", "message": "Password updated successfully."}
    except Exception as e:
        logger.error(f"Error updating password: {e}")
        return {"status": "error", "message": "Database error while updating password."}
