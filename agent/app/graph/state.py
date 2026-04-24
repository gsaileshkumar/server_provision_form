from __future__ import annotations

from typing import Annotated, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages

Mode = Literal["A", "B"]
Stage = Literal["estimate", "proposal", "provisioning"]


class Question(TypedDict, total=False):
    """A planned question grouped into structured options where possible."""

    path: str  # dotted field path, e.g. "hardware.workloadProfile"
    prompt: str  # human-readable prompt
    options: list[str]  # structured options, if any
    kind: Literal["select", "number", "text", "boolean"]


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
    pending_questions: list[Question]
    # Scratch buffer for field values the user has answered but haven't yet
    # been PATCHed back to the Form API. Kept for debugging.
    extracted: dict
    # Populated by validator node after calling /validate.
    last_validation: dict
    # True while the reviewer has posted a summary and is waiting for an
    # explicit approval / edit instruction from the user.
    review_pending: Optional[bool]
    # Populated by submitter node.
    submitted_record: Optional[dict]
    # Terminal marker so the graph can END without requiring a user turn.
    done: Optional[bool]
