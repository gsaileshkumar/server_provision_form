from __future__ import annotations

import json
import os

from langchain_core.messages import AIMessage

from app.graph.state import AgentState
from app.tools.form_api import FormApi


def _summary_line(label: str, value: object) -> str:
    return f"  {label}: {value}"


def _format_summary(record: dict, pricing: dict) -> str:
    lines: list[str] = [
        f"**{record.get('recordName', 'Record')}** — {record.get('stage')}",
        "",
        "Hardware:",
    ]
    hw = record.get("hardware") or {}
    for key in (
        "workloadProfile",
        "expectedConcurrentUsers",
        "cpuCores",
        "ramGb",
        "primaryStorageGb",
        "storageType",
        "raidLevel",
        "gpuRequired",
        "networkBandwidthGbps",
    ):
        v = hw.get(key)
        if v is not None:
            lines.append(_summary_line(key, v))
    lines.append("")
    lines.append("Software (OS):")
    os_ = record.get("softwareOS") or {}
    for key in ("osFamily", "osDistribution", "osVersion", "licensingModel", "patchingPolicy"):
        v = os_.get(key)
        if v is not None:
            lines.append(_summary_line(key, v))
    lines.append("")
    lines.append("Applications:")
    for a in record.get("applications") or []:
        parts = [f"{a.get('name') or '?'}"]
        if a.get("version"):
            parts.append(f"v{a['version']}")
        if a.get("edition"):
            parts.append(f"({a['edition']})")
        if a.get("expectedDataVolumeGb"):
            parts.append(f"data {a['expectedDataVolumeGb']}GB")
        lines.append(_summary_line("-", " ".join(parts)))
    lines.append("")
    lines.append(
        f"Estimated total: **${pricing.get('total', 0):.2f}** "
        f"(hw ${pricing.get('hardwareCost', 0):.2f}, "
        f"sw ${pricing.get('softwareCost', 0):.2f}, "
        f"tax ${pricing.get('taxes', 0):.2f})"
    )
    lines.append("")
    lines.append(
        "Reply **approve** to submit and lock this record, or describe any "
        "changes you'd like to make."
    )
    return "\n".join(lines)


def _llm_review(record: dict, pricing: dict) -> str | None:
    """Ask the LLM to write a conversational pre-submission review."""
    if not os.environ.get("LLM_PROVIDER"):
        return None
    try:
        from app.llm import get_llm
        llm = get_llm()
    except Exception:
        return None

    pricing_summary = {
        "hardwareCost": pricing.get("hardwareCost", 0),
        "softwareCost": pricing.get("softwareCost", 0),
        "taxes": pricing.get("taxes", 0),
        "total": pricing.get("total", 0),
    }
    record_json = json.dumps(record, default=str, indent=2)
    pricing_json = json.dumps(pricing_summary, indent=2)

    system = (
        "You are a server provisioning assistant presenting a final review before submission. "
        "Summarize the server configuration in clear, friendly markdown with section headers. "
        "Include hardware specs, OS details, applications, and the cost breakdown. "
        "Highlight anything notable (e.g. high storage, GPU, RAID level). "
        "End by asking the user to reply 'approve' to submit and lock, or to describe any changes. "
        "Never output raw JSON or internal field path names."
    )
    user_content = (
        f"Record to review:\n{record_json}\n\n"
        f"Pricing:\n{pricing_json}"
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


def reviewer(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {}

    with FormApi() as api:
        record = api.get_record(record_id)
        pricing = api.compute_pricing(record_id)

    msg = _llm_review(record, pricing) or _format_summary(record, pricing)
    return {
        "review_pending": True,
        "messages": [AIMessage(content=msg)],
    }
