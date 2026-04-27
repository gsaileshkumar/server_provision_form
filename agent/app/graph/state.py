from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages

Mode = Literal["A", "B"]
Stage = Literal["estimate", "proposal", "provisioning"]


class UseCaseQuestion(TypedDict, total=False):
    """A use-case question rendered as a dynamic A2UI surface.

    The planner decides what to ask next based on the user's prompt and the
    current record state. The question never asks for a record field by name;
    it asks about the user's *intent* (workload, scale, HA, compliance, etc.)
    and the field_inferrer maps the answer to one or more record fields.
    """

    question_id: str
    intent: str  # short label used by extractor / inferrer to group answers
    surface_id: str
    a2ui_operations: list[dict[str, Any]]


class AgentState(TypedDict, total=False):
    """State shared across LangGraph nodes.

    ``messages`` uses ``add_messages`` reducer so user/AI turns append rather
    than replace.
    """

    messages: Annotated[list, add_messages]
    mode: Mode
    stage: Stage
    record_id: Optional[str]
    record_name: Optional[str]
    # The active use-case question. While populated, the chat awaits a
    # structured A2UI action from the user (form submission via a Button).
    pending_use_case_question: Optional[UseCaseQuestion]
    # Append-only history of (intent, answer) pairs the user has provided so
    # the planner can avoid asking the same use-case topic twice.
    use_case_answers: list[dict[str, Any]]
    # Populated by validator node after calling /validate.
    last_validation: dict
    # True while the reviewer has posted a summary and is waiting for an
    # explicit approval / edit instruction from the user.
    review_pending: Optional[bool]
    # Populated by submitter node.
    submitted_record: Optional[dict]
    # Terminal marker so the graph can END without requiring a user turn.
    done: Optional[bool]
