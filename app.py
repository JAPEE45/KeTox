"""
KeTox — app.py  (application entry point)

Routes live in:  routes/pages.py  (GET /, /about, /performance)
                 routes/api.py    (POST /predict, GET /api/performance)

Data lives in:   data/mock_compounds.py  (KNOWN_COMPOUNDS, COMPOUND_ALIASES,
                                          PERFORMANCE_METRICS)

ML inference:    services/predictor.py   (predict_compound stub — wire in when
                                          RDKit + trained models are ready)

Configuration:   config.py              (reads FLASK_ENV / FLASK_DEBUG / SECRET_KEY)
"""

import os
from flask import Flask

from config import get_config
from routes.pages import pages_bp
from routes.api   import api_bp
from routes.auth  import auth_bp

app = Flask(__name__)
app.config.from_object(get_config())

# Register blueprints
app.register_blueprint(pages_bp)
app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)


# ---------------------------------------------------------------------------
# Dev server — debug and port come from environment, never hardcoded.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port)
