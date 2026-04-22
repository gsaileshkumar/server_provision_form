from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from app.graph.state import AgentState
from app.tools.form_api import FormApi

WORKLOAD_DEFAULTS: dict[str, dict[str, Any]] = {
    "web": {"cpuPerUser": 0.02, "ramPerUserGb": 0.04, "storagePerUserGb": 0.05, "minCpu": 2, "minRam": 8, "minStorage": 100},
    "database": {"cpuPerUser": 0.05, "ramPerUserGb": 0.2, "storagePerUserGb": 0.5, "minCpu": 4, "minRam": 32, "minStorage": 200},
    "app": {"cpuPerUser": 0.04, "ramPerUserGb": 0.08, "storagePerUserGb": 0.1, "minCpu": 4, "minRam": 16, "minStorage": 100},
    "analytics": {"cpuPerUser": 0.08, "ramPerUserGb": 0.5, "storagePerUserGb": 1, "minCpu": 8, "minRam": 64, "minStorage": 500},
    "general-purpose": {"cpuPerUser": 0.03, "ramPerUserGb": 0.1, "storagePerUserGb": 0.1, "minCpu": 2, "minRam": 8, "minStorage": 100},
}


def _suggest(workload: str, users: int) -> dict[str, int] | None:
    rules = WORKLOAD_DEFAULTS.get(workload)
    if rules is None:
        return None

    def _next_power_of_two(n: float) -> int:
        n = max(1, int(n))
        result = 1
        while result < n:
            result <<= 1
        return result

    cpu = max(rules["minCpu"], _next_power_of_two(rules["cpuPerUser"] * users))
    ram = max(rules["minRam"], _next_power_of_two(rules["ramPerUserGb"] * users))
    storage = max(rules["minStorage"], int(round(rules["storagePerUserGb"] * users / 50) * 50) or 50)
    return {"cpuCores": cpu, "ramGb": ram, "primaryStorageGb": storage}


def recommender(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {}
    with FormApi() as api:
        record = api.get_record(record_id)
    hw = record.get("hardware") or {}
    workload = hw.get("workloadProfile")
    users = hw.get("expectedConcurrentUsers")
    if not workload or not users:
        return {}

    missing = {
        k: hw.get(k) is None
        for k in ("cpuCores", "ramGb", "primaryStorageGb")
    }
    if not any(missing.values()):
        return {}

    suggestion = _suggest(workload, int(users))
    if suggestion is None:
        return {}

    patch_hw = {k: v for k, v in suggestion.items() if missing.get(k)}
    with FormApi() as api:
        api.update_record(record_id, {"hardware": patch_hw})

    fields = ", ".join(f"{k}={v}" for k, v in patch_hw.items())
    return {
        "messages": [
            AIMessage(
                content=(
                    f"Based on a {workload} workload for ~{users} users, I've "
                    f"suggested: {fields}. You can override any of these as we "
                    f"continue."
                )
            )
        ]
    }
