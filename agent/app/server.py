from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from app.graph.builder import build_graph
from app.graph.state import AgentState
from app.persistence.checkpointer import get_checkpointer

app = FastAPI(title="Server Provisioning Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def _graph():
    return build_graph(checkpointer=get_checkpointer())


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent"}


class StartRequest(BaseModel):
    stage: str = "estimate"
    record_id: Optional[str] = None
    record_name: Optional[str] = None


class StartResponse(BaseModel):
    thread_id: str
    state: dict


class MessageRequest(BaseModel):
    content: str


class AgentTurn(BaseModel):
    thread_id: Optional[str] = None
    messages: list[dict]
    record_id: Optional[str] = None
    stage: Optional[str] = None
    mode: Optional[str] = None
    last_validation: Optional[dict] = None
    pending_questions: list[dict] = []


def _serialize_messages(messages: list) -> list[dict]:
    out = []
    for m in messages:
        if isinstance(m, HumanMessage):
            out.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            out.append({"role": "assistant", "content": m.content})
        else:
            out.append({"role": getattr(m, "type", "system"), "content": getattr(m, "content", "")})
    return out


def _snapshot_to_turn(snapshot) -> AgentTurn:
    values: AgentState = snapshot.values  # type: ignore[assignment]
    return AgentTurn(
        messages=_serialize_messages(values.get("messages", [])),
        record_id=values.get("record_id"),
        stage=values.get("stage"),
        mode=values.get("mode"),
        last_validation=values.get("last_validation"),
        pending_questions=list(values.get("pending_questions") or []),
    )


@app.post("/threads/start", response_model=AgentTurn)
def start_thread(req: StartRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    initial: AgentState = {
        "stage": req.stage,  # type: ignore[typeddict-item]
        "record_id": req.record_id,
        "record_name": req.record_name,
    }
    _graph().invoke(initial, config=config)
    snap = _graph().get_state(config)
    turn = _snapshot_to_turn(snap)
    turn.thread_id = thread_id
    return turn


@app.post("/threads/{thread_id}/message", response_model=AgentTurn)
def send_message(thread_id: str, req: MessageRequest):
    config = {"configurable": {"thread_id": thread_id}}
    _graph().invoke(
        {"messages": [HumanMessage(content=req.content)]},
        config=config,
    )
    return _snapshot_to_turn(_graph().get_state(config))


@app.get("/threads/{thread_id}", response_model=AgentTurn)
def get_thread(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    return _snapshot_to_turn(_graph().get_state(config))
