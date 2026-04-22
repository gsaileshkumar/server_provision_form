from __future__ import annotations

from app.graph.state import AgentState
from app.tools.form_api import FormApi


def intake(state: AgentState) -> dict:
    """Load an existing record or create a fresh draft, depending on what
    the caller put into state. Sets ``mode`` from ``stage``."""
    stage = state.get("stage", "estimate")
    mode = "B" if stage == "provisioning" else "A"

    updates: dict = {"mode": mode}

    record_id = state.get("record_id")
    if record_id:
        # Already have an id; nothing to create.
        return updates

    record_name = state.get("record_name") or f"Agent-driven {stage}"
    with FormApi() as api:
        created = api.create_record(
            record_name=record_name,
            stage=stage,
            agent_context={"mode": mode},
        )
    updates["record_id"] = created["_id"]
    updates["record_name"] = created["recordName"]
    return updates
