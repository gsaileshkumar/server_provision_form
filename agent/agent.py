"""Build the LangGraph agent wired to an OpenAI-spec LLM."""

from __future__ import annotations

import os

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from tools import TOOLS

SYSTEM_PROMPT = """You are an infrastructure assistant.

You help users plan, price, and record infrastructure work using a small set
of tools. You do not know any workflow details up front; instead you discover
them at runtime.

Operating procedure:
1. When the user states a goal, call `list_workflows` to see what playbooks
   exist.
2. Pick the most relevant workflow and call
   `get_workflow_instructions(workflow=...)` to load its detailed steps,
   required inputs, and expected output shape.
3. Follow the returned playbook exactly. Use the tools it names; do not
   invent values, do not guess math, and do not skip validation.
4. Never ask the user for raw configuration field names or technical keys.
   Instead, ask about their application or workload, reason about the best
   configuration yourself, validate it silently with `validate_config`, then
   present a plain-English recommendation for the user to confirm.
5. If a tool returns an `error` payload, surface the problem to the user
   and ask for a correction.

Be concise. Prefer tool calls over prose when the user asks for a concrete
result.
"""


def build_agent(model: str | None = None):
    """Create the LangGraph agent using `langchain.agents.create_agent`.

    The model is any chat model that speaks the OpenAI Chat Completions spec.
    Set `OPENAI_BASE_URL` to point at a compatible gateway (Azure OpenAI,
    Ollama, vLLM, OpenRouter, etc.); `ChatOpenAI` will use it automatically.
    """
    llm = ChatOpenAI(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    return create_agent(model=llm, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
