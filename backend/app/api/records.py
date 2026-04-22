from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from pydantic import ValidationError

from app.models import RecordCreate, RecordPatch, Stage, Status
from app.services import records_repo

bp = Blueprint("records", __name__, url_prefix="/api/records")


def _record_json(record) -> dict:
    return record.model_dump(by_alias=True, mode="json")


def _parse_enum_param(value: str | None, enum_cls):
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        abort(400, description=f"Invalid {enum_cls.__name__}: {value}")


@bp.get("")
def list_records():
    stage = _parse_enum_param(request.args.get("stage"), Stage)
    status = _parse_enum_param(request.args.get("status"), Status)
    records = records_repo.list_records(stage=stage, status=status)
    return jsonify([_record_json(r) for r in records])


@bp.post("")
def create_record():
    try:
        payload = RecordCreate.model_validate(request.get_json(force=True, silent=False))
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400

    record = records_repo.create_record(payload)
    return jsonify(_record_json(record)), 201


@bp.get("/<record_id>")
def get_record(record_id: str):
    try:
        record = records_repo.get_record(record_id)
    except records_repo.InvalidRecordId:
        return jsonify({"error": "invalid_id"}), 400
    except records_repo.RecordNotFound:
        return jsonify({"error": "not_found"}), 404
    return jsonify(_record_json(record))


@bp.patch("/<record_id>")
def patch_record(record_id: str):
    try:
        patch = RecordPatch.model_validate(request.get_json(force=True, silent=False))
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400

    try:
        record = records_repo.patch_record(record_id, patch)
    except records_repo.InvalidRecordId:
        return jsonify({"error": "invalid_id"}), 400
    except records_repo.RecordNotFound:
        return jsonify({"error": "not_found"}), 404
    except records_repo.RecordLocked:
        return jsonify({"error": "locked"}), 400

    return jsonify(_record_json(record))
