from __future__ import annotations

import json
import os
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.graph.state import AgentState
from app.tools.form_api import FormApi


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

    # Narrow the compatibility list to entries relevant to the current OS
    # (full matrix is noisy).
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


def _summarize_changes(changes: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in changes.items())
