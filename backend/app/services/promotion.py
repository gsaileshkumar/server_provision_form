from __future__ import annotations

from datetime import datetime, timezone

from app.models import Record, Stage, Status
from app.models.enums import STAGE_ORDER
from app.services import records_repo


class PromotionError(Exception):
    pass


def next_stage(stage: Stage) -> Stage:
    idx = STAGE_ORDER.index(Stage(stage))
    if idx + 1 >= len(STAGE_ORDER):
        raise PromotionError(f"No stage after {stage}.")
    return STAGE_ORDER[idx + 1]


def promote(record: Record) -> Record:
    if record.status not in (Status.locked.value, Status.locked):
        raise PromotionError(
            "Predecessor must be locked (submitted) before it can be promoted."
        )
    target = next_stage(Stage(record.stage))
    now = datetime.now(timezone.utc)
    new = Record(
        recordName=f"{record.recordName} ({target.value})",
        stage=target,
        status=Status.draft,
        predecessorId=record.id,
        hardware=record.hardware,
        softwareOS=record.softwareOS,
        applications=list(record.applications),
        agentContext=None,
        pricing=None,
        createdAt=now,
        updatedAt=now,
    )
    return records_repo.insert_promoted(new)
