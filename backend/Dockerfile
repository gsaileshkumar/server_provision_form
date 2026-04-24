# ---- Stage 1: build the React SPA ----
FROM node:20-alpine AS frontend-builder

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Flask API + compiled SPA ----
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/run.py ./
COPY backend/app/ ./app/

# Flask serves the SPA from app/static/ (SPA fallback handled in app/__init__.py)
COPY --from=frontend-builder /build/dist/ ./app/static/

EXPOSE 5001

CMD ["uv", "run", "python", "run.py"]
