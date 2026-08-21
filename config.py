"""
config.py — KeTox Flask application configuration

Usage (in app.py):
    from config import get_config
    app.config.from_object(get_config())

Environment variables:
    FLASK_ENV    "development" (default) | "production"
    FLASK_DEBUG  "1" | "0"   (overrides the env default when set explicitly)
    SECRET_KEY   Random string — MUST be set in production via environment.

Development defaults are safe for local use only.
In production, set FLASK_ENV=production and provide a SECRET_KEY env var.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class _Base:
    """Shared settings for all environments."""
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-insecure-change-in-production")
    JSON_SORT_KEYS: bool = False

    # MongoDB configuration
    MONGO_URI: str = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017/ketox")
    MONGO_DB_NAME: str = os.environ.get("MONGO_DB_NAME", "ketox")


class Development(_Base):
    DEBUG: bool = True
    TESTING: bool = False


class Production(_Base):
    DEBUG: bool = False
    TESTING: bool = False


class Testing(_Base):
    DEBUG: bool = True
    TESTING: bool = True


_ENV_MAP = {
    "development": Development,
    "production":  Production,
    "testing":     Testing,
}


def get_config():
    """
    Return the config class matching the current FLASK_ENV.

    FLASK_DEBUG=1 will force debug mode regardless of FLASK_ENV.
    FLASK_DEBUG=0 will force it off regardless of FLASK_ENV.
    """
    env = os.environ.get("FLASK_ENV", "development").lower()
    cfg = _ENV_MAP.get(env, Development)

    # Allow explicit override via FLASK_DEBUG env var
    debug_override = os.environ.get("FLASK_DEBUG")
    if debug_override is not None:
        cfg.DEBUG = debug_override == "1"

    return cfg
