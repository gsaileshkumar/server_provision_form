from __future__ import annotations

import json
import os
from typing import Any

from langchain_core.messages import AIMessage

from app.graph.state import AgentState, Question
from app.tools.form_api import FormApi


# Labels + structured options for the fields we know about. Fields without an
# entry here fall through to free-text prompts.
FIELD_META: dict[str, dict[str, Any]] = {
    "hardware.workloadProfile": {
        "prompt": "What's the workload profile for this server?",
        "kind": "select",
        "options": ["web", "database", "app", "analytics", "general-purpose"],
    },
    "hardware.expectedConcurrentUsers": {
        "prompt": "Roughly how many concurrent users do you expect?",
        "kind": "number",
    },
    "hardware.cpuCores": {
        "prompt": "How many CPU cores?",
        "kind": "number",
    },
    "hardware.ramGb": {
        "prompt": "How much RAM (in GB)?",
        "kind": "number",
    },
    "hardware.primaryStorageGb": {
        "prompt": "How much primary storage (GB)?",
        "kind": "number",
    },
    "hardware.storageType": {
        "prompt": "Which storage type?",
        "kind": "select",
        "options": ["HDD", "SSD", "NVMe"],
    },
    "hardware.raidLevel": {
        "prompt": "Which RAID level?",
        "kind": "select",
        "options": ["none", "1", "5", "10"],
    },
    "hardware.gpuRequired": {
        "prompt": "Is a GPU required?",
        "kind": "boolean",
    },
    "hardware.networkBandwidthGbps": {
        "prompt": "Network bandwidth (Gbps)?",
        "kind": "select",
        "options": ["1", "10", "25", "40"],
    },
    "softwareOS.osFamily": {
        "prompt": "Which OS family?",
        "kind": "select",
        "options": ["Linux", "Windows"],
    },
    "softwareOS.osDistribution": {
        "prompt": "Which distribution?",
        "kind": "text",
    },
    "softwareOS.osVersion": {
        "prompt": "Which version?",
        "kind": "text",
    },
    "softwareOS.licensingModel": {
        "prompt": "OS licensing model?",
        "kind": "select",
        "options": ["BYOL", "included", "subscription"],
    },
    "softwareOS.patchingPolicy": {
        "prompt": "Patching policy?",
        "kind": "select",
        "options": ["auto", "manual", "scheduled"],
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
    },
    "applications[].name": {
        "prompt": "Which application?",
        "kind": "text",
    },
}


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


def _first_missing(record: dict, required: list[str]) -> str | None:
    for path in required:
        if path.startswith("applications[]"):
            sub = path.split(".", 1)[1]
            apps = record.get("applications") or []
            if not apps:
                return path
            for app in apps:
                if _is_blank(app.get(sub)):
                    return path
            continue
        if _is_blank(_get(record, path)):
            return path
    return None


def _llm_question(record: dict, missing: str, meta: dict) -> str | None:
    """Ask the LLM to generate a context-aware question for the next missing field."""
    if not os.environ.get("LLM_PROVIDER"):
        return None
    try:
        from app.llm import get_llm
        llm = get_llm()
    except Exception:
        return None

    options_hint = (
        f"Valid options are: {', '.join(meta['options'])}." if meta.get("options") else ""
    )
    record_json = json.dumps(record, default=str, indent=2)
    system = (
        "You are a server provisioning assistant collecting configuration details one field at a time. "
        "Generate a single natural, conversational question to collect the next missing field. "
        "Use the current configuration context to make the question relevant and helpful. "
        "Be concise (1-2 sentences). If there are valid options, mention them naturally at the end. "
        "Never output JSON, raw field paths, or technical identifiers."
    )
    user_content = (
        f"Current configuration so far:\n{record_json}\n\n"
        f"Next field to collect: {missing}\n"
        f"Fallback question: {meta['prompt']}\n"
        f"{options_hint}"
    )
    try:
        resp = llm.invoke([
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ])
        content = resp.content if hasattr(resp, "content") else str(resp)
        return (content if isinstance(content, str) else str(content)).strip() or None
    except Exception:
        return None


def question_planner(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {"done": True}

    with FormApi() as api:
        record = api.get_record(record_id)
        catalog = api.get_catalog(stage=record["stage"])

    required = catalog.get("stageRequiredFields", [])
    missing = _first_missing(record, required)
    if missing is None:
        # Nothing left to collect → next stop is validator (the graph routes).
        return {"pending_questions": []}

    meta = FIELD_META.get(missing, {"prompt": f"Please provide {missing}.", "kind": "text"})
    question: Question = {
        "path": missing,
        "prompt": meta["prompt"],
        "kind": meta.get("kind", "text"),
        "options": list(meta.get("options", [])),
    }

    # LLM-generated question; fall back to the canned prompt if not configured.
    prompt_text = _llm_question(record, missing, meta)
    if not prompt_text:
        prompt_text = meta["prompt"]
        if meta.get("options"):
            prompt_text += f"  Options: {', '.join(meta['options'])}"

    return {
        "pending_questions": [question],
        "messages": [AIMessage(content=prompt_text)],
    }
