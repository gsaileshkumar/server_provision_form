from __future__ import annotations

import os

from langchain_core.messages import AIMessage

from app.graph.state import AgentState
from app.tools.form_api import FormApi


def _llm_validation_message(errors: list, warnings: list) -> str | None:
    """Ask the LLM to rewrite validation results in a friendly, helpful tone."""
    if not os.environ.get("LLM_PROVIDER"):
        return None
    if not errors and not warnings:
        return None
    try:
        from app.llm import get_llm
        llm = get_llm()
    except Exception:
        return None

    items = []
    if errors:
        items.append("Errors:\n" + "\n".join(f"- {e['path']}: {e['message']}" for e in errors))
    if warnings:
        items.append("Warnings:\n" + "\n".join(f"- {w['path']}: {w['message']}" for w in warnings))

    system = (
        "You are a server provisioning assistant reporting form validation results. "
        "Rewrite the errors and warnings in a friendly, helpful tone. "
        "For each error explain what it means in plain English and how the user can fix it. "
        "For warnings briefly note the concern. Be concise. "
        "Never output raw JSON or internal field path names — use plain English descriptions."
    )
    try:
        resp = llm.invoke([
            {"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(items)},
        ])
        content = resp.content if hasattr(resp, "content") else str(resp)
        return (content if isinstance(content, str) else str(content)).strip() or None
    except Exception:
        return None


def validator(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {"done": True}

    with FormApi() as api:
        result = api.validate_record(record_id)

    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    if errors:
        msg = _llm_validation_message(errors, warnings)
        if not msg:
            lines = ["I ran validation and found some errors:"]
            for e in errors:
                lines.append(f"- {e['path']}: {e['message']}")
            msg = "\n".join(lines)
        return {
            "last_validation": result,
            "messages": [AIMessage(content=msg)],
        }

    msg = _llm_validation_message([], warnings)
    if not msg:
        lines = ["Validation passed."]
        if warnings:
            lines.append("Warnings:")
            for w in warnings:
                lines.append(f"- {w['path']}: {w['message']}")
        msg = "\n".join(lines)

    return {
        "last_validation": result,
        "messages": [AIMessage(content=msg)],
    }
