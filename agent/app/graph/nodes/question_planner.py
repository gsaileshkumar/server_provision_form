from __future__ import annotations

import json
import os
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from app.graph.state import AgentState, Question, QuestionBatch
from app.tools.form_api import FormApi


# Labels + structured options for the fields we know about. Fields without an
# entry here fall through to free-text prompts.
#
# ``depends_on`` lets the batched planner avoid asking for a field whose
# prerequisite is still blank (e.g. don't ask for osDistribution before
# osFamily is known).
FIELD_META: dict[str, dict[str, Any]] = {
    "hardware.workloadProfile": {
        "prompt": "What's the workload profile for this server?",
        "kind": "select",
        "options": ["web", "database", "app", "analytics", "general-purpose"],
        "section": "hardware",
    },
    "hardware.expectedConcurrentUsers": {
        "prompt": "Roughly how many concurrent users do you expect?",
        "kind": "number",
        "section": "hardware",
    },
    "hardware.cpuCores": {
        "prompt": "How many CPU cores?",
        "kind": "number",
        "section": "hardware",
    },
    "hardware.ramGb": {
        "prompt": "How much RAM (in GB)?",
        "kind": "number",
        "section": "hardware",
    },
    "hardware.primaryStorageGb": {
        "prompt": "How much primary storage (GB)?",
        "kind": "number",
        "section": "hardware",
    },
    "hardware.storageType": {
        "prompt": "Which storage type?",
        "kind": "select",
        "options": ["HDD", "SSD", "NVMe"],
        "section": "hardware",
    },
    "hardware.raidLevel": {
        "prompt": "Which RAID level?",
        "kind": "select",
        "options": ["none", "1", "5", "10"],
        "section": "hardware",
    },
    "hardware.gpuRequired": {
        "prompt": "Is a GPU required?",
        "kind": "boolean",
        "section": "hardware",
    },
    "hardware.networkBandwidthGbps": {
        "prompt": "Network bandwidth (Gbps)?",
        "kind": "select",
        "options": ["1", "10", "25", "40"],
        "section": "hardware",
    },
    "hardware.redundancy": {
        "prompt": "Which redundancy posture?",
        "kind": "select",
        "options": ["none", "active-passive", "active-active"],
        "section": "hardware",
    },
    "hardware.rackUnits": {
        "prompt": "How many rack units?",
        "kind": "number",
        "section": "hardware",
    },
    "hardware.powerDrawWatts": {
        "prompt": "Estimated power draw (watts)?",
        "kind": "number",
        "section": "hardware",
    },
    "softwareOS.osFamily": {
        "prompt": "Which OS family?",
        "kind": "select",
        "options": ["Linux", "Windows"],
        "section": "softwareOS",
    },
    "softwareOS.osDistribution": {
        "prompt": "Which distribution?",
        "kind": "text",
        "section": "softwareOS",
        "depends_on": "softwareOS.osFamily",
    },
    "softwareOS.osVersion": {
        "prompt": "Which version?",
        "kind": "text",
        "section": "softwareOS",
        "depends_on": "softwareOS.osDistribution",
    },
    "softwareOS.licensingModel": {
        "prompt": "OS licensing model?",
        "kind": "select",
        "options": ["BYOL", "included", "subscription"],
        "section": "softwareOS",
    },
    "softwareOS.patchingPolicy": {
        "prompt": "Patching policy?",
        "kind": "select",
        "options": ["auto", "manual", "scheduled"],
        "section": "softwareOS",
    },
    "softwareOS.hardeningProfile": {
        "prompt": "Which hardening profile?",
        "kind": "text",
        "section": "softwareOS",
    },
    "softwareOS.filesystemLayout": {
        "prompt": "Filesystem layout?",
        "kind": "text",
        "section": "softwareOS",
    },
    "softwareOS.timezone": {
        "prompt": "Timezone?",
        "kind": "text",
        "section": "softwareOS",
    },
    "softwareOS.locale": {
        "prompt": "Locale?",
        "kind": "text",
        "section": "softwareOS",
    },
    "applications[].category": {
        "prompt": "What category is the first application?",
        "kind": "select",
        "options": [
            "database",
            "web server",
            "app runtime",
            "cache",
            "message queue",
            "monitoring",
            "custom",
        ],
        "section": "applications",
    },
    "applications[].name": {
        "prompt": "Which application?",
        "kind": "text",
        "section": "applications",
    },
    "applications[].version": {
        "prompt": "Which application version?",
        "kind": "text",
        "section": "applications",
    },
    "applications[].edition": {
        "prompt": "Which edition?",
        "kind": "text",
        "section": "applications",
    },
    "applications[].expectedDataVolumeGb": {
        "prompt": "Expected data volume (GB)?",
        "kind": "number",
        "section": "applications",
    },
    "applications[].haConfig": {
        "prompt": "High-availability configuration?",
        "kind": "text",
        "section": "applications",
    },
    "applications[].installSource": {
        "prompt": "Install source (repo, tarball, image, etc.)?",
        "kind": "text",
        "section": "applications",
    },
}


