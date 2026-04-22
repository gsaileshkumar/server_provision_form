from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.graph.state import AgentState
from app.tools.form_api import FormApi

# Map of user-visible names to dotted field paths. Order matters: longest
# keys first so "raid level" is matched before "raid".
_FIELD_ALIASES: list[tuple[str, str]] = [
    ("workload profile", "hardware.workloadProfile"),
    ("workload", "hardware.workloadProfile"),
    ("concurrent users", "hardware.expectedConcurrentUsers"),
    ("users", "hardware.expectedConcurrentUsers"),
    ("cpu cores", "hardware.cpuCores"),
    ("cpu", "hardware.cpuCores"),
    ("ram", "hardware.ramGb"),
    ("memory", "hardware.ramGb"),
    ("primary storage", "hardware.primaryStorageGb"),
    ("storage type", "hardware.storageType"),
    ("storage", "hardware.primaryStorageGb"),
    ("raid level", "hardware.raidLevel"),
    ("raid", "hardware.raidLevel"),
    ("gpu required", "hardware.gpuRequired"),
    ("gpu", "hardware.gpuRequired"),
    ("gpu model", "hardware.gpuModel"),
    ("gpu vram", "hardware.gpuVramGb"),
    ("vram", "hardware.gpuVramGb"),
    ("network bandwidth", "hardware.networkBandwidthGbps"),
    ("bandwidth", "hardware.networkBandwidthGbps"),
    ("redundancy", "hardware.redundancy"),
    ("rack units", "hardware.rackUnits"),
    ("power draw", "hardware.powerDrawWatts"),
    ("os family", "softwareOS.osFamily"),
    ("distribution", "softwareOS.osDistribution"),
    ("os version", "softwareOS.osVersion"),
    ("licensing", "softwareOS.licensingModel"),
    ("patching", "softwareOS.patchingPolicy"),
    ("hardening", "softwareOS.hardeningProfile"),
    ("filesystem", "softwareOS.filesystemLayout"),
    ("timezone", "softwareOS.timezone"),
    ("locale", "softwareOS.locale"),
]

# Patterns that indicate an explicit edit instruction.
_EDIT_PATTERNS = [
    re.compile(r"^\s*set\s+(?P<field>.+?)\s+(?:to|=)\s+(?P<value>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*change\s+(?P<field>.+?)\s+to\s+(?P<value>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*make\s+(?P<field>.+?)\s+(?P<value>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*use\s+(?P<value>.+?)\s+for\s+(?P<field>.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*update\s+(?P<field>.+?)\s+to\s+(?P<value>.+?)\s*$", re.IGNORECASE),
]


def _match_field(text: str) -> str | None:
    t = text.lower().strip()
    for alias, path in _FIELD_ALIASES:
        if t == alias or alias in t:
            return path
    return None


def _coerce(path: str, raw: str) -> Any:
    v = raw.strip().strip("\"'")
    numeric_paths = {
        "hardware.expectedConcurrentUsers",
        "hardware.cpuCores",
        "hardware.ramGb",
        "hardware.primaryStorageGb",
        "hardware.gpuVramGb",
        "hardware.networkBandwidthGbps",
        "hardware.rackUnits",
        "hardware.powerDrawWatts",
    }
    bool_paths = {"hardware.gpuRequired"}
    if path in numeric_paths:
        m = re.search(r"-?\d+(?:\.\d+)?", v)
        if m:
            num = float(m.group())
            return int(num) if num.is_integer() else num
        return None
    if path in bool_paths:
        return v.lower() in {"yes", "y", "true", "on", "1", "enabled"}
    return v


def detect_edit(text: str) -> tuple[str, Any] | None:
    for pat in _EDIT_PATTERNS:
        m = pat.match(text)
        if not m:
            continue
        field = _match_field(m.group("field"))
        if field is None:
            continue
        value = _coerce(field, m.group("value"))
        if value is None:
            continue
        return field, value
    return None


def _last_human_text(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


def _apply_patch(path: str, value: Any) -> dict:
    head, _, tail = path.partition(".")
    return {head: {tail: value}}


def ui_updater(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {}
    text = _last_human_text(state.get("messages", []))
    edit = detect_edit(text)
    if edit is None:
        return {}
    field, value = edit
    patch = _apply_patch(field, value)
    with FormApi() as api:
        api.update_record(record_id, patch)
    return {
        "messages": [
            AIMessage(content=f"Updated {field} → {value}.")
        ]
    }
