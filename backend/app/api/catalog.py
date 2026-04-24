from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.models import Stage
from app.services.catalog_loader import load_catalog, load_compatibility
from app.services.stage_fields import required_fields_for

bp = Blueprint("catalog", __name__, url_prefix="/api/catalog")


@bp.get("/options")
def options():
    catalog = load_catalog()
    resp = catalog.model_dump()

    stage_param = request.args.get("stage")
    if stage_param is not None:
        try:
            stage = Stage(stage_param)
        except ValueError:
            return jsonify({"error": "invalid_stage"}), 400
        resp["stageRequiredFields"] = required_fields_for(stage)

    return jsonify(resp)


@bp.get("/compatibility")
def compatibility():
    return jsonify(load_compatibility().model_dump())
