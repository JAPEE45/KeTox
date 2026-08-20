"""
routes/pages.py — KeTox page (HTML) routes

Registers: GET /   GET /about   GET /performance
"""

from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/about")
def about():
    return render_template("about.html")


@pages_bp.route("/performance")
def performance():
    return render_template("performance.html")
