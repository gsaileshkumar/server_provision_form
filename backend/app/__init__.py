import os
from pathlib import Path

import requests
from flask import Flask, Response, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import NotFound

from app.api.catalog import bp as catalog_bp
from app.api.records import bp as records_bp
from app.api.summary import bp as summary_bp
from app.config import Config
from app.db import ensure_indexes


def create_app() -> Flask:
    static_dir = Path(__file__).parent / "static"
    # static_url_path="" mounts assets at the site root so /assets/foo.js,
    # /favicon.ico, etc. resolve without extra routing.
    app = Flask(
        __name__,
        static_folder=str(static_dir),
        static_url_path="",
    )
    CORS(app)

    ensure_indexes()

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "form-api"}

    app.register_blueprint(records_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(summary_bp)

    _register_agui_proxy(app)
    _register_spa(app)

    return app


def _register_spa(app: Flask) -> None:
    """Serve the built SPA: static assets at their real paths, everything else
    (unknown routes that aren't /api/*) falls through to index.html so React
    Router can handle client-side navigation."""

    index_path = Path(app.static_folder or "") / "index.html"

    @app.get("/")
    def _index():
        if not index_path.exists():
            return ("SPA build not present", 404)
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/<path:path>")
    def _spa_fallback(path: str):
        # Don't mask unknown API / proxy paths with an HTML shell — leave
        # 404s there so clients see real errors.
        if path.startswith(("api/", "agui", "health")):
            return ("Not Found", 404)
        try:
            return send_from_directory(app.static_folder, path)
        except NotFound:
            if not index_path.exists():
                return ("SPA build not present", 404)
            return send_from_directory(app.static_folder, "index.html")


def _register_agui_proxy(app: Flask) -> None:
    """Forward /agui/* to the Python agent's AG-UI endpoint. The React SDK
    talks AG-UI directly via @ag-ui/client's HttpAgent (configured through
    <CopilotKit selfManagedAgents>), so there is no Node bridge in between."""

    agent_url = os.environ.get(
        "AGENT_AGUI_URL", "http://localhost:5002/agui"
    ).rstrip("/")

    # Headers we must not forward verbatim — hop-by-hop per RFC 7230 plus
    # Flask-handled content framing.
    HOP_BY_HOP = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "content-length",
        "content-encoding",
        "host",
    }

    @app.route(
        "/agui",
        defaults={"subpath": ""},
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    @app.route(
        "/agui/<path:subpath>",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    def _agui_proxy(subpath: str):
        target = f"{agent_url}/{subpath}" if subpath else agent_url
        fwd_headers = {
            k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP
        }
        upstream = requests.request(
            method=request.method,
            url=target,
            params=request.args,
            data=request.get_data(),
            headers=fwd_headers,
            stream=True,
            allow_redirects=False,
            timeout=None,
        )
        resp_headers = [
            (k, v) for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP
        ]
        # stream=True + iter_content lets SSE / chunked streaming pass through.
        return Response(
            upstream.iter_content(chunk_size=8192),
            status=upstream.status_code,
            headers=resp_headers,
        )


__all__ = ["create_app", "Config"]
