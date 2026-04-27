"""Workflow playbooks the agent fetches on demand.

The system prompt stays generic; per-workflow detail (required inputs,
step order, output shape) lives here and is exposed through two tools the
agent calls when it decides a workflow is relevant.
"""

from __future__ import annotations

from langchain_core.tools import tool

WORKFLOWS: dict[str, str] = {
    "server_estimation": """Goal: produce a monthly USD cost estimate for a server build.

Required inputs: server_type, os, cpu_cores, memory_gb, storage_gb, region (default 'us-east').

Steps:
  1. If the user is unsure of valid values for any field, call
     `list_supported_fields` and/or `get_field_options(field=...)`.
  2. Once every required input is known, call `estimate_server_cost(...)`.
  3. Never compute the price yourself. If the tool returns an `error`
     payload, ask the user to fix the offending field.
  4. Reply with the monthly cost and the breakdown.
""",
    "server_proposal": """Goal: register a server build configuration as a formal proposal (status='proposed').

Required inputs: same six fields as `server_estimation` (server_type, os,
cpu_cores, memory_gb, storage_gb, region).

Steps:
  1. Gather the same inputs as `server_estimation`. Use `get_field_options`
     if any value looks unusual.
  2. Call `submit_proposal(...)` with the full configuration.
  3. On success the tool returns `{"id": ..., "proposal": {...}}`. Tell
     the user the proposal id; they will need it to export later.
  4. If the tool returns an `error` payload, the configuration failed
     validation - ask the user to correct it.
""",
    "proposal_export": """Goal: write a previously submitted proposal to disk as a JSON file.

Required input: proposal_id. Optional: path (defaults to './proposal_<id>.json').

Steps:
  1. If the user does not remember the id, call `list_proposals` and
     present the choices.
  2. Call `export_proposal(proposal_id=..., path=...)`.
  3. On success the tool returns the written path; report it to the user.
  4. If the id is unknown, the tool returns an `error` payload; ask the
     user to pick a valid id.
""",
}


@tool
def list_workflows() -> dict:
    """List the workflow playbooks this assistant supports.

    Call this first when the user states a goal so you know which playbook
    to fetch with `get_workflow_instructions`.
    """
    return {"workflows": sorted(WORKFLOWS.keys())}


@tool
def get_workflow_instructions(workflow: str) -> dict:
    """Return the detailed playbook for a single workflow.

    Always call this before executing a workflow you have not yet loaded
    in the current conversation.
    """
    key = workflow.strip().lower()
    if key not in WORKFLOWS:
        return {
            "error": f"Unknown workflow '{workflow}'.",
            "known_workflows": sorted(WORKFLOWS.keys()),
        }
    return {"workflow": key, "instructions": WORKFLOWS[key]}
