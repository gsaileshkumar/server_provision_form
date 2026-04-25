from __future__ import annotations

import os
import time
import uuid
from functools import lru_cache
from typing import Optional

from ag_ui_langgraph import LangGraphAgent
from ag_ui_langgraph.endpoint import add_langgraph_fastapi_endpoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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


# Expose the compiled LangGraph over AG-UI protocol. The Node CopilotKit
# runtime connects to this via LangGraphHttpAgent; the React SDK talks to
# the Node runtime. We use ag_ui_langgraph directly (not the CopilotKit
# Python SDK's add_fastapi_endpoint) because CopilotRuntime 1.56.2's
# `remoteEndpoints` with `copilotKitEndpoint` is a no-op for agents
# (see copilot-runtime.ts assignEndpointsToAgents) — the supported path is
# AG-UI HTTP + the `agents` config on the Node runtime.
_agui_agent = LangGraphAgent(
    name="provisioning_agent",
    description=(
        "Smart server provisioning assistant. In Mode A (estimate/"
        "proposal) it drives the conversation to build a record; in "
        "Mode B (provisioning) it answers questions and edits fields "
        "only on explicit user instruction."
    ),
    graph=_graph(),
)
add_langgraph_fastapi_endpoint(app, _agui_agent, path="/agui/provisioning_agent")


@app.get("/health")
def health():
    return {"status": "ok", "service": "agent"}


@app.get("/llm/ping")
def llm_ping():
    """Smoke-test the configured LLM end-to-end. Calls get_llm().invoke([...])
    with a trivial prompt so the user can confirm their LLM_PROVIDER /
    LLM_MODEL / LLM_API_KEY env vars work without driving a full chat
    conversation. Surfaces in the provider's usage dashboard."""
    provider = os.environ.get("LLM_PROVIDER")
    model = os.environ.get("LLM_MODEL")
    try:
        from app.llm import get_llm

        llm = get_llm()
        start = time.perf_counter()
        resp = llm.invoke(
            [
                {"role": "system", "content": "Respond with exactly one word: pong"},
                {"role": "user", "content": "ping"},
            ]
        )
        latency_ms = round((time.perf_counter() - start) * 1000)
        content = resp.content if hasattr(resp, "content") else str(resp)
        return {
            "status": "ok",
            "provider": provider,
            "model": model,
            "response": content if isinstance(content, str) else str(content),
            "latency_ms": latency_ms,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "provider": provider,
                "model": model,
                "error": f"{type(e).__name__}: {e}",
            },
        )

#
# class StartRequest(BaseModel):
#     stage: str = "estimate"
#     record_id: Optional[str] = None
#     record_name: Optional[str] = None
#
#
# class StartResponse(BaseModel):
#     thread_id: str
#     state: dict
#
#
# class MessageRequest(BaseModel):
#     content: str
#
#
# class AgentTurn(BaseModel):
#     thread_id: Optional[str] = None
#     messages: list[dict]
#     record_id: Optional[str] = None
#     stage: Optional[str] = None
#     mode: Optional[str] = None
#     last_validation: Optional[dict] = None
#     pending_questions: list[dict] = []
#     pending_batch: Optional[dict] = None
#
#
# def _serialize_messages(messages: list) -> list[dict]:
#     out = []
#     for m in messages:
#         if isinstance(m, HumanMessage):
#             out.append({"role": "user", "content": m.content})
#         elif isinstance(m, AIMessage):
#             out.append({"role": "assistant", "content": m.content})
#         else:
#             out.append({"role": getattr(m, "type", "system"), "content": getattr(m, "content", "")})
#     return out
#
#
# def _snapshot_to_turn(snapshot) -> AgentTurn:
#     values: AgentState = snapshot.values  # type: ignore[assignment]
#     return AgentTurn(
#         messages=_serialize_messages(values.get("messages", [])),
#         record_id=values.get("record_id"),
#         stage=values.get("stage"),
#         mode=values.get("mode"),
#         last_validation=values.get("last_validation"),
#         pending_questions=list(values.get("pending_questions") or []),
#         pending_batch=values.get("pending_batch"),
#     )
#
#
# @app.post("/threads/start", response_model=AgentTurn)
# def start_thread(req: StartRequest):
#     thread_id = str(uuid.uuid4())
#     config = {"configurable": {"thread_id": thread_id}}
#     initial: AgentState = {
#         "stage": req.stage,  # type: ignore[typeddict-item]
#         "record_id": req.record_id,
#         "record_name": req.record_name,
#     }
#     _graph().invoke(initial, config=config)
#     snap = _graph().get_state(config)
#     turn = _snapshot_to_turn(snap)
#     turn.thread_id = thread_id
#     return turn
#
#
# @app.post("/threads/{thread_id}/message", response_model=AgentTurn)
# def send_message(thread_id: str, req: MessageRequest):
#     config = {"configurable": {"thread_id": thread_id}}
#     _graph().invoke(
#         {"messages": [HumanMessage(content=req.content)]},
#         config=config,
#     )
#     return _snapshot_to_turn(_graph().get_state(config))
#
#
# @app.get("/threads/{thread_id}", response_model=AgentTurn)
# def get_thread(thread_id: str):
#     config = {"configurable": {"thread_id": thread_id}}
#     return _snapshot_to_turn(_graph().get_state(config))
