from __future__ import annotations

from langchain_core.messages import AIMessage

from app.graph.state import AgentState
from app.tools.form_api import FormApi


def validator(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {"done": True}

    with FormApi() as api:
        result = api.validate_record(record_id)

    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    if errors:
        lines = ["I ran validation and found some errors:"]
        for e in errors:
            lines.append(f"- {e['path']}: {e['message']}")
        return {
            "last_validation": result,
            "messages": [AIMessage(content="\n".join(lines))],
        }

    lines = ["Validation passed."]
    if warnings:
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"- {w['path']}: {w['message']}")
    return {
        "last_validation": result,
        "messages": [AIMessage(content="\n".join(lines))],
    }
