from __future__ import annotations

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


def reviewer(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {}

    with FormApi() as api:
        record = api.get_record(record_id)
        pricing = api.compute_pricing(record_id)

    msg = _format_summary(record, pricing)
    return {
        "review_pending": True,
        "messages": [AIMessage(content=msg)],
    }
