# Smart Server Provisioning Assistant

Web app for producing server provisioning specs across a three-stage workflow (Estimate → Proposal → Provisioning), with an integrated LangGraph agent. No real infrastructure is provisioned; the output is a set of structured records.

See `/root/.claude/plans/1-project-overview-the-whimsical-crane.md` for the full design doc.

## Layout

| Path | Purpose |
| --- | --- |
| `backend/` | Flask Form API (Pydantic v2, PyMongo), Phase 1 |
| `agent/` | FastAPI + LangGraph agent service, Phase 2 |
| `frontend/` | Vite + React + TypeScript UI (form + CopilotKit embed) |
| `docker-compose.yml` | Local MongoDB (+ mongo-express at `:8081`) |

## Prerequisites

- Docker + Docker Compose
- Python 3.11+ with `uv`
- Node.js 20+

## Bring-up

```bash
cp .env.example .env

# 1. MongoDB
docker compose up -d mongo

# 2. Form API (port 5001)
cd backend
uv sync
uv run python run.py

# 3. Agent (port 5002) — requires LLM_* env vars
cd agent
uv sync
uv run python run.py

# 4. Frontend (port 5173)
cd frontend
npm install
npm run dev
```

## Environment Variables

See `.env.example`. The agent service requires `LLM_PROVIDER`, `LLM_MODEL`, and `LLM_API_KEY`; the factory fails fast if any are missing.

## Development Branch

All work is on `claude/smart-server-provisioning-MWpLD`.
