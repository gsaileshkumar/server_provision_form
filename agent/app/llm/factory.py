from __future__ import annotations

import os
from functools import lru_cache

from langchain_core.language_models import BaseChatModel


class LLMConfigError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Return the configured chat model. Fails fast if env vars are missing.

    Required env vars:
      - LLM_PROVIDER : "anthropic" | "openai"
      - LLM_MODEL    : model id (e.g. "claude-sonnet-4-6", "gpt-4o")
      - LLM_API_KEY  : provider API key
    """
    provider = os.environ.get("LLM_PROVIDER")
    if not provider:
        raise LLMConfigError(
            "LLM_PROVIDER is required. Set it to one of: anthropic, openai."
        )
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise LLMConfigError("LLM_MODEL is required.")
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise LLMConfigError("LLM_API_KEY is required.")

    timeout = int(os.environ.get("LLM_TIMEOUT", "30"))
    provider = provider.lower()
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, api_key=api_key, temperature=0, timeout=timeout)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=api_key, temperature=0, timeout=timeout)

    raise LLMConfigError(
        f"Unknown LLM_PROVIDER {provider!r}. Supported: anthropic, openai."
    )