MAX_BATCH = 5
MIN_BATCH = 2


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _get(record: dict, path: str) -> Any:
    obj: Any = record
    for p in path.split("."):
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(p)
        else:
            obj = getattr(obj, p, None)
    return obj


def _path_is_blank(record: dict, path: str) -> bool:
    if path.startswith("applications[]"):
        sub = path.split(".", 1)[1]
        apps = record.get("applications") or []
        if not apps:
            return True
        return _is_blank(apps[0].get(sub))
    return _is_blank(_get(record, path))


def _missing_paths(record: dict, required: list[str]) -> list[str]:
    return [p for p in required if _path_is_blank(record, p)]


def _build_question(path: str) -> Question:
    meta = FIELD_META.get(path, {"prompt": f"Please provide {path}.", "kind": "text"})
    q: Question = {
        "path": path,
        "prompt": meta["prompt"],
        "kind": meta.get("kind", "text"),
        "options": list(meta.get("options", [])),
        "required": True,
    }
    if meta.get("depends_on"):
        q["depends_on"] = meta["depends_on"]
    return q


def _initial_user_prompt(messages: list) -> str:
    for m in messages or []:
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


def _filter_by_dependencies(record: dict, paths: list[str]) -> list[str]:
    """Drop any path whose ``depends_on`` field is still blank — so we never
    ask for osDistribution before osFamily is answered."""
    out = []
    for p in paths:
        dep = FIELD_META.get(p, {}).get("depends_on")
        if dep and _path_is_blank(record, dep):
            continue
        out.append(p)
    return out


class BatchPlan(BaseModel):
    """Structured LLM output for the batched question planner."""

    title: str = Field(description="Short section title for the form, 2-6 words.")
    rationale: str = Field(description="One sentence on why these fields are grouped now.")
    field_paths: list[str] = Field(
        description="Ordered list of dotted field paths to ask together. "
                    "Must be 2-5 items and each must be from the provided candidates.",
    )


def _llm_plan_batch(
    user_prompt: str,
    record: dict,
    stage: str,
    candidates: list[str],
) -> BatchPlan | None:
    """Ask the LLM to choose a semantically related batch of 2-5 fields."""
    if not os.environ.get("LLM_PROVIDER") or not candidates:
        return None
    try:
        from app.llm import get_llm

        llm = get_llm()
    except Exception:
        return None

    cand_meta = []
    for p in candidates:
        m = FIELD_META.get(p, {})
        cand_meta.append({
            "path": p,
            "prompt": m.get("prompt", p),
            "kind": m.get("kind", "text"),
            "section": m.get("section"),
            "options": m.get("options") or [],
        })

    sys = (
        "You are a server provisioning assistant deciding which unfilled fields "
        "to ask the user about *together* in one focused form. "
        "Pick between 2 and 5 fields that are semantically related AND relevant "
        "to what the user described in their initial prompt. "
        "Prefer grouping fields from the same section (hardware, softwareOS, "
        "applications). Skip fields that obviously don't apply to the user's "
        "stated use case (e.g. don't include GPU fields for a lightweight "
        "static web site). Every field_path MUST be copied verbatim from the "
        "candidates list — do not invent paths."
    )
    user_content = (
        f"Stage: {stage}\n"
        f"Initial user prompt: {user_prompt or '(none)'}\n"
        f"Current record (partial, JSON):\n{json.dumps(record, default=str)[:4000]}\n\n"
        f"Candidate unfilled fields:\n{json.dumps(cand_meta, indent=2)}"
    )
    try:
        structured = llm.with_structured_output(BatchPlan)
        plan = structured.invoke([
            {"role": "system", "content": sys},
            {"role": "user", "content": user_content},
        ])
    except Exception:
        return None

    # Defensive validation — structured_output may echo hallucinated paths.
    allowed = set(candidates)
    cleaned = [p for p in plan.field_paths if p in allowed]
    if len(cleaned) < MIN_BATCH:
        return None
    plan.field_paths = cleaned[:MAX_BATCH]
    return plan


