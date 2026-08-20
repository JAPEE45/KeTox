"""
KeTox — app.py  (application entry point)

Routes live in:  routes/pages.py  (GET /, /about, /performance)
                 routes/api.py    (POST /predict, GET /api/performance)

Data lives in:   data/mock_compounds.py  (KNOWN_COMPOUNDS, COMPOUND_ALIASES,
                                          PERFORMANCE_METRICS)

ML inference:    services/predictor.py   (predict_compound stub — wire in when
                                          RDKit + trained models are ready)
"""

from flask import Flask

from routes.pages import pages_bp
from routes.api   import api_bp

app = Flask(__name__)

# Register blueprints
app.register_blueprint(pages_bp)
app.register_blueprint(api_bp)


# ---------------------------------------------------------------------------
# Dev server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
