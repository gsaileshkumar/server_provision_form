"""Parse the user's A2UI action payload into a use-case answer.

When the user clicks the submit button on an a2ui surface, the frontend
posts a HumanMessage whose content is ``__A2UI_ACTION__{...}``. The JSON
carries the question_id (so we can match it to the pending question) and
the answer the user picked. We append it to ``use_case_answers`` and clear
``pending_use_case_question``; the field_inferrer then runs to silently
update the record.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage

from app.graph.state import AgentState

A2UI_ACTION_SENTINEL = "__A2UI_ACTION__"


def _last_human_text(messages: list) -> str | None:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
    return None


def _parse_action_payload(text: str) -> dict | None:
    if not text:
        return None
    stripped = text.lstrip()
    if not stripped.startswith(A2UI_ACTION_SENTINEL):
        return None
    body = stripped[len(A2UI_ACTION_SENTINEL):].strip()
    try:
        data = json.loads(body)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def extractor(state: AgentState) -> dict:
    text = _last_human_text(state.get("messages", []))
    pending = state.get("pending_use_case_question")
    if not pending:
        return {}

    payload = _parse_action_payload(text or "")
    if payload is None:
        # User typed free-form text instead of clicking the form. Leave the
        # pending question in place so the frontend keeps showing it.
        return {}

    if payload.get("question_id") != pending.get("question_id"):
        # Stale submission from a previously rendered surface — ignore.
        return {}

    answer: Any = payload.get("answer")

    history = list(state.get("use_case_answers") or [])
    history.append(
        {
            "question_id": pending.get("question_id"),
            "intent": pending.get("intent"),
            "answer": answer,
        }
    )

    return {
        "use_case_answers": history,
        "pending_use_case_question": None,
    }