def _fallback_batch(candidates: list[str]) -> BatchPlan:
    """Section-based grouping used when the LLM is unavailable or hallucinates."""
    # Group candidates by section in a stable order matching the schema.
    section_order = ["hardware", "softwareOS", "applications"]
    by_section: dict[str, list[str]] = {}
    for p in candidates:
        sec = FIELD_META.get(p, {}).get("section", "other")
        by_section.setdefault(sec, []).append(p)

    for sec in section_order:
        bucket = by_section.get(sec) or []
        if bucket:
            chosen = bucket[:MAX_BATCH]
            return BatchPlan(
                title=_section_title(sec),
                rationale=f"Grouped {sec} fields to fill next.",
                field_paths=chosen,
            )
    # Nothing matched the known sections — take whatever's left.
    chosen = candidates[:MAX_BATCH]
    return BatchPlan(
        title="A few more details",
        rationale="Remaining fields needed to complete the record.",
        field_paths=chosen,
    )


def _section_title(section: str) -> str:
    return {
        "hardware": "Hardware sizing",
        "softwareOS": "Operating system",
        "applications": "Application details",
    }.get(section, "More details")


def _humanize_prompts(record: dict, questions: list[Question], title: str) -> None:
    """Rewrite each question's ``prompt`` in a single LLM round-trip. Silently
    leaves the canned prompts in place on any error."""
    if not os.environ.get("LLM_PROVIDER") or not questions:
        return
    try:
        from app.llm import get_llm

        llm = get_llm()
    except Exception:
        return

    items = [{"path": q["path"], "fallback": q.get("prompt", "")} for q in questions]
    sys = (
        "Rewrite each field's prompt as a concise, natural question (one sentence, "
        "no trailing option list, no field path). Return ONLY a JSON object of the "
        "form {\"prompts\": [{\"path\": \"...\", \"prompt\": \"...\"}, ...]} with one "
        "entry per input item and the same paths."
    )
    user = json.dumps({
        "title": title,
        "record": record,
        "items": items,
    }, default=str)[:6000]
    try:
        resp = llm.invoke([
            {"role": "system", "content": sys},
            {"role": "user", "content": user},
        ])
        content = resp.content if hasattr(resp, "content") else str(resp)
        if not isinstance(content, str):
            content = str(content)
        # Strip markdown fences the LLM might add.
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        data = json.loads(content)
        rewrites = {x["path"]: x["prompt"] for x in data.get("prompts", []) if x.get("prompt")}
    except Exception:
        return

    for q in questions:
        new = rewrites.get(q["path"])
        if new:
            q["prompt"] = new


def question_planner(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {"done": True}

    with FormApi() as api:
        record = api.get_record(record_id)
        catalog = api.get_catalog(stage=record["stage"])

    required = catalog.get("stageRequiredFields", [])
    missing = _missing_paths(record, required)
    if not missing:
        # Nothing left to collect → next stop is validator (the graph routes).
        return {"pending_batch": None, "pending_questions": []}

    candidates = _filter_by_dependencies(record, missing)
    if not candidates:
        # All remaining fields are dependency-gated — fall back to surfacing
        # the gating fields themselves (should be in `missing`).
        candidates = missing

    user_prompt = _initial_user_prompt(state.get("messages") or [])
    plan = _llm_plan_batch(
        user_prompt=user_prompt,
        record=record,
        stage=record.get("stage", "estimate"),
        candidates=candidates,
    )
    if plan is None:
        plan = _fallback_batch(candidates)

    questions = [_build_question(p) for p in plan.field_paths]
    _humanize_prompts(record, questions, plan.title)

    batch: QuestionBatch = {
        "batch_id": str(uuid.uuid4()),
        "title": plan.title,
        "rationale": plan.rationale,
        "questions": questions,
        "submitted": False,
        "errors": {},
    }

    # The batch rides as a sentinel-prefixed JSON payload inside the AIMessage
    # content. The frontend parses messages (which we know flow reliably via
    # AG-UI MESSAGES_SNAPSHOT/TEXT_MESSAGE events) and renders the form
    # whenever the latest AI message starts with `__BATCH__`. Mirroring it on
    # `pending_batch` is kept for the REST `/threads/*` fallback only.
    payload = json.dumps({"batch": batch}, default=str)
    content = f"__BATCH__{payload}"
    return {
        "pending_batch": batch,
        "pending_questions": [],
        "messages": [AIMessage(content=content)],
    }
