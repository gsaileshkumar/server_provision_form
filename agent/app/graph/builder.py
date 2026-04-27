from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from app.graph.nodes.extractor import extractor
from app.graph.nodes.field_helper import field_helper
from app.graph.nodes.field_inferrer import field_inferrer
from app.graph.nodes.intake import intake
from app.graph.nodes.question_planner import question_planner
from app.graph.nodes.recommender import recommender
from app.graph.nodes.reviewer import reviewer
from app.graph.nodes.submitter import submitter
from app.graph.nodes.ui_updater import detect_edit, ui_updater
from app.graph.nodes.validator import validator
from app.graph.state import AgentState

_APPROVE_TOKENS = {"approve", "approved", "submit", "yes", "looks good", "lgtm"}


def _last_human_content(state: AgentState) -> str:
    for m in reversed(state.get("messages") or []):
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


def _is_approval(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(tok == t or t.startswith(tok) for tok in _APPROVE_TOKENS)


def _route_after_intake(state: AgentState) -> str:
    """On a fresh thread, intake runs without human input and we go straight
    to the question_planner. On a continuing thread, the most recent human
    message is routed based on mode + review state + whether there's a
    pending a2ui form awaiting an answer."""
    messages = state.get("messages") or []
    last_is_human = bool(messages) and isinstance(messages[-1], HumanMessage)
    mode = state.get("mode")

    if mode == "B":
        if not last_is_human:
            return END
        text = _last_human_content(state)
        if detect_edit(text):
            return "ui_updater"
        return "field_helper"

    if last_is_human and state.get("review_pending"):
        if _is_approval(_last_human_content(state)):
            return "submitter"
        return "edit_router"

    if last_is_human and state.get("pending_use_case_question"):
        return "extractor"

    return "question_planner"


def _route_after_extractor(state: AgentState) -> str:
    """The extractor always either consumes the pending question (clearing
    it) or leaves it in place. If it cleared it, advance through the
    silent inference + recommender chain. If it didn't (the user typed free
    text), END so the frontend keeps showing the same form."""
    if state.get("pending_use_case_question"):
        return END
    return "field_inferrer"


def _route_after_question_planner(state: AgentState) -> str:
    if state.get("pending_use_case_question"):
        return END  # wait for the user to submit the a2ui form
    return "validator"


def _route_after_validator(state: AgentState) -> str:
    result = state.get("last_validation") or {}
    if result.get("errors"):
        # Validator surfaced errors; END so the user can see them. Their next
        # turn will route through the planner again, which may ask another
        # use-case question or skip to validator if nothing else can be
        # asked.
        return END
    return "reviewer"


def _edit_router(state: AgentState) -> dict:
    """Clear review_pending when the user asks for a change after review."""
    return {"review_pending": False}


def build_graph(checkpointer=None):
    """Mode-A graph (estimate/proposal): drive a use-case-driven Q&A,
    silently infer record fields, validate, review with approval gate,
    submit. Mode-B routes through field_helper / ui_updater."""
    g = StateGraph(AgentState)
    g.add_node("intake", intake)
    g.add_node("question_planner", question_planner)
    g.add_node("extractor", extractor)
    g.add_node("field_inferrer", field_inferrer)
    g.add_node("recommender", recommender)
    g.add_node("validator", validator)
    g.add_node("reviewer", reviewer)
    g.add_node("submitter", submitter)
    g.add_node("edit_router", _edit_router)
    g.add_node("field_helper", field_helper)
    g.add_node("ui_updater", ui_updater)

    g.add_edge(START, "intake")
    g.add_conditional_edges(
        "intake",
        _route_after_intake,
        {
            "extractor": "extractor",
            "question_planner": "question_planner",
            "submitter": "submitter",
            "edit_router": "edit_router",
            "field_helper": "field_helper",
            "ui_updater": "ui_updater",
            END: END,
        },
    )
    g.add_conditional_edges(
        "extractor",
        _route_after_extractor,
        {"field_inferrer": "field_inferrer", END: END},
    )
    g.add_edge("field_inferrer", "recommender")
    g.add_edge("recommender", "question_planner")
    g.add_conditional_edges(
        "question_planner",
        _route_after_question_planner,
        {"validator": "validator", END: END},
    )
    g.add_conditional_edges(
        "validator",
        _route_after_validator,
        {"reviewer": "reviewer", END: END},
    )
    g.add_edge("reviewer", END)
    g.add_edge("submitter", END)
    g.add_edge("edit_router", "question_planner")
    g.add_edge("field_helper", END)
    g.add_edge("ui_updater", END)

    return g.compile(checkpointer=checkpointer)
