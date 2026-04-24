from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId

from app.db import records_collection
from app.models import Record, RecordCreate, RecordPatch, Stage, Status


class RecordNotFound(Exception):
    pass


class InvalidRecordId(Exception):
    pass


class RecordLocked(Exception):
    pass


def _to_object_id(record_id: str) -> ObjectId:
    try:
        return ObjectId(record_id)
    except (InvalidId, TypeError) as e:
        raise InvalidRecordId(record_id) from e


def _doc_to_record(doc: dict[str, Any]) -> Record:
    copy = dict(doc)
    copy["_id"] = str(copy["_id"])
    if copy.get("predecessorId"):
        copy["predecessorId"] = str(copy["predecessorId"])
    return Record.model_validate(copy)


def _record_to_doc(record: Record, *, include_id: bool = False) -> dict[str, Any]:
    dumped = record.model_dump(by_alias=True, exclude_none=False)
    if not include_id:
        dumped.pop("_id", None)
    elif record.id:
        dumped["_id"] = ObjectId(record.id)
    if dumped.get("predecessorId"):
        dumped["predecessorId"] = ObjectId(dumped["predecessorId"])
    return dumped


def list_records(
    stage: Optional[Stage] = None, status: Optional[Status] = None
) -> list[Record]:
    query: dict[str, Any] = {}
    if stage is not None:
        query["stage"] = Stage(stage).value
    if status is not None:
        query["status"] = Status(status).value
    cursor = records_collection().find(query).sort("updatedAt", -1)
    return [_doc_to_record(d) for d in cursor]


def get_record(record_id: str) -> Record:
    oid = _to_object_id(record_id)
    doc = records_collection().find_one({"_id": oid})
    if doc is None:
        raise RecordNotFound(record_id)
    return _doc_to_record(doc)


def create_record(payload: RecordCreate) -> Record:
    now = datetime.now(timezone.utc)
    record = Record(
        recordName=payload.recordName,
        stage=payload.stage,
        status=Status.draft,
        hardware=payload.hardware or Record.model_fields["hardware"].default_factory(),
        softwareOS=payload.softwareOS or Record.model_fields["softwareOS"].default_factory(),
        applications=payload.applications or [],
        agentContext=payload.agentContext,
        createdAt=now,
        updatedAt=now,
    )
    doc = _record_to_doc(record, include_id=False)
    result = records_collection().insert_one(doc)
    record.id = str(result.inserted_id)
    return record


def _merge_nested(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for k, v in incoming.items():
        if v is not None:
            merged[k] = v
    return merged


def patch_record(record_id: str, patch: RecordPatch) -> Record:
    current = get_record(record_id)
    if current.status == Status.locked.value or current.status == Status.locked:
        raise RecordLocked(record_id)

    update: dict[str, Any] = {"updatedAt": datetime.now(timezone.utc)}
    if patch.recordName is not None:
        update["recordName"] = patch.recordName
    if patch.hardware is not None:
        update["hardware"] = _merge_nested(
            current.hardware.model_dump(), patch.hardware.model_dump(exclude_none=True)
        )
    if patch.softwareOS is not None:
        update["softwareOS"] = _merge_nested(
            current.softwareOS.model_dump(), patch.softwareOS.model_dump(exclude_none=True)
        )
    if patch.applications is not None:
        update["applications"] = [a.model_dump() for a in patch.applications]
    if patch.agentContext is not None:
        update["agentContext"] = _merge_nested(
            (current.agentContext.model_dump() if current.agentContext else {}),
            patch.agentContext.model_dump(exclude_none=True),
        )

    records_collection().update_one(
        {"_id": _to_object_id(record_id)}, {"$set": update}
    )
    return get_record(record_id)


def lock_record(record_id: str, pricing: dict[str, Any]) -> Record:
    records_collection().update_one(
        {"_id": _to_object_id(record_id)},
        {
            "$set": {
                "status": Status.locked.value,
                "pricing": pricing,
                "updatedAt": datetime.now(timezone.utc),
            }
        },
    )
    return get_record(record_id)


def insert_promoted(record: Record) -> Record:
    doc = _record_to_doc(record, include_id=False)
    result = records_collection().insert_one(doc)
    record.id = str(result.inserted_id)
    return record
