from __future__ import annotations

import json
import os
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.graph.state import AgentState
from app.tools.form_api import FormApi


# Schema describing the record fields the inferrer / planner reason about.
# Stays in code (not loaded from the Form API) so the agent has a stable
# vocabulary for both filling values and judging which use-case questions
# would unblock the most fields.
REMAINING_FIELD_SCHEMA: dict[str, dict[str, Any]] = {
    "hardware.workloadProfile": {
        "kind": "select",
        "options": ["web", "database", "app", "analytics", "general-purpose"],
        "section": "hardware",
    },
    "hardware.expectedConcurrentUsers": {"kind": "number", "section": "hardware"},
    "hardware.cpuCores": {"kind": "number", "section": "hardware"},
    "hardware.ramGb": {"kind": "number", "section": "hardware"},
    "hardware.primaryStorageGb": {"kind": "number", "section": "hardware"},
    "hardware.storageType": {
        "kind": "select",
        "options": ["HDD", "SSD", "NVMe"],
        "section": "hardware",
    },
    "hardware.raidLevel": {
        "kind": "select",
        "options": ["none", "1", "5", "10"],
        "section": "hardware",
    },
    "hardware.gpuRequired": {"kind": "boolean", "section": "hardware"},
    "hardware.networkBandwidthGbps": {
        "kind": "select",
        "options": ["1", "10", "25", "40"],
        "section": "hardware",
    },
    "hardware.redundancy": {
        "kind": "select",
        "options": ["none", "active-passive", "active-active"],
        "section": "hardware",
    },
    "hardware.rackUnits": {"kind": "number", "section": "hardware"},
    "hardware.powerDrawWatts": {"kind": "number", "section": "hardware"},
    "softwareOS.osFamily": {
        "kind": "select",
        "options": ["Linux", "Windows"],
        "section": "softwareOS",
    },
    "softwareOS.osDistribution": {
        "kind": "text",
        "section": "softwareOS",
        "depends_on": "softwareOS.osFamily",
    },
    "softwareOS.osVersion": {
        "kind": "text",
        "section": "softwareOS",
        "depends_on": "softwareOS.osDistribution",
    },
    "softwareOS.licensingModel": {
        "kind": "select",
        "options": ["BYOL", "included", "subscription"],
        "section": "softwareOS",
    },
    "softwareOS.patchingPolicy": {
        "kind": "select",
        "options": ["auto", "manual", "scheduled"],
        "section": "softwareOS",
    },
    "softwareOS.hardeningProfile": {
        "kind": "select",
        "options": ["none", "CIS", "custom"],
        "section": "softwareOS",
    },
    "softwareOS.filesystemLayout": {"kind": "text", "section": "softwareOS"},
    "softwareOS.timezone": {"kind": "text", "section": "softwareOS"},
    "softwareOS.locale": {"kind": "text", "section": "softwareOS"},
    "applications[].category": {
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
    "applications[].name": {"kind": "text", "section": "applications"},
    "applications[].version": {"kind": "text", "section": "applications"},
    "applications[].edition": {
        "kind": "select",
        "options": ["Community", "Enterprise"],
        "section": "applications",
    },
    "applications[].expectedDataVolumeGb": {"kind": "number", "section": "applications"},
    "applications[].haConfig": {"kind": "text", "section": "applications"},
    "applications[].installSource": {
        "kind": "select",
        "options": ["package manager", "binary", "container image", "custom URL"],
        "section": "applications",
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


def _path_is_blank(record: dict, path: str) -> bool:
    if path.startswith("applications[]"):
        sub = path.split(".", 1)[1]
        apps = record.get("applications") or []
        if not apps:
            return True
        return _is_blank(apps[0].get(sub))
    return _is_blank(_get(record, path))


def missing_field_paths(record: dict, required: list[str]) -> list[str]:
    return [p for p in required if _path_is_blank(record, p)]


def _last_human_text(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


def _build_system_context(
    record: dict, catalog: dict, compatibility: dict, pricing: dict
) -> str:
    """Package the record + pricing + compatibility snapshot so the LLM has
    everything it needs to answer Mode-B questions without guessing."""
    os_info = record.get("softwareOS") or {}
    distro = os_info.get("osDistribution")
    version = os_info.get("osVersion")

    relevant_compat: list[dict] = []
    if distro and version:
        label = (
            f"Windows Server {version}"
            if distro == "WindowsServer"
            else f"{distro} {version}"
        )
        relevant_compat = [
            e
            for e in compatibility.get("entries", [])
            if label in e.get("supportedOSDistributions", [])
        ][:20]

    pricing_summary = {
        "hardwareCost": pricing.get("hardwareCost", 0),
        "softwareCost": pricing.get("softwareCost", 0),
        "taxes": pricing.get("taxes", 0),
        "total": pricing.get("total", 0),
    }

    record_json = json.dumps(record, default=str, indent=2)
    pricing_json = json.dumps(pricing_summary, indent=2)
    compat_json = json.dumps(relevant_compat, indent=2) if relevant_compat else "[]"

    return (
        "You are a read-only provisioning assistant helping the user review "
        "their server configuration in Mode B (provisioning stage). Answer "
        "their question clearly and concisely using ONLY the data provided "
        "below.\n\n"
        "Rules:\n"
        "- Do not instruct the user to change fields unless they explicitly "
        "asked for a recommendation.\n"
        "- Never output JSON or raw field paths.\n"
        "- For pricing questions, quote the totals below (US dollars).\n"
        "- For compatibility questions, only claim support if the app is in "
        "the relevant compatibility list.\n"
        "- For RAID / storage / sizing questions, explain trade-offs in plain "
        "English.\n\n"
        f"Current record:\n```\n{record_json}\n```\n\n"
        f"Current pricing:\n```\n{pricing_json}\n```\n\n"
        f"Apps compatible with the selected OS ({distro} {version}):\n"
        f"```\n{compat_json}\n```"
    )


def field_helper(state: AgentState) -> dict:
    """Mode B read-only helper. Always calls the LLM with the full record,
    pricing, and OS-filtered compatibility snapshot as system context. If no
    LLM is configured, returns a pointer message."""
    record_id = state.get("record_id")
    if not record_id:
        return {"messages": [AIMessage(content="No record loaded yet.")]}

    question = _last_human_text(state.get("messages", []))

    with FormApi() as api:
        record = api.get_record(record_id)
        catalog = api.get_catalog(stage=record.get("stage"))
        compatibility = api.get_compatibility()
        pricing = api.compute_pricing(record_id)

    if not os.environ.get("LLM_PROVIDER"):
        answer = (
            "No LLM is configured (set LLM_PROVIDER, LLM_MODEL, LLM_API_KEY). "
            "Once configured, I can answer questions about your current "
            "configuration, pricing, compatibility, and hardware trade-offs."
        )
        return {"messages": [AIMessage(content=answer)]}

    try:
        from app.llm import get_llm

        llm = get_llm()
        system = _build_system_context(record, catalog, compatibility, pricing)
        resp = llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ]
        )
        content = resp.content if hasattr(resp, "content") else str(resp)
        answer = content if isinstance(content, str) else str(content)
    except Exception as e:
        answer = f"I couldn't consult the LLM: {type(e).__name__}: {e}"

    return {"messages": [AIMessage(content=answer)]}
