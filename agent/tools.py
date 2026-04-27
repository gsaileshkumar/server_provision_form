"""Tools the infrastructure agent can call.

Field/estimation tools and proposal tools all live here; workflow-discovery
tools are imported from `workflows.py` and re-exported through `TOOLS` so
the agent sees a single tool list.
"""

from __future__ import annotations

import json

from langchain_core.tools import tool

import proposals
from config import (
    BASE_PRICE_USD,
    FIELD_OPTIONS,
    PER_CORE_USD,
    PER_GB_MEMORY_USD,
    PER_GB_STORAGE_USD,
    REGION_MULTIPLIER,
)
from workflows import get_workflow_instructions, list_workflows


def _validate_server_config(
    server_type: str,
    os: str,
    cpu_cores: int,
    memory_gb: int,
    storage_gb: int,
    region: str,
) -> tuple[dict, list[str]]:
    """Normalize inputs and collect validation errors.

    Shared between `estimate_server_cost` and `submit_proposal` so they
    accept and reject identical configurations.
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

    normalized = {
        "server_type": server_type_n,
        "os": os_n,
        "cpu_cores": cpu_cores,
        "memory_gb": memory_gb,
        "storage_gb": storage_gb,
        "region": region_n,
    }
    return normalized, errors


@tool
def validate_config(
    server_type: str,
    os: str,
    cpu_cores: int,
    memory_gb: int,
    storage_gb: int,
    region: str = "us-east",
) -> dict:
    """Validate a server configuration without saving or estimating cost.

    Returns the normalized configuration on success, or an error payload listing
    every invalid field so you can choose corrected values and retry.
    Call this before presenting any recommended configuration to the user.
    """
    config, errors = _validate_server_config(
        server_type, os, cpu_cores, memory_gb, storage_gb, region
    )
    if errors:
        return {
            "valid": False,
            "errors": errors,
            "valid_options": {k: v for k, v in FIELD_OPTIONS.items()},
        }
    return {"valid": True, "configuration": config}


@tool
def get_field_options(fields) -> dict:
    """Return the available options for one or more server provisioning fields.

    Args:
        fields (str | list[str]): A single field or a list of fields such as
        "os", "server_type", "cpu_cores", "memory_gb", "storage_gb", or "region".
    """
    if isinstance(fields, str):
        fields = [fields]

    result = {}
    errors = {}

    for field in fields:
        key = field.strip().lower().replace(" ", "_")

        if key not in FIELD_OPTIONS:
            errors[field] = {
                "error": f"Unknown field '{field}'.",
                "known_fields": sorted(FIELD_OPTIONS.keys()),
            }
        else:
            result[key] = FIELD_OPTIONS[key]

    response = {"options": result}

    if errors:
        response["errors"] = errors

    return response


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
    config, errors = _validate_server_config(
        server_type, os, cpu_cores, memory_gb, storage_gb, region
    )
    if errors:
        return {"error": "Invalid configuration", "details": errors}

    base = BASE_PRICE_USD[(config["server_type"], config["os"])]
    cpu_cost = config["cpu_cores"] * PER_CORE_USD
    memory_cost = config["memory_gb"] * PER_GB_MEMORY_USD
    storage_cost = config["storage_gb"] * PER_GB_STORAGE_USD
    subtotal = base + cpu_cost + memory_cost + storage_cost
    multiplier = REGION_MULTIPLIER[config["region"]]
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
        "configuration": config,
    }


@tool
def submit_proposal(
    server_type: str,
    os: str,
    cpu_cores: int,
    memory_gb: int,
    storage_gb: int,
    region: str = "us-east",
) -> dict:
    """Register a server build configuration as a formal proposal.

    Uses the same field set and validation as `estimate_server_cost`.
    On success returns the proposal id and the stored record (status
    'proposed'). On invalid input returns an `error` payload.
    """
    config, errors = _validate_server_config(
        server_type, os, cpu_cores, memory_gb, storage_gb, region
    )
    if errors:
        return {"error": "Invalid configuration", "details": errors}

    record = proposals.save_proposal(config)
    return {"id": record["id"], "proposal": record}


@tool
def list_proposals() -> dict:
    """List every proposal stored in this session."""
    return {"proposals": proposals.list_proposals()}


@tool
def export_proposal(proposal_id: str, path: str | None = None) -> dict:
    """Write a stored proposal to disk as a JSON file.

    Default path is `./proposal_<id>.json`. Returns the written path on
    success, or an `error` payload if the id is unknown or the file
    cannot be written.
    """
    record = proposals.get_proposal(proposal_id)
    if record is None:
        return {"error": f"Unknown proposal_id '{proposal_id}'."}

    target = path or f"./proposal_{proposal_id}.json"
    try:
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2, sort_keys=True)
    except OSError as exc:
        return {"error": f"Could not write file: {exc}"}
    return {"path": target, "proposal_id": proposal_id}


TOOLS = [
    validate_config,
    get_field_options,
    list_supported_fields,
    estimate_server_cost,
    submit_proposal,
    list_proposals,
    export_proposal,
    list_workflows,
    get_workflow_instructions,
]
