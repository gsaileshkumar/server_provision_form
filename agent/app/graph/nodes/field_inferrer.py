"""Silent field inference.

Runs after the extractor has parsed a use-case answer. Asks the LLM to map
``(use_case_answers, current_record, missing_field_paths)`` to a JSON patch
of record fields. The patch is applied via the Form API; nothing is added
to the chat transcript — the user only ever sees the next use-case question
or the final review.
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.graph.nodes.field_helper import REMAINING_FIELD_SCHEMA, missing_field_paths
from app.graph.state import AgentState
from app.tools.form_api import FormApi, FormApiError


def _coerce_value(path: str, value: Any) -> Any:
    """Light coercion using the schema. Returns None when a value can't be
    safely matched — we'd rather leave a field blank than write garbage."""
    if value is None:
        return None
    meta = REMAINING_FIELD_SCHEMA.get(path, {})
    kind = meta.get("kind", "text")
    options = meta.get("options")

    if kind == "select" and options:
        s = str(value).strip()
        for opt in options:
            if s.lower() == opt.lower():
                return opt
        return None
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in {"true", "yes", "y", "1"}:
            return True
        if s in {"false", "no", "n", "0"}:
            return False
        return None
    if kind == "number":
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
        return int(num) if num.is_integer() else num
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return value


def _apply_patch(path: str, value: Any, patch: dict) -> None:
    if path.startswith("applications[]"):
        sub = path.split(".", 1)[1]
        apps = patch.setdefault("applications", [])
        if not apps:
            apps.append({})
        apps[0][sub] = value
        return
    head, _, tail = path.partition(".")
    group = patch.setdefault(head, {})
    group[tail] = value


def _llm_infer(
    record: dict,
    use_case_answers: list[dict[str, Any]],
    candidate_paths: list[str],
) -> dict[str, Any] | None:
    """Ask the LLM for a JSON patch keyed by field path. Returns None when
    the LLM is unavailable or replies unparseably."""
    if not os.environ.get("LLM_PROVIDER") or not candidate_paths:
        return None
    try:
        from app.llm import get_llm

        llm = get_llm()
    except Exception:
        return None

    schema = {p: REMAINING_FIELD_SCHEMA.get(p, {}) for p in candidate_paths}
    system = (
        "You are silently filling a server provisioning record on behalf of "
        "the user, based on what they have told you about their use case. "
        "Decide values for as many of the candidate fields as you can justify "
        "from the use-case answers. If you do not have enough information to "
        "pick a defensible value for a field, OMIT it (do NOT guess). "
        "Return ONLY a JSON object whose keys are field paths from the "
        "candidate list and whose values match each field's schema. Do not "
        "wrap in markdown. Do not add commentary. For select fields, the "
        "value MUST be one of the listed options verbatim. For boolean "
        "fields, use true/false. For number fields, use a JSON number."
    )
    user_content = (
        f"Use-case answers gathered so far:\n"
        f"{json.dumps(use_case_answers, default=str, indent=2)}\n\n"
        f"Current record (partial):\n"
        f"{json.dumps(record, default=str)[:3000]}\n\n"
        f"Candidate fields and schemas:\n"
        f"{json.dumps(schema, indent=2)}"
    )
    try:
        resp = llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ]
        )
    except Exception:
        return None

    content = resp.content if hasattr(resp, "content") else str(resp)
    text = (content if isinstance(content, str) else str(content)).strip()
    # Strip optional markdown fence.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def field_inferrer(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {}

    with FormApi() as api:
        record = api.get_record(record_id)
        catalog = api.get_catalog(stage=record["stage"])

    required = catalog.get("stageRequiredFields", [])
    candidates = missing_field_paths(record, required)
    if not candidates:
        return {}

    use_case_answers = list(state.get("use_case_answers") or [])
    if not use_case_answers:
        return {}

    raw = _llm_infer(record, use_case_answers, candidates)
    if not raw:
        return {}

    patch: dict[str, Any] = {}
    for path, value in raw.items():
        if path not in candidates:
            continue
        coerced = _coerce_value(path, value)
        if coerced is None:
            continue
        _apply_patch(path, coerced, patch)

    if not patch:
        return {}

    if patch.get("applications"):
        existing = list(record.get("applications") or [])
        if not existing:
            existing = [{}]
        existing[0].update(patch["applications"][0])
        patch["applications"] = existing

    try:
        with FormApi() as api:
            api.update_record(record_id, patch)
    except FormApiError:
        # Don't fail the conversation on a Form API hiccup; leave the gap
        # for validator to surface.
        return {}

    return {}
