"""Build the LangGraph agent wired to an OpenAI-spec LLM."""

from __future__ import annotations

import os

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

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
