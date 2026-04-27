# Server Provisioning Agent

A minimal LangChain v1 / [LangGraph](https://github.com/langchain-ai/langgraph)
agent (built with `langchain.agents.create_agent`) that helps a user size and
price a server before they fill out the provisioning form. The agent is wired
to an OpenAI-spec chat model (so it works with OpenAI, Azure OpenAI, Ollama,
vLLM, OpenRouter, etc.) and a small set of dummy tools backed by a hardcoded
catalog.

## Tools

| Tool | What it does |
| --- | --- |
| `list_supported_fields` | Returns every field the agent understands. |
| `get_field_options(field)` | Returns valid values for a field. For example `os` -> `["Linux", "Windows"]`, `server_type` -> `["Physical", "Virtual"]`. |
| `estimate_server_cost(...)` | Validates a configuration against the catalog and returns a monthly cost estimate with breakdown. |

The catalog lives in `src/server_agent/config.py`; tweak it freely.

## Setup

This project uses [`uv`](https://docs.astral.sh/uv/).

```bash
cd agent
uv sync
cp .env.example .env   # then fill in OPENAI_API_KEY (and optionally OPENAI_BASE_URL)
```

## Run the REPL

```bash
uv run server-agent
```

Example session:

```
you> what os options can i pick?
agent> You can pick Linux or Windows.
you> price a virtual linux box, 8 cores, 32gb ram, 250gb disk, eu-central
agent> A Virtual Linux server with 8 cores / 32 GB / 250 GB in eu-central is
       about $169.05 per month.
```

## Versions

Pinned to the latest releases as of April 2026:

* `langgraph >= 1.1.9`
* `langchain >= 1.2.15`
* `langchain-openai >= 1.2.1`
