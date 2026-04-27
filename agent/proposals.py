"""In-memory store for submitted server build proposals.

Process-lifetime only: closing the REPL drops every record. Exported
JSON files (written by the `export_proposal` tool) survive on disk.
"""

from __future__ import annotations

import uuid
from copy import deepcopy

_PROPOSALS: dict[str, dict] = {}


def save_proposal(config: dict) -> dict:
    """Store `config` as a new proposal with status='proposed' and return it."""
    pid = uuid.uuid4().hex
    record = {"id": pid, "status": "proposed", "configuration": deepcopy(config)}
    _PROPOSALS[pid] = record
    return deepcopy(record)


def get_proposal(proposal_id: str) -> dict | None:
    record = _PROPOSALS.get(proposal_id)
    return deepcopy(record) if record else None


def list_proposals() -> list[dict]:
    return [deepcopy(r) for r in _PROPOSALS.values()]
