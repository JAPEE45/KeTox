"""
routes/pages.py — KeTox page (HTML) routes

Registers: GET /   GET /home   GET /about (alias)   GET /performance   GET /login
"""

from flask import Blueprint, render_template, session, redirect, url_for

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/about")
def about():
    return render_template("index.html")


@pages_bp.route("/home")
def home():
    if not session.get("user_id"):
        return redirect(url_for("pages.login"))
    return render_template("home.html")


@pages_bp.route("/login")
def login():
    return render_template("login_signup.html")


@pages_bp.route("/performance")
def performance():
    return render_template("performance.html")
