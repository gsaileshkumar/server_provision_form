from __future__ import annotations

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


def _quick_answer(question: str, record: dict, catalog: dict, compatibility: dict, pricing: dict) -> str | None:
    """Hard-coded answers for a few common questions so Mode B works usefully
    even when no LLM is configured."""
    q = question.lower()
    if "pricing" in q or "price" in q or "cost" in q or "total" in q:
        return (
            f"Current estimate: hardware ${pricing.get('hardwareCost', 0):.2f}, "
            f"software ${pricing.get('softwareCost', 0):.2f}, "
            f"taxes ${pricing.get('taxes', 0):.2f}, total **${pricing.get('total', 0):.2f}**."
        )
    if "raid" in q:
        return (
            "RAID options: 'none' (single disk), '1' (mirror, good for durability), "
            "'5' (parity across 3+ disks, balanced read/capacity), '10' (stripe of mirrors, "
            "best for databases that need both redundancy and write throughput)."
        )
    if "compatib" in q or "support" in q:
        os_info = record.get("softwareOS") or {}
        distro = os_info.get("osDistribution")
        version = os_info.get("osVersion")
        if distro and version:
            label = f"Windows Server {version}" if distro == "WindowsServer" else f"{distro} {version}"
            supported = [
                e for e in compatibility.get("entries", [])
                if label in e.get("supportedOSDistributions", [])
            ]
            names = ", ".join(f"{e['appName']} {e['appVersion']}" for e in supported[:8])
            return (
                f"Apps that list {label} as supported include: {names}."
                if supported else
                f"No compatibility entries list {label} as supported. Double-check app versions."
            )
    return None


def field_helper(state: AgentState) -> dict:
    """Mode B read-only helper. Answers the user's question using catalog +
    compatibility + pricing data; falls back to an LLM if one is configured
    and no quick answer matches."""
    record_id = state.get("record_id")
    if not record_id:
        return {"messages": [AIMessage(content="No record loaded yet.")]}

    question = _last_human_text(state.get("messages", []))

    with FormApi() as api:
        record = api.get_record(record_id)
        catalog = api.get_catalog(stage=record.get("stage"))
        compatibility = api.get_compatibility()
        pricing = api.compute_pricing(record_id)

    answer = _quick_answer(question, record, catalog, compatibility, pricing)
    if answer is None and os.environ.get("LLM_PROVIDER"):
        try:
            from app.llm import get_llm

            llm = get_llm()
            context = (
                f"You are a read-only provisioning assistant. The current record is:\n"
                f"{record}\n\n"
                f"Compatibility matrix has {len(compatibility.get('entries', []))} entries. "
                f"Current pricing total is ${pricing.get('total', 0):.2f}.\n\n"
                f"Answer the user's question about their server configuration "
                f"concisely. Do NOT instruct the user to change fields unless "
                f"they explicitly asked for a recommendation. Never output JSON."
            )
            resp = llm.invoke([
                {"role": "system", "content": context},
                {"role": "user", "content": question},
            ])
            content = resp.content if hasattr(resp, "content") else str(resp)
            answer = content if isinstance(content, str) else str(content)
        except Exception as e:
            answer = f"I couldn't consult the LLM: {e}"

    if answer is None:
        answer = (
            "I can answer questions about your current configuration, pricing, "
            "compatibility, or RAID/storage trade-offs. Try asking something "
            "like \"what's the total cost?\" or \"is PostgreSQL 16 compatible with "
            "Ubuntu 22.04?\""
        )

    return {"messages": [AIMessage(content=answer)]}


def _summarize_changes(changes: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in changes.items())
