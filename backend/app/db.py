from __future__ import annotations

import os
from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from app.config import Config


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    if os.environ.get("MONGO_MOCK") == "1":
        # Prototype/demo mode: in-memory mongo via mongomock.
        # Never used in production code paths.
        import mongomock

        return mongomock.MongoClient()
    return MongoClient(Config.mongo_uri)


def get_db() -> Database:
    return get_client()[Config.mongo_db]


def records_collection():
    return get_db()["records"]


def agent_checkpoints_collection():
    return get_db()["agent_checkpoints"]


def ensure_indexes() -> None:
    records = records_collection()
    records.create_index(
        [("stage", ASCENDING), ("status", ASCENDING), ("updatedAt", DESCENDING)],
        name="stage_status_updatedAt",
    )
    records.create_index([("predecessorId", ASCENDING)], name="predecessorId")
