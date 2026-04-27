"""Dummy tools the agent can call to help users estimate a server."""

from __future__ import annotations

from langchain_core.tools import tool

from config import (
    BASE_PRICE_USD,
    FIELD_OPTIONS,
    PER_CORE_USD,
    PER_GB_MEMORY_USD,
    PER_GB_STORAGE_USD,
    REGION_MULTIPLIER,
)


@tool
def get_field_options(field: str) -> dict:
    """Return the available options for a server provisioning field.

    Use this when the user asks what values are valid for a field such as
    "os", "server_type", "cpu_cores", "memory_gb", "storage_gb", or "region".
    """
    key = field.strip().lower().replace(" ", "_")
    if key not in FIELD_OPTIONS:
        return {
            "field": field,
            "error": f"Unknown field '{field}'.",
            "known_fields": sorted(FIELD_OPTIONS.keys()),
        }
    return {"field": key, "options": FIELD_OPTIONS[key]}


@tool
def list_supported_fields() -> dict:
    """List every server provisioning field the agent understands."""
    return {"fields": sorted(FIELD_OPTIONS.keys())}


@tool
def estimate_server_cost(
    server_type: str,
    os: str,
    cpu_cores: int,
    memory_gb: int,
    storage_gb: int,
    region: str = "us-east",
) -> dict:
    """Estimate the monthly cost for a server with the given configuration.

    Validates the inputs against the supported options and returns a cost
    breakdown in USD per month. Returns an error payload if any input is
    invalid so the agent can ask the user to correct it.
    """
    server_type_n = server_type.strip().title()
    os_n = os.strip().title()
    region_n = region.strip().lower()

    errors: list[str] = []
    if server_type_n not in FIELD_OPTIONS["server_type"]:
        errors.append(f"server_type must be one of {FIELD_OPTIONS['server_type']}")
    if os_n not in FIELD_OPTIONS["os"]:
        errors.append(f"os must be one of {FIELD_OPTIONS['os']}")
    if region_n not in REGION_MULTIPLIER:
        errors.append(f"region must be one of {sorted(REGION_MULTIPLIER)}")
    if cpu_cores <= 0:
        errors.append("cpu_cores must be a positive integer")
    if memory_gb <= 0:
        errors.append("memory_gb must be a positive integer")
    if storage_gb <= 0:
        errors.append("storage_gb must be a positive integer")

    if errors:
        return {"error": "Invalid configuration", "details": errors}

    base = BASE_PRICE_USD[(server_type_n, os_n)]
    cpu_cost = cpu_cores * PER_CORE_USD
    memory_cost = memory_gb * PER_GB_MEMORY_USD
    storage_cost = storage_gb * PER_GB_STORAGE_USD
    subtotal = base + cpu_cost + memory_cost + storage_cost
    multiplier = REGION_MULTIPLIER[region_n]
    monthly = round(subtotal * multiplier, 2)

    return {
        "currency": "USD",
        "monthly_cost": monthly,
        "breakdown": {
            "base": round(base, 2),
            "cpu": round(cpu_cost, 2),
            "memory": round(memory_cost, 2),
            "storage": round(storage_cost, 2),
            "region_multiplier": multiplier,
        },
        "configuration": {
            "server_type": server_type_n,
            "os": os_n,
            "cpu_cores": cpu_cores,
            "memory_gb": memory_gb,
            "storage_gb": storage_gb,
            "region": region_n,
        },
    }


TOOLS = [get_field_options, list_supported_fields, estimate_server_cost]
