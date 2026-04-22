from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from app.graph.nodes.extractor import extractor
from app.graph.nodes.intake import intake
from app.graph.nodes.question_planner import question_planner
from app.graph.nodes.validator import validator
from app.graph.state import AgentState


def _route_after_intake(state: AgentState) -> str:
    messages = state.get("messages") or []
    has_pending = bool(state.get("pending_questions"))
    last_human = any(isinstance(m, HumanMessage) for m in messages[-1:])
    if has_pending and last_human:
        return "extractor"
    return "question_planner"


def _route_after_extractor(state: AgentState) -> str:
    return "question_planner"


def _route_after_question_planner(state: AgentState) -> str:
    if state.get("pending_questions"):
        # A new question was added; yield control to the user.
        return END
    return "validator"


def build_graph(checkpointer=None):
    """Compile and return the M6 scaffold graph.

    Flow:
      START → intake → (extractor on human reply | question_planner)
      extractor → question_planner
      question_planner → END (if pending question) or → validator → END
    """
    g = StateGraph(AgentState)
    g.add_node("intake", intake)
    g.add_node("question_planner", question_planner)
    g.add_node("extractor", extractor)
    g.add_node("validator", validator)

    g.add_edge(START, "intake")
    g.add_conditional_edges(
        "intake",
        _route_after_intake,
        {"extractor": "extractor", "question_planner": "question_planner"},
    )
    g.add_edge("extractor", "question_planner")
    g.add_conditional_edges(
        "question_planner",
        _route_after_question_planner,
        {"validator": "validator", END: END},
    )
    g.add_edge("validator", END)

    return g.compile(checkpointer=checkpointer)
