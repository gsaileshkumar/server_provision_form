from __future__ import annotations

import os
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.graph.state import AgentState
from app.tools.form_api import FormApi, FormApiError

_BOOL_TRUE = {"yes", "y", "true", "t", "1"}
_BOOL_FALSE = {"no", "n", "false", "f", "0"}


def _last_human_text(messages: list) -> str | None:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
    return None


def _parse_value(text: str, kind: str, options: list[str]) -> Any:
    """Strict parser — returns None when the input does NOT unambiguously
    match the expected kind/options, so the LLM fallback in extractor() gets
    a chance to convert natural language to a concrete value."""
    cleaned = text.strip()
    if not cleaned:
        return None
    lower = cleaned.lower()

    # Options always win: exact or case-insensitive match.
    if options:
        for o in options:
            if lower == o.lower():
                return o
        return None  # options given, no match → let the LLM try

    if kind == "number":
        m = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        if m:
            val = float(m.group())
            return int(val) if val.is_integer() else val
        return None
    if kind == "boolean":
        if lower in _BOOL_TRUE:
            return True
        if lower in _BOOL_FALSE:
            return False
        return None
    # kind == "text" (or unknown): accept free text.
    return cleaned


def _llm_parse(text: str, path: str, kind: str, options: list[str]) -> Any:
    """LLM fallback when the heuristic parse fails. Returns a value that
    passes _parse_value with the same kind/options, or None."""
    try:
        from app.llm import get_llm

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
    try:
        resp = llm.invoke(
            [
                {"role": "system", "content": sys},
                {"role": "user", "content": text},
            ]
        )
    except Exception:
        return None
    content = resp.content if hasattr(resp, "content") else str(resp)
    content = (content if isinstance(content, str) else str(content)).strip()
    if not content or content.upper() == "NONE":
        return None
    # Re-run the strict parser on the LLM output so we never persist a value
    # that isn't in the allowed options / right shape.
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


def _clarify_message(question: dict) -> AIMessage:
    options = question.get("options") or []
    kind = question.get("kind", "text")
    if options:
        suffix = f"Please reply with one of: {', '.join(options)}."
    elif kind == "number":
        suffix = "Please reply with a number."
    elif kind == "boolean":
        suffix = "Please reply with yes or no."
    else:
        suffix = "Could you rephrase that?"
    return AIMessage(content=f"Sorry, I couldn't parse that. {suffix}")


def extractor(state: AgentState) -> dict:
    pending = state.get("pending_questions") or []
    if not pending:
        return {}
    question = pending[0]
    text = _last_human_text(state.get("messages", []))
    if text is None:
        return {}

    kind = question.get("kind", "text")
    options = question.get("options", [])

    value = _parse_value(text, kind, options)
    if value is None and os.environ.get("LLM_PROVIDER"):
        value = _llm_parse(text, question["path"], kind, options)

    if value is None:
        # Keep the question pending so the next user reply comes back here
        # instead of blowing past to question_planner.
        return {"messages": [_clarify_message(question)]}

    record_id = state.get("record_id")
    patch: dict = {}
    _apply_to_patch(question["path"], value, patch)
    if patch.get("applications"):
        with FormApi() as api:
            current = api.get_record(record_id)
        existing = list(current.get("applications") or [])
        if not existing:
            existing = [{}]
        existing[0].update(patch["applications"][0])
        patch["applications"] = existing

    try:
        with FormApi() as api:
            api.update_record(record_id, patch)
    except FormApiError as e:
        # Server-side validation rejected the parsed value. Keep the question
        # pending and surface the server's message instead of crashing the
        # graph.
        return {
            "messages": [
                AIMessage(
                    content=(
                        f"The server rejected '{value}' for {question['path']}. "
                        f"Please try again. (details: {e})"
                    )
                )
            ]
        }

    extracted = dict(state.get("extracted") or {})
    extracted[question["path"]] = value

    return {
        "pending_questions": [],
        "extracted": extracted,
    }
