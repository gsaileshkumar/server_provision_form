"""Build the LangGraph ReAct agent wired to an OpenAI-spec LLM."""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from server_agent.tools import TOOLS

SYSTEM_PROMPT = """You are a helpful server provisioning assistant.

You help users size and price a server before they fill out the official form.
Use the available tools to:
  * tell users which options are valid for a field (e.g. OS, server type),
  * list the fields you know about, and
  * compute a monthly cost estimate once you have enough information.

Always call `get_field_options` when the user asks what values are allowed for
a field. Always call `estimate_server_cost` to produce a price; never guess
the math yourself. If a required value is missing, ask the user for it
before calling the estimator.
"""


def build_agent(model: str | None = None):
    """Create the LangGraph ReAct agent.

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
    return create_react_agent(llm, tools=TOOLS, prompt=SYSTEM_PROMPT)
