"""Use-case-driven question planner using the canonical A2UI pattern.

Adapted from the AG-UI dojo `a2ui_dynamic_schema` example:

  https://dojo.ag-ui.com/langgraph-fastapi/feature/a2ui_dynamic_schema

Key idea: a *secondary* "designer" LLM is bound with a `render_a2ui` tool
and forced to emit a tool call via ``tool_choice="render_a2ui"``. Forcing
the tool call gives us strongly-typed output without going through OpenAI's
strict json_schema mode (which can't express the free-form A2UI component
tree). We never execute the tool — we read ``response.tool_calls[0]["args"]``
and wrap them in v0.9 ops via ``copilotkit.a2ui``.

The component schema, generation guidelines, and design guidelines all
flow from the React frontend (via ``A2UICatalog`` / ``useAgentContext``)
into ``state["ag-ui"]["context"]`` and ``state["ag-ui"]["a2ui_schema"]``,
mirroring ``_build_context_prompt`` in the dojo example.

Wire format (no Node middleware in our stack): the planner emits an
``AIMessage`` with a ``tool_calls`` entry plus a paired ``ToolMessage``
whose content is ``a2ui.render(ops)`` (a JSON string with the
``a2ui_operations`` envelope). The frontend parses the latest
``ToolMessage`` with ``name="render_a2ui"``.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any

from copilotkit import a2ui as ck_a2ui
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool as lc_tool

from app.graph.a2ui_builder import (
    ALLOWED_COMPONENTS,
    click_only_rules,
    fallback_component_schema,
)
# `_emit_render_messages` and `_llm_design_question` use copilotkit.a2ui
# directly to mirror the dojo `a2ui_dynamic_schema` example.
from app.graph.nodes.field_helper import REMAINING_FIELD_SCHEMA, missing_field_paths
from app.graph.state import AgentState, UseCaseQuestion
from app.tools.form_api import FormApi


@lc_tool
def render_a2ui(
    surfaceId: str,
    catalogId: str,
    intent: str,
    components: list[dict],
    data: dict | None = None,
) -> str:
    """Render a dynamic A2UI v0.9 surface for a single use-case question.

    Args:
        surfaceId: Unique surface identifier (e.g. "use-case-question").
        catalogId: A2UI catalog id, e.g. the basic catalog URL.
        intent: Short snake_case label for the use-case topic — used to
            avoid asking the same topic twice (e.g. "uptime_target",
            "workload_kind", "data_sensitivity").
        components: A2UI v0.9 component array. Root id MUST be "root".
        data: Optional initial data model (e.g. ``{"answer": null}`` so
            input ``value`` paths bind cleanly).
    """
    # Body is never executed — we read response.tool_calls[0]["args"] in
    # the planner. Mirroring the dojo pattern.
    return "rendered"


@dataclass
class _DesignerOutput:
    intent: str
    components: list[dict[str, Any]]
    data: dict[str, Any]


def _initial_user_prompt(messages: list) -> str:
    for m in messages or []:
        if isinstance(m, HumanMessage):
            content = m.content if isinstance(m.content, str) else str(m.content)
            if content.startswith("__A2UI_ACTION__"):
                continue
            return content
    return ""


def _validate_components(components: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    """Reject component trees that use disallowed components or omit the
    submit Button. Returns the (unchanged) tree on success, None on failure."""
    if not isinstance(components, list) or not components:
        return None

    ok = True
    saw_submit = False

    def _walk(node: Any) -> None:
        nonlocal ok, saw_submit
        if not ok or not isinstance(node, dict):
            return
        comp = node.get("component")
        if comp not in ALLOWED_COMPONENTS:
            ok = False
            return
        if comp == "Button":
            event = (node.get("action") or {}).get("event") or {}
            if event.get("name") == "submit":
                saw_submit = True
        children = node.get("children")
        if isinstance(children, list):
            for c in children:
                _walk(c)
        elif isinstance(children, dict):
            _walk(children)

    for n in components:
        _walk(n)

    if not ok or not saw_submit:
        return None
    return components


def _build_context_prompt(state: AgentState) -> str:
    """Assemble client-supplied context entries — generation guidelines,
    design guidelines, A2UI component schema — into the secondary LLM's
    system prompt. Mirrors the dojo's ``_build_context_prompt``.
    """
    ag_ui = state.get("ag-ui") if isinstance(state, dict) else None
    if not isinstance(ag_ui, dict):
        ag_ui = {}

    parts: list[str] = []
    for entry in ag_ui.get("context", []) or []:
        if isinstance(entry, dict):
            desc = entry.get("description")
            value = entry.get("value")
        else:
            desc = getattr(entry, "description", None)
            value = getattr(entry, "value", None)
        if value is None:
            continue
        parts.append(f"## {desc}\n{value}\n" if desc else f"{value}\n")

    schema = ag_ui.get("a2ui_schema")
    if isinstance(schema, str) and schema.strip():
        parts.append(f"## Available Components\n{schema}\n")
    elif not parts:
        # Bare-curl fallback so the planner stays useful when no React
        # frontend is mounting A2UICatalog.
        parts.append(f"## Available Components\n{fallback_component_schema()}\n")

    return "\n".join(parts)


def _domain_rules(missing_paths: list[str], use_case_answers: list[dict[str, Any]]) -> str:
    asked_intents = [a.get("intent") for a in use_case_answers if a.get("intent")]
    fields_left = [
        {"path": p, "schema": REMAINING_FIELD_SCHEMA.get(p, {})}
        for p in missing_paths
    ]
    return (
        "ROLE\n"
        "You are a server provisioning solutions engineer. Your job is to "
        "ask ONE high-value follow-up question about the user's use case "
        "(workload kind, traffic pattern, scale, uptime/SLA target, data "
        "sensitivity, compliance regime, budget posture, geographic "
        "distribution, runtime stack, etc.). NEVER ask the user about a "
        "concrete record field by name like 'how many CPU cores?' or "
        "'which RAID level?' — those are decided internally based on the "
        "use-case answer.\n\n"
        "Pick the next question by considering:\n"
        " 1. What you still don't know about the use case.\n"
        " 2. Which still-unfilled record fields could be inferred from the "
        "answer.\n"
        " 3. Topics already covered (do not repeat an `intent`).\n\n"
        f"Click-only constraint (product policy): use ONLY these "
        f"components from the advertised catalog: "
        f"{', '.join(ALLOWED_COMPONENTS)}. Do NOT use TextField, "
        f"DateTimeInput, or any other typing input.\n\n"
        f"{click_only_rules()}\n\n"
        "When you call the `render_a2ui` tool, set the arguments as "
        "follows:\n"
        " - `surfaceId`: a stable string (e.g. \"use-case-question\").\n"
        " - `catalogId`: \"https://a2ui.org/specification/v0_9/basic_catalog.json\".\n"
        " - `intent`: snake_case label for the topic (e.g. uptime_target).\n"
        " - `components`: the A2UI v0.9 component tree (Card → Column → "
        "   Text + input + submit Button).\n"
        " - `data`: {\"answer\": null}.\n\n"
        f"Topics already asked about (do NOT repeat): "
        f"{json.dumps(asked_intents)}\n\n"
        f"Use-case answers gathered so far:\n"
        f"{json.dumps(use_case_answers, default=str, indent=2)}\n\n"
        f"Record fields still missing (the planner will silently infer "
        f"these from the answer downstream):\n"
        f"{json.dumps(fields_left, default=str, indent=2)[:4000]}"
    )


def _llm_design_question(
    state: AgentState,
    user_prompt: str,
    record: dict,
    use_case_answers: list[dict[str, Any]],
    missing_paths: list[str],
) -> _DesignerOutput | None:
    if not os.environ.get("LLM_PROVIDER"):
        return None
    try:
        from app.llm import get_llm

        llm = get_llm()
    except Exception:
        return None

    # Force the LLM to emit exactly one render_a2ui tool call. This is the
    # "structured output via tool_choice" trick from the dojo example —
    # gives us typed args without OpenAI's strict json_schema mode.
    try:
        designer = llm.bind_tools([render_a2ui], tool_choice="render_a2ui")
    except Exception:
        # Some providers don't support tool_choice — degrade gracefully.
        return None

    context_section = _build_context_prompt(state)
    domain_section = _domain_rules(missing_paths, use_case_answers)
    system_prompt = f"{context_section}\n\n{domain_section}"

    user_content = (
        f"Initial user prompt: {user_prompt or '(none)'}\n\n"
        f"Current record (partial):\n{json.dumps(record, default=str)[:3000]}"
    )

    try:
        response = designer.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
        )
    except Exception:
        return None

    tool_calls = getattr(response, "tool_calls", None) or []
    if not tool_calls:
        return None
    args = tool_calls[0].get("args") or {}

    intent = args.get("intent")
    components = args.get("components")
    data = args.get("data") or {"answer": None}
    if not isinstance(intent, str) or not intent.strip():
        return None
    cleaned = _validate_components(components if isinstance(components, list) else [])
    if cleaned is None:
        return None
    if not isinstance(data, dict):
        data = {"answer": None}
    return _DesignerOutput(intent=intent.strip(), components=cleaned, data=data)


def _emit_render_messages(
    surface_id: str, ops: list[dict[str, Any]]
) -> list[Any]:
    """Wire the planner's surface to the frontend by emitting a
    AIMessage(tool_calls) + ToolMessage(content) pair, mirroring what the
    dojo agent's ToolNode produces. The ToolMessage content is the
    canonical ``{"a2ui_operations": [...]}`` JSON envelope.
    """
    tool_call_id = f"call_{uuid.uuid4().hex[:12]}"
    tool_call = {
        "id": tool_call_id,
        "name": "render_a2ui",
        "args": {"surfaceId": surface_id},
    }
    rendered = ck_a2ui.render(ops)  # JSON string with a2ui_operations
    return [
        AIMessage(content="", tool_calls=[tool_call]),
        ToolMessage(content=rendered, tool_call_id=tool_call_id, name="render_a2ui"),
    ]


def question_planner(state: AgentState) -> dict:
    record_id = state.get("record_id")
    if not record_id:
        return {"done": True}

    with FormApi() as api:
        record = api.get_record(record_id)
        catalog = api.get_catalog(stage=record["stage"])

    required = catalog.get("stageRequiredFields", [])
    missing = missing_field_paths(record, required)
    if not missing:
        return {"pending_use_case_question": None}

    use_case_answers = list(state.get("use_case_answers") or [])
    user_prompt = _initial_user_prompt(state.get("messages") or [])

    designer = _llm_design_question(
        state=state,
        user_prompt=user_prompt,
        record=record,
        use_case_answers=use_case_answers,
        missing_paths=missing,
    )
    if designer is None:
        # No LLM / tool_choice not supported / invalid surface — let the
        # graph proceed; validator will surface the gaps.
        return {"pending_use_case_question": None}

    surface_id = "use-case-question"
    catalog_id = ck_a2ui.BASIC_CATALOG_ID
    ops = [
        ck_a2ui.create_surface(surface_id, catalog_id=catalog_id),
        ck_a2ui.update_components(surface_id, designer.components),
        ck_a2ui.update_data_model(surface_id, designer.data),
    ]
    question_id = str(uuid.uuid4())

    pending: UseCaseQuestion = {
        "question_id": question_id,
        "intent": designer.intent,
        "surface_id": surface_id,
        "a2ui_operations": ops,
    }

    return {
        "pending_use_case_question": pending,
        "messages": _emit_render_messages(surface_id, ops),
    }
