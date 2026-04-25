from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.graph.state import AgentState, Question, QuestionBatch
from app.tools.form_api import FormApi, FormApiError

_BOOL_TRUE = {"yes", "y", "true", "t", "1"}
_BOOL_FALSE = {"no", "n", "false", "f", "0"}

_BATCH_ANSWER_SENTINEL = "__BATCH_ANSWER__"


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


def _parse_batch_answer(text: str) -> dict | None:
    """Parse the `__BATCH_ANSWER__{...}` payload that the frontend sends when
    a user submits a batched question form. Returns the decoded dict, or
    None if the message doesn't look like a batch submission."""
    if not text:
        return None
    stripped = text.lstrip()
    if not stripped.startswith(_BATCH_ANSWER_SENTINEL):
        return None
    body = stripped[len(_BATCH_ANSWER_SENTINEL):].strip()
    try:
        data = json.loads(body)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _coerce_batch_value(value: Any, question: Question) -> tuple[Any, str | None]:
    """Validate + normalize a single form answer against its Question spec.

    Returns (value, error). When error is non-None, value should be ignored.
    """
    kind = question.get("kind", "text")
    options = question.get("options") or []
    required = question.get("required", True)

    if value is None or value == "":
        if required:
            return None, "This field is required."
        return None, None

    if kind == "multi-select":
        if not isinstance(value, list) or not value:
            return None, "Select at least one option."
        invalid = [v for v in value if v not in options]
        if invalid:
            return None, f"Not valid options: {', '.join(map(str, invalid))}."
        return value, None

    if kind == "select":
        if options and value not in options:
            return None, f"Must be one of: {', '.join(options)}."
        return value, None

    if kind == "number":
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None, "Must be a number."
        return (int(num) if num.is_integer() else num), None

    if kind == "boolean":
        if isinstance(value, bool):
            return value, None
        if isinstance(value, str):
            low = value.strip().lower()
            if low in _BOOL_TRUE:
                return True, None
            if low in _BOOL_FALSE:
                return False, None
        return None, "Must be yes or no."

    # kind == "text"
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None, "Please provide a value."
    return value, None


def _extract_batch(state: AgentState, batch: QuestionBatch, payload: dict) -> dict:
    """Handle a structured batch submission from the frontend form."""
    record_id = state.get("record_id")

    if payload.get("batch_id") != batch.get("batch_id"):
        # Stale submission from a previously rendered form — ignore silently.
        return {}

    answers = payload.get("answers") or {}
    if not isinstance(answers, dict):
        return {}

    questions_by_path = {q["path"]: q for q in batch.get("questions", [])}
    patch: dict = {}
    errors: dict[str, str] = {}
    accepted: dict[str, Any] = {}

    for path, raw in answers.items():
        question = questions_by_path.get(path)
        if question is None:
            # Unknown path — ignore rather than failing the whole batch.
            continue
        value, err = _coerce_batch_value(raw, question)
        if err:
            errors[path] = err
            continue
        if value is None:
            continue  # optional, empty
        accepted[path] = value
        _apply_to_patch(path, value, patch)

    # Check missing required fields.
    for q in batch.get("questions", []):
        if not q.get("required", True):
            continue
        if q["path"] not in accepted and q["path"] not in errors:
            errors[q["path"]] = "This field is required."

    if errors:
        updated_batch = dict(batch)
        updated_batch["errors"] = errors
        updated_batch["submitted"] = False
        return {
            "pending_batch": updated_batch,
            "messages": [
                AIMessage(content="Please fix the highlighted fields and submit again.")
            ],
        }

    # Merge into existing applications[0] so we don't clobber fields the user
    # already set in previous batches.
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
        rejected_batch = dict(batch)
        rejected_batch["errors"] = {"__global__": str(e)}
        return {
            "pending_batch": rejected_batch,
            "messages": [
                AIMessage(content=f"The server rejected that submission: {e}")
            ],
        }

    extracted = dict(state.get("extracted") or {})
    extracted.update(accepted)

    return {
        "pending_batch": None,
        "last_batch_id": batch.get("batch_id"),
        "pending_questions": [],
        "extracted": extracted,
    }


def extractor(state: AgentState) -> dict:
    text = _last_human_text(state.get("messages", []))

    # Mode-A batched form submission.
    batch = state.get("pending_batch")
    if batch and not batch.get("submitted"):
        payload = _parse_batch_answer(text or "")
        if payload is not None:
            return _extract_batch(state, batch, payload)
        # No batch payload but a batch is pending — the user typed plain text
        # which we can't map to multiple fields. Leave the batch in place.
        return {}

    # Legacy single-question path (Mode-B / tests).
    pending = state.get("pending_questions") or []
    if not pending:
        return {}
    question = pending[0]
    if text is None:
        return {}

    kind = question.get("kind", "text")
    options = question.get("options", [])

    value = _parse_value(text, kind, options)
    if value is None and os.environ.get("LLM_PROVIDER"):
        value = _llm_parse(text, question["path"], kind, options)

    if value is None:
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
