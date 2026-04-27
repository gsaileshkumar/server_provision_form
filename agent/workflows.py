"""Workflow playbooks the agent fetches on demand.

The system prompt stays generic; per-workflow detail (required inputs,
step order, output shape) lives here and is exposed through two tools the
agent calls when it decides a workflow is relevant.
"""

from __future__ import annotations

from langchain_core.tools import tool

WORKFLOWS: dict[str, str] = {
    "server_estimation": """Goal: produce a monthly USD cost estimate for a server build.

Steps:
  1. Ask the user about their application or workload - understand the use case
     before touching any configuration fields. One or two focused questions are
     enough (e.g. "What will run on this server?", "Expected traffic or data
     volume?", "Any OS or region preference?"). Do NOT list field names at the user.
  2. Based on their answers, reason internally about the best-fit configuration
     (server_type, os, cpu_cores, memory_gb, storage_gb, region). Use
     `get_field_options(field=...)` if you need to confirm which values are valid.
  3. Call `validate_config(...)` with your chosen values.
     - If it returns `valid: false`, examine the errors, pick corrected values
       from the returned `valid_options`, and retry `validate_config` until it
       returns `valid: true`. Never show an invalid config to the user.
  4. Present the validated configuration to the user as a recommendation with
     brief reasoning (e.g. "For a medium-traffic web app I'd suggest...").
     Ask them to confirm or adjust.
  5. Once the user confirms (or provides corrections), call
     `estimate_server_cost(...)` with the final configuration.
  6. Reply with the monthly cost and the breakdown. Never compute the price
     yourself. If the tool returns an `error` payload, fix the offending field
     and retry.
""",
    "server_proposal": """Goal: register a server build configuration as a formal proposal (status='proposed').

Steps:
  1. Ask the user about their application or workload - understand the use case
     before touching any configuration fields. One or two focused questions are
     enough (e.g. "What will run on this server?", "Expected traffic or data
     volume?", "Any OS or region preference?"). Do NOT list field names at the user.
  2. Based on their answers, reason internally about the best-fit configuration
     (server_type, os, cpu_cores, memory_gb, storage_gb, region). Use
     `get_field_options(field=...)` if you need to confirm which values are valid.
  3. Call `validate_config(...)` with your chosen values.
     - If it returns `valid: false`, examine the errors, pick corrected values
       from the returned `valid_options`, and retry `validate_config` until it
       returns `valid: true`. Never show an invalid config to the user.
  4. Present the validated configuration to the user as a clear recommendation
     (e.g. "Based on your use case, I'd suggest..."). Ask them to confirm or
     adjust before creating the proposal.
  5. If the user adjusts any values, call `validate_config` again to confirm the
     revised configuration is valid before submitting.
  6. Call `submit_proposal(...)` with the confirmed configuration.
     - On success the tool returns `{"id": ..., "proposal": {...}}`. Tell the
       user the proposal id; they will need it to export later.
     - If the tool returns an `error` payload, fix the offending field and retry.
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
