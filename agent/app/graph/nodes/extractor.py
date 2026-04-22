from __future__ import annotations

import os
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.graph.state import AgentState
from app.tools.form_api import FormApi

_BOOL_TRUE = {"yes", "y", "true", "t", "1"}
_BOOL_FALSE = {"no", "n", "false", "f", "0"}


def _last_human_text(messages: list) -> str | None:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
    return None


def _parse_value(text: str, kind: str, options: list[str]) -> Any:
    cleaned = text.strip()
    lower = cleaned.lower()
    if options:
        for o in options:
            if lower == o.lower():
                return o
    if kind == "number":
        m = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        if m:
            val = float(m.group())
            return int(val) if val.is_integer() else val
    if kind == "boolean":
        if lower in _BOOL_TRUE:
            return True
        if lower in _BOOL_FALSE:
            return False
    return cleaned or None


def _llm_parse(text: str, path: str, kind: str, options: list[str]) -> Any:
    """LLM fallback when the heuristic parse fails. Only used if an LLM
    provider is configured."""
    try:
        from app.llm import get_llm
    except Exception:
        return None
    try:
        llm = get_llm()
    except Exception:
        return None

    opt_hint = (
        f"Pick exactly one of: {', '.join(options)}." if options else ""
    )
    sys = (
        f"Extract the value of the form field `{path}` (kind={kind}) from the "
        f"user's message. {opt_hint} Respond with JUST the value, no quotes, "
        f"no extra words. If you cannot determine a value, respond with NONE."
    )
    resp = llm.invoke([
        {"role": "system", "content": sys},
        {"role": "user", "content": text},
    ])
    content = resp.content if hasattr(resp, "content") else str(resp)
    content = (content if isinstance(content, str) else str(content)).strip()
    if content.upper() == "NONE" or not content:
        return None
    return _parse_value(content, kind, options)


def _apply_to_patch(path: str, value: Any, patch: dict) -> None:
    if path.startswith("applications[]"):
        # Upsert into the first application entry that has this field blank
        # (or append a new one). Kept deliberately simple for the scaffold.
        sub = path.split(".", 1)[1]
        apps = patch.setdefault("applications", [])
        if not apps:
            apps.append({})
        apps[0][sub] = value
        return
    head, _, tail = path.partition(".")
    group = patch.setdefault(head, {})
    group[tail] = value


def extractor(state: AgentState) -> dict:
    pending = state.get("pending_questions") or []
    if not pending:
        return {}
    question = pending[0]
    text = _last_human_text(state.get("messages", []))
    if text is None:
        return {}

    value = _parse_value(text, question.get("kind", "text"), question.get("options", []))
    if value is None and os.environ.get("LLM_PROVIDER"):
        value = _llm_parse(
            text, question["path"], question.get("kind", "text"), question.get("options", [])
        )
    if value is None:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "Sorry, I couldn't parse that. "
                        + (
                            f"Please reply with one of: {', '.join(question['options'])}."
                            if question.get("options")
                            else "Could you try rephrasing?"
                        )
                    )
                )
            ]
        }

    record_id = state.get("record_id")
    patch: dict = {}
    _apply_to_patch(question["path"], value, patch)
    if patch.get("applications"):
        # For applications[] we need to merge with existing array.
        with FormApi() as api:
            current = api.get_record(record_id)
        existing = list(current.get("applications") or [])
        if not existing:
            existing = [{}]
        existing[0].update(patch["applications"][0])
        patch["applications"] = existing

    with FormApi() as api:
        api.update_record(record_id, patch)

    extracted = dict(state.get("extracted") or {})
    extracted[question["path"]] = value

    return {
        "pending_questions": [],
        "extracted": extracted,
    }
