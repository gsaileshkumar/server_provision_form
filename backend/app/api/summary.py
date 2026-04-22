from __future__ import annotations

from flask import Blueprint, jsonify

from app.services import records_repo
from app.services.pricing import default_engine

bp = Blueprint("summary", __name__, url_prefix="/api/records")


@bp.get("/<record_id>/summary")
def summary(record_id: str):
    try:
        record = records_repo.get_record(record_id)
    except records_repo.InvalidRecordId:
        return jsonify({"error": "invalid_id"}), 400
    except records_repo.RecordNotFound:
        return jsonify({"error": "not_found"}), 404

    pricing = record.pricing or default_engine().compute(record)
    payload = record.model_dump(by_alias=True, mode="json")
    payload["pricing"] = pricing.model_dump(mode="json")
    return jsonify(payload)
