from __future__ import annotations

import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient


def get_checkpointer():
    """Return a LangGraph checkpointer. Uses MongoDB in production and
    an in-memory saver when ``MONGO_MOCK=1`` (prototype mode)."""
    if os.environ.get("MONGO_MOCK") == "1":
        return MemorySaver()
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGO_DB", "server_provision")
    client = MongoClient(uri)
    return MongoDBSaver(client, db_name=db_name, collection_name="agent_checkpoints")
