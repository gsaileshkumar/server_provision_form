from flask import Flask
from flask_cors import CORS

from app.config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "form-api"}

    # Blueprints are registered in later milestones:
    # from app.api.records import bp as records_bp; app.register_blueprint(records_bp)
    # from app.api.catalog import bp as catalog_bp; app.register_blueprint(catalog_bp)
    # from app.api.summary import bp as summary_bp; app.register_blueprint(summary_bp)

    return app


__all__ = ["create_app", "Config"]
