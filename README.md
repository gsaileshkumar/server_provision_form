# Smart Server Provisioning Assistant

Web app for producing server provisioning specs across a three-stage workflow (Estimate → Proposal → Provisioning), with an integrated LangGraph agent. No real infrastructure is provisioned; the output is a set of structured records.

## Layout

| Path | Purpose |
| --- | --- |
| `backend/` | Flask Form API (Pydantic v2, PyMongo) |
| `agent/` | FastAPI + LangGraph agent service |
| `frontend/` | Vite + React + TypeScript UI (form + CopilotKit chat) |
| `docker-compose.yml` | MongoDB, form API, agent (all three services) |

## Prerequisites

- Docker + Docker Compose
- Node.js 20+ (frontend dev server only)

## Quick start (Docker)

Copy the example env file and fill in your LLM credentials, then start everything with one command:

```bash
cp .env.example .env
# Edit .env — set LLM_PROVIDER, LLM_MODEL, LLM_API_KEY

docker compose up --build
```

| Service | URL |
| --- | --- |
| Form API | http://localhost:5001 |
| Agent | http://localhost:5002 |
| MongoDB | localhost:27017 |
| Mongo Express (DB UI) | http://localhost:8081 |

To run just the databases without rebuilding the app images:

```bash
docker compose up mongo mongo-express
```

## Frontend dev server

The React UI is not included in Docker Compose (it runs under Vite HMR locally). Start it separately:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173

# CopilotKit Node runtime bridge (required for the agent chat panel)
npm run runtime    # http://localhost:5003
```

Vite proxies `/api` → `:5001`, `/agent` → `:5002`, and `/copilotkit` → `:5003`, so the frontend always talks to `localhost` regardless of whether the backends run in Docker or bare-metal.

## Local bare-metal bring-up (without Docker)

If you prefer to run the Python services outside containers:

```bash
# 1. MongoDB only
docker compose up -d mongo

# 2. Form API (port 5001)
cd backend && uv sync && uv run python run.py

# 3. Agent (port 5002)
cd agent && uv sync && uv run python run.py

# 4. Frontend (port 5173) + runtime bridge (port 5003) — two terminals
cd frontend && npm install && npm run dev
cd frontend && npm run runtime
```

## Environment variables

See `.env.example` for all options.

| Variable | Required | Description |
| --- | --- | --- |
| `MONGO_URI` | no | Defaults to `mongodb://localhost:27017` |
| `MONGO_DB` | no | Database name, defaults to `server_provision` |
| `FORM_API_URL` | no | Agent → Form API base URL, defaults to `http://localhost:5001` |
| `LLM_PROVIDER` | **yes** (agent) | `anthropic` or `openai` |
| `LLM_MODEL` | **yes** (agent) | e.g. `claude-sonnet-4-6` |
| `LLM_API_KEY` | **yes** (agent) | Provider API key |

The agent factory raises immediately on start-up if any `LLM_*` variable is missing.

## Workflow overview

1. **Estimate** — create a record and answer the agent's questions (Mode A) or fill the form manually.
2. **Proposal** — promote the locked Estimate; refine hardware, OS, and application choices.
3. **Provisioning** — promote the locked Proposal; the agent switches to Mode B (read-only Q&A + explicit edits only).

At any stage, click **Export JSON** or visit `/records/:id/summary` for a printable JSON summary including a pricing breakdown.
